import datetime
import pandas as pd
from typing import List, Dict, Any, Optional, Callable
import logging
import uuid
import copy
from .metrics import SimulationMetrics
class Order:
    """Represents an intraday trading order for a specific delivery window.
    
    Attributes:
        price (float): Limit price for the order
        quantity (float): Quantity to trade
        contract_time (datetime): Delivery time of the contract
        side (str): 'buy' or 'sell'
        order_id (str): Unique identifier
        submission_time (datetime): When the order was submitted
        status (str): Current order status
        strategy_id (str): Unique identifier for the strategy that submitted the order
        event_type (str): Type of event (submitted, updated, expired, filled, canceled)
    """
    def __init__(self, 
                 price: float, 
                 quantity: float, 
                 contract_time: datetime.datetime, 
                 side: str, 
                 order_id: Optional[str] = None,
                 submission_time: Optional[datetime.datetime] = None,
                 strategy_id: Optional[str] = None):
        if side not in ['buy', 'sell']:
            raise ValueError(f"Side must be 'buy' or 'sell', not {side}")
        
        self.price = price
        self.quantity = quantity
        self.contract_time = contract_time
        self.side = side
        self.order_id = order_id or str(uuid.uuid4())
        self.strategy_id = strategy_id
        self.submission_time = submission_time
        self.status = "active"  # active, filled, canceled, expired
        self.execution_price = None
        self.execution_time = None
        self.update_count = 0
        self.event_type = "submitted"  # submitted, updated, expired, filled, canceled

    def update(self, price: float = None, quantity: float = None):
        """Update order price and/or quantity"""
        if price is not None:
            self.price = price
        if quantity is not None:
            self.quantity = quantity
        self.update_count += 1
        
    def __repr__(self):
        return (f"Order(id={self.order_id}, {self.side}, price={self.price}, "
                f"qty={self.quantity}, contract={self.contract_time}, status={self.status})")


