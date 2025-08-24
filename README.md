# MeshMind: Production Safety for LangGraph Agents

[![PyPI version](https://badge.fury.io/py/meshmind.svg)](https://badge.fury.io/py/meshmind)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

**MeshMind** provides runtime safety and cost control for LangGraph-based AI agents. It enables intent preflight, resource locking, budget control, and idempotent effects to prevent production disasters in multi-agent systems.

## 🚀 Key Features

- **Intent Preflight**: Accept/Replan/Hold/Deny decisions before any LLM/tool call
- **Semantic Locks & Holds**: Redis-based locking with fairness queues
- **Budget/RPM Guards**: Stop-loss mechanisms for controlling LLM costs
- **Idempotent Effects**: Exact-once execution for HTTP POST and emails
- **Policy-as-Code**: YAML-based configuration for frequency caps and incident suppression
- **Graceful Degradation**: Continues operating even if referee service is unavailable
- **Observability**: OpenTelemetry integration with Jaeger tracing
- **🧾 Ghost-Run**: Dry-run simulator for cost estimation and conflict detection

## 📦 Installation

```bash
pip install meshmind
```

## 🎯 Quick Start

### Option 1: Automated Setup (Recommended)

**Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows:**
```cmd
setup.bat
```

### Option 2: Manual Setup

1. **Install dependencies:**
```bash
pip install -e .
```

2. **Start services:**
```bash
docker compose up -d
```

3. **Verify setup:**
```bash
curl http://localhost:8080/healthz
# Expected: {"status": "healthy", "service": "meshmind-referee"}
```

4. **Run demo:**
```bash
python examples/yc_demo/demo.py
```

5. **Run Ghost-Run demo:**
```bash
python examples/ghost_run_demo.py
```

### Basic Usage

```python
from meshmind.langgraph import wrap_node

@wrap_node(lambda s: ("email.send", {
    "resource": f"customer:{s['email']}",
    "author": "support-agent"
}))
async def send_email(state):
    """Send email with MeshMind protection."""
    return await email_service.send(state["email"])
```

### Budget Control

```python
from meshmind.core import BudgetContext, call_model

async def process_ticket(state):
    with BudgetContext(usd_cap=5.0, rpm=60) as budget:
        response = await call_model(
            f"Analyze ticket: {state['description']}", 
            budget,
            provider="openai"
        )
    return {"analysis": response}
```

### Idempotent Effects

```python
from meshmind.core import http_post, email_send

async def process_order(state):
    # Idempotent HTTP POST
    result = await http_post(
        url="https://api.payment.com/charge",
        data={"amount": state["amount"]},
        idempotency_key=f"payment:{state['order_id']}"
    )
    
    # Idempotent email
    await email_send(
        contact_id=state["customer_id"],
        body="Your order has been processed",
        subject="Order Confirmation",
        idempotency_key=f"email:{state['order_id']}"
    )
    
    return {"processed": True}
```

### Ghost-Run Simulation

```python
from meshmind.ghost import ghost_run, GhostConfig

# Run simulation before deployment
report = await ghost_run(
    graph=my_workflow,
    input_state={"ticket_id": "123", "customer_email": "user@example.com"},
    budget_cap=10.0,
    rpm_limit=60
)

print(f"Estimated cost: ${report.total_cost:.2f}")
print(f"Conflicts detected: {len(report.conflicts)}")

# Generate HTML report
from meshmind.ghost.reports import save_html_report
save_html_report(report, "simulation_report.html")
```

## 🏗️ Architecture

MeshMind consists of several components:

### Core Services

| Service | Port | Purpose |
|---------|------|---------|
| **Referee** | 8080 | Main safety service (FastAPI) |
| **PostgreSQL** | 5432 | Database for holds, budgets, intents |
| **Redis** | 6379 | Cache and message broker |
| **Jaeger** | 16686 | Distributed tracing UI |
| **OpenTelemetry Collector** | 4317 | Observability data collection |

### 1. Referee Service (FastAPI)

A stateless HTTP service that makes decisions about intents:

```bash
# Start all services
docker compose up -d

# Start just the referee service
docker compose up -d referee
```

**Endpoints:**
- `GET /healthz` - Health check
- `POST /v1/intents` - Intent preflight
- `POST /v1/holds/request` - Request resource hold
- `POST /v1/holds/confirm` - Confirm hold
- `POST /v1/holds/release` - Release hold
- `POST /v1/budgets/start` - Start budget session
- `POST /v1/budgets/consume` - Consume from budget
- `POST /v1/budgets/stop` - Stop budget session

### 2. Python SDK

Client library for integrating with LangGraph:

```python
from meshmind import wrap_node, BudgetContext, http_post, email_send
```

## 🔧 Configuration

### Environment Variables

```bash
# Referee service
MESHMIND_BASE_URL=http://localhost:8080
MESHMIND_TIMEOUT=10.0
MESHMIND_MAX_RETRIES=3

# Database
DATABASE_URL=postgresql://meshmind:meshmind@localhost/meshmind
REDIS_URL=redis://localhost:6379

# Observability
MESHMIND_ENABLE_OTEL=true
JAEGER_ENDPOINT=http://localhost:14268/api/traces
```

### Policy Configuration

```yaml
# policy.yaml
frequency_caps:
  contact.email:
    window_hours: 48
    max_count: 1
  contact.sms:
    window_hours: 24
    max_count: 2

incidents:
  suppress_outreach: false
  suppressed_types: []

approvals:
  high_value:
    require_if:
      - amount_gt_1000: true
```

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=meshmind

# Run specific test categories
pytest -m unit
pytest -m integration
```

## 📚 Examples

### Customer Support Agent

```python
from meshmind.langgraph import wrap_node
from meshmind.core import BudgetContext, call_model, email_send

@wrap_node(lambda s: ("ticket.process", {
    "resource": f"ticket:{s['ticket_id']}",
    "author": "support-agent"
}))
async def process_support_ticket(state):
    """Process support ticket with safety controls."""
    
    with BudgetContext(usd_cap=2.0, rpm=30) as budget:
        # Analyze ticket
        analysis = await call_model(
            f"Analyze this support ticket: {state['description']}",
            budget
        )
        
        # Generate response
        response = await call_model(
            f"Generate response for: {state['description']}",
            budget
        )
    
    # Send email (idempotent)
    await email_send(
        contact_id=state["customer_id"],
        body=response,
        subject=f"Re: {state['subject']}",
        idempotency_key=f"response:{state['ticket_id']}"
    )
    
    return {"processed": True, "analysis": analysis}
```

### E-commerce Order Processing

```python
@wrap_node(lambda s: ("order.process", {
    "resource": f"order:{s['order_id']}",
    "author": "order-agent"
}))
async def process_order(state):
    """Process e-commerce order with safety controls."""
    
    # Reserve inventory
    await http_post(
        url="https://api.inventory.com/reserve",
        data={"product_id": state["product_id"]},
        idempotency_key=f"inventory:{state['order_id']}"
    )
    
    # Process payment
    payment = await http_post(
        url="https://api.payment.com/charge",
        data={"amount": state["amount"]},
        idempotency_key=f"payment:{state['order_id']}"
    )
    
    # Send confirmation
    await email_send(
        contact_id=state["customer_id"],
        body=f"Order {state['order_id']} confirmed",
        subject="Order Confirmation",
        idempotency_key=f"confirmation:{state['order_id']}"
    )
    
    return {"order_id": state["order_id"], "payment_id": payment["id"]}
```

## 🧾 Ghost-Run: Dry-Run Simulator

Ghost-Run is a powerful simulation tool that lets you test LangGraph workflows before deployment. It provides:

- **Cost Estimation**: Predict LLM and API costs before spending money
- **Conflict Detection**: Identify resource locks, frequency caps, and policy violations
- **Budget Analysis**: Ensure workflows stay within budget limits
- **Detailed Reports**: Generate HTML and JSON reports for analysis

### CLI Usage

```bash
# Run simulation on a workflow
ghost-run run workflow.py input.json --budget 10.0 --rpm 60

# Initialize configuration
ghost-run init

# Convert reports between formats
ghost-run convert report.json --format html
```

### Python API

```python
from meshmind.ghost import ghost_run, GhostConfig

# Basic simulation
report = await ghost_run(
    graph=my_workflow,
    input_state={"user_id": "123"},
    budget_cap=5.0
)

# Advanced configuration
config = GhostConfig(
    budget_cap=10.0,
    rpm_limit=60,
    fail_on_conflict=True,
    max_steps=100
)

report = await ghost_run(
    graph=my_workflow,
    input_state=input_data,
    ghost_config=config
)

# Analyze results
print(f"Cost: ${report.total_cost:.3f}")
print(f"Conflicts: {len(report.conflicts)}")
print(f"Success: {not report.budget_exceeded}")
```

### Report Analysis

Ghost-Run generates comprehensive reports with:

- **Cost Breakdown**: Per-node cost analysis
- **Conflict Details**: Resource locks, frequency caps, policy violations
- **Performance Metrics**: Execution time, token usage, API calls
- **Visual Reports**: Beautiful HTML reports with charts and summaries

## 🔍 Monitoring & Observability

MeshMind provides comprehensive observability through OpenTelemetry:

```python
from meshmind.utils.logging import setup_logging

# Setup structured logging
logger = setup_logging(level="INFO", enable_structured=True)

# Log operations
logger.info("Processing ticket", extra={
    "structured_data": {
        "ticket_id": "123",
        "customer_id": "456",
        "priority": "high"
    }
})
```

### Jaeger Tracing

View traces in Jaeger UI at `http://localhost:16686`:

```bash
# Start Jaeger
docker-compose up jaeger
```

## 🚀 Deployment

### Docker Compose (Development)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f referee
```

### Kubernetes (Production)

```bash
# Deploy with Helm
helm install meshmind ./infra/helm

# Check status
kubectl get pods -l app=meshmind
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone repository
git clone https://github.com/meshmind/meshmind.git
cd meshmind

# Install development dependencies
pip install -e ".[dev]"

# Setup pre-commit hooks
pre-commit install

# Run tests
pytest
```

### Code Quality

```bash
# Format code
black src/
isort src/

# Type checking
mypy src/

# Linting
ruff check src/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [https://docs.meshmind.ai](https://docs.meshmind.ai)
- **Issues**: [GitHub Issues](https://github.com/meshmind/meshmind/issues)
- **Discussions**: [GitHub Discussions](https://github.com/meshmind/meshmind/discussions)
- **Email**: team@meshmind.ai

## 🙏 Acknowledgments

- Built on top of [LangGraph](https://github.com/langchain-ai/langgraph)
- Inspired by production safety needs in AI agent systems
- Community feedback and contributions

---

**MeshMind** - Making AI agents production-ready, one intent at a time. 🚀