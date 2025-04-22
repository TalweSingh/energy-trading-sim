import numpy as np
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from typing import Optional, Dict, Any, Tuple

def constant_profile(
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    value: float = 10.0,
    time_step: datetime.timedelta = datetime.timedelta(minutes=15),
    noise_factor: float = 0.0
) -> pd.DataFrame:
    """Create a constant load or generation profile.
    
    Args:
        start_time: Start time for the profile
        end_time: End time for the profile
        value: Constant value in MW
        time_step: Time resolution (default: 15 minutes)
        noise_factor: Amount of random noise to add (0.0 to 1.0)
        
    Returns:
        DataFrame with timestamp and value columns
    """
    timestamps = pd.date_range(
        start=start_time, 
        end=end_time, 
        freq=f'{time_step.total_seconds()//60}min'
    )
    
    # Create base profile
    values = np.full(len(timestamps), value)
    
    # Add noise if requested
    if noise_factor > 0:
        noise = np.random.normal(0, value * noise_factor, len(values))
        values = values + noise
        values = np.maximum(values, 0)
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'value': values
    })
    
    return df

def residential_profile(
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    base_load: float = 5.0,
    morning_peak: float = 10.0,
    evening_peak: float = 15.0,
    time_step: datetime.timedelta = datetime.timedelta(minutes=15),
    noise_factor: float = 0.05
) -> pd.DataFrame:
    """Create a residential load profile with morning and evening peaks.
    
    Args:
        start_time: Start time for the profile
        end_time: End time for the profile
        base_load: Baseline load in MW
        morning_peak: Additional morning peak load in MW
        evening_peak: Additional evening peak load in MW
        time_step: Time resolution (default: 15 minutes)
        noise_factor: Amount of random noise to add (0.0 to 1.0)
        
    Returns:
        DataFrame with timestamp and value columns
    """
    timestamps = pd.date_range(
        start=start_time, 
        end=end_time, 
        freq=f'{time_step.total_seconds()//60}min'
    )
    
    # Initialize with base load
    values = np.full(len(timestamps), base_load)
    
    # Add peaks for each day
    for i, ts in enumerate(timestamps):
        hour = ts.hour
        
        # Morning peak (centered at 8 AM)
        morning_factor = np.exp(-((hour - 8)**2) / 4)
        values[i] += morning_peak * morning_factor
        
        # Evening peak (centered at 7 PM)
        evening_factor = np.exp(-((hour - 19)**2) / 6)
        values[i] += evening_peak * evening_factor
    
    # Add noise if requested
    if noise_factor > 0:
        base_values = values.copy()
        noise = np.random.normal(0, base_values * noise_factor, len(values))
        values = values + noise
        values = np.maximum(values, 0)
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'value': values
    })
    
    return df

def industrial_profile(
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    base_load: float = 20.0,
    peak_load: float = 50.0,
    working_hours: tuple = (8, 18),
    weekend_factor: float = 0.6,
    time_step: datetime.timedelta = datetime.timedelta(minutes=15),
    noise_factor: float = 0.03
) -> pd.DataFrame:
    """Create an industrial load profile with working hour patterns.
    
    Args:
        start_time: Start time for the profile
        end_time: End time for the profile
        base_load: Baseline load in MW (nights and weekends)
        peak_load: Peak load during working hours in MW
        working_hours: Tuple of (start_hour, end_hour) for working hours
        weekend_factor: Reduction factor for weekends
        time_step: Time resolution (default: 15 minutes)
        noise_factor: Amount of random noise to add (0.0 to 1.0)
        
    Returns:
        DataFrame with timestamp and value columns
    """
    timestamps = pd.date_range(
        start=start_time, 
        end=end_time, 
        freq=f'{time_step.total_seconds()//60}min'
    )
    
    # Initialize with base load
    values = np.full(len(timestamps), base_load)
    
    # Add working hour patterns
    work_start, work_end = working_hours
    
    for i, ts in enumerate(timestamps):
        if ts.weekday() >= 5:  # Weekend
            values[i] *= weekend_factor
        else:  # Weekday
            hour = ts.hour
            if work_start <= hour < work_end:
                # Gradual ramp-up in morning
                if hour < work_start + 2:
                    ramp_factor = (hour - work_start) / 2
                    values[i] = base_load + (peak_load - base_load) * ramp_factor
                # Gradual ramp-down in evening
                elif hour >= work_end - 2:
                    ramp_factor = (work_end - hour) / 2
                    values[i] = base_load + (peak_load - base_load) * ramp_factor
                # Full peak during main working hours
                else:
                    values[i] = peak_load
    
    # Add noise if requested
    if noise_factor > 0:
        base_values = values.copy()
        noise = np.random.normal(0, base_values * noise_factor, len(values))
        values = values + noise
        values = np.maximum(values, 0)
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'value': values
    })
    
    return df

