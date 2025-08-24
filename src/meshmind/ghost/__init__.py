"""
MeshMind Ghost-Run: Dry-Run Simulator for LangGraph Agents

Ghost-Run intercepts LangGraph workflows to simulate execution without making
actual LLM calls, API requests, or side-effects. It provides cost estimates,
conflict detection, and safety analysis before deployment.

Key Features:
- Cost estimation for LLM calls and API requests
- Resource conflict detection (locks, holds, frequency caps)
- Budget and policy compliance checking
- Detailed execution reports (JSON + HTML)
- Integration with existing MeshMind safety controls

Example:
    from meshmind.ghost import ghost_run
    
    # Run simulation
    report = await ghost_run(
        graph=my_langgraph_workflow,
        input_state={"ticket_id": "123", "customer_email": "user@example.com"},
        budget_cap=10.0
    )
    
    print(f"Estimated cost: ${report.total_cost:.2f}")
    print(f"Conflicts detected: {len(report.conflicts)}")
"""

from .simulator import GhostSimulator, ghost_run, GhostConfig
from .reports import GhostReport, generate_html_report
from .cli import main as cli_main

__all__ = [
    "GhostSimulator",
    "GhostReport", 
    "generate_html_report",
    "cli_main",
    "ghost_run",
    "GhostConfig"
]
