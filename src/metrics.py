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
                'mean_seconds': matched_orders['time_to_fill'].mean(),
                'median_seconds': matched_orders['time_to_fill'].median(),
                'min_seconds': matched_orders['time_to_fill'].min(),
                'max_seconds': matched_orders['time_to_fill'].max(),
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
            "execution_prices": self.execution_prices()
        }
