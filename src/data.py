import pandas as pd
import numpy as np
import datetime
import random
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class DataSource(ABC):
    """Base class for data sources in the trading simulation.
    
    This is a simple interface that users can implement for their own data types.
    Common data sources might include day-ahead prices, intraday trades, or order books.
    """
    
    def __init__(self, name: Optional[str] = None):
        """Initialize the data source.
        
        Args:
            name: Optional name for this data source
        """
        self.name = name or self.__class__.__name__
    
    @abstractmethod
    def get_data(self, delivery_time: datetime.datetime, current_time: Optional[datetime.datetime] = None) -> float:
        """Retrieve the data for the specified delivery time.
        
        Args:
            delivery_time: Time of delivery
            current_time: Current time
            
        Returns:
            Data for the specified delivery time
        """
        pass


def generate_intraday_trades(start_date, num_days=7, trades_per_contract=10000):
    """Generate synthetic intraday electricity market trades.
    
    Args:
        start_date: datetime object for the first delivery day
        num_days: number of days to generate data for
        trades_per_contract: approximate number of trades to generate per contract
    
    Returns:
        DataFrame with trade data and VWAP calculations
    """
    all_trades = []
    
    for day_offset in range(num_days):
        delivery_date = start_date + datetime.timedelta(days=day_offset)
        
        for hour in range(24):
            # Delivery time for this contract
            delivery_time = datetime.datetime.combine(
                delivery_date.date(), 
                datetime.time(hour, 0)
            )
            
            # Trading starts at 3PM the previous day
            trading_start = datetime.datetime.combine(
                (delivery_date - datetime.timedelta(days=1)).date(),
                datetime.time(15, 0)
            )
            
            # Generate trades for this contract
            # Base price - different for each hour with day/night pattern
            hour_factor = 1.0 + 0.3 * np.sin((hour - 6) * np.pi / 12)  # Higher during day
            base_price = 45 * hour_factor + random.normalvariate(0, 5)
            
            # Total trading time in minutes
            total_minutes = (delivery_time - trading_start).total_seconds() / 60
            
            # Generate trades for this contract
            trades_for_contract = []
            
            # More trades closer to delivery (non-linear distribution)
            num_trades = trades_per_contract
            
            # Distribution that focuses more trades closer to delivery
            power_param = 0.3  # Lower = more concentration toward delivery
            
            # Generate timestamps with increasing frequency
            # 20% of trades in the first 70% of time (overnight & early trading)
            overnight_count = int(num_trades * 0.2)
            remaining_count = num_trades - overnight_count
            
            # Sparse trading at first (overnight and early)
            overnight_points = np.random.exponential(total_minutes/20, overnight_count)
            overnight_points = overnight_points[overnight_points < total_minutes * 0.7]
            
            # More frequent trading during day and close to delivery
            remaining_points = np.random.power(power_param, remaining_count) * (total_minutes * 0.3)
            remaining_points += total_minutes * 0.7
            
            time_points = np.concatenate([overnight_points, remaining_points])
            time_points = np.clip(time_points, 0, total_minutes)
            time_points = np.sort(time_points)
            
            # Initial price with some randomness
            current_price = base_price
            
            # Dict to store hourly trades for VWAP calculation
            hourly_trades = {}
            
            for minutes in time_points:
                trade_time = trading_start + datetime.timedelta(minutes=minutes)
                
                # Time to delivery in hours
                hours_to_delivery = (delivery_time - trade_time).total_seconds() / 3600
                
                # Hourly bucket for VWAP calculation (floor of trade hour)
                trade_hour = trade_time.replace(minute=0, second=0, microsecond=0)
                if trade_hour not in hourly_trades:
                    hourly_trades[trade_hour] = []
                
                # Volatility increases as we get closer to delivery
                volatility = 0.5 + 1.5 * max(0, (24 - hours_to_delivery) / 24)
                
                # Generate a price change
                price_change = random.normalvariate(0, volatility)
                current_price += price_change
                
                # Ensure price stays reasonable (no negative prices for simplicity)
                current_price = max(10, min(current_price, base_price * 2))
                
                # Random volume between 0.1 and 10, higher closer to delivery
                proximity_factor = max(0.1, min(1.0, (24 - hours_to_delivery) / 24))
                volume = 0.1 + (9.9 * proximity_factor * random.random())
                
                trade = {
                    'delivery_time': delivery_time,
                    'trade_time': trade_time,
                    'trade_hour': trade_hour,
                    'price': round(current_price, 2),
                    'volume': round(volume, 1),  # Round to 1 decimal
                    'contract': delivery_time.strftime('%Y-%m-%d %H:00'),
                    'hours_to_delivery': round(hours_to_delivery, 2)
                }
                
                trades_for_contract.append(trade)
                hourly_trades[trade_hour].append(trade)
            
            # Calculate VWAP for each hour and overall VWAP for this contract
            if trades_for_contract:
                # Overall VWAP calculation
                df_contract = pd.DataFrame(trades_for_contract)
                df_contract['price_volume'] = df_contract['price'] * df_contract['volume']
                overall_vwap = df_contract['price_volume'].sum() / df_contract['volume'].sum()
                
                # Calculate hourly VWAP and add to trades
                hourly_vwaps = {}
                for hour_bucket, hour_trades in hourly_trades.items():
                    df_hour = pd.DataFrame(hour_trades)
                    df_hour['price_volume'] = df_hour['price'] * df_hour['volume']
                    hour_vwap = df_hour['price_volume'].sum() / df_hour['volume'].sum()
                    hourly_vwaps[hour_bucket] = round(hour_vwap, 2)
                
                # Add VWAPs to each trade
                for trade in trades_for_contract:
                    trade_hour = trade['trade_hour']
                    trade['hourly_vwap'] = hourly_vwaps[trade_hour]
                    trade['overall_vwap'] = round(overall_vwap, 2)
                
                all_trades.extend(trades_for_contract)
    
    # Create final dataframe with all trades
    df = pd.DataFrame(all_trades)
    return df
