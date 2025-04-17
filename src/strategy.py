import datetime
import uuid
from typing import List, Dict, Tuple, Any, Optional
from abc import ABC, abstractmethod
from .sim import Order

class Strategy(ABC):
    """Abstract base class for trading strategies.
    
    All trading strategies should inherit from this class and implement
    the required methods.
    """
    
    def __init__(self, strategy_id: Optional[str] = None):
        """Initialize the strategy.
        
        Args:
            strategy_id: Unique identifier for this strategy instance.
                         If not provided, a UUID will be generated.
        """
        self.id = strategy_id or str(uuid.uuid4())
        self.active_orders = {}  # Dictionary of active orders (order_id -> Order)
    
    def initialize(self, start_time: datetime.datetime, end_time: datetime.datetime) -> None:
        """Initialize the strategy with simulation timeframe.
        
        Args:
            start_time: Start time of the simulation
            end_time: End time of the simulation
        """
        self.start_time = start_time
        self.end_time = end_time
    
    @abstractmethod
    def update_orders(self, current_time: datetime.datetime) -> Tuple[List, List, List]:
        """Generate trading decisions for the current time step.
        
        This method is called at each simulation step and should return:
        - new_orders: List of new Order objects to submit
        - updated_orders: List of Order objects to update
        - canceled_orders: List of order_ids to cancel
        
        Args:
            current_time: Current simulation time
            
        Returns:
            Tuple of (new_orders, updated_orders, canceled_order_ids)
        """
        pass
    
    def process_results(self, results: Dict[str, List]) -> None:
        """Process feedback from the simulation.
        
        Args:
            results: Dictionary containing:
                - 'expired_orders': List of orders that expired this step
                - 'cleared_orders': List of orders that cleared this step
                - 'active_orders': List of currently active orders
        """
        # Update the active orders based on what the simulation tells us
        self.active_orders = {order.order_id: order for order in results.get('active_orders', [])}
    
    def create_order(self, price: float, quantity: float, 
                    contract_time: datetime.datetime, side: str) -> Any:
        """Helper method to create a new order with strategy ID.
        
        Args:
            price: Limit price for the order
            quantity: Quantity to trade
            contract_time: Delivery time of the contract
            side: 'buy' or 'sell'
            
        Returns:
            A new Order object
        """
        return Order(
            price=price,
            quantity=quantity,
            contract_time=contract_time,
            side=side,
            strategy_id=self.id
        )
