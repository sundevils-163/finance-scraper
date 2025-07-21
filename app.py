#!/usr/bin/env python3
"""
Finance Scraper API
A Flask application to retrieve stock information using yfinance with MongoDB storage
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import yfinance as yf
from pymongo import MongoClient, ReplaceOne
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import pandas as pd
from functools import lru_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Optimize Flask for production
app.config['JSON_SORT_KEYS'] = False  # Reduce CPU usage for JSON serialization
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False  # Disable pretty printing

# MongoDB configuration
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://mongodb.lan:27017/')
AUTHENTICATION_SOURCE = os.environ.get('AUTHENTICATION_SOURCE', 'epicurus-stock-io')
MONGODB_USERNAME = os.environ.get('MONGODB_USERNAME')
MONGODB_PASSWORD = os.environ.get('MONGODB_PASSWORD')
DB_NAME = os.environ.get('MONGODB_DB', 'epicurus-stock-io')
COLLECTION_NAME = os.environ.get('MONGODB_COLLECTION', 'stock-info')
PRICES_COLLECTION_NAME = os.environ.get('MONGODB_PRICES_COLLECTION', 'stock-prices')

# Build MongoDB URI with credentials if provided
if MONGODB_USERNAME and MONGODB_PASSWORD:
    # If credentials are provided separately, build the URI
    if 'mongodb://' in MONGODB_URI and '@' not in MONGODB_URI:
        # Extract host from URI and rebuild with credentials
        host_part = MONGODB_URI.replace('mongodb://', '')
        MONGODB_URI = f"mongodb://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{host_part}"
    logger.info(f"Using MongoDB with authentication, authSource: {AUTHENTICATION_SOURCE}")
else:
    logger.info("Using MongoDB without authentication")

# Initialize MongoDB client
try:
    # Create MongoDB client with authentication source and optimized settings
    mongo_client = MongoClient(
        MONGODB_URI, 
        serverSelectionTimeoutMS=5000,
        authSource=AUTHENTICATION_SOURCE,
        maxPoolSize=10,  # Limit connection pool
        minPoolSize=1,   # Minimum connections
        maxIdleTimeMS=30000,  # Close idle connections after 30 seconds
        connectTimeoutMS=5000,  # Connection timeout
        socketTimeoutMS=5000    # Socket timeout
    )
    # Test the connection
    mongo_client.admin.command('ping')
    db = mongo_client[DB_NAME]
    collection = db[COLLECTION_NAME]
    prices_collection = db[PRICES_COLLECTION_NAME]
    logger.info(f"Successfully connected to MongoDB: {DB_NAME}.{COLLECTION_NAME}, {PRICES_COLLECTION_NAME}")
    MONGODB_AVAILABLE = True
except (ConnectionFailure, ServerSelectionTimeoutError) as e:
    logger.warning(f"MongoDB connection failed: {e}. Running without storage.")
    MONGODB_AVAILABLE = False
    mongo_client = None
    db = None
    collection = None
    prices_collection = None

def validate_symbol(symbol: str) -> bool:
    """Validate stock symbol format"""
    if not symbol or not isinstance(symbol, str):
        return False
    # Basic validation - alphanumeric and common symbols
    return symbol.replace('.', '').replace('-', '').isalnum()

def validate_date_format(date_str: str) -> bool:
    """Validate date format (YYYY-MM-DD)"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def get_stock_from_database(symbol: str) -> Optional[Dict[str, Any]]:
    """Retrieve stock data from MongoDB database"""
    if not MONGODB_AVAILABLE:
        return None
    
    try:
        # Check if symbol exists in database
        stored_data = collection.find_one({'symbol': symbol.upper()})
        
        if stored_data:
            logger.info(f"Retrieved {symbol} from MongoDB database")
            # Remove MongoDB _id field from response
            stored_data.pop('_id', None)
            return stored_data.get('data')
        
        return None
    except Exception as e:
        logger.error(f"Error retrieving from MongoDB database for {symbol}: {e}")
        return None

