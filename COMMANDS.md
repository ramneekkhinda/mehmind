# MeshMind Development Commands

Quick reference for common development commands.

## 🚀 Setup & Installation

```bash
# Automated setup (Linux/macOS)
./setup.sh

# Automated setup (Windows)
setup.bat

# Manual setup
pip install -e .
docker compose up -d
```

## 🐳 Docker Commands

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Rebuild and restart
docker compose up -d --build

# View all logs
docker compose logs -f

# View specific service logs
docker compose logs referee -f
docker compose logs postgres -f
docker compose logs redis -f

# Access service shells
docker compose exec referee bash
docker compose exec postgres psql -U meshmind -d meshmind
docker compose exec redis redis-cli
```

## 🧪 Testing & Development

```bash
# Run the demo
python examples/yc_demo/demo.py

# Test referee health
curl http://localhost:8080/healthz

# Test intent preflight
curl -X POST http://localhost:8080/v1/intents \
  -H "Content-Type: application/json" \
  -d '{"type": "test", "resource": "test:123", "author": "test"}'

# Check service status
docker compose ps
```

## 📊 Monitoring

```bash
# Jaeger tracing UI
open http://localhost:16686

# Referee API
open http://localhost:8080

# PostgreSQL (via Docker)
docker compose exec postgres psql -U meshmind -d meshmind

# Redis (via Docker)
docker compose exec redis redis-cli
```

## 🔧 Development Workflow

```bash
# 1. Make changes to referee code
# 2. Rebuild and restart referee
docker compose up -d --build referee

# 3. Make changes to SDK code
# 4. Reinstall SDK
pip install -e .

# 5. Test changes
python examples/yc_demo/demo.py
```

## 🐛 Troubleshooting

```bash
# Check if services are running
docker compose ps

# Check referee logs
docker compose logs referee

# Restart all services
docker compose restart

# Reset everything (including data)
docker compose down -v
docker compose up -d
```

## 📁 Useful Files

- `docker-compose.yml` - Service orchestration
- `DEVELOPMENT.md` - Detailed development guide
- `examples/yc_demo/demo.py` - Working demo
- `referee/app.py` - Main referee service
- `src/meshmind/` - Python SDK
- `policy.yaml` - Safety policies