def solar_generation(
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    capacity: float = 100.0,
    time_step: datetime.timedelta = datetime.timedelta(minutes=15),
    cloudiness: float = 0.2
) -> pd.DataFrame:
    """Create a solar generation profile.
    
    Args:
        start_time: Start time for the profile
        end_time: End time for the profile
        capacity: Maximum generation capacity in MW
        time_step: Time resolution (default: 15 minutes)
        cloudiness: Random factor to simulate cloud cover (0.0 to 1.0)
        
    Returns:
        DataFrame with timestamp and value columns
    """
    timestamps = pd.date_range(
        start=start_time, 
        end=end_time, 
        freq=f'{time_step.total_seconds()//60}min'
    )
    
    # Initialize with zeros
    values = np.zeros(len(timestamps))
    
    # Create solar profile for each day
    for i, ts in enumerate(timestamps):
        hour = ts.hour
        
        # Solar generation occurs between sunrise and sunset (approx 6 AM - 8 PM)
        if 6 <= hour < 20:
            # Bell curve with peak at midday
            sun_factor = np.exp(-((hour - 13)**2) / 18)
            
            # Base generation before clouds
            values[i] = capacity * sun_factor
            
            # Apply daily cloud variation
            day_of_year = ts.dayofyear
            # Add some randomness by day
            daily_factor = 0.8 + 0.2 * np.sin(day_of_year / 365 * 2 * np.pi)
            values[i] *= daily_factor
            
            # Apply random clouds
            if cloudiness > 0 and np.random.random() < cloudiness:
                cloud_factor = 1.0 - (0.3 * np.random.random())
                values[i] *= cloud_factor
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'value': values
    })
    
    return df

def wind_generation(
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    capacity: float = 80.0,
    time_step: datetime.timedelta = datetime.timedelta(minutes=15),
    volatility: float = 0.2
) -> pd.DataFrame:
    """Create a wind generation profile.
    
    Args:
        start_time: Start time for the profile
        end_time: End time for the profile
        capacity: Maximum generation capacity in MW
        time_step: Time resolution (default: 15 minutes)
        volatility: Factor for wind speed changes (0.0 to 1.0)
        
    Returns:
        DataFrame with timestamp and value columns
    """
    timestamps = pd.date_range(
        start=start_time, 
        end=end_time, 
        freq=f'{time_step.total_seconds()//60}min'
    )
    
    # Initialize with random value
    values = np.zeros(len(timestamps))
    
    # Start with a random wind speed
    current_factor = np.random.random() * 0.5
    
    # Create wind profile with temporal correlation
    for i in range(len(timestamps)):
        # Evolve wind factor with some randomness
        current_factor += np.random.normal(0, volatility * 0.1)
        current_factor = max(0, min(1, current_factor))
        
        # Apply to capacity
        values[i] = capacity * current_factor
        
        # Occasionally add wind gusts or lulls
        if np.random.random() < 0.05:  # 5% chance of a significant change
            if np.random.random() < 0.5:
                # Wind gust
                current_factor += np.random.random() * 0.3
            else:
                # Wind lull
                current_factor -= np.random.random() * 0.3
            
        current_factor = max(0, min(1, current_factor))
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'value': values
    })
    
    return df

def plot_profile(df: pd.DataFrame, title: str = "Energy Profile") -> None:
    """Plot an energy profile.
    
    Args:
        df: DataFrame with timestamp and value columns
        title: Plot title
    """
    plt.figure(figsize=(10, 6))
    plt.plot(df['timestamp'], df['value'])
    plt.title(title)
    plt.xlabel('Time')
    plt.ylabel('MW')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def combine_profiles(profiles: list) -> pd.DataFrame:
    """Combine multiple profiles (e.g., add generation to load).
    
    Args:
        profiles: List of DataFrames to combine
        
    Returns:
        Combined DataFrame
    """
    if not profiles:
        return pd.DataFrame()
    
    # Start with first profile
    result = profiles[0].copy()
    
    # Add additional profiles
    for profile in profiles[1:]:
        # Align by timestamp
        aligned = pd.merge(
            result,
            profile,
            on='timestamp',
            how='outer',
            suffixes=('_1', '_2')
        )
        
        # Sum the values
        aligned['value'] = aligned['value_1'].fillna(0) + aligned['value_2'].fillna(0)
        
        # Keep only timestamp and value columns
        result = aligned[['timestamp', 'value']]
    
    return result
