# Finance Scraper Scheduler

The Finance Scraper now includes an automated scheduler that can retrieve stock data and historical prices on a configurable schedule without manual API calls.

## Features

- **Automated Data Retrieval**: Automatically fetches stock information and historical prices
- **Incremental Updates**: Only retrieves new data since the last update
- **Rate Limiting**: Configurable delays between API calls to avoid overwhelming Yahoo Finance
- **Configurable Frequency**: Set how often to update each symbol (default: once per day)
- **Batch Processing**: Process multiple symbols per run with configurable limits
- **Error Handling**: Robust error handling with retry logic
- **Multiple Deployment Options**: Can run as part of the API or as a standalone service

## Architecture

The scheduler can be deployed in two modes:

1. **Integrated Mode**: Scheduler runs in the same pod as the API
2. **Separate Mode**: Scheduler runs in its own pod with its own API for lifecycle management

### Integrated Mode

When `ENABLE_SCHEDULER=true` is set, the scheduler runs in the same pod as the main API. The API provides endpoints to control the scheduler lifecycle.

### Separate Mode

When running in separate pods, the scheduler pod exposes its own API for lifecycle management, and the main API communicates with it via HTTP requests. The scheduler pod runs both the scheduler service and a Flask API for lifecycle management.

## How It Works

1. **Symbol Discovery**: The scheduler retrieves all stock symbols from the `stock-info` collection
2. **Update Check**: For each symbol, it checks when it was last updated
3. **Incremental Updates**: For historical prices, it finds the last price date and only fetches newer data
4. **Rate Limiting**: Adds configurable delays between API calls to be respectful to Yahoo Finance
5. **Bulk Storage**: Uses MongoDB bulk operations for efficient data storage

## Configuration

The scheduler uses a consolidated configuration approach where environment variables are shared between the API and scheduler deployments:

### Shared Configuration (API and Scheduler)
All environment variables are defined in a single `env` section in `values.yaml`:

#### MongoDB Configuration
- `MONGODB_URI`: MongoDB connection string (default: `mongodb://mongodb.lan:27017/`)
- `AUTHENTICATION_SOURCE`: MongoDB authentication source (default: `epicurus-stock-io`)
- `MONGODB_USERNAME`: MongoDB username
- `MONGODB_PASSWORD`: MongoDB password
- `MONGODB_DB`: Database name (default: `epicurus-stock-io`)
- `MONGODB_COLLECTION`: Stock info collection (default: `stock-info`)
- `MONGODB_PRICES_COLLECTION`: Stock prices collection (default: `stock-prices`)

#### Scheduler Configuration
- `SCHEDULER_FREQUENCY_HOURS`: How often to run the full job (default: `24`)
- `SYMBOL_FREQUENCY_HOURS`: How often to update each symbol (default: `24`)
- `MAX_SYMBOLS_PER_RUN`: Maximum symbols to process per run (default: `50`)
- `RATE_LIMIT_DELAY_SECONDS`: Delay between API calls (default: `1.0`)
- `JITTER_SECONDS`: Random jitter to avoid thundering herd (default: `0.5`)
- `MAX_RETRIES`: Maximum retry attempts (default: `3`)
- `RETRY_DELAY_SECONDS`: Delay between retries (default: `5.0`)
- `INITIAL_START_DATE`: Initial start date (YYYY-MM-DD) when no historical data exists (default: `2020-01-01`)
- `DOWNLOAD_CHUNK_DAYS`: Number of days to download per chunk (default: `365`)
- `DOWNLOAD_CHUNK_DELAY_MINUTES`: Minutes to wait between chunks for same symbol (default: `10`)

#### API-Specific Configuration
- `FLASK_ENV`: Flask environment (default: `production`)
- `PORT`: API port (default: `5000`)
- `ENABLE_SCHEDULER`: Enable scheduler in API mode (default: `false`)

### Deployment Configuration
- `scheduler.enabled`: Enable standalone scheduler deployment (default: `false`)
- `scheduler.replicaCount`: Number of scheduler replicas (default: `1`)
- `scheduler.image`: Scheduler container image configuration

## Usage

### Option 1: Integrated with API (Recommended)

Run the scheduler as part of the main API application:

```bash
# Enable scheduler in API mode
export ENABLE_SCHEDULER=true
export SCHEDULER_FREQUENCY_HOURS=24
export SYMBOL_FREQUENCY_HOURS=24

# Run the API with scheduler
python app.py
```

### Option 2: Standalone Scheduler Service

