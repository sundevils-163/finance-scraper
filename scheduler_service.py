#!/usr/bin/env python3
"""
Finance Scraper Scheduler Service
Standalone service that runs the scheduler with API for lifecycle management
"""

import logging
import os
import signal
import sys
import time
import threading
from flask import Flask, jsonify
from scheduler import create_scheduler_from_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global scheduler instance
_scheduler = None
_scheduler_lock = threading.Lock()

def get_scheduler():
    """Get the global scheduler instance"""
    global _scheduler
    with _scheduler_lock:
        if _scheduler is None:
            try:
                _scheduler = create_scheduler_from_env()
                logger.info("Scheduler instance created")
            except Exception as e:
                logger.error(f"Failed to create scheduler: {e}")
                return None
    return _scheduler

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "scheduler",
        "timestamp": time.time()
    }), 200

@app.route('/status')
def scheduler_status():
    """Get scheduler status"""
    scheduler = get_scheduler()
    
    if not scheduler:
        return jsonify({
            "status": "error",
            "message": "Scheduler not available"
        }), 500
    
    is_running = scheduler.scheduler_thread and scheduler.scheduler_thread.is_alive()
    
    return jsonify({
        "status": "running" if is_running else "stopped",
        "enabled": True,
        "config": {
            "run_frequency_hours": scheduler.config.run_frequency_hours,
            "symbol_frequency_hours": scheduler.config.symbol_frequency_hours,
            "max_symbols_per_run": scheduler.config.max_symbols_per_run,
            "rate_limit_delay_seconds": scheduler.config.rate_limit_delay_seconds,
            "initial_start_date": scheduler.config.initial_start_date,
            "download_chunk_days": scheduler.config.download_chunk_days,
            "download_chunk_delay_seconds": scheduler.config.download_chunk_delay_seconds
        }
    }), 200

@app.route('/start', methods=['POST'])
def start_scheduler():
    """Start the scheduler"""
    scheduler = get_scheduler()
    
    if not scheduler:
        return jsonify({
            "error": "Scheduler not available"
        }), 500
    
    try:
        scheduler.start()
        return jsonify({
            "message": "Scheduler started successfully",
            "status": "running"
        }), 200
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        return jsonify({
            "error": "Failed to start scheduler"
        }), 500

@app.route('/stop', methods=['POST'])
def stop_scheduler():
    """Stop the scheduler"""
    scheduler = get_scheduler()
    
    if not scheduler:
        return jsonify({
            "error": "Scheduler not available"
        }), 500
    
    try:
        scheduler.stop()
        return jsonify({
            "message": "Scheduler stopped successfully",
            "status": "stopped"
        }), 200
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        return jsonify({
            "error": "Failed to stop scheduler"
        }), 500

@app.route('/run-now', methods=['POST'])
def run_scheduler_now():
    """Run scheduler cycle immediately"""
    scheduler = get_scheduler()
    
    if not scheduler:
        return jsonify({
            "error": "Scheduler not available"
        }), 500
    
    try:
        # Run in a separate thread to avoid blocking
        thread = threading.Thread(target=scheduler.run_single_cycle, daemon=True)
        thread.start()
        
        return jsonify({
            "message": "Scheduler cycle started",
            "status": "running"
        }), 200
    except Exception as e:
        logger.error(f"Error running scheduler cycle: {e}")
        return jsonify({
            "error": "Failed to run scheduler cycle"
        }), 500

@app.route('/config')
def get_config():
    """Get scheduler configuration"""
    scheduler = get_scheduler()
    
    if not scheduler:
        return jsonify({
            "error": "Scheduler not available"
        }), 500
    
    return jsonify({
        "config": {
            "run_frequency_hours": scheduler.config.run_frequency_hours,
            "symbol_frequency_hours": scheduler.config.symbol_frequency_hours,
            "max_symbols_per_run": scheduler.config.max_symbols_per_run,
            "rate_limit_delay_seconds": scheduler.config.rate_limit_delay_seconds,
            "jitter_seconds": scheduler.config.jitter_seconds,
            "max_retries": scheduler.config.max_retries,
            "retry_delay_seconds": scheduler.config.retry_delay_seconds,
            "initial_start_date": scheduler.config.initial_start_date,
            "download_chunk_days": scheduler.config.download_chunk_days,
            "download_chunk_delay_seconds": scheduler.config.download_chunk_delay_seconds
        }
    }), 200

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Main function"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting Finance Scraper Scheduler Service with API")
    
    try:
        # Create scheduler (will be started via API)
        scheduler = get_scheduler()
        if not scheduler:
            logger.error("Failed to create scheduler")
            sys.exit(1)
        
        logger.info("Scheduler created successfully")
        
        # Start the Flask API
        port = int(os.environ.get('PORT', 5001))
        debug = os.environ.get('FLASK_ENV') == 'development'
        
        logger.info(f"Starting Scheduler API on port {port}")
        app.run(host='0.0.0.0', port=port, debug=debug)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error in scheduler service: {e}")
        sys.exit(1)
    finally:
        if 'scheduler' in locals():
            scheduler.stop()
            logger.info("Scheduler stopped")

if __name__ == '__main__':
    main() 