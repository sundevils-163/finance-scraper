#!/usr/bin/env python3
"""
Test script for Finance Scraper Scheduler
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_scheduler_import():
    """Test that scheduler can be imported"""
    try:
        from scheduler import create_scheduler_from_env
        logger.info("✓ Scheduler import successful")
        return True
    except ImportError as e:
        logger.error(f"✗ Scheduler import failed: {e}")
        return False

def test_scheduler_creation():
    """Test scheduler creation"""
    try:
        from scheduler import create_scheduler_from_env
        
        # Set test environment variables
        os.environ['MONGODB_URI'] = 'mongodb://localhost:27017/'
        os.environ['MONGODB_DB'] = 'test-db'
        os.environ['SCHEDULER_FREQUENCY_HOURS'] = '1'
        os.environ['SYMBOL_FREQUENCY_HOURS'] = '1'
        os.environ['MAX_SYMBOLS_PER_RUN'] = '5'
        os.environ['INITIAL_START_DAYS_BACK'] = '30'
        
        scheduler = create_scheduler_from_env()
        logger.info("✓ Scheduler creation successful")
        
        # Test configuration
        config = scheduler.config
        assert config.run_frequency_hours == 1
        assert config.symbol_frequency_hours == 1
        assert config.max_symbols_per_run == 5
        assert config.initial_start_days_back == 30
        logger.info("✓ Scheduler configuration correct")
        
        return True
    except Exception as e:
        logger.error(f"✗ Scheduler creation failed: {e}")
        return False

def test_scheduler_lifecycle():
    """Test scheduler start/stop lifecycle"""
    try:
        from scheduler import create_scheduler_from_env
        
        # Create scheduler with short intervals for testing
        os.environ['SCHEDULER_FREQUENCY_HOURS'] = '1'
        os.environ['SYMBOL_FREQUENCY_HOURS'] = '1'
        os.environ['MAX_SYMBOLS_PER_RUN'] = '1'
        
        scheduler = create_scheduler_from_env()
        
        # Test start
        scheduler.start()
        time.sleep(1)  # Give it time to start
        
        is_running = scheduler.scheduler_thread and scheduler.scheduler_thread.is_alive()
        if is_running:
            logger.info("✓ Scheduler started successfully")
        else:
            logger.error("✗ Scheduler failed to start")
            return False
        
        # Test stop
        scheduler.stop()
        time.sleep(1)  # Give it time to stop
        
        is_stopped = not (scheduler.scheduler_thread and scheduler.scheduler_thread.is_alive())
        if is_stopped:
            logger.info("✓ Scheduler stopped successfully")
        else:
            logger.error("✗ Scheduler failed to stop")
            return False
        
        return True
    except Exception as e:
        logger.error(f"✗ Scheduler lifecycle test failed: {e}")
        return False

def test_config_module():
    """Test configuration module"""
    try:
        from scheduler_config import get_scheduler_config, print_scheduler_config
        
        # Test configuration retrieval
        config = get_scheduler_config()
        assert 'run_frequency_hours' in config
        assert 'max_symbols_per_run' in config
        logger.info("✓ Configuration module working")
        
        return True
    except Exception as e:
        logger.error(f"✗ Configuration module test failed: {e}")
        return False

def test_service_import():
    """Test scheduler service import"""
    try:
        from scheduler_service import main
        logger.info("✓ Scheduler service import successful")
        return True
    except ImportError as e:
        logger.error(f"✗ Scheduler service import failed: {e}")
        return False

def run_tests():
    """Run all tests"""
    logger.info("Running Finance Scraper Scheduler Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Scheduler Import", test_scheduler_import),
        ("Scheduler Creation", test_scheduler_creation),
        ("Scheduler Lifecycle", test_scheduler_lifecycle),
        ("Configuration Module", test_config_module),
        ("Service Import", test_service_import),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning test: {test_name}")
        try:
            if test_func():
                passed += 1
                logger.info(f"✓ {test_name} PASSED")
            else:
                logger.error(f"✗ {test_name} FAILED")
        except Exception as e:
            logger.error(f"✗ {test_name} FAILED with exception: {e}")
    
    logger.info("\n" + "=" * 50)
    logger.info(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed!")
        return True
    else:
        logger.error("❌ Some tests failed!")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 