Run the scheduler as a separate service:

```bash
# Run standalone scheduler
python scheduler_service.py
```

### Option 3: Docker

#### API with Scheduler
```bash
# Build and run API with scheduler
docker build -t finance-scraper:latest .
docker run -p 8080:5000 \
  -e ENABLE_SCHEDULER=true \
  -e MONGODB_URI=mongodb://your-mongodb:27017/ \
  finance-scraper:latest
```

#### Standalone Scheduler
```bash
# Build and run standalone scheduler
docker build -f Dockerfile.scheduler -t finance-scraper-scheduler:latest .
docker run \
  -e MONGODB_URI=mongodb://your-mongodb:27017/ \
  finance-scraper-scheduler:latest
```

### Option 4: Using Makefile

```bash
# Run API with scheduler locally
make run

# Run standalone scheduler locally
make run-scheduler

# Build Docker images
make docker-build
make docker-build-scheduler
make docker-build-scheduler-api

# Run Docker containers
make docker-run
make docker-run-scheduler
```

## API Endpoints

When running the scheduler with the API, additional endpoints are available:

### Main API Endpoints (when scheduler is enabled)

#### Get Scheduler Status
```bash
GET /scheduler/status
```

Response:
```json
{
  "status": "running",
  "enabled": true,
  "mode": "integrated",
  "config": {
    "run_frequency_hours": 24,
    "symbol_frequency_hours": 24,
    "max_symbols_per_run": 50,
    "rate_limit_delay_seconds": 1.0
  }
}
```

#### Start Scheduler
```bash
POST /scheduler/start
```

#### Stop Scheduler
```bash
POST /scheduler/stop
```

#### Run Scheduler Cycle Immediately
```bash
POST /scheduler/run-now
```

### Scheduler API Endpoints (when running separately)

When the scheduler runs in a separate pod, it exposes its own API on port 5001:

#### Health Check
```bash
GET http://scheduler-pod:5001/health
```

#### Get Scheduler Status
```bash
GET http://scheduler-pod:5001/status
```

#### Start Scheduler
```bash
POST http://scheduler-pod:5001/start
```

#### Stop Scheduler
```bash
POST http://scheduler-pod:5001/stop
```

#### Run Scheduler Cycle Immediately
```bash
POST http://scheduler-pod:5001/run-now
```

#### Get Scheduler Configuration
```bash
GET http://scheduler-pod:5001/config
```

## Example Configuration

### Development Environment
```bash
export MONGODB_URI=mongodb://localhost:27017/
export MONGODB_DB=finance-dev
export ENABLE_SCHEDULER=true
export SCHEDULER_FREQUENCY_HOURS=1
export SYMBOL_FREQUENCY_HOURS=1
export MAX_SYMBOLS_PER_RUN=10
export RATE_LIMIT_DELAY_SECONDS=2.0
```

### Production Environment
```bash
export MONGODB_URI=mongodb://prod-mongodb:27017/
export MONGODB_USERNAME=finance_user
export MONGODB_PASSWORD=secure_password
export MONGODB_DB=finance-prod
export ENABLE_SCHEDULER=true
export SCHEDULER_FREQUENCY_HOURS=24
export SYMBOL_FREQUENCY_HOURS=24
export MAX_SYMBOLS_PER_RUN=100
export RATE_LIMIT_DELAY_SECONDS=1.0
export INITIAL_START_DATE=2015-01-01
export DOWNLOAD_CHUNK_DAYS=365
export DOWNLOAD_CHUNK_DELAY_MINUTES=10
```

### Kubernetes/Helm Configuration

The scheduler configuration is managed through a single Helm chart with shared MongoDB configuration:

#### Deployment Modes

**1. API Only (Default)**
```bash
helm install finance-scraper ./helm/finance-scraper
```
- Only the API service runs
- No scheduler functionality



**2. API with Integrated Scheduler**
```yaml
# values.yaml
env:
  - name: ENABLE_SCHEDULER
    value: "true"  # Scheduler runs in same pod as API
  - name: SCHEDULER_FREQUENCY_HOURS
    value: "24"
  - name: SYMBOL_FREQUENCY_HOURS
    value: "24"
  - name: MAX_SYMBOLS_PER_RUN
    value: "50"
  - name: INITIAL_START_DAYS_BACK
    value: "365"
```
```bash
helm install finance-scraper ./helm/finance-scraper --set env[5].value=true
```
- **API Endpoints**: `/scheduler/status`, `/scheduler/start`, `/scheduler/stop`, `/scheduler/run-now` work
- **Control**: API can start/stop/control the scheduler

