#!/usr/bin/env python3
"""
Finance Scraper Scheduler
Automated cron-style job to retrieve stock data and historical prices
"""

import logging
import os
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from threading import Thread, Event
import yfinance as yf
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SchedulerConfig:
    """Configuration for the scheduler"""
    # MongoDB configuration
    mongodb_uri: str
    authentication_source: str
    mongodb_username: Optional[str]
    mongodb_password: Optional[str]
    db_name: str
    collection_name: str
    prices_collection_name: str
    
    # Scheduler configuration
    run_frequency_hours: int = 24  # How often to run the full job
    symbol_frequency_hours: int = 24  # How often to update each symbol
    max_symbols_per_run: int = 50  # Maximum symbols to process per run
    rate_limit_delay_seconds: float = 1.0  # Delay between API calls
    jitter_seconds: float = 0.5  # Random jitter to avoid thundering herd
    
    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    
    # Historical data configuration
    initial_start_date: str = "2020-01-01"  # Initial start date (YYYY-MM-DD) when no historical data exists
    download_chunk_days: int = 365  # Number of days to download per chunk
    download_chunk_delay_seconds: int = 60  # Seconds to wait between chunks for same symbol

class StockScheduler:
    """Main scheduler class for automated stock data retrieval"""
    
    def __init__(self, config: SchedulerConfig):
        self.config = config
        self.stop_event = Event()
        self.scheduler_thread = None
        self.mongo_client = None
        self.db = None
        self.collection = None
        self.prices_collection = None
        self.mongodb_available = False
        
        self._setup_mongodb()
    
    def _setup_mongodb(self):
        """Initialize MongoDB connection"""
        try:
            # Build MongoDB URI with credentials if provided
            mongodb_uri = self.config.mongodb_uri
            if self.config.mongodb_username and self.config.mongodb_password:
                if 'mongodb://' in mongodb_uri and '@' not in mongodb_uri:
                    host_part = mongodb_uri.replace('mongodb://', '')
                    mongodb_uri = f"mongodb://{self.config.mongodb_username}:{self.config.mongodb_password}@{host_part}"
            
            # Create MongoDB client
            self.mongo_client = MongoClient(
                mongodb_uri,
                serverSelectionTimeoutMS=5000,
                authSource=self.config.authentication_source
            )
            
            # Test connection
            self.mongo_client.admin.command('ping')
            self.db = self.mongo_client[self.config.db_name]
            self.collection = self.db[self.config.collection_name]
            self.prices_collection = self.db[self.config.prices_collection_name]
            self.mongodb_available = True
            
            logger.info(f"Successfully connected to MongoDB: {self.config.db_name}")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB connection failed: {e}")
            self.mongodb_available = False
    
    def get_all_symbols(self) -> List[str]:
        """Retrieve all stock symbols from the database"""
        if not self.mongodb_available:
            logger.error("MongoDB not available")
            return []
        
        try:
            symbols = self.collection.distinct('symbol')
            logger.info(f"Retrieved {len(symbols)} symbols from database")
            return symbols
        except Exception as e:
            logger.error(f"Error retrieving symbols: {e}")
            return []
    
    def get_last_price_date(self, symbol: str) -> Optional[datetime]:
        """Get the date of the last price entry for a symbol"""
        if not self.mongodb_available:
            return None
        
        try:
            # Find the most recent price entry
            last_price = self.prices_collection.find_one(
                {'symbol': symbol.upper()},
                sort=[('date', -1)]
            )
            
            if last_price:
                return last_price['date']
            return None
        except Exception as e:
            logger.error(f"Error getting last price date for {symbol}: {e}")
            return None
    
    def should_update_symbol(self, symbol: str) -> bool:
        """Check if a symbol should be updated based on frequency"""
        if not self.mongodb_available:
            return False
        
        try:
            # Check when the symbol was last updated by looking at the last price date
            last_price_date = self.get_last_price_date(symbol)
            if not last_price_date:
                # No historical prices found, should update
                return True
            
            hours_since_update = (datetime.utcnow() - last_price_date).total_seconds() / 3600
            return hours_since_update >= self.config.symbol_frequency_hours
        except Exception as e:
            logger.error(f"Error checking update status for {symbol}: {e}")
            return True
    
    def update_stock_info(self, symbol: str) -> bool:
        """Update stock information for a symbol"""
        try:
            logger.info(f"Updating stock info for {symbol}")
            
            # Get stock data from Yahoo Finance
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info or 'regularMarketPrice' not in info:
                logger.warning(f"No valid data received for {symbol}")
                return False
            
            # Prepare document for MongoDB
            document = {
                'symbol': symbol.upper(),
                'data': info,
                'updated_at': datetime.utcnow(),
                'source': 'yfinance',
                'last_fetched': datetime.utcnow()
            }
            
            # Upsert the document
            self.collection.replace_one(
                {'symbol': symbol.upper()},
                document,
                upsert=True
            )
            
            logger.info(f"Successfully updated stock info for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating stock info for {symbol}: {e}")
            return False
    
    def update_historical_prices(self, symbol: str) -> bool:
        """Update historical prices for a symbol in chunks"""
        try:
            logger.info(f"Updating historical prices for {symbol}")
            
            # Get the last price date
            last_date = self.get_last_price_date(symbol)
            current_start_date = None
            
            if last_date:
                # Start from the day after the last price
                current_start_date = last_date + timedelta(days=1)
            else:
                # No previous data, use configured initial start date
                try:
                    current_start_date = datetime.strptime(self.config.initial_start_date, '%Y-%m-%d')
                    logger.info(f"No historical data found for {symbol}, starting from {self.config.initial_start_date}")
                except ValueError as e:
                    logger.error(f"Invalid initial start date format: {self.config.initial_start_date}. Expected YYYY-MM-DD. Using default 2020-01-01")
                    current_start_date = datetime.strptime('2020-01-01', '%Y-%m-%d')
            
            end_date = datetime.utcnow()
            
            # Don't update if start_date is in the future
            if current_start_date > end_date:
                logger.info(f"No new data needed for {symbol}")
                return True
            
            ticker = yf.Ticker(symbol)
            total_documents = 0
            chunk_count = 0
            
            # Download data in chunks
            while current_start_date < end_date and not self.stop_event.is_set():
                chunk_count += 1
                
                # Calculate chunk end date (current_start_date + chunk_days, but not beyond end_date)
                chunk_end_date = min(
                    current_start_date + timedelta(days=self.config.download_chunk_days),
                    end_date
                )
                
                logger.info(f"Downloading chunk {chunk_count} for {symbol}: {current_start_date.strftime('%Y-%m-%d')} to {chunk_end_date.strftime('%Y-%m-%d')}")
                
                # Get historical data for this chunk
                hist = ticker.history(
                    start=current_start_date.strftime('%Y-%m-%d'),
                    end=chunk_end_date.strftime('%Y-%m-%d'),
                    auto_adjust=False
                )
                
                if hist.empty:
                    logger.info(f"No data for chunk {chunk_count} of {symbol}")
                    # Move to next chunk
                    current_start_date = chunk_end_date
                    continue
                
                # Convert to list of documents
                documents = []
                for date, row in hist.iterrows():
                    document = {
                        'symbol': symbol.upper(),
                        'date': date.to_pydatetime(),
                        'open': round(float(row['Open']), 2) if pd.notna(row['Open']) else None,
                        'high': round(float(row['High']), 2) if pd.notna(row['High']) else None,
                        'low': round(float(row['Low']), 2) if pd.notna(row['Low']) else None,
                        'close': round(float(row['Close']), 2) if pd.notna(row['Close']) else None,
                        'volume': int(row['Volume']) if pd.notna(row['Volume']) else None,
                        'adj_close': round(float(row['Adj Close']), 2) if pd.notna(row['Adj Close']) else None,
                        'source': 'yfinance'
                    }
                    documents.append(document)
                
                if documents:
                    # Use bulk operations for better performance
                    from pymongo import ReplaceOne
                    operations = [
                        ReplaceOne(
                            {'symbol': doc['symbol'], 'date': doc['date']},
                            doc,
                            upsert=True
                        ) for doc in documents
                    ]
                    
                    result = self.prices_collection.bulk_write(operations)
                    total_documents += len(documents)
                    logger.info(f"Updated {len(documents)} historical prices for {symbol} (chunk {chunk_count})")
                
                # Move to next chunk
                current_start_date = chunk_end_date
                
                # Wait between chunks (except for the last chunk)
                if current_start_date < end_date:
                    delay_seconds = self.config.download_chunk_delay_seconds
                    logger.info(f"Waiting {delay_seconds} seconds before next chunk for {symbol}")
                    
                    # Wait in smaller intervals to allow for stop event
                    for _ in range(delay_seconds):
                        if self.stop_event.is_set():
                            logger.info(f"Stop event received, interrupting historical price update for {symbol}")
                            return True
                        time.sleep(1)
            
            if total_documents > 0:
                logger.info(f"Completed historical price update for {symbol}: {total_documents} total documents in {chunk_count} chunks")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating historical prices for {symbol}: {e}")
            return False
    
    def process_symbol(self, symbol: str) -> bool:
        """Process a single symbol (update both info and prices)"""
        try:
            # Add rate limiting with jitter
            delay = self.config.rate_limit_delay_seconds + random.uniform(0, self.config.jitter_seconds)
            time.sleep(delay)
            
            # Update stock info
            info_success = self.update_stock_info(symbol)
            
            # Add small delay between info and prices update
            time.sleep(0.5)
            
            # Update historical prices
            prices_success = self.update_historical_prices(symbol)
            
            return info_success and prices_success
            
        except Exception as e:
            logger.error(f"Error processing symbol {symbol}: {e}")
            return False
    
    def run_single_cycle(self):
        """Run a single cycle of the scheduler"""
        logger.info("Starting scheduler cycle")
        
        if not self.mongodb_available:
            logger.error("MongoDB not available, skipping cycle")
            return
        
        try:
            # Get all symbols
            all_symbols = self.get_all_symbols()
            if not all_symbols:
                logger.warning("No symbols found in database")
                return
            
            # Filter symbols that need updating
            symbols_to_update = [
                symbol for symbol in all_symbols 
                if self.should_update_symbol(symbol)
            ]
            
            logger.info(f"Found {len(symbols_to_update)} symbols that need updating")
            
            # Limit the number of symbols processed per run
            symbols_to_process = symbols_to_update[:self.config.max_symbols_per_run]
            
            if not symbols_to_process:
                logger.info("No symbols need updating in this cycle")
                return
            
            # Process symbols
            success_count = 0
            for i, symbol in enumerate(symbols_to_process, 1):
                logger.info(f"Processing symbol {i}/{len(symbols_to_process)}: {symbol}")
                
                if self.process_symbol(symbol):
                    success_count += 1
                else:
                    logger.warning(f"Failed to process symbol {symbol}")
                
                # Check if we should stop
                if self.stop_event.is_set():
                    logger.info("Stop event received, interrupting cycle")
                    break
            
            logger.info(f"Cycle completed: {success_count}/{len(symbols_to_process)} symbols processed successfully")
            
        except Exception as e:
            logger.error(f"Error in scheduler cycle: {e}")
    
    def start(self):
        """Start the scheduler in a background thread"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.warning("Scheduler is already running")
            return
        
        self.stop_event.clear()
        self.scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.stop_event.set()
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        logger.info("Scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info(f"Scheduler running with {self.config.run_frequency_hours}h frequency")
        
        while not self.stop_event.is_set():
            try:
                # Run a single cycle
                self.run_single_cycle()
                
                # Wait for next cycle
                logger.info(f"Waiting {self.config.run_frequency_hours} hours until next cycle")
                self.stop_event.wait(self.config.run_frequency_hours * 3600)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                # Wait a bit before retrying
                self.stop_event.wait(300)  # 5 minutes

def create_scheduler_from_env() -> StockScheduler:
    """Create scheduler instance from environment variables"""
    
    config = SchedulerConfig(
        # MongoDB configuration - use same as main app
        mongodb_uri=os.environ.get('MONGODB_URI', 'mongodb://mongodb.lan:27017/'),
        authentication_source=os.environ.get('AUTHENTICATION_SOURCE', 'epicurus-stock-io'),
        mongodb_username=os.environ.get('MONGODB_USERNAME'),
        mongodb_password=os.environ.get('MONGODB_PASSWORD'),
        db_name=os.environ.get('MONGODB_DB', 'epicurus-stock-io'),
        collection_name=os.environ.get('MONGODB_COLLECTION', 'stock-info'),
        prices_collection_name=os.environ.get('MONGODB_PRICES_COLLECTION', 'stock-prices'),
        # Scheduler-specific configuration from environment variables
        run_frequency_hours=int(os.environ.get('SCHEDULER_FREQUENCY_HOURS', '24')),
        symbol_frequency_hours=int(os.environ.get('SYMBOL_FREQUENCY_HOURS', '24')),
        max_symbols_per_run=int(os.environ.get('MAX_SYMBOLS_PER_RUN', '50')),
        rate_limit_delay_seconds=float(os.environ.get('RATE_LIMIT_DELAY_SECONDS', '1.0')),
        jitter_seconds=float(os.environ.get('JITTER_SECONDS', '0.5')),
        max_retries=int(os.environ.get('MAX_RETRIES', '3')),
        retry_delay_seconds=float(os.environ.get('RETRY_DELAY_SECONDS', '5.0')),
        initial_start_date=os.environ.get('INITIAL_START_DATE', '2020-01-01'),
        download_chunk_days=int(os.environ.get('DOWNLOAD_CHUNK_DAYS', '365')),
        download_chunk_delay_seconds=int(os.environ.get('DOWNLOAD_CHUNK_DELAY_SECONDS', '60'))
    )
    
    return StockScheduler(config)

if __name__ == "__main__":
    # Run scheduler standalone
    scheduler = create_scheduler_from_env()
    
    try:
        scheduler.start()
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        scheduler.stop()
        logger.info("Scheduler stopped") 