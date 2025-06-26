# Finance Scraper API

A production-ready Flask API that retrieves stock information using the yfinance library with MongoDB persistent storage. This project includes a complete Kubernetes deployment setup with Helm charts.

## Features

- **Stock Information API**: Get comprehensive stock data from Yahoo Finance
- **MongoDB Storage**: Persistent storage layer to reduce API calls and improve performance
- **Price Endpoint**: Dedicated endpoint for current stock prices and metrics
- **Health Checks**: Built-in health monitoring endpoints
- **Database Management**: Endpoints to manage stored data and view statistics
- **Production Ready**: Multi-stage Docker build with security best practices
- **Kubernetes Native**: Complete Helm chart for easy deployment
- **Auto-scaling**: Horizontal Pod Autoscaler for dynamic scaling
- **Monitoring Ready**: Prometheus ServiceMonitor support
- **Security**: Non-root execution, read-only filesystem, dropped capabilities
- **Secret Management**: Kubernetes secrets for MongoDB credentials

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set MongoDB environment variables (optional)
export MONGODB_URI="mongodb://username:password@localhost:27017/"
export MONGODB_DB="epicurus-stock-io"
export MONGODB_COLLECTION="stock-info"

# Run the application
python app.py

# Test the API
curl http://localhost:5000/health
curl http://localhost:5000/stock/AAPL
curl http://localhost:5000/stock/AAPL/price
```

### Docker Deployment

```bash
# Build the image
docker build -t finance-scraper:latest .

# Run the container
docker run -p 8080:5000 finance-scraper:latest

# Test the API
curl http://localhost:8080/health
```

### Kubernetes Deployment

#### 1. Create MongoDB Secret

First, create the Kubernetes secret with your MongoDB credentials:

```bash
# Create the secret with your actual credentials
kubectl create secret generic finance-scraper-mongodb-secret \
  --from-literal=MONGODB_URI="mongodb://username:password@mongodb.lan:27017/" \
  --from-literal=MONGODB_USERNAME="your-mongodb-username" \
  --from-literal=MONGODB_PASSWORD="your-mongodb-password"
```

#### 2. Deploy the Application

```bash
# Use the deployment script
./deploy.sh

# Or deploy manually
docker build -t finance-scraper:latest .
helm install finance-scraper ./helm/finance-scraper

# Port forward to access the service
kubectl port-forward deployment/finance-scraper 8080:5000
```

## API Endpoints

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "finance-scraper-api",
  "mongodb": "connected"
}
```

### Stock Information (with storage)
```http
GET /stock/{symbol}
```

**Example:**
```bash
curl http://localhost:5000/stock/AAPL
```

**Response:**
```json
{
  "symbol": "AAPL",
  "data": {
    "currentPrice": 150.25,
    "previousClose": 148.50,
    "open": 149.00,
    "dayHigh": 152.00,
    "dayLow": 148.25,
    "volume": 12345678,
    "marketCap": 2500000000000,
    "currency": "USD",
    // ... more fields
  }
}
```

### Stock Price (with storage)
```http
GET /stock/{symbol}/price
```

**Example:**
```bash
curl http://localhost:5000/stock/AAPL/price
```

**Response:**
```json
{
  "symbol": "AAPL",
  "current_price": 150.25,
  "previous_close": 148.50,
  "open": 149.00,
  "day_high": 152.00,
  "day_low": 148.25,
  "volume": 12345678,
  "market_cap": 2500000000000,
  "currency": "USD"
}
```

### Database Management

#### Database Statistics
```http
GET /database/stats
```

**Example:**
```bash
curl http://localhost:5000/database/stats
```

**Response:**
```json
{
  "total_symbols": 15,
  "database": "epicurus-stock-io",
  "collection": "stock-info",
  "latest_update": "2024-01-15T10:30:00Z",
  "latest_symbol": "AAPL"
}
```

#### Remove Specific Symbol
```http
DELETE /database/clear/{symbol}
```

**Example:**
```bash
curl -X DELETE http://localhost:5000/database/clear/AAPL
```

**Response:**
```json
{
  "message": "Symbol removed from database successfully",
  "symbol": "AAPL"
}
```

#### Clear All Data
```http
DELETE /database/clear
```

**Example:**
```bash
curl -X DELETE http://localhost:5000/database/clear
```

**Response:**
```json
{
  "message": "All data cleared from database successfully",
  "deleted_count": 15
}
```

## MongoDB Storage

The application implements persistent storage using MongoDB:

### How it works:
1. **First Request** for `AAPL`:
   - Check MongoDB for existing data
   - If not found → fetch from Yahoo Finance
   - Save to MongoDB with timestamp
   - Return data

2. **Subsequent Requests** for `AAPL`:
   - Check MongoDB for existing data
   - If found → return stored data instantly
   - No Yahoo Finance API call needed

### Storage Configuration:
- **Database**: `epicurus-stock-io`
- **Collection**: `stock-info`
- **Connection**: `mongodb.lan:27017` (with authentication)
- **Credentials**: Stored in Kubernetes secrets

### Environment Variables:
- `MONGODB_URI`: MongoDB connection string (from secret)
- `MONGODB_USERNAME`: MongoDB username (from secret)
- `MONGODB_PASSWORD`: MongoDB password (from secret)
- `MONGODB_DB`: Database name
- `MONGODB_COLLECTION`: Collection name

### Benefits:
- ✅ **Faster Response Times**: Stored data returns instantly
- ✅ **Reduced API Calls**: Fewer requests to Yahoo Finance
- ✅ **Persistent Storage**: Data survives pod restarts
- ✅ **Better Reliability**: Graceful fallback if MongoDB is unavailable
- ✅ **Data Analytics**: Stored data can be used for other purposes

