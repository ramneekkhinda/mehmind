"""
Ghost-Run Reports: Structured reporting and HTML generation for simulation results.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ConflictReport:
    """Report of a detected conflict during simulation."""

    conflict_type: str  # "resource_lock", "frequency_cap", "budget_exceeded", "policy_violation"
    resource: str
    node_name: str
    step_number: int
    severity: str  # "low", "medium", "high", "critical"
    description: str
    suggested_fix: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepReport:
    """Report for a single execution step."""

    step_number: int
    node_name: str
    duration_ms: float
    cost: float
    tokens: int
    conflicts: List[ConflictReport] = field(default_factory=list)
    budget_exceeded: bool = False
    error: Optional[str] = None
    state_snapshot: Optional[Dict[str, Any]] = None


@dataclass
class GhostReport:
    """Complete Ghost-Run simulation report."""

    simulation_id: str
    total_steps: int
    total_cost: float
    total_tokens: int
    execution_time_ms: float
    llm_calls: int
    api_calls: int
    effects_count: int
    steps: List[StepReport]
    conflicts: List[ConflictReport]
    policy_violations: List[str]
    budget_exceeded: bool
    input_state: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the simulation results."""
        return {
            "simulation_id": self.simulation_id,
            "timestamp": self.timestamp,
            "total_steps": self.total_steps,
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "execution_time_ms": self.execution_time_ms,
            "llm_calls": self.llm_calls,
            "api_calls": self.api_calls,
            "effects_count": self.effects_count,
            "conflicts_count": len(self.conflicts),
            "policy_violations_count": len(self.policy_violations),
            "budget_exceeded": self.budget_exceeded,
            "success": not self.budget_exceeded and len(self.conflicts) == 0,
        }

    def get_cost_breakdown(self) -> Dict[str, float]:
        """Get cost breakdown by step."""
        breakdown = {}
        for step in self.steps:
            if step.cost > 0:
                breakdown[step.node_name] = breakdown.get(step.node_name, 0) + step.cost
        return breakdown

    def get_conflicts_by_type(self) -> Dict[str, List[ConflictReport]]:
        """Group conflicts by type."""
        grouped = {}
        for conflict in self.conflicts:
            if conflict.conflict_type not in grouped:
                grouped[conflict.conflict_type] = []
            grouped[conflict.conflict_type].append(conflict)
        return grouped


