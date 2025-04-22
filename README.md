# Electricity Trading Simulation Framework
A Python framework for simulating and analyzing electricity intraday trading strategies, developed for academic research on market dynamics and trading algorithm performance.
It's designed to be simple and extensible - no need for detailed order book data or complex market models to get started.

## Overview

This framework enables researchers and practitioners to:
- **Simulate electricity intraday markets** with customizable clearing mechanisms
- **Test trading strategies** under these clearing mechanisms
- **Analyze performance metrics** including fill rates, execution prices, and time-to-fill
- **Compare different market designs** and their impact on trading outcomes
- **Validate theoretical models** with empirical data integration

## Key Features
- **Strategy Framework**: Extensible base class for implementing custom trading algorithms
- **Clearing Mechanisms**: Pluggable market clearing implementations (continuous, batch, reference-based)
- **Data Integration**: Support for real market data (day-ahead prices, intraday trades)
- **Metrics**: Performance analysis and visualization

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/electricity-trading-sim.git
cd electricity-trading-sim

# Install dependencies
pip install -e .
```

## Quick Start

### Basic Simulation
```python
import datetime
from src.sim import TradingSimulation
from src.strategy import Strategy
from src.clearing import ClearingMechanism

# Define a simple strategy
class MyStrategy(Strategy):
    def update_orders(self, current_time):
        # Your trading logic here
        return new_orders, updated_orders, canceled_orders

# Define a clearing mechanism
class MyClearing(ClearingMechanism):
    def clear(self, current_time, active_orders):
        # Your market clearing logic here
        return filled_orders

# Run simulation
sim = TradingSimulation(
    start_time=datetime.datetime(2023, 1, 1, 10, 0),
    end_time=datetime.datetime(2023, 1, 1, 16, 0),
    time_step=datetime.timedelta(minutes=15),
    strategies=[MyStrategy()],
    clearing_mechanism=MyClearing()
)

results = sim.run()
```

### Performance Analysis
```python
from src.metrics import SimulationMetrics
from src.plot import SimulationVisualizer

# Calculate metrics
metrics = SimulationMetrics(results['order_history'])
performance = metrics.run_all()

# Visualize results
visualizer = SimulationVisualizer(results)
visualizer.plot_strategy_metrics(performance)
```

## Case Studies

The framework includes two case studies demonstrating how the framework can be utilized:

### Case Study 1: Using Publicly Available Market Data
- **Objective**: Compare different clearing mechanisms' impact on trading outcomes
- **Data Sources**: Day-ahead prices from [SMARD](https://www.smard.de/home/marktdaten) and intraday prices from [NordPool](https://data.nordpoolgroup.com/intraday/intraday-hourly-statistic).
- **Strategies**: Urgency-based trading with time-dependent price adjustments
- **Clearing**: Day-ahead reference, intraday VWAP, and time-horizon based clearing.
- **Results**: Analysis of key metrics like execution prices, time to fill and fill rates.

### Case Study 2: Using Synthetic Trade-level Data
- **Objective**: Evaluate different trading strategy performance under trade level data
- **Strategies**: Urgency-based vs. forecast-based approaches
- **Data**: Synthetically generated trade-level data
 **Clearing**: Hourly Vwap-based clearing and volume-based clearing
- **Results**: Analysis of key metrics like execution prices, time to fill and fill rates.

## Contributing

This framework is designed for research. Contributions are welcome for:
- New trading strategies
- Additional clearing mechanisms
- Performance metrics
- Data source integrations
- Documentation improvements
