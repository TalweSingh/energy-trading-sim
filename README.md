# Electricity Trading Simulation Framework
A lightweight, flexible simulation platform for electricity intraday trading strategies.

## Introduction
This is a lightweight Python framework that lets you:
- Test trading strategies for electricity markets
- Simulate market clearing mechanisms
- Analyze order history and trading results

It's designed to be simple and extensible - you don't need detailed order book data or complex market models to get started.

## Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/electricity-trading-sim.git
cd electricity-trading-sim

# Install dependencies
pip install -e .
```

## Creating Custom Components
### Custom Strategy
```python
from src.strategy import Strategy

class MyStrategy(Strategy):
    def update_orders(self, current_time):
        # Your trading logic here
        return new_orders, updated_orders, canceled_orders
```

### Custom Clearing
```python
from src.clearing import ClearingMechanism

class MyClearing(ClearingMechanism):
    def clear(self, current_time, active_orders):
        # Your market clearing logic here
        return filled_orders
```

## Basic Usage
```python
import datetime
from src.sim import TradingSimulation

# Create a simple simulation
sim = TradingSimulation(
    start_time=datetime.datetime(2023, 1, 1, 10, 0),
    end_time=datetime.datetime(2023, 1, 1, 16, 0),
    time_step=datetime.timedelta(minutes=15),
    strategies=[
        MyStrategy(price=50.0, side='buy'),
        MyStrategy(price=50.0, side='sell')
    ],
    clearing_mechanism=MyClearing()
)

# Run simulation and get results
results = sim.run()
print(results)
```