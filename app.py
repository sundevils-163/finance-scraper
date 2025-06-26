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
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

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
    # Create MongoDB client with authentication source
    mongo_client = MongoClient(
        MONGODB_URI, 
        serverSelectionTimeoutMS=5000,
        authSource=AUTHENTICATION_SOURCE
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
                'source': 'yfinance',
                'fetched_at': datetime.utcnow()
            }
            documents.append(document)
        
        if documents:
            # Use bulk operations for better performance
            result = prices_collection.bulk_write([
                {
                    'replaceOne': {
                        'filter': {
                            'symbol': doc['symbol'],
                            'date': doc['date']
                        },
                        'replacement': doc,
                        'upsert': True
                    }
                } for doc in documents
            ])
            
            logger.info(f"Saved {len(documents)} historical prices for {symbol} to MongoDB")
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error saving historical prices to MongoDB for {symbol}: {e}")
        return False

def get_stock_data_from_yahoo(symbol: str) -> Optional[Dict[str, Any]]:
    """Retrieve stock data from yfinance"""
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

def get_historical_prices_from_yahoo(symbol: str, start_date: str, end_date: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieve historical prices from yfinance"""
    try:
        ticker = yf.Ticker(symbol.upper())
        
        # Get historical data
        hist = ticker.history(start=start_date, end=end_date)
        
        if hist.empty:
            logger.warning(f"No historical data received for symbol: {symbol}")
            return None
        
        # Convert DataFrame to list of dictionaries
        prices_data = []
        for date, row in hist.iterrows():
            price_data = {
                'Date': date.strftime('%Y-%m-%d'),
                'Open': float(row['Open']) if not pd.isna(row['Open']) else None,
                'High': float(row['High']) if not pd.isna(row['High']) else None,
                'Low': float(row['Low']) if not pd.isna(row['Low']) else None,
                'Close': float(row['Close']) if not pd.isna(row['Close']) else None,
                'Volume': int(row['Volume']) if not pd.isna(row['Volume']) else None,
                'Adj Close': float(row['Adj Close']) if not pd.isna(row['Adj Close']) else None
            }
            prices_data.append(price_data)
        
        logger.info(f"Retrieved {len(prices_data)} historical prices for {symbol} from Yahoo Finance")
        return prices_data
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
        return None

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

@app.route('/health')
def health_check():
    """Health check endpoint"""
    mongodb_status = "connected" if MONGODB_AVAILABLE else "disconnected"
    return jsonify({
        "status": "healthy",
        "service": "finance-scraper-api",
        "mongodb": mongodb_status
    }), 200

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
            "/database/clear/<symbol>",
            "/database/clear",
            "/database/stats"
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
    
    logger.info(f"Starting Finance Scraper API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