def save_stock_to_database(symbol: str, stock_data: Dict[str, Any]) -> bool:
    """Save stock data to MongoDB database"""
    if not MONGODB_AVAILABLE:
        return False
    
    try:
        # Prepare document for MongoDB
        document = {
            'symbol': symbol.upper(),
            'data': stock_data,
            'updated_at': datetime.utcnow(),
            'source': 'yfinance',
            'last_fetched': datetime.utcnow()
        }
        
        # Upsert the document (insert if not exists, update if exists)
        result = collection.replace_one(
            {'symbol': symbol.upper()},
            document,
            upsert=True
        )
        
        logger.info(f"Saved {symbol} to MongoDB database")
        return True
    except Exception as e:
        logger.error(f"Error saving to MongoDB database for {symbol}: {e}")
        return False

def get_historical_prices_from_database(symbol: str, start_date: str, end_date: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieve historical prices from MongoDB database"""
    if not MONGODB_AVAILABLE:
        return None
    
    try:
        # Convert date strings to datetime objects for comparison
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Query for prices within the date range
        stored_prices = list(prices_collection.find({
            'symbol': symbol.upper(),
            'date': {
                '$gte': start_dt,
                '$lte': end_dt
            }
        }).sort('date', 1))
        
        if stored_prices:
            logger.info(f"Retrieved {len(stored_prices)} historical prices for {symbol} from MongoDB")
            # Remove MongoDB _id field from response
            for price in stored_prices:
                price.pop('_id', None)
            return stored_prices
        
        return None
    except Exception as e:
        logger.error(f"Error retrieving historical prices from MongoDB for {symbol}: {e}")
        return None

def save_historical_prices_to_database(symbol: str, prices_data: List[Dict[str, Any]]) -> bool:
    """Save historical prices to MongoDB database"""
    if not MONGODB_AVAILABLE:
        return False
    
    try:
        # Prepare documents for MongoDB
        documents = []
        for price_data in prices_data:
            # Convert date string to datetime object
            date_str = price_data.get('Date', '')
            if date_str:
                try:
                    date_dt = datetime.strptime(str(date_str).split(' ')[0], '%Y-%m-%d')
                except:
                    continue
            else:
                continue
            
            document = {
                'symbol': symbol.upper(),
                'date': date_dt,
                'open': price_data.get('Open'),
                'high': price_data.get('High'),
                'low': price_data.get('Low'),
                'close': price_data.get('Close'),
                'volume': price_data.get('Volume'),
                'adj_close': price_data.get('Adj Close'),
                'source': 'yfinance'
            }
            documents.append(document)
        
        if documents:
            # Use bulk operations for better performance
            operations = [
                ReplaceOne(
                    {'symbol': doc['symbol'], 'date': doc['date']},
                    doc,
                    upsert=True
                ) for doc in documents
            ]
            
            result = prices_collection.bulk_write(operations)
            
            logger.info(f"Saved {len(documents)} historical prices for {symbol} to MongoDB")
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error saving historical prices to MongoDB for {symbol}: {e}")
        return False

def get_stock_data_from_yahoo(symbol: str) -> Optional[Dict[str, Any]]:
    """Retrieve stock data from yfinance"""
    ticker = None
    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info
        
        # Check if we got valid data
        if not info or len(info) < 5:  # Basic check for valid response
            logger.warning(f"No valid data received for symbol: {symbol}")
            return None
            
        return info
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        return None
    finally:
        # Clean up ticker object to free memory
        if ticker:
            del ticker

def get_historical_prices_from_yahoo(symbol: str, start_date: str, end_date: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieve historical prices from yfinance"""
    ticker = None
    hist = None
    try:
        ticker = yf.Ticker(symbol.upper())
        
        # Get historical data
        hist = ticker.history(start=start_date, end=end_date, auto_adjust=False)
        
        if hist.empty:
            logger.warning(f"No historical data received for symbol: {symbol}")
            return None
        
        # Convert DataFrame to list of dictionaries
        prices_data = []
        for date, row in hist.iterrows():
            price_data = {
                'Date': date.strftime('%Y-%m-%d'),
                'Open': round(float(row['Open']), 2) if not pd.isna(row['Open']) else None,
                'High': round(float(row['High']), 2) if not pd.isna(row['High']) else None,
                'Low': round(float(row['Low']), 2) if not pd.isna(row['Low']) else None,
                'Close': round(float(row['Close']), 2) if not pd.isna(row['Close']) else None,
                'Volume': int(row['Volume']) if not pd.isna(row['Volume']) else None,
                'Adj Close': round(float(row['Adj Close']), 2) if not pd.isna(row['Adj Close']) else None
            }
            prices_data.append(price_data)
        
        logger.info(f"Retrieved {len(prices_data)} historical prices for {symbol} from Yahoo Finance")
        return prices_data
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
        return None
    finally:
        # Clean up objects to free memory
        if hist is not None:
            del hist
        if ticker is not None:
            del ticker
        # Force garbage collection
        import gc
        gc.collect()

def get_stock_data(symbol: str) -> Optional[Dict[str, Any]]:
    """Get stock data with MongoDB storage"""
    # First, try to get from database
    stored_data = get_stock_from_database(symbol)
    if stored_data:
        return stored_data
    
    # If not in database, fetch from Yahoo
    logger.info(f"Symbol {symbol} not found in database, fetching from Yahoo Finance")
    yahoo_data = get_stock_data_from_yahoo(symbol)
    
    if yahoo_data:
        # Save to database for future requests
        save_stock_to_database(symbol, yahoo_data)
        return yahoo_data
    
    return None

def get_historical_prices(symbol: str, start_date: str, end_date: str) -> Optional[List[Dict[str, Any]]]:
    """Get historical prices with MongoDB storage"""
    # First, try to get from database
    stored_prices = get_historical_prices_from_database(symbol, start_date, end_date)
    if stored_prices:
        return stored_prices
    
    # If not in database, fetch from Yahoo
    logger.info(f"Historical prices for {symbol} not found in database, fetching from Yahoo Finance")
    yahoo_prices = get_historical_prices_from_yahoo(symbol, start_date, end_date)
    
    if yahoo_prices:
        # Save to database for future requests
        save_historical_prices_to_database(symbol, yahoo_prices)
        return yahoo_prices
    
    return None

def get_market_status() -> Dict[str, Any]:
    """Get current market status (open/closed)"""
    try:
        # Use a major index to determine market status
        # S&P 500 is a good indicator for US market status
        sp500 = yf.Ticker("SPY")
        info = sp500.info
        
        # Check if market is open based on regularMarketState
        market_state = info.get('marketState', 'unknown')
        
        # Map market states to our format
        if market_state == 'REGULAR':
            status = 'open'
        elif market_state in ['PRE', 'PREPRE']:
            status = 'pre_market'
        elif market_state in ['POST', 'POSTPOST']:
            status = 'after_hours'
        elif market_state == 'CLOSED':
            status = 'closed'
        else:
            status = 'unknown'
        
        return {
            'status': status,
            'market_state': market_state,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting market status: {e}")
        return {
            'status': 'unknown',
            'market_state': 'unknown',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }

def get_index_data(symbol: str) -> Optional[Dict[str, Any]]:
    """Get index data for a specific symbol"""
    ticker = None
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Extract relevant index information
        index_data = {
            'symbol': symbol,
            'name': info.get('longName', info.get('shortName', symbol)),
            'current_price': info.get('regularMarketPrice'),
            'previous_close': info.get('previousClose'),
            'open': info.get('open'),
            'day_high': info.get('dayHigh'),
            'day_low': info.get('dayLow'),
            'volume': info.get('volume'),
            'currency': info.get('currency', 'USD'),
            'regular_market_state': info.get('marketState'),
            'regular_market_time': info.get('regularMarketTime'),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return index_data
    except Exception as e:
        logger.error(f"Error fetching index data for {symbol}: {str(e)}")
        return None
    finally:
        # Clean up ticker object to free memory
        if ticker:
            del ticker

def get_market_information() -> Dict[str, Any]:
    """Get comprehensive market information including major indices"""
    try:
        # Get market status
        market_status = get_market_status()
        
        # Define major indices
        indices = {
            'dow_jones': '^DJI',
            'nasdaq': '^IXIC', 
            'sp500': '^GSPC'
        }
        
        # Get data for each index
        index_data = {}
        for index_name, symbol in indices.items():
            data = get_index_data(symbol)
            if data:
                index_data[index_name] = data
        
        # Compile market information
        market_info = {
            'market_status': market_status,
            'indices': index_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return market_info
    except Exception as e:
        logger.error(f"Error getting market information: {e}")
        return {
            'error': 'Failed to retrieve market information',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }

# Simple cache for health check responses
_health_cache = {"response": None, "timestamp": None, "ttl": 30}  # 30 second TTL

@app.route('/health')
def health_check():
    """Health check endpoint - lightweight version for probes with caching"""
    current_time = datetime.utcnow()
    
    # Return cached response if still valid
    if (_health_cache["response"] and _health_cache["timestamp"] and 
        (current_time - _health_cache["timestamp"]).total_seconds() < _health_cache["ttl"]):
        return _health_cache["response"]
    
    # Create new response
    response = jsonify({
        "status": "healthy",
        "service": "finance-scraper-api"
    }), 200
    
    # Cache the response
    _health_cache["response"] = response
    _health_cache["timestamp"] = current_time
    
    return response

@app.route('/health/detailed')
def detailed_health_check():
    """Detailed health check endpoint with MongoDB status"""
    mongodb_status = "connected" if MONGODB_AVAILABLE else "disconnected"
    
    # Get memory usage information
    import psutil
    import os
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    return jsonify({
        "status": "healthy",
        "service": "finance-scraper-api",
        "mongodb": mongodb_status,
        "memory": {
            "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            "percent": round(process.memory_percent(), 2)
        }
    }), 200

@app.route('/health/memory-cleanup', methods=['POST'])
def memory_cleanup():
    """Force garbage collection to free memory"""
    try:
        import gc
        import psutil
        import os
        
        # Get memory before cleanup
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024
        
        # Force garbage collection
        collected = gc.collect()
        
        # Get memory after cleanup
        memory_after = process.memory_info().rss / 1024 / 1024
        memory_freed = memory_before - memory_after
        
        return jsonify({
            "status": "success",
            "message": "Memory cleanup completed",
            "garbage_collected": collected,
            "memory_freed_mb": round(memory_freed, 2),
            "memory_before_mb": round(memory_before, 2),
            "memory_after_mb": round(memory_after, 2)
        }), 200
    except Exception as e:
        logger.error(f"Error during memory cleanup: {e}")
        return jsonify({
            "error": "Memory cleanup failed",
            "message": str(e)
        }), 500

@app.route('/stock/<symbol>')
def get_stock_info(symbol: str):
    """Get stock information for a given symbol with MongoDB storage"""
    try:
        # Validate input
        if not validate_symbol(symbol):
            return jsonify({
                "error": "Invalid symbol format",
                "symbol": symbol
            }), 400
        
        logger.info(f"Fetching stock data for symbol: {symbol}")
        
        # Get stock data (with database storage)
        stock_data = get_stock_data(symbol)
        
        if stock_data is None:
            return jsonify({
                "error": "Unable to fetch stock data",
                "symbol": symbol
            }), 404
        
        return jsonify({
            "symbol": symbol.upper(),
            "data": stock_data
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error processing request for {symbol}: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "symbol": symbol
        }), 500

@app.route('/stock/<symbol>/price')
def get_stock_price(symbol: str):
    """Get current stock price for a given symbol"""
    try:
        # Validate input
        if not validate_symbol(symbol):
            return jsonify({
                "error": "Invalid symbol format",
                "symbol": symbol
            }), 400
        
        logger.info(f"Fetching stock price for symbol: {symbol}")
        
        # Get stock data (with database storage)
        stock_data = get_stock_data(symbol)
        
        if stock_data is None:
            return jsonify({
                "error": "Unable to fetch stock data",
                "symbol": symbol
            }), 404
        
        # Extract price information
        price_info = {
            "symbol": symbol.upper(),
            "current_price": stock_data.get('currentPrice'),
            "previous_close": stock_data.get('previousClose'),
            "open": stock_data.get('open'),
            "day_high": stock_data.get('dayHigh'),
            "day_low": stock_data.get('dayLow'),
            "volume": stock_data.get('volume'),
            "market_cap": stock_data.get('marketCap'),
            "currency": stock_data.get('currency', 'USD')
        }
        
        return jsonify(price_info), 200
        
    except Exception as e:
        logger.error(f"Unexpected error processing price request for {symbol}: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "symbol": symbol
        }), 500

@app.route('/stock/<symbol>/history')
def get_historical_prices_endpoint(symbol: str):
    """Get historical prices for a given symbol with date range"""
    try:
        # Validate symbol
        if not validate_symbol(symbol):
            return jsonify({
                "error": "Invalid symbol format",
                "symbol": symbol
            }), 400
        
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Validate required parameters
        if not start_date or not end_date:
            return jsonify({
                "error": "Missing required parameters",
                "required": ["start_date", "end_date"],
                "format": "YYYY-MM-DD"
            }), 400
        
        # Validate date format
        if not validate_date_format(start_date) or not validate_date_format(end_date):
            return jsonify({
                "error": "Invalid date format",
                "format": "YYYY-MM-DD",
                "received": {
                    "start_date": start_date,
                    "end_date": end_date
                }
            }), 400
        
        # Validate date range
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        if start_dt > end_dt:
            return jsonify({
                "error": "Invalid date range",
                "start_date": start_date,
                "end_date": end_date
            }), 400
        
        # Check date range size to prevent memory issues (max 5 years)
        days_diff = (end_dt - start_dt).days
        if days_diff > 1825:  # 5 years
            return jsonify({
                "error": "Date range too large",
                "max_days": 1825,
                "requested_days": days_diff,
                "suggestion": "Please request smaller date ranges"
            }), 400
        
        logger.info(f"Fetching historical prices for {symbol} from {start_date} to {end_date}")
        
        # Get historical prices (with database storage)
        prices_data = get_historical_prices(symbol, start_date, end_date)
        
        if prices_data is None:
            return jsonify({
                "error": "Unable to fetch historical prices",
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date
            }), 404
        
        # Check result size to prevent memory issues
        if len(prices_data) > 10000:  # Max 10,000 price records
            logger.warning(f"Large dataset returned for {symbol}: {len(prices_data)} records")
        
        return jsonify({
            "symbol": symbol.upper(),
            "start_date": start_date,
            "end_date": end_date,
            "count": len(prices_data),
            "prices": prices_data
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error processing historical prices request for {symbol}: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "symbol": symbol
        }), 500

@app.route('/market')
def get_market_info():
    """Get general market information including major indices"""
    try:
        logger.info("Fetching market information")
        
        # Get comprehensive market information
        market_info = get_market_information()
        
        if 'error' in market_info:
            return jsonify(market_info), 500
        
        return jsonify(market_info), 200
        
    except Exception as e:
        logger.error(f"Unexpected error processing market information request: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.route('/market/status')
def get_market_status_endpoint():
    """Get current market status only"""
    try:
        logger.info("Fetching market status")
        
        # Get market status
        market_status = get_market_status()
        
        return jsonify(market_status), 200
        
    except Exception as e:
        logger.error(f"Unexpected error processing market status request: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.route('/market/indices')
def get_market_indices():
    """Get major indices data only"""
    try:
        logger.info("Fetching market indices")
        
        # Define major indices
        indices = {
            'dow_jones': '^DJI',
            'nasdaq': '^IXIC', 
            'sp500': '^GSPC'
        }
        
        # Get data for each index
        index_data = {}
        for index_name, symbol in indices.items():
            data = get_index_data(symbol)
            if data:
                index_data[index_name] = data
        
        return jsonify({
            'indices': index_data,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error processing market indices request: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.route('/database/clear/<symbol>')
def clear_database_entry(symbol: str):
    """Remove a specific symbol from the database"""
    if not MONGODB_AVAILABLE:
        return jsonify({
            "error": "MongoDB not available",
            "symbol": symbol
        }), 503
    
    try:
        result = collection.delete_one({'symbol': symbol.upper()})
        if result.deleted_count > 0:
            logger.info(f"Removed {symbol} from database")
            return jsonify({
                "message": "Symbol removed from database successfully",
                "symbol": symbol
            }), 200
        else:
            return jsonify({
                "message": "Symbol not found in database",
                "symbol": symbol
            }), 404
    except Exception as e:
        logger.error(f"Error removing symbol from database: {e}")
        return jsonify({
            "error": "Internal server error",
            "symbol": symbol
        }), 500

@app.route('/database/clear')
def clear_database():
    """Clear all data from the database"""
    if not MONGODB_AVAILABLE:
        return jsonify({
            "error": "MongoDB not available"
        }), 503
    
    try:
        result = collection.delete_many({})
        logger.info(f"Cleared all data from database, deleted {result.deleted_count} documents")
        return jsonify({
            "message": "All data cleared from database successfully",
            "deleted_count": result.deleted_count
        }), 200
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        return jsonify({
            "error": "Internal server error"
        }), 500

@app.route('/database/stats')
def database_stats():
    """Get database statistics"""
    if not MONGODB_AVAILABLE:
        return jsonify({
            "error": "MongoDB not available"
        }), 503
    
    try:
        total_documents = collection.count_documents({})
        total_prices = prices_collection.count_documents({})
        latest_update = collection.find_one(
            sort=[('updated_at', -1)]
        )
        latest_price = prices_collection.find_one(
            sort=[('fetched_at', -1)]
        )
        
        stats = {
            "total_symbols": total_documents,
            "total_price_records": total_prices,
            "database": DB_NAME,
            "collections": {
                "stock_info": COLLECTION_NAME,
                "stock_prices": PRICES_COLLECTION_NAME
            },
            "auth_source": AUTHENTICATION_SOURCE
        }
        
        if latest_update:
            stats["latest_update"] = latest_update.get('updated_at')
            stats["latest_symbol"] = latest_update.get('symbol')
        
        if latest_price:
            stats["latest_price_update"] = latest_price.get('fetched_at')
            stats["latest_price_symbol"] = latest_price.get('symbol')
        
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return jsonify({
            "error": "Internal server error"
        }), 500


def get_scheduler_api_url():
    """Get the scheduler API URL"""
    scheduler_host = os.environ.get('SCHEDULER_API_HOST', 'finance-scraper-scheduler')
    scheduler_port = os.environ.get('SCHEDULER_API_PORT', '5001')
    return f"http://{scheduler_host}:{scheduler_port}"

def call_scheduler_api(endpoint, method='GET', data=None):
    """Make a call to the scheduler API"""
    try:
        import requests
        url = f"{get_scheduler_api_url()}{endpoint}"
        
        if method == 'GET':
            response = requests.get(url, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=10)
        else:
            return None, "Unsupported method"
        
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error calling scheduler API: {e}")
        return None, 500



@app.route('/scheduler/status')
def scheduler_status():
    """Get scheduler status"""
    # API pod always communicates with scheduler API
    response_data, status_code = call_scheduler_api('/status')
    
    if response_data:
        response_data['mode'] = 'separate'
        return jsonify(response_data), status_code
    else:
        return jsonify({
            "status": "error",
            "message": "Cannot connect to scheduler API",
            "mode": "separate"
        }), 500

@app.route('/scheduler/start', methods=['POST'])
def start_scheduler():
    """Start the scheduler"""
    # API pod always communicates with scheduler API
    response_data, status_code = call_scheduler_api('/start', method='POST')
    
    if response_data:
        return jsonify(response_data), status_code
    else:
        return jsonify({
            "error": "Cannot connect to scheduler API"
        }), 500

@app.route('/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """Stop the scheduler"""
    # API pod always communicates with scheduler API
    response_data, status_code = call_scheduler_api('/stop', method='POST')
    
    if response_data:
        return jsonify(response_data), status_code
    else:
        return jsonify({
            "error": "Cannot connect to scheduler API"
        }), 500

@app.route('/scheduler/run-now', methods=['POST'])
def run_scheduler_now():
    """Run scheduler cycle immediately"""
    # API pod always communicates with scheduler API
    response_data, status_code = call_scheduler_api('/run-now', method='POST')
    
    if response_data:
        return jsonify(response_data), status_code
    else:
        return jsonify({
            "error": "Cannot connect to scheduler API"
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": [
            "/health",
            "/stock/<symbol>",
            "/stock/<symbol>/price",
            "/stock/<symbol>/history?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD",
            "/market",
            "/market/status",
            "/market/indices",
            "/database/clear/<symbol>",
            "/database/clear",
            "/database/stats",
            "/scheduler/status",
            "/scheduler/start (POST)",
            "/scheduler/stop (POST)",
            "/scheduler/run-now (POST)"
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        "error": "Internal server error"
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    # Enable garbage collection for memory management
    import gc
    gc.enable()
    
    # Set garbage collection thresholds for better memory management
    gc.set_threshold(700, 10, 10)  # More aggressive collection
    
    # Initialize scheduler if enabled
    if os.environ.get('ENABLE_SCHEDULER', 'false').lower() == 'true':
        try:
            from scheduler import create_scheduler_from_env
            _scheduler = create_scheduler_from_env()
            _scheduler.start()
            logger.info("Scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
    
    logger.info(f"Starting Finance Scraper API on port {port}")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=debug)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        if '_scheduler' in globals():
            _scheduler.stop()
        logger.info("Application stopped")
