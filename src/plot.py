import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
import datetime

class SimulationVisualizer:
    """Creates interactive visualizations for trading simulation results using Plotly."""
    
    def __init__(self, metrics: Dict[str, Any], order_history: pd.DataFrame, max_time_to_fill=600):
        """Initialize with metrics and order history.
        
        Args:
            metrics: Dictionary of metrics from sim.analyze()
            order_history: DataFrame with order events
            max_time_to_fill: Maximum time to fill in minutes
        """
        self.metrics = metrics
        self.order_history = order_history
        self.max_time_to_fill = max_time_to_fill
        
        # First analysis of the raw data
        print(f"Order history shape: {order_history.shape}")
        if not order_history.empty:
            # Count unique orders vs. events
            total_events = len(order_history)
            unique_orders = order_history['order_id'].nunique()
            print(f"Total events: {total_events}, Unique orders: {unique_orders}")
            
            # Analyze events by type
            event_counts = order_history['event_type'].value_counts()
            print(f"Event type counts:\n{event_counts}")
            
            # Analyze statuses
            status_counts = order_history['status'].value_counts()
            print(f"Status counts:\n{status_counts}")
            
            # Check metrics fill rate if available
            if self.metrics and 'fill_rate' in self.metrics:
                print("Metrics fill_rate data:")
                for strategy_id, data in self.metrics['fill_rate'].items():
                    print(f"  {strategy_id}: {data}")
            
            # Start with submitted orders only (initial order placement)
            submitted = order_history[order_history['event_type'] == 'submitted']
            self.orders = submitted.copy()
            
            # Find filled orders from the filled events
            filled_events = order_history[
                (order_history['event_type'] == 'filled') & 
                (order_history['status'] == 'filled')
            ]
            filled_order_ids = set(filled_events['order_id'])
            
            # Flag filled orders
            self.orders['is_filled'] = self.orders['order_id'].isin(filled_order_ids)
            
            # Calculate time to fill
            self.orders['time_to_fill'] = float('nan')
            
            # Create a mapping of order_id to fill time
            fill_times = {}
            for _, row in filled_events.iterrows():
                fill_times[row['order_id']] = row['execution_time']
            
            # Apply fill times
            for idx, row in self.orders.iterrows():
                if row['order_id'] in fill_times:
                    fill_time = fill_times[row['order_id']]
                    self.orders.at[idx, 'time_to_fill'] = (fill_time - row['submission_time']).total_seconds() / 60
            
            print("\nFill counts by strategy:")
            for strategy in self.orders['strategy_id'].unique():
                strat_orders = self.orders[self.orders['strategy_id'] == strategy]
                filled = strat_orders['is_filled'].sum()
                total = len(strat_orders)
                print(f"  {strategy}: {filled}/{total} ({filled/total:.1%} filled)")
    
    def plot_buy_orders(self, strategy_id=None, title=None):
        """Plot buy orders showing filled vs unfilled with time properties.
        
        Args:
            strategy_id: Optional strategy ID to filter by
            title: Optional custom title for the plot
            
        Returns:
            Plotly figure
        """
        if self.order_history.empty:
            return go.Figure().update_layout(
                title="No order data available",
                xaxis_title="Contract Time",
                yaxis_title="Price in €"
            )
        
        # Filter orders if strategy_id provided
        orders = self.orders
        if strategy_id is not None:
            orders = orders[orders['strategy_id'] == strategy_id]
        
        # Filter buy orders only
        buy_orders = orders[orders['side'] == 'buy']
        if buy_orders.empty:
            return go.Figure().update_layout(
                title="No buy orders available",
                xaxis_title="Contract Time",
                yaxis_title="Price in €"
            )
        
        fig = go.Figure()
        
        # Filled buy orders
        filled_buys = buy_orders[buy_orders['is_filled']]
        if not filled_buys.empty:
            fig.add_trace(go.Scatter(
                x=filled_buys['contract_time'],
                y=filled_buys['price'],
                mode='markers',
                marker=dict(
                    size=filled_buys['quantity'] * 2,  # Scale by quantity
                    color=filled_buys['time_to_fill'],
                    colorscale='Viridis',
                    colorbar=dict(title="Time to Fill (min)"),
                    symbol='triangle-up'
                ),
                name='Filled Buy Orders',
                hovertemplate=(
                    '<b>Buy Order</b><br>' +
                    'Price: %{y:.2f}<br>' +
                    'Delivery Time: %{x}<br>' +
                    'Filled: Yes<br>' +
                    'Submission: %{customdata[1]}<br>' +
                    'Time to Fill: %{customdata[2]:.0f} sec<br>' +
                    'Quantity: %{customdata[3]}'
                ),
                customdata=np.column_stack((
                    filled_buys['strategy_id'],
                    filled_buys['submission_time'].dt.strftime('%Y-%m-%d %H:%M'),
                    filled_buys['time_to_fill'],
                    filled_buys['quantity']
                ))
            ))
        
        # Unfilled buy orders
        unfilled_buys = buy_orders[~buy_orders['is_filled']]
        if not unfilled_buys.empty:
            fig.add_trace(go.Scatter(
                x=unfilled_buys['contract_time'],
                y=unfilled_buys['price'],
                mode='markers',
                marker=dict(
                    size = 12,
                    opacity=1.0,
                    color='black',
                    symbol='triangle-down',
                ),
                name='Unfilled Buy Orders',
                hovertemplate=(
                    '<b>Buy Order</b><br>' +
                    'Price: %{y:.2f}<br>' +
                    'Delivery Time: %{x}<br>' +
                    'Filled: No<br>' +
                    'Volume: %{customdata[2]}<br>' +
                    'Submission: %{customdata[1]}'
                ),
                customdata=np.column_stack((
                    unfilled_buys['strategy_id'],
                    unfilled_buys['submission_time'].dt.strftime('%Y-%m-%d %H:%M'),
                    unfilled_buys['quantity']
                ))
            ))
        
        if title:
            plot_title = title
        else:
            plot_title = "Buy Order Placement"
            if strategy_id:
                plot_title += f" - Strategy: {strategy_id}"
        
        fig.update_layout(
            title=plot_title,
            xaxis_title="Contract Time",
            yaxis_title="Price in €/MWh",
            legend_title="Order Status",
            hovermode="closest",
            legend=dict(
                x=1.15,
                y=0.5,
                xanchor="left",
                yanchor="middle",
                bordercolor="black",
                borderwidth=1,
                bgcolor="white"
            )
        )
        
        hovertemplate = (
            "Price: %{y:.2f}<br>" +
            "Delivery Time: %{x}<br>" +
            "Status: %{customdata[0]}<br>" +
            "Time to Fill: %{marker.color} minutes<br>" +
            "<extra></extra>"
        )
        
        fig.update_traces(
            marker=dict(size=12),
            opacity=1.0,
            hovertemplate=hovertemplate
        )
        
        # Update colorscale to start at 0 with configurable max (default 600)
        fig.update_traces(
            marker=dict(
                colorscale="Viridis",
                cmin=0,
                cmax=self.max_time_to_fill if hasattr(self, 'max_time_to_fill') else 600,
            )
        )
        
        fig.update_xaxes(title_text="Delivery Time")
        
        return fig
    
    def plot_sell_orders(self, strategy_id=None, title=None):
        """Plot sell orders showing filled vs unfilled with time properties.
        
        Args:
            strategy_id: Optional strategy ID to filter by
            title: Optional custom title for the plot
            
        Returns:
            Plotly figure
        """
        if self.order_history.empty:
            return go.Figure().update_layout(
                title="No order data available",
                xaxis_title="Contract Time",
                yaxis_title="Price"
            )
        
        # Filter orders if strategy_id provided
        orders = self.orders
        if strategy_id is not None:
            orders = orders[orders['strategy_id'] == strategy_id]
        
        # Filter sell orders only
        sell_orders = orders[orders['side'] == 'sell']
        if sell_orders.empty:
            return go.Figure().update_layout(
                title="No sell orders available",
                xaxis_title="Contract Time",
                yaxis_title="Price"
            )
        
        fig = go.Figure()
        
        # Filled sell orders
        filled_sells = sell_orders[sell_orders['is_filled']]
        if not filled_sells.empty:
            fig.add_trace(go.Scatter(
                x=filled_sells['contract_time'],
                y=filled_sells['price'],
                mode='markers',
                marker=dict(
                    size=filled_sells['quantity'] * 2,  # Scale by quantity
                    color=filled_sells['time_to_fill'],
                    colorscale='Viridis',
                    colorbar=dict(title="Minutes until order was filled"),
                    symbol='triangle-up'
                ),
                name='Filled Sell Orders',
                hovertemplate=(
                    '<b>Sell Order</b><br>' +
                    'Price: %{y:.2f}<br>' +
                    'Contract Time: %{x}<br>' +
                    'Filled: Yes<br>' +
                    'Strategy: %{customdata[0]}<br>' +
                    'Submission: %{customdata[1]}<br>' +
                    'Time to Fill: %{customdata[2]:.0f} sec<br>' +
                    'Quantity: %{customdata[3]}'
                ),
                customdata=np.column_stack((
                    filled_sells['strategy_id'],
                    filled_sells['submission_time'].dt.strftime('%Y-%m-%d %H:%M'),
                    filled_sells['time_to_fill'],
                    filled_sells['quantity']
                ))
            ))
        
        # Unfilled sell orders
        unfilled_sells = sell_orders[~sell_orders['is_filled']]
        if not unfilled_sells.empty:
            fig.add_trace(go.Scatter(
                x=unfilled_sells['contract_time'],
                y=unfilled_sells['price'],
                mode='markers',
                marker=dict(
                    size=unfilled_sells['quantity'] * 2,  # Scale by quantity
                    color='rgba(255, 0, 0, 0.5)',
                    symbol='triangle-down',
                    line=dict(width=1, color='black')
                ),
                name='Unfilled Sell Orders',
                hovertemplate=(
                    '<b>Sell Order</b><br>' +
                    'Price: %{y:.2f}<br>' +
                    'Contract Time: %{x}<br>' +
                    'Filled: No<br>' +
                    'Strategy: %{customdata[0]}<br>' +
                    'Submission: %{customdata[1]}<br>' +
                    'Quantity: %{customdata[2]}'
                ),
                customdata=np.column_stack((
                    unfilled_sells['strategy_id'],
                    unfilled_sells['submission_time'].dt.strftime('%Y-%m-%d %H:%M'),
                    unfilled_sells['quantity']
                ))
            ))
        
        if title:
            plot_title = title
        else:
            plot_title = "Sell Order Placement"
            if strategy_id:
                plot_title += f" - Strategy: {strategy_id}"
        
        fig.update_layout(
            title=plot_title,
            xaxis_title="Contract Time",
            yaxis_title="Price",
            legend_title="Order Status",
            hovermode="closest",
            legend=dict(
                x=1.1,
                y=0.5,
                xanchor="left",
                yanchor="middle",
                bordercolor="black",
                borderwidth=1,
                bgcolor="white"
            )
        )
        
        hovertemplate = (
            "Price: %{y:.2f}<br>" +
            "Delivery Time: %{x}<br>" +
            "Status: %{customdata[0]}<br>" +
            "Time to Fill: %{marker.color} minutes<br>" +
            "<extra></extra>"
        )
        
        fig.update_traces(
            marker=dict(size=12),
            opacity=1.0,
            hovertemplate=hovertemplate
        )
        
        # Update colorscale to start at 0 with configurable max (default 600)
        fig.update_traces(
            marker=dict(
                colorscale="Viridis",
                cmin=0,
                cmax=self.max_time_to_fill if hasattr(self, 'max_time_to_fill') else 600,
            )
        )
        
        fig.update_xaxes(title_text="Delivery Time")
        
        return fig
    
    def create_metrics_table(self):
        """Create a tabular view of key metrics for all strategies.
        
        Returns:
            Plotly figure
        """
        if not self.metrics:
            return go.Figure().update_layout(title="No metrics data available")
        
        # Define all columns
        all_columns = ['Strategy', 'Fill Rate', 'VWAP', 'Buy VWAP', 'Sell VWAP', 
                      'Time to Fill (min)', 'Volume', 'Buy Cost', 'Intended Volume', 'Execution Rate']
        
        table_data = []
        
        # Get strategies from fill_rate metrics
        if 'fill_rate' in self.metrics:
            for strategy_id, data in self.metrics['fill_rate'].items():
                # Initialize row with all columns set to empty strings
                row = {col: '' for col in all_columns}
                row['Strategy'] = strategy_id
                
                # Add fill rate
                if 'fill_rate' in data:
                    row['Fill Rate'] = f"{data['fill_rate']:.2%}"
                
                # Add execution prices (VWAP)
                if 'execution_prices' in self.metrics and strategy_id in self.metrics['execution_prices']:
                    price_data = self.metrics['execution_prices'][strategy_id]
                    if 'vwap' in price_data:
                        row['VWAP'] = f"{price_data['vwap']:.2f}"
                    
                    # Add buy/sell specific VWAP
                    if 'buy' in price_data and 'vwap' in price_data['buy']:
                        row['Buy VWAP'] = f"{price_data['buy']['vwap']:.2f}"
                    
                    if 'sell' in price_data and 'vwap' in price_data['sell']:
                        row['Sell VWAP'] = f"{price_data['sell']['vwap']:.2f}"
                
                # Add time to fill
                if 'time_to_fill' in self.metrics and strategy_id in self.metrics['time_to_fill']:
                    ttf_data = self.metrics['time_to_fill'][strategy_id]
                    if 'mean_minutes' in ttf_data:
                        row['Time to Fill (min)'] = f"{ttf_data['mean_minutes']:.2f}"
                
                # Add volume
                if 'contract_volume' in self.metrics and strategy_id in self.metrics['contract_volume']:
                    vol_data = self.metrics['contract_volume'][strategy_id]
                    if 'total_volume' in vol_data:
                        row['Volume'] = f"{vol_data['total_volume']:.2f}"
                
                # Add buy cost
                if 'buy_cost' in self.metrics and strategy_id in self.metrics['buy_cost']:
                    cost_data = self.metrics['buy_cost'][strategy_id]
                    if 'total_buy_cost' in cost_data:
                        row['Buy Cost'] = f"{cost_data['total_buy_cost']:.2f}"
                
                # Add volume execution rate data
                if 'volume_execution_rate' in self.metrics and strategy_id in self.metrics['volume_execution_rate']:
                    vol_exec_data = self.metrics['volume_execution_rate'][strategy_id]
                    if 'intended_volume' in vol_exec_data:
                        row['Intended Volume'] = f"{vol_exec_data['intended_volume']:.2f}"
                    if 'execution_rate' in vol_exec_data:
                        row['Execution Rate'] = f"{vol_exec_data['execution_rate']:.2%}"
                
                table_data.append(row)
        
        if not table_data:
            return go.Figure().update_layout(title="No metrics data available")
        
        headerColor = ['rgb(235, 245, 255)'] * len(all_columns)
        
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=all_columns,
                fill_color=headerColor,
                align='left',
                font=dict(size=11)
            ),
            cells=dict(
                values=[
                    [row[col] for row in table_data]
                    for col in all_columns
                ],
                align='left',
                font=dict(size=10)
            )
        )])
        
        fig.update_layout(
            title="Strategy Performance Metrics",
            height=130 + 30 * len(table_data)
        )
        
        return fig
    
    def create_dashboard(self):
        """Create a dashboard with strategy metrics.
        
        Returns:
            Plotly figure
        """
        if self.order_history.empty:
            return go.Figure().update_layout(
                title="No order data available for dashboard"
            )
        
        specs = [[{"type": "table"}]]
        subplot_titles = ["Strategy Metrics"]
        
        fig = make_subplots(
            rows=1, 
            cols=1,
            specs=specs,
            subplot_titles=subplot_titles,
            vertical_spacing=0.05
        )
        
        # Add table to the subplot
        metrics_fig = self.create_metrics_table()
        fig.add_trace(metrics_fig.data[0], row=1, col=1)
        
        fig.update_layout(
            title_text="Trading Simulation Results by Strategy",
            height=400,
            showlegend=False
        )
        
        return fig