class TradingSimulation:
    """Main simulation engine for intraday electricity trading.
    
    Handles the time loop, order management, and interaction between
    strategies and clearing mechanisms.
    """
    def __init__(self, 
                 start_time: datetime.datetime,
                 end_time: datetime.datetime,
                 time_step: datetime.timedelta,
                 strategies: List[Any] = None,
                 clearing_mechanism: Any = None):
        """Initialize the trading simulation."""
        self.start_time = start_time
        self.end_time = end_time
        self.time_step = time_step
        self.current_time = start_time
        
        self.strategies = strategies or []
        self.clearing_mechanism = clearing_mechanism
        
        self.active_orders: Dict[str, Order] = {}  # order_id -> Order
        self.order_history: List[Order] = []  # List of all processed orders
        
        # Configure logging
        logging.basicConfig(level=logging.INFO, 
                          format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger("TradingSimulation")

    def run(self):
        """Execute the full simulation from start_time to end_time."""
        self.logger.info(f"Starting simulation from {self.start_time} to {self.end_time}")
        
        # Initialize strategies
        for strategy in self.strategies:
            strategy.initialize(self.start_time, self.end_time)
        
        # Main simulation loop
        while self.current_time <= self.end_time:
            self.step()
            
        self.logger.info("Simulation complete")
        return self.get_results()
    
    def step(self):
        """Execute a single time step of the simulation."""
        self.logger.debug(f"Step at {self.current_time}")
        
        # Process expired contracts
        expired_orders = self._expire_contracts()

        # Clear the market
        cleared_orders = []
        if self.clearing_mechanism:
            cleared_orders = self.clearing_mechanism.clear(
                self.current_time, 
                self.active_orders
            )
            self._process_clearing_results(cleared_orders)
        
        # Update strategies with feedback
        expired_by_strategy = self.group_by_strategy_id(expired_orders)
        cleared_by_strategy = self.group_by_strategy_id(cleared_orders)
        active_by_strategy = self.group_by_strategy_id(self.active_orders.values())
        
        # Give each strategy its relevant orders
        for strategy in self.strategies:
            strategy_results = {
                'expired_orders': expired_by_strategy.get(strategy.id, []),
                'cleared_orders': cleared_by_strategy.get(strategy.id, []),
                'active_orders': active_by_strategy.get(strategy.id, [])
            }
            strategy.process_results(strategy_results)

        # Update strats(remove, add, update, give market state)
        for strategy in self.strategies:
            new_orders, updated_orders, canceled_orders = strategy.update_orders(self.current_time)
            self._process_new_orders(new_orders, strategy)
            self._process_updated_orders(updated_orders, strategy)
            self._process_canceled_orders(canceled_orders, strategy)

        # Advance time
        self.current_time += self.time_step

    def group_by_strategy_id(self, orders: List[Order]) -> Dict[str, List[Order]]:
        """Group orders by strategy_id."""
        result = {}
        for order in orders:
            if order.strategy_id not in result:
                result[order.strategy_id] = []
            result[order.strategy_id].append(order)
        return result
    
    def _expire_contracts(self):
        """Expire contracts that have reached delivery time."""
        expired_contracts = []
        for order_id, order in list(self.active_orders.items()):
            # TODO: add variable in config that determines how far ahead a contracts expired
            if order.contract_time < self.current_time:
                # Create history snapshot before changing status
                history_order = copy.deepcopy(order)
                history_order.status = "expired"
                history_order.event_type = "expired"
                history_order.execution_time = self.current_time
                self.order_history.append(history_order)
                
                # Update active order and move to expired
                order.status = "expired"
                order.execution_time = self.current_time
                expired_contracts.append(order)
                self.active_orders.pop(order_id, None)

        return expired_contracts
    
    def _process_clearing_results(self, cleared_orders: List[Order]):
        """Process the results of the clearing mechanism."""
        for order in cleared_orders:
            # Create history snapshot before changing status
            history_order = copy.deepcopy(order)
            history_order.status = "filled"
            history_order.event_type = "filled"
            history_order.execution_time = self.current_time
            self.order_history.append(history_order)
            
            # Update active order and remove
            order.status = "filled"
            order.execution_time = self.current_time
            self.active_orders.pop(order.order_id, None)

    def _process_new_orders(self, new_orders: List[Order], strategy: Any):
        """Process new orders."""
        for order in new_orders:
            # Set submission time if not already set
            if not order.submission_time:
                order.submission_time = self.current_time
            
            # Add order to active orders
            order.event_type = "submitted"
            self.active_orders[order.order_id] = order
            
            # Add to history
            history_order = copy.deepcopy(order)
            self.order_history.append(history_order)

    def _process_updated_orders(self, updated_orders: List[Order], strategy: Any):
        """Process updated orders."""
        for updated_order in updated_orders:
            if updated_order.order_id in self.active_orders:
                # Create a copy of the original order before updating
                original = self.active_orders[updated_order.order_id]
                history_order = copy.deepcopy(original)
                history_order.status = "updated"
                history_order.event_type = "updated"
                history_order.execution_time = self.current_time
                self.order_history.append(history_order)
                
                # Now update the actual order
                updated_order.update_count = original.update_count + 1
                self.active_orders[updated_order.order_id] = updated_order

    def _process_canceled_orders(self, canceled_orders: List[Order], strategy: Any):
        """Process canceled orders."""
        for order_id in canceled_orders:
            if order_id in self.active_orders:
                # Create history snapshot before canceling
                order = self.active_orders[order_id]
                history_order = copy.deepcopy(order)
                history_order.status = "canceled"
                history_order.event_type = "canceled"
                history_order.execution_time = self.current_time
                self.order_history.append(history_order)
                
                # Remove from active orders
                self.active_orders.pop(order_id, None)

    def get_results(self):
        """Return simulation results as a DataFrame."""
        # Convert order history to DataFrame
        if not self.order_history:
            return pd.DataFrame()
            
        records = []
        for order in self.order_history:
            record = {
                'order_id': order.order_id,
                'strategy_id': order.strategy_id,
                'side': order.side,
                'price': order.price,
                'quantity': order.quantity,
                'contract_time': order.contract_time,
                'submission_time': order.submission_time,
                'execution_time': order.execution_time,
                'status': order.status,
                'event_type': order.event_type,
                'update_count': order.update_count,
                'execution_price': order.execution_price
            }
            records.append(record)
            
        return pd.DataFrame(records)

    def analyze(self, metrics: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Run analysis on simulation results by strategy.
        
        Args:
            metrics: List of metric names to calculate. None means run all.
            
        Returns:
            Dictionary of metric results by strategy
        """
        order_history = self.get_results()
        
        calculator = SimulationMetrics(order_history)
        
        if metrics is None:
            return calculator.run_all()
        
        results = {}
        available_metrics = {
            "fill_rate": calculator.fill_rate,
            "time_to_fill": calculator.time_to_fill,
            "contract_volume": calculator.contract_volume,
            "order_status_counts": calculator.order_status_counts,
            "execution_prices": calculator.execution_prices
        }
        
        for metric in metrics:
            if metric in available_metrics:
                results[metric] = available_metrics[metric]()
        
        return results
