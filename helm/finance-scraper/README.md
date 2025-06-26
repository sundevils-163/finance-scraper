# Finance Scraper Helm Chart

A Helm chart for deploying the Finance Scraper API to Kubernetes. This application provides stock information using the yfinance library.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- kubectl configured to communicate with your cluster

## Installation

### Quick Start

```bash
# Add the chart repository (if using a repository)
helm repo add finance-scraper https://your-repo-url

# Install the chart
helm install finance-scraper ./helm/finance-scraper

# Or install with a custom release name
helm install my-finance-app ./helm/finance-scraper --name-template my-finance-app
```

### Building and Installing from Local Chart

```bash
# Build the Docker image
docker build -t finance-scraper:latest .

# Install the chart
helm install finance-scraper ./helm/finance-scraper
```

## Configuration

The following table lists the configurable parameters of the finance-scraper chart and their default values.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `2` |
| `image.repository` | Docker image repository | `finance-scraper` |
| `image.tag` | Docker image tag | `latest` |
| `image.pullPolicy` | Docker image pull policy | `IfNotPresent` |
| `service.type` | Kubernetes service type | `ClusterIP` |
| `service.port` | Service port | `80` |
| `ingress.enabled` | Enable ingress | `false` |
| `resources.limits.cpu` | CPU resource limits | `500m` |
| `resources.limits.memory` | Memory resource limits | `512Mi` |
| `resources.requests.cpu` | CPU resource requests | `100m` |
| `resources.requests.memory` | Memory resource requests | `128Mi` |
| `autoscaling.enabled` | Enable horizontal pod autoscaling | `true` |
| `autoscaling.minReplicas` | Minimum number of replicas | `2` |
| `autoscaling.maxReplicas` | Maximum number of replicas | `10` |

### Example Custom Values

Create a `values-custom.yaml` file:

```yaml
replicaCount: 3
image:
  repository: your-registry/finance-scraper
  tag: "v1.0.0"

service:
  type: LoadBalancer

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: finance-scraper.yourdomain.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 200m
    memory: 256Mi
```

Install with custom values:

```bash
helm install finance-scraper ./helm/finance-scraper -f values-custom.yaml
```

## API Endpoints

The application provides the following endpoints:

- `GET /health` - Health check endpoint
- `GET /stock/{symbol}` - Get comprehensive stock information
- `GET /stock/{symbol}/price` - Get current stock price and basic metrics

### Example Usage

```bash
# Health check
curl http://localhost:8080/health

# Get stock information for Apple
curl http://localhost:8080/stock/AAPL

# Get stock price for Tesla
curl http://localhost:8080/stock/TSLA/price
```

## Monitoring

### Service Monitor

To enable Prometheus monitoring, set `serviceMonitor.enabled: true` in your values:

```yaml
serviceMonitor:
  enabled: true
  interval: 30s
  path: /health
  port: http
```

### Health Checks

The application includes:
- Liveness probe: `/health` endpoint
- Readiness probe: `/health` endpoint
- Health check in Docker container

## Security

The chart includes several security features:

- Non-root user execution
- Read-only root filesystem
- Dropped capabilities
- Pod security context
- Network policies (optional)

## Scaling

### Horizontal Pod Autoscaler

The chart includes an HPA that scales based on CPU and memory utilization:

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

### Check Pod Status

```bash
kubectl get pods -l app.kubernetes.io/name=finance-scraper
kubectl describe pod <pod-name>
```

### Check Logs

```bash
kubectl logs -l app.kubernetes.io/name=finance-scraper
kubectl logs -f deployment/finance-scraper
```

### Port Forward for Testing

```bash
kubectl port-forward deployment/finance-scraper 8080:5000
```

### Check Service

```bash
kubectl get svc finance-scraper
kubectl describe svc finance-scraper
```

## Uninstalling

```bash
helm uninstall finance-scraper
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test the chart
5. Submit a pull request

## License

This project is licensed under the MIT License. 