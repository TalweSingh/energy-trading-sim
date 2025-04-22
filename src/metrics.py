import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

class SimulationMetrics:
    """Metrics calculator for trading simulation results, grouped by strategy."""
    
    def __init__(self, order_history: pd.DataFrame):
        """Initialize with order history data.
        
        Args:
            order_history: DataFrame containing order events
        """
        self.order_history = order_history
        
        # Pre-split the data by strategy
        if not order_history.empty:
            self.strategies = order_history['strategy_id'].unique()
            self.order_by_strategy = {
                strategy: order_history[order_history['strategy_id'] == strategy]
                for strategy in self.strategies
            }
        else:
            self.strategies = []
            self.order_by_strategy = {}
    
    def fill_rate(self) -> Dict[str, Dict[str, Any]]:
        """Calculate fill rate by strategy.
        
        Returns:
            Dictionary with fill rates by strategy
        """
        results = {}
        
        for strategy_id, strategy_orders in self.order_by_strategy.items():
            # Count submitted orders
            submitted = strategy_orders[strategy_orders['event_type'] == 'submitted'].shape[0]
            
            # Count filled orders
            filled = strategy_orders[
                (strategy_orders['status'] == 'filled') & 
                (strategy_orders['event_type'] == 'filled')
            ].shape[0]
            
            # Calculate fill rate
            fill_rate = filled / submitted if submitted > 0 else 0
            
            results[strategy_id] = {
                'submitted_orders': submitted,
                'filled_orders': filled,
                'fill_rate': fill_rate
            }
        
        return results
    
    def time_to_fill(self) -> Dict[str, Dict[str, Any]]:
        """Calculate time to fill by strategy.
        
        Returns:
            Dictionary with time-to-fill statistics by strategy
        """
        results = {}
        
        for strategy_id, strategy_orders in self.order_by_strategy.items():
            # Get filled orders
            filled_orders = strategy_orders[
                (strategy_orders['status'] == 'filled') & 
                (strategy_orders['event_type'] == 'filled')
            ]
            
            if filled_orders.empty:
                results[strategy_id] = {'status': 'No filled orders'}
                continue
            
            # Find corresponding submissions
            submissions = strategy_orders[strategy_orders['event_type'] == 'submitted']
            
            # Create mapping of order_id to submission time
            submission_times = submissions.set_index('order_id')['submission_time']
            
            # Match with filled orders
            matched_orders = filled_orders.join(
                submission_times, on='order_id', rsuffix='_submitted'
            )
            
            # Calculate time to fill
            matched_orders['time_to_fill'] = (
                matched_orders['execution_time'] - matched_orders['submission_time']
            ).dt.total_seconds()
            
            # Calculate statistics
            results[strategy_id] = {
                'mean_minutes': matched_orders['time_to_fill'].mean() / 60,
                'median_minutes': matched_orders['time_to_fill'].median() / 60,
                'min_minutes': matched_orders['time_to_fill'].min() / 60,
                'max_minutes': matched_orders['time_to_fill'].max() / 60,
                'count': len(matched_orders)
            }
        
        return results
    
    def contract_volume(self) -> Dict[str, Dict[str, Any]]:
        """Calculate trading volume by strategy and contract time.
        
        Returns:
            Dictionary with volume statistics by strategy
        """
        results = {}
        
        for strategy_id, strategy_orders in self.order_by_strategy.items():
            # Get filled orders
            filled_orders = strategy_orders[
                (strategy_orders['status'] == 'filled') & 
                (strategy_orders['event_type'] == 'filled')
            ]
            
            if filled_orders.empty:
                results[strategy_id] = {'status': 'No filled orders'}
                continue
            
            # Group by contract time
            volume_by_contract = filled_orders.groupby('contract_time')['quantity'].sum()
            
            results[strategy_id] = {
                'total_volume': filled_orders['quantity'].sum(),
                'by_contract': volume_by_contract.to_dict()
            }
        
        return results
    
    def order_status_counts(self) -> Dict[str, Dict[str, Any]]:
        """Count orders by final status for each strategy.
        
        Returns:
            Dictionary with order counts by status and strategy
        """
        results = {}
        
        for strategy_id, strategy_orders in self.order_by_strategy.items():
            # Count orders by status
            status_counts = strategy_orders['status'].value_counts().to_dict()
            
            # Count orders by event type
            event_counts = strategy_orders['event_type'].value_counts().to_dict()
            
            results[strategy_id] = {
                'status_counts': status_counts,
                'event_counts': event_counts,
                'total_orders': len(strategy_orders['order_id'].unique())
            }
        
        return results
    
    def execution_prices(self) -> Dict[str, Dict[str, Any]]:
        """Analyze execution prices by strategy, including VWAP.
        
        Returns:
            Dictionary with price statistics by strategy
        """
        results = {}
        
        for strategy_id, strategy_orders in self.order_by_strategy.items():
            # Get filled orders
            filled_orders = strategy_orders[
                (strategy_orders['status'] == 'filled') & 
                (strategy_orders['event_type'] == 'filled')
            ]
            
            if filled_orders.empty:
                results[strategy_id] = {'status': 'No filled orders'}
                continue
            
            # Calculate basic price statistics
            results[strategy_id] = {
                'mean_price': filled_orders['price'].mean(),
                'median_price': filled_orders['price'].median(),
                'min_price': filled_orders['price'].min(),
                'max_price': filled_orders['price'].max(),
                'std_price': filled_orders['price'].std(),
                'count': len(filled_orders)
            }
            
            # Calculate VWAP (Volume-Weighted Average Price)
            vwap = (filled_orders['price'] * filled_orders['quantity']).sum() / filled_orders['quantity'].sum()
            results[strategy_id]['vwap'] = vwap
            
            # Separate by side
            buy_orders = filled_orders[filled_orders['side'] == 'buy']
            sell_orders = filled_orders[filled_orders['side'] == 'sell']
            
            if not buy_orders.empty:
                buy_vwap = (buy_orders['price'] * buy_orders['quantity']).sum() / buy_orders['quantity'].sum()
                results[strategy_id]['buy'] = {
                    'vwap': buy_vwap,
                    'count': len(buy_orders),
                    'volume': buy_orders['quantity'].sum()
                }
            
            if not sell_orders.empty:
                sell_vwap = (sell_orders['price'] * sell_orders['quantity']).sum() / sell_orders['quantity'].sum()
                results[strategy_id]['sell'] = {
                    'vwap': sell_vwap,
                    'count': len(sell_orders),
                    'volume': sell_orders['quantity'].sum()
                }
        
        return results
    
    def buy_cost(self) -> Dict[str, Dict[str, Any]]:
        """Calculate total buy cost (price × quantity) by strategy.
        
        Returns:
            Dictionary with total buy cost by strategy
        """
        results = {}
        
        for strategy_id, strategy_orders in self.order_by_strategy.items():
            # Get filled buy orders
            filled_buys = strategy_orders[
                (strategy_orders['status'] == 'filled') & 
                (strategy_orders['event_type'] == 'filled') &
                (strategy_orders['side'] == 'buy')
            ]
            
            if filled_buys.empty:
                results[strategy_id] = {'status': 'No filled buy orders'}
                continue
            
            # Calculate total buy cost
            total_cost = (filled_buys['price'] * filled_buys['quantity']).sum()
            total_volume = filled_buys['quantity'].sum()
            
            results[strategy_id] = {
                'total_buy_cost': total_cost,
                'total_buy_volume': total_volume,
                'avg_price': total_cost / total_volume if total_volume > 0 else 0
            }
        
        return results
    
    def volume_execution_rate(self) -> Dict[str, Dict[str, Any]]:
        """Compare intended trading volume vs. actual executed volume.
        
        Returns:
            Dictionary with volume execution statistics by strategy
        """
        results = {}
        
        for strategy_id, strategy_orders in self.order_by_strategy.items():
            # Get submitted orders
            submitted_orders = strategy_orders[strategy_orders['event_type'] == 'submitted']
            
            # Get filled orders 
            filled_orders = strategy_orders[
                (strategy_orders['status'] == 'filled') & 
                (strategy_orders['event_type'] == 'filled')
            ]
            
            if submitted_orders.empty:
                results[strategy_id] = {'status': 'No submitted orders'}
                continue
            
            # Calculate intended and executed volumes
            intended_volume = submitted_orders['quantity'].sum()
            executed_volume = filled_orders['quantity'].sum()
            execution_rate = executed_volume / intended_volume if intended_volume > 0 else 0
            
            results[strategy_id] = {
                'intended_volume': intended_volume,
                'executed_volume': executed_volume,
                'execution_rate': execution_rate
            }
            
            # Split by side
            for side in ['buy', 'sell']:
                side_submitted = submitted_orders[submitted_orders['side'] == side]
                side_filled = filled_orders[filled_orders['side'] == side]
                
                if not side_submitted.empty:
                    side_intended = side_submitted['quantity'].sum()
                    side_executed = side_filled['quantity'].sum() if not side_filled.empty else 0
                    side_rate = side_executed / side_intended if side_intended > 0 else 0
                    
                    results[strategy_id][side] = {
                        'intended_volume': side_intended,
                        'executed_volume': side_executed,
                        'execution_rate': side_rate
                    }
        
        return results
    
    def run_all(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Run all available metrics.
        
        Returns:
            Dictionary with results from all metrics by strategy
        """
        return {
            "fill_rate": self.fill_rate(),
            "time_to_fill": self.time_to_fill(),
            "contract_volume": self.contract_volume(),
            "order_status_counts": self.order_status_counts(),
            "execution_prices": self.execution_prices(),
            "buy_cost": self.buy_cost(),
            "volume_execution_rate": self.volume_execution_rate()
        }
