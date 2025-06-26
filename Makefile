# Finance Scraper Makefile

.PHONY: help build run test clean deploy helm-install helm-upgrade helm-uninstall docker-build docker-run

# Default target
help:
	@echo "Finance Scraper - Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  run          - Run the application locally"
	@echo "  test         - Run API tests"
	@echo "  clean        - Clean up Python cache files"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run Docker container"
	@echo ""
	@echo "Kubernetes/Helm:"
	@echo "  deploy       - Build and deploy to Kubernetes"
	@echo "  helm-install - Install Helm chart"
	@echo "  helm-upgrade - Upgrade Helm chart"
	@echo "  helm-uninstall - Uninstall Helm chart"
	@echo ""
	@echo "Examples:"
	@echo "  make run"
	@echo "  make docker-build"
	@echo "  make deploy"

# Development
run:
	python app.py

test:
	python test_api.py

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Docker
docker-build:
	docker build -t finance-scraper:latest .

docker-run:
	docker run -p 8080:5000 finance-scraper:latest

# Kubernetes/Helm
deploy:
	./deploy.sh

helm-install:
	helm install finance-scraper ./helm/finance-scraper

helm-upgrade:
	helm upgrade finance-scraper ./helm/finance-scraper

helm-uninstall:
	helm uninstall finance-scraper

# Additional useful commands
port-forward:
	kubectl port-forward deployment/finance-scraper 8080:5000

logs:
	kubectl logs -f deployment/finance-scraper

status:
	kubectl get pods -l app.kubernetes.io/name=finance-scraper
	kubectl get svc -l app.kubernetes.io/name=finance-scraper

scale:
	@read -p "Enter number of replicas: " replicas; \
	helm upgrade finance-scraper ./helm/finance-scraper --set replicaCount=$$replicas 