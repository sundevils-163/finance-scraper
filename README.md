# Finance Scraper API

A Flask-based API for retrieving stock information using Yahoo Finance (yfinance) with MongoDB persistent storage.

## Features

- **Stock Information**: Retrieve comprehensive stock data for any symbol
- **Current Price**: Get current stock price and basic market data
- **Historical Prices**: Retrieve historical price data with date range filtering
- **MongoDB Storage**: Persistent storage of stock data and historical prices
- **Database Management**: Clear specific symbols or all data from database
- **Health Monitoring**: Health check endpoint for monitoring
- **Kubernetes Ready**: Complete Helm chart for Kubernetes deployment

## API Endpoints

### Health Check
```
GET /health
```
Returns the health status of the API and MongoDB connection.

### Stock Information
```
GET /stock/{symbol}
```
Retrieves comprehensive stock information for a given symbol.

**Example:**
```bash
curl http://localhost:5000/stock/AAPL
```

### Current Stock Price
```
GET /stock/{symbol}/price
```
Retrieves current price and basic market data for a given symbol.

**Example:**
```bash
curl http://localhost:5000/stock/AAPL/price
```

### Historical Prices
```
GET /stock/{symbol}/history?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```
Retrieves historical price data for a given symbol within a specified date range.

**Parameters:**
- `start_date`: Start date in YYYY-MM-DD format
- `end_date`: End date in YYYY-MM-DD format

**Example:**
```bash
curl "http://localhost:5000/stock/AAPL/history?start_date=2024-01-01&end_date=2024-01-31"
```

**Response:**
```json
{
  "symbol": "AAPL",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "count": 22,
  "prices": [
    {
      "Date": "2024-01-02",
      "Open": 185.59,
      "High": 186.12,
      "Low": 183.62,
      "Close": 185.14,
      "Volume": 52455980,
      "Adj Close": 185.14
    }
  ]
}
```

### Database Management

#### Database Statistics
```
GET /database/stats
```
Returns statistics about the database including total symbols and price records stored.

#### Clear Specific Symbol
```
GET /database/clear/{symbol}
```
Removes a specific symbol from the database.

#### Clear All Data
```
GET /database/clear
```
Removes all data from the database.

## MongoDB Collections

The API uses two MongoDB collections:

1. **stock-info**: Stores comprehensive stock information
   - Document structure includes symbol, data, updated_at, source, and last_fetched fields

2. **stock-prices**: Stores historical price data
   - Document structure includes symbol, date, open, high, low, close, volume, adj_close, source, and fetched_at fields

## Data Flow

1. **Stock Information**: 
   - First checks MongoDB for existing data
   - If not found, fetches from Yahoo Finance and saves to MongoDB
   - Returns cached data for subsequent requests

2. **Historical Prices**:
   - First checks MongoDB for existing price data within the date range
   - If not found, fetches from Yahoo Finance and saves to MongoDB
   - Returns cached data for subsequent requests

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB connection URI | `mongodb://mongodb.lan:27017/` |
| `MONGODB_DB` | Database name | `epicurus-stock-io` |
| `MONGODB_COLLECTION` | Stock info collection name | `stock-info` |
| `MONGODB_PRICES_COLLECTION` | Stock prices collection name | `stock-prices` |
| `AUTHENTICATION_SOURCE` | MongoDB authentication source | `epicurus-stock-io` |
| `MONGODB_USERNAME` | MongoDB username | - |
| `MONGODB_PASSWORD` | MongoDB password | - |
| `PORT` | Application port | `5000` |
| `FLASK_ENV` | Flask environment | - |

## Local Development

### Prerequisites
- Python 3.8+
- MongoDB instance (optional for development)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd finance-scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables (optional):
```bash
export MONGODB_URI="mongodb://localhost:27017/"
export MONGODB_DB="finance_db"
```

4. Run the application:
```bash
python app.py
```

The API will be available at `http://localhost:5000`

### Testing

Run the test suite:
```bash
python test_api.py
```

## Docker Deployment

### Build the image:
```bash
docker build -t finance-scraper .
```

### Run the container:
```bash
docker run -p 5000:5000 \
  -e MONGODB_URI="mongodb://your-mongodb-host:27017/" \
  -e MONGODB_USERNAME="your-username" \
  -e MONGODB_PASSWORD="your-password" \
  finance-scraper
```

## Kubernetes Deployment

### Prerequisites
- Kubernetes cluster
- Helm 3.x
- MongoDB instance

### Deploy with Helm

1. Create a values file (`my-values.yaml`):
```yaml
mongodb:
  uri: "mongodb://your-mongodb-host:27017/"
  db: "finance_db"
  collection: "stock-info"
  prices_collection: "stock-prices"
  authentication_source: "admin"
  username: "your-username"
  password: "your-password"

ingress:
  enabled: true
  hosts:
    - host: finance-api.your-domain.com
      paths:
        - path: /
          pathType: Prefix
```

2. Create the MongoDB secret:
```bash
kubectl create secret generic finance-scraper-secret \
  --from-literal=MONGODB_USERNAME=your-username \
  --from-literal=MONGODB_PASSWORD=your-password
```

3. Deploy the application:
```bash
helm install finance-scraper ./helm/finance-scraper -f my-values.yaml
```

### Using the Makefile

```bash
# Build and deploy
make deploy

# Update deployment
make upgrade

# Remove deployment
make uninstall

# View logs
make logs

# Test the API
make test
```

## API Response Examples

### Stock Information Response
```json
{
  "symbol": "AAPL",
  "data": {
    "longName": "Apple Inc.",
    "currentPrice": 185.14,
    "previousClose": 185.64,
    "open": 185.59,
    "dayHigh": 186.12,
    "dayLow": 183.62,
    "volume": 52455980,
    "marketCap": 2890000000000,
    "currency": "USD"
  }
}
```

### Current Price Response
```json
{
  "symbol": "AAPL",
  "current_price": 185.14,
  "previous_close": 185.64,
  "open": 185.59,
  "day_high": 186.12,
  "day_low": 183.62,
  "volume": 52455980,
  "market_cap": 2890000000000,
  "currency": "USD"
}
```

### Database Stats Response
```json
{
  "total_symbols": 5,
  "total_price_records": 1250,
  "database": "epicurus-stock-io",
  "collections": {
    "stock_info": "stock-info",
    "stock_prices": "stock-prices"
  },
  "auth_source": "epicurus-stock-io",
  "latest_update": "2024-01-15T10:30:00Z",
  "latest_symbol": "AAPL",
  "latest_price_update": "2024-01-15T10:25:00Z",
  "latest_price_symbol": "AAPL"
}
```

## Error Handling

The API provides comprehensive error handling:

- **400 Bad Request**: Invalid symbol format or missing required parameters
- **404 Not Found**: Symbol not found or no data available
- **500 Internal Server Error**: Unexpected server errors
- **503 Service Unavailable**: MongoDB connection issues

## Monitoring

The application includes:
- Structured logging with timestamps
- Health check endpoint for monitoring
- Database statistics for operational insights
- Error tracking and reporting

## Security Considerations

- Non-root container execution
- Environment variable-based configuration
- Kubernetes secrets for sensitive data
- Input validation and sanitization
- Error message sanitization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License. 