## Project Structure

```
finance-scraper/
├── app.py                 # Main Flask application with MongoDB storage
├── requirements.txt       # Python dependencies including pymongo
├── Dockerfile            # Multi-stage Docker build
├── .dockerignore         # Docker build exclusions
├── deploy.sh             # Deployment automation script
├── test_api.py           # Comprehensive API testing
├── Makefile              # Development and deployment commands
├── README.md             # This file
└── helm/
    └── finance-scraper/  # Helm chart
        ├── Chart.yaml
        ├── values.yaml
        ├── README.md
        ├── templates/
        │   ├── deployment.yaml
        │   ├── service.yaml
        │   ├── ingress.yaml
        │   ├── hpa.yaml
        │   ├── pdb.yaml
        │   ├── configmap.yaml
        │   ├── secret.yaml
        │   ├── servicemonitor.yaml
        │   ├── networkpolicy.yaml
        │   ├── _helpers.tpl
        │   └── NOTES.txt
        └── secret-example.yaml  # Example secret manifest
```

## Configuration

### Environment Variables

- `PORT`: Application port (default: 5000)
- `FLASK_ENV`: Environment mode (development/production)
- `MONGODB_URI`: MongoDB connection string (from secret)
- `MONGODB_USERNAME`: MongoDB username (from secret)
- `MONGODB_PASSWORD`: MongoDB password (from secret)
- `MONGODB_DB`: Database name (default: epicurus-stock-io)
- `MONGODB_COLLECTION`: Collection name (default: stock-info)

### Helm Values

The Helm chart supports extensive customization through `values.yaml`:

```yaml
# Basic configuration
replicaCount: 2
image:
  repository: finance-scraper
  tag: "latest"

# MongoDB configuration (non-sensitive)
env:
  - name: MONGODB_DB
    value: "epicurus-stock-io"
  - name: MONGODB_COLLECTION
    value: "stock-info"

# Service configuration
service:
  type: ClusterIP
  port: 80

# Ingress configuration
ingress:
  enabled: true
  className: "nginx"

# Resource limits
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi

# Auto-scaling
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
```

### Kubernetes Secret Setup

The application expects a secret named `finance-scraper-mongodb-secret` with the following keys:

```bash
# Create the secret
kubectl create secret generic finance-scraper-mongodb-secret \
  --from-literal=MONGODB_URI="mongodb://username:password@mongodb.lan:27017/" \
  --from-literal=MONGODB_USERNAME="your-username" \
  --from-literal=MONGODB_PASSWORD="your-password"
```

## Security Features

- **Non-root execution**: Application runs as non-root user
- **Read-only filesystem**: Container filesystem is read-only
- **Dropped capabilities**: All Linux capabilities are dropped
- **Pod security context**: Kubernetes security policies applied
- **Network policies**: Optional network isolation
- **Input validation**: Symbol validation and sanitization
- **Secret management**: MongoDB credentials stored in Kubernetes secrets

## Monitoring

### Health Checks

- **Liveness probe**: `/health` endpoint
- **Readiness probe**: `/health` endpoint
- **Docker health check**: Built into container
- **MongoDB status**: Included in health check response

### Prometheus Integration

Enable ServiceMonitor in values.yaml:

```yaml
serviceMonitor:
  enabled: true
  interval: 30s
  path: /health
  port: http
```

## Scaling

### Horizontal Pod Autoscaler

The application includes an HPA that scales based on CPU and memory utilization:

```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
  targetMemoryUtilizationPercentage: 80
```

### Manual Scaling

```bash
# Scale to 5 replicas
kubectl scale deployment finance-scraper --replicas=5

# Or using Helm
helm upgrade finance-scraper ./helm/finance-scraper --set replicaCount=5
```

## Troubleshooting

### Check Application Status

```bash
# Check pods
kubectl get pods -l app.kubernetes.io/name=finance-scraper

# Check logs
kubectl logs -l app.kubernetes.io/name=finance-scraper

# Check service
kubectl get svc finance-scraper
```

### MongoDB Issues

```bash
# Check MongoDB connection
curl http://localhost:5000/health

# Check database stats
curl http://localhost:5000/database/stats

# Clear data if needed
curl -X DELETE http://localhost:5000/database/clear

# Remove specific symbol
curl -X DELETE http://localhost:5000/database/clear/AAPL
```

### Secret Issues

```bash
# Check if secret exists
kubectl get secret finance-scraper-mongodb-secret

# View secret details (base64 encoded)
kubectl get secret finance-scraper-mongodb-secret -o yaml

# Recreate secret if needed
kubectl delete secret finance-scraper-mongodb-secret
kubectl create secret generic finance-scraper-mongodb-secret \
  --from-literal=MONGODB_URI="mongodb://username:password@mongodb.lan:27017/" \
  --from-literal=MONGODB_USERNAME="your-username" \
  --from-literal=MONGODB_PASSWORD="your-password"
```

### Common Issues

1. **MongoDB connection errors**: Check if MongoDB is accessible and credentials are correct
2. **Secret not found**: Ensure the secret `finance-scraper-mongodb-secret` exists
3. **Authentication failures**: Verify MongoDB username and password
4. **Image pull errors**: Ensure the Docker image is built and available
5. **Health check failures**: Check if the application is starting correctly
6. **Resource constraints**: Monitor CPU and memory usage

## Development

### Adding New Endpoints

1. Add the route in `app.py`
2. Include proper error handling and logging
3. Add input validation
4. Update the API documentation

### Testing

```bash
# Run the application
python app.py

# Run comprehensive tests
python test_api.py

# Test specific endpoints
curl http://localhost:5000/health
curl http://localhost:5000/stock/AAPL
curl http://localhost:5000/database/stats
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the Helm chart documentation 