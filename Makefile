# Finance Scraper Makefile

.PHONY: help build run test clean deploy helm-install helm-upgrade helm-uninstall docker-build docker-run

# Default target
help:
	@echo "Finance Scraper - Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  run          - Run the application locally"
	@echo "  run-scheduler - Run the scheduler service locally"
	@echo "  test         - Run API tests"
	@echo "  clean        - Clean up Python cache files"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build - Build Docker image (API)"
	@echo "  docker-build-scheduler - Build Docker image (Scheduler)"
	@echo "  docker-run   - Run Docker container (API)"
	@echo "  docker-run-scheduler - Run Docker container (Scheduler)"
	@echo ""
	@echo "Kubernetes/Helm:"
	@echo "  deploy       - Build and deploy to Kubernetes"
	@echo "  helm-install - Install Helm chart"
	@echo "  helm-upgrade - Upgrade Helm chart"
	@echo "  helm-uninstall - Uninstall Helm chart"
	@echo "  helm-install-with-scheduler - Install with standalone scheduler"
	@echo "  helm-upgrade-with-scheduler - Upgrade with standalone scheduler"
	@echo "  helm-install-scheduler-only - Install scheduler only (no API)"
	@echo ""
	@echo "Examples:"
	@echo "  make run"
	@echo "  make run-scheduler"
	@echo "  make docker-build"
	@echo "  make deploy"

# Development
run:
	python app.py

run-scheduler:
	python scheduler_service.py

test:
	python test_api.py

test-scheduler:
	python test_scheduler.py

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Docker
docker-build:
	docker build -t finance-scraper:latest .

docker-build-scheduler:
	docker build -f Dockerfile.scheduler -t finance-scraper-scheduler:latest .

docker-run:
	docker run -p 8080:5000 finance-scraper:latest

docker-run-scheduler:
	docker run -p 5001:5001 finance-scraper-scheduler:latest

# Kubernetes/Helm
deploy:
	./deploy.sh

helm-install:
	helm install finance-scraper ./helm/finance-scraper

helm-upgrade:
	helm upgrade finance-scraper ./helm/finance-scraper

helm-uninstall:
	helm uninstall finance-scraper

# Scheduler deployment commands
helm-install-with-scheduler:
	helm install finance-scraper ./helm/finance-scraper --set scheduler.enabled=true

helm-upgrade-with-scheduler:
	helm upgrade finance-scraper ./helm/finance-scraper --set scheduler.enabled=true

helm-install-scheduler-only:
	helm install finance-scraper ./helm/finance-scraper --set scheduler.enabled=true --set replicaCount=0



# Additional useful commands
port-forward:
	kubectl port-forward deployment/finance-scraper 8080:5000

logs:
	kubectl logs -f deployment/finance-scraper

logs-scheduler:
	kubectl logs -f deployment/finance-scraper-scheduler



status:
	kubectl get pods -l app.kubernetes.io/name=finance-scraper
	kubectl get svc -l app.kubernetes.io/name=finance-scraper

scale:
	@read -p "Enter number of replicas: " replicas; \
	helm upgrade finance-scraper ./helm/finance-scraper --set replicaCount=$$replicas 