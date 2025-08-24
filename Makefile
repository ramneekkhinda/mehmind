.PHONY: help install dev test lint format clean docker-up docker-down docker-build

help: ## Show this help message
	@echo "MeshMind Development Commands"
	@echo "============================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -e .

dev: ## Install development dependencies
	pip install -e ".[dev]"

test: ## Run tests
	pytest testkit/ -v

lint: ## Run linting
	black referee/ src/ examples/
	isort referee/ src/ examples/
	ruff check referee/ src/ examples/

format: ## Format code
	black referee/ src/ examples/
	isort referee/ src/ examples/

clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

docker-up: ## Start Docker services
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

docker-build: ## Build Docker images
	docker-compose build

docker-logs: ## Show Docker logs
	docker-compose logs -f

start-referee: ## Start referee service locally
	python -m referee.app

run-example: ## Run YC demo
	python examples/yc_demo/demo.py

ghost-run: ## Run ghost-run (dry-run) on example
	@echo "Ghost-run feature coming soon..."

setup-db: ## Setup database tables
	python -c "import asyncio; from referee.store import Store; asyncio.run(Store().connect())"

check-health: ## Check service health
	curl -f http://localhost:8080/healthz || echo "Service not healthy"

metrics: ## Get service metrics
	curl http://localhost:8080/v1/metrics | jq .

# Development shortcuts
dev-setup: install dev docker-up ## Complete development setup
	@echo "Development environment ready!"
	@echo "Referee service: http://localhost:8080"
	@echo "Jaeger UI: http://localhost:16686"

quick-test: docker-up ## Quick test with Docker
	@sleep 5  # Wait for services to start
	@make check-health
	@make run-example

# Production helpers
prod-build: ## Build production Docker image
	docker build -f infra/docker/Dockerfile.referee -t meshmind/referee:latest .

prod-deploy: ## Deploy to production (example)
	@echo "Deploying to production..."
	@echo "Add your deployment commands here"

# Documentation
docs-serve: ## Serve documentation locally
	@echo "Documentation available at: http://localhost:8000"
	@python -m http.server 8000 -d docs/

# Monitoring
monitor: ## Open monitoring dashboards
	@echo "Opening monitoring dashboards..."
	@echo "Jaeger UI: http://localhost:16686"
	@echo "Service Health: http://localhost:8080/healthz"
	@echo "Metrics: http://localhost:8080/v1/metrics"