def generate_html_report(report: GhostReport, title: str = "Ghost-Run Report") -> str:
    """
    Generate an HTML report for the Ghost-Run simulation.

    Args:
        report: GhostReport to convert to HTML
        title: Title for the HTML page

    Returns:
        HTML string with formatted report
    """

    # CSS styles
    css = """
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }
        .header h1 { margin: 0; font-size: 2.5em; font-weight: 300; }
        .header .subtitle { margin: 10px 0 0 0; opacity: 0.9; font-size: 1.1em; }
        .content { padding: 30px; }
        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .summary-card { background: #f8f9fa; border-radius: 8px; padding: 20px; text-align: center; border-left: 4px solid #667eea; }
        .summary-card h3 { margin: 0 0 10px 0; color: #333; font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px; }
        .summary-card .value { font-size: 2em; font-weight: bold; color: #667eea; }
        .summary-card .unit { font-size: 0.8em; color: #666; }
        .section { margin-bottom: 30px; }
        .section h2 { color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; margin-bottom: 20px; }
        .steps-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        .steps-table th, .steps-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        .steps-table th { background: #f8f9fa; font-weight: 600; color: #333; }
        .steps-table tr:hover { background: #f5f5f5; }
        .conflict { background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 15px; margin: 10px 0; }
        .conflict h4 { margin: 0 0 10px 0; color: #856404; }
        .conflict .severity { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; margin-left: 10px; }
        .severity.critical { background: #dc3545; color: white; }
        .severity.high { background: #fd7e14; color: white; }
        .severity.medium { background: #ffc107; color: #212529; }
        .severity.low { background: #28a745; color: white; }
        .success { color: #28a745; }
        .warning { color: #ffc107; }
        .error { color: #dc3545; }
        .cost-breakdown { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 15px; }
        .cost-item { background: #e9ecef; padding: 8px 12px; border-radius: 20px; font-size: 0.9em; }
        .json-viewer { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 15px; font-family: 'Monaco', 'Menlo', monospace; font-size: 0.9em; overflow-x: auto; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }
        .badge.success { background: #d4edda; color: #155724; }
        .badge.warning { background: #fff3cd; color: #856404; }
        .badge.error { background: #f8d7da; color: #721c24; }
    </style>
    """

    # Generate summary cards
    summary_cards = []

    # Cost card
    cost_color = (
        "success"
        if report.total_cost <= 1.0
        else "warning"
        if report.total_cost <= 5.0
        else "error"
    )
    summary_cards.append(
        f"""
        <div class="summary-card">
            <h3>Total Cost</h3>
            <div class="value {cost_color}">${report.total_cost:.2f}</div>
            <div class="unit">USD</div>
        </div>
    """
    )

    # Steps card
    summary_cards.append(
        f"""
        <div class="summary-card">
            <h3>Total Steps</h3>
            <div class="value">{report.total_steps}</div>
            <div class="unit">execution steps</div>
        </div>
    """
    )

    # LLM Calls card
    summary_cards.append(
        f"""
        <div class="summary-card">
            <h3>LLM Calls</h3>
            <div class="value">{report.llm_calls}</div>
            <div class="unit">API calls</div>
        </div>
    """
    )

    # Conflicts card
    conflict_color = (
        "success"
        if len(report.conflicts) == 0
        else "warning"
        if len(report.conflicts) <= 2
        else "error"
    )
    summary_cards.append(
        f"""
        <div class="summary-card">
            <h3>Conflicts</h3>
            <div class="value {conflict_color}">{len(report.conflicts)}</div>
            <div class="unit">detected</div>
        </div>
    """
    )

    # Execution time card
    summary_cards.append(
        f"""
        <div class="summary-card">
            <h3>Execution Time</h3>
            <div class="value">{report.execution_time_ms:.0f}</div>
            <div class="unit">milliseconds</div>
        </div>
    """
    )

    # Status card
    status = (
        "success"
        if not report.budget_exceeded and len(report.conflicts) == 0
        else "warning"
        if len(report.conflicts) <= 2
        else "error"
    )
    status_text = (
        "PASS"
        if status == "success"
        else "WARNINGS"
        if status == "warning"
        else "FAILED"
    )
    summary_cards.append(
        f"""
        <div class="summary-card">
            <h3>Status</h3>
            <div class="value {status}">{status_text}</div>
            <div class="unit">simulation</div>
        </div>
    """
    )

    # Generate steps table
    steps_rows = []
    for step in report.steps:
        conflict_badges = ""
        if step.conflicts:
            conflict_badges = " ".join(
                [
                    f'<span class="badge {conflict.severity}">{conflict.conflict_type}</span>'
                    for conflict in step.conflicts
                ]
            )

        steps_rows.append(
            f"""
            <tr>
                <td>{step.step_number}</td>
                <td><strong>{step.node_name}</strong></td>
                <td>${step.cost:.3f}</td>
                <td>{step.tokens:,}</td>
                <td>{step.duration_ms:.1f}ms</td>
                <td>{conflict_badges}</td>
            </tr>
        """
        )

    # Generate conflicts section
    conflicts_html = ""
    if report.conflicts:
        for conflict in report.conflicts:
            conflicts_html += f"""
                <div class="conflict">
                    <h4>
                        {conflict.conflict_type.replace('_', ' ').title()}
                        <span class="severity {conflict.severity}">{conflict.severity.upper()}</span>
                    </h4>
                    <p><strong>Resource:</strong> {conflict.resource}</p>
                    <p><strong>Node:</strong> {conflict.node_name} (Step {conflict.step_number})</p>
                    <p><strong>Description:</strong> {conflict.description}</p>
                    {f'<p><strong>Suggested Fix:</strong> {conflict.suggested_fix}</p>' if conflict.suggested_fix else ''}
                </div>
            """
    else:
        conflicts_html = (
            '<p class="success">✅ No conflicts detected during simulation.</p>'
        )

    # Generate cost breakdown
    cost_breakdown = report.get_cost_breakdown()
    cost_items = []
    for node, cost in cost_breakdown.items():
        cost_items.append(f'<span class="cost-item">{node}: ${cost:.3f}</span>')

    # Generate policy violations
    policy_html = ""
    if report.policy_violations:
        for violation in report.policy_violations:
            policy_html += f'<li class="error">{violation}</li>'
    else:
        policy_html = '<li class="success">✅ No policy violations detected.</li>'

    # Main HTML template
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        {css}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🧾 Ghost-Run Report</h1>
                <p class="subtitle">Simulation Results for LangGraph Workflow</p>
            </div>
            
            <div class="content">
                <div class="section">
                    <h2>📊 Simulation Summary</h2>
                    <div class="summary-grid">
                        {''.join(summary_cards)}
                    </div>
                </div>
                
                <div class="section">
                    <h2>💰 Cost Analysis</h2>
                    <p><strong>Total Estimated Cost:</strong> <span class="value {cost_color}">${report.total_cost:.3f}</span></p>
                    <p><strong>Total Tokens:</strong> {report.total_tokens:,}</p>
                    <div class="cost-breakdown">
                        {''.join(cost_items)}
                    </div>
                </div>
                
                <div class="section">
                    <h2>🚨 Conflicts & Issues</h2>
                    {conflicts_html}
                </div>
                
                <div class="section">
                    <h2>📋 Policy Compliance</h2>
                    <ul>
                        {policy_html}
                    </ul>
                </div>
                
                <div class="section">
                    <h2>📈 Execution Steps</h2>
                    <table class="steps-table">
                        <thead>
                            <tr>
                                <th>Step</th>
                                <th>Node</th>
                                <th>Cost</th>
                                <th>Tokens</th>
                                <th>Duration</th>
                                <th>Conflicts</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(steps_rows)}
                        </tbody>
                    </table>
                </div>
                
                <div class="section">
                    <h2>🔧 Technical Details</h2>
                    <p><strong>Simulation ID:</strong> {report.simulation_id}</p>
                    <p><strong>Timestamp:</strong> {report.timestamp}</p>
                    <p><strong>LLM Calls:</strong> {report.llm_calls}</p>
                    <p><strong>API Calls:</strong> {report.api_calls}</p>
                    <p><strong>Side Effects:</strong> {report.effects_count}</p>
                    <p><strong>Budget Exceeded:</strong> {'Yes' if report.budget_exceeded else 'No'}</p>
                </div>
                
                <div class="section">
                    <h2>📄 Input State</h2>
                    <div class="json-viewer">
                        {json.dumps(report.input_state, indent=2)}
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    return html


def save_html_report(
    report: GhostReport, filepath: str, title: str = "Ghost-Run Report"
) -> None:
    """
    Save HTML report to a file.

    Args:
        report: GhostReport to save
        filepath: Path to save the HTML file
        title: Title for the HTML page
    """
    html_content = generate_html_report(report, title)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)


def save_json_report(report: GhostReport, filepath: str) -> None:
    """
    Save JSON report to a file.

    Args:
        report: GhostReport to save
        filepath: Path to save the JSON file
    """
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report.to_json())