**3. API + Standalone Scheduler**
```yaml
# values.yaml
# Shared environment variables (used by both API and scheduler)
env:
  # MongoDB configuration (shared)
  - name: MONGODB_DB
    value: "epicurus-stock-io"
  - name: MONGODB_COLLECTION
    value: "stock-info"
  - name: MONGODB_PRICES_COLLECTION
    value: "stock-prices"
  
  # Scheduler configuration (shared)
  - name: SCHEDULER_FREQUENCY_HOURS
    value: "24"
  - name: SYMBOL_FREQUENCY_HOURS
    value: "24"
  - name: MAX_SYMBOLS_PER_RUN
    value: "50"
  - name: INITIAL_START_DAYS_BACK
    value: "365"

# Scheduler deployment
scheduler:
  enabled: true  # Separate scheduler pod
  replicaCount: 1
  image:
    repository: finance-scraper-scheduler
    tag: "latest"
```
```bash
helm install finance-scraper ./helm/finance-scraper --set scheduler.enabled=true
```
- **API Endpoints**: Return helpful error messages directing to kubectl commands
- **Control**: Use `kubectl scale` to manage scheduler deployment
- **Independent**: Scheduler runs completely independently

**4. Standalone Scheduler Only**
```bash
helm install finance-scraper ./helm/finance-scraper --set scheduler.enabled=true --set replicaCount=0
```
- Only scheduler runs, no API service
- Useful for dedicated scheduler deployments

### Managing Standalone Scheduler

When using separate pods, manage the scheduler using kubectl:

```bash
# Check scheduler status
kubectl get pods -l app.kubernetes.io/component=scheduler

# View scheduler logs
kubectl logs -f deployment/finance-scraper-scheduler

# Start scheduler (scale to 1 replica)
kubectl scale deployment finance-scraper-scheduler --replicas=1

# Stop scheduler (scale to 0 replicas)
kubectl scale deployment finance-scraper-scheduler --replicas=0

# Restart scheduler
kubectl rollout restart deployment/finance-scraper-scheduler
```

## Monitoring and Logging

The scheduler provides comprehensive logging:

- **Info Level**: General operation information
- **Warning Level**: Non-critical issues (e.g., no new data available)
- **Error Level**: Critical errors that need attention

Example log output:
```
2024-01-15 10:00:00 - scheduler - INFO - Starting scheduler cycle
2024-01-15 10:00:01 - scheduler - INFO - Retrieved 150 symbols from database
2024-01-15 10:00:02 - scheduler - INFO - Found 25 symbols that need updating
2024-01-15 10:00:03 - scheduler - INFO - Processing symbol 1/25: AAPL
2024-01-15 10:00:04 - scheduler - INFO - Successfully updated stock info for AAPL
2024-01-15 10:00:05 - scheduler - INFO - Updated 5 historical prices for AAPL
```

## Best Practices

1. **Rate Limiting**: Always use appropriate rate limiting to avoid being blocked by Yahoo Finance
2. **Monitoring**: Monitor the logs for any errors or warnings
3. **Database Indexing**: Ensure proper indexes on the MongoDB collections for performance
4. **Backup**: Regularly backup your MongoDB data
5. **Testing**: Test with a small number of symbols before scaling up

## Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   - Check MongoDB URI and credentials
   - Ensure MongoDB is running and accessible

2. **No Symbols Found**
   - Ensure the `stock-info` collection has data
   - Check MongoDB connection and permissions

3. **Rate Limiting Issues**
   - Increase `RATE_LIMIT_DELAY_SECONDS`
   - Reduce `MAX_SYMBOLS_PER_RUN`

4. **Memory Issues**
   - Reduce `MAX_SYMBOLS_PER_RUN`
   - Monitor memory usage and adjust accordingly

### Debug Mode

To enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python scheduler_service.py
```

## Security Considerations

1. **MongoDB Authentication**: Always use authentication in production
2. **Network Security**: Ensure MongoDB is not exposed to the public internet
3. **Environment Variables**: Store sensitive configuration in environment variables
4. **Container Security**: Run containers as non-root users (already configured in Dockerfiles)

## Performance Tuning

1. **Batch Size**: Adjust `MAX_SYMBOLS_PER_RUN` based on your system resources
2. **Update Frequency**: Balance between data freshness and system load
3. **Rate Limiting**: Find the right balance between speed and API limits
4. **Database Optimization**: Use appropriate indexes and connection pooling 