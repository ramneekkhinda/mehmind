# MeshMind Development Setup

This guide will help you set up and run MeshMind locally for development.

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose**: Required for running the referee service and dependencies
- **Python 3.9+**: For running the MeshMind SDK and demos
- **Git**: For cloning the repository

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd meshmind

# Install Python dependencies
pip install -e .
```

### 2. Start the Referee Service

```bash
# Start all services (PostgreSQL, Redis, Jaeger, OpenTelemetry Collector, Referee)
docker compose up -d

# Check service status
docker compose ps
```

### 3. Verify Services Are Running

```bash
# Check referee health
curl http://localhost:8080/healthz

# Expected response:
# {"status": "healthy", "service": "meshmind-referee"}
```

### 4. Run the Demo

```bash
# Run the Y Combinator demo
python examples/yc_demo/demo.py
```

## 🏗️ Architecture Overview

MeshMind consists of several components:

### Core Services (Docker Compose)

| Service | Port | Purpose |
|---------|------|---------|
| **Referee** | 8080 | Main safety service (FastAPI) |
| **PostgreSQL** | 5432 | Database for holds, budgets, intents |
| **Redis** | 6379 | Cache and message broker |
| **Jaeger** | 16686 | Distributed tracing UI |
| **OpenTelemetry Collector** | 4317 | Observability data collection |

### MeshMind SDK

The SDK provides Python bindings for the referee service:

- **Intent Preflight**: `wrap_node` decorator for LangGraph integration
- **Budget Control**: `BudgetContext` for cost management
- **Effects**: `email_send`, `http_post` for idempotent operations
- **Error Handling**: Graceful degradation and fallbacks

## 🔧 Development Workflow

### 1. Making Changes to the Referee Service

```bash
# Edit referee code in referee/ directory
# Rebuild and restart the service
docker compose up -d --build referee

# Check logs
docker compose logs referee -f
```

### 2. Making Changes to the SDK

```bash
# Edit SDK code in src/meshmind/ directory
# Reinstall in development mode
pip install -e .

# Test changes
python examples/yc_demo/demo.py
```

### 3. Database Changes

```bash
# Access PostgreSQL directly
docker compose exec postgres psql -U meshmind -d meshmind

# View referee logs
docker compose logs referee -f
```

## 🧪 Testing

### Run the Demo

```bash
# Basic demo
python examples/yc_demo/demo.py

# Expected output shows:
# - Intent preflight working
# - Budget control (99% cost savings)
# - Hold management
# - Idempotent operations
```

### Manual API Testing

```bash
# Test intent preflight
curl -X POST http://localhost:8080/v1/intents \
  -H "Content-Type: application/json" \
  -d '{
    "type": "ticket.process",
    "resource": "ticket:TICKET-001",
    "action": "execute",
    "author": "test-agent",
    "scope": "write",
    "ttl_s": 90
  }'

# Test hold management
curl -X POST http://localhost:8080/v1/holds/request \
  -H "Content-Type: application/json" \
  -d '{
    "resource": "ticket:TICKET-001",
    "ttl_s": 30,
    "author": "test-agent",
    "correlation": "test-session"
  }'

# Test budget management
curl -X POST http://localhost:8080/v1/budgets/start \
  -H "Content-Type: application/json" \
  -d '{
    "usd_cap": 5.0,
    "rpm": 10,
    "tags": {"test": "true"}
  }'
```

## 📊 Monitoring & Observability

### Jaeger Tracing UI

Access the distributed tracing interface:
- **URL**: http://localhost:16686
- **Purpose**: View traces, spans, and performance metrics

### Database Access

```bash
# PostgreSQL connection details
Host: localhost
Port: 5432
Database: meshmind
Username: meshmind
Password: meshmind

# Connect via Docker
docker compose exec postgres psql -U meshmind -d meshmind
```

### Redis Access

```bash
# Connect to Redis
docker compose exec redis redis-cli

# View keys
KEYS *
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Referee Service Won't Start

```bash
# Check logs
docker compose logs referee

# Common fixes:
# - Ensure ports 8080, 5432, 6379 are available
# - Check Docker has enough resources
# - Verify all dependencies are built
```

#### 2. Demo Fails to Connect

```bash
# Verify referee is healthy
curl http://localhost:8080/healthz

# Check if services are running
docker compose ps

# Restart services if needed
docker compose restart
```

#### 3. Database Connection Issues

```bash
# Reset database
docker compose down -v
docker compose up -d

# Check PostgreSQL logs
docker compose logs postgres
```

### Debug Mode

```bash
# Run referee in debug mode
docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d

# View detailed logs
docker compose logs referee -f --tail=100
```

## 🔄 Development Commands

### Useful Docker Commands

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Rebuild and restart
docker compose up -d --build

# View logs
docker compose logs -f

# View specific service logs
docker compose logs referee -f

# Access service shell
docker compose exec referee bash
docker compose exec postgres psql -U meshmind -d meshmind
```

### Useful Python Commands

```bash
# Install in development mode
pip install -e .

# Run tests
python -m pytest

# Run demo
python examples/yc_demo/demo.py

# Check SDK installation
python -c "import meshmind; print(meshmind.__version__)"
```

## 📁 Project Structure

```
meshmind/
├── docker-compose.yml          # Service orchestration
├── infra/docker/               # Docker configurations
│   └── Dockerfile.referee      # Referee service container
├── referee/                    # Referee service (FastAPI)
│   ├── app.py                  # Main FastAPI application
│   ├── otel.py                 # OpenTelemetry setup
│   └── models.py               # Data models
├── src/meshmind/               # Python SDK
│   ├── core/                   # Core functionality
│   │   ├── budget.py           # Budget management
│   │   ├── effects.py          # Idempotent effects
│   │   └── intents.py          # Intent preflight
│   ├── langgraph/              # LangGraph integration
│   └── utils/                  # Utilities
├── examples/                   # Demo applications
│   └── yc_demo/               # Y Combinator demo
└── policy.yaml                # Safety policies
```

## 🚀 Next Steps

1. **Run the Demo**: `python examples/yc_demo/demo.py`
2. **Explore Jaeger**: http://localhost:16686
3. **Test APIs**: Use the manual API testing examples above
4. **Modify Code**: Make changes and test with the demo
5. **Add Features**: Extend the referee service or SDK

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review the referee logs: `docker compose logs referee`
3. Verify all services are running: `docker compose ps`
4. Test the health endpoint: `curl http://localhost:8080/healthz`

Happy developing! 🎉
