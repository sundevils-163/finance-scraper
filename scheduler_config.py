#!/usr/bin/env python3
"""
Finance Scraper Scheduler Configuration
Scheduler-specific configuration values and environment variable mappings
"""

import os
from typing import Dict, Any

# Default scheduler configuration values (MongoDB config comes from main app)
DEFAULT_SCHEDULER_CONFIG = {
    # Scheduler configuration
    'run_frequency_hours': 24,  # How often to run the full job
    'symbol_frequency_hours': 24,  # How often to update each symbol
    'max_symbols_per_run': 50,  # Maximum symbols to process per run
    'rate_limit_delay_seconds': 1.0,  # Delay between API calls
    'jitter_seconds': 0.5,  # Random jitter to avoid thundering herd
    
    # Retry configuration
    'max_retries': 3,
    'retry_delay_seconds': 5.0,
    
    # Historical data configuration
    'initial_start_days_back': 365,  # Days back to start when no historical data exists
}

# Scheduler-specific environment variable mappings
SCHEDULER_ENV_MAPPINGS = {
    'SCHEDULER_FREQUENCY_HOURS': 'run_frequency_hours',
    'SYMBOL_FREQUENCY_HOURS': 'symbol_frequency_hours',
    'MAX_SYMBOLS_PER_RUN': 'max_symbols_per_run',
    'RATE_LIMIT_DELAY_SECONDS': 'rate_limit_delay_seconds',
    'JITTER_SECONDS': 'jitter_seconds',
    'MAX_RETRIES': 'max_retries',
    'RETRY_DELAY_SECONDS': 'retry_delay_seconds',
    'INITIAL_START_DAYS_BACK': 'initial_start_days_back',
}

def get_scheduler_config() -> Dict[str, Any]:
    """Get scheduler-specific configuration from environment variables with defaults"""
    config = DEFAULT_SCHEDULER_CONFIG.copy()
    
    for env_var, config_key in SCHEDULER_ENV_MAPPINGS.items():
        env_value = os.environ.get(env_var)
        if env_value is not None:
            # Convert types based on default value
            default_value = DEFAULT_SCHEDULER_CONFIG[config_key]
            if isinstance(default_value, bool):
                config[config_key] = env_value.lower() == 'true'
            elif isinstance(default_value, int):
                config[config_key] = int(env_value)
            elif isinstance(default_value, float):
                config[config_key] = float(env_value)
            else:
                config[config_key] = env_value
    
    return config

def print_scheduler_config():
    """Print current scheduler configuration"""
    config = get_scheduler_config()
    print("Finance Scraper Scheduler Configuration:")
    print("=" * 40)
    
    for key, value in config.items():
        print(f"{key}: {value}")
    
    print("=" * 40)

if __name__ == "__main__":
    print_scheduler_config() 