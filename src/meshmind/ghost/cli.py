"""
Ghost-Run CLI: Command-line interface for running Ghost-Run simulations.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click
import yaml

from ..utils.logging import get_logger
from .reports import save_html_report, save_json_report
from .simulator import GhostConfig, ghost_run

logger = get_logger(__name__)


@click.group()
@click.version_option()
def cli():
    """MeshMind Ghost-Run: Dry-run simulator for LangGraph agents."""
    pass


@cli.command()
@click.argument("graph_file", type=click.Path(exists=True))
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--budget", "-b", default=10.0, help="Budget cap in USD")
@click.option("--rpm", "-r", default=60, help="Requests per minute limit")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["json", "html", "both"]),
    default="both",
    help="Output format",
)
@click.option(
    "--fail-on-conflict", is_flag=True, help="Fail simulation on first conflict"
)
@click.option("--max-steps", default=100, help="Maximum execution steps")
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file")
def run(
    graph_file: str,
    input_file: str,
    budget: float,
    rpm: int,
    output: Optional[str],
    output_format: str,
    fail_on_conflict: bool,
    max_steps: int,
    config: Optional[str],
):
    """
    Run Ghost-Run simulation on a LangGraph workflow.

    GRAPH_FILE: Path to Python file containing the LangGraph workflow
    INPUT_FILE: Path to JSON file with input state
    """

    try:
        # Load configuration if provided
        ghost_config = None
        if config:
            with open(config, "r") as f:
                config_data = yaml.safe_load(f)
                ghost_config = GhostConfig(**config_data)
        else:
            ghost_config = GhostConfig(
                budget_cap=budget,
                rpm_limit=rpm,
                fail_on_conflict=fail_on_conflict,
                max_steps=max_steps,
            )

        # Load input state
        with open(input_file, "r") as f:
            input_state = json.load(f)

        # Import and load the graph
        graph = _load_graph_from_file(graph_file)

        # Run simulation
        click.echo("🧾 Starting Ghost-Run simulation...")
        report = asyncio.run(ghost_run(graph, input_state, ghost_config=ghost_config))

        # Display summary
        _display_summary(report)

        # Save outputs
        if output:
            base_path = Path(output)
            if output_format in ["json", "both"]:
                json_path = base_path.with_suffix(".json")
                save_json_report(report, str(json_path))
                click.echo(f"📄 JSON report saved to: {json_path}")

            if output_format in ["html", "both"]:
                html_path = base_path.with_suffix(".html")
                save_html_report(report, str(html_path))
                click.echo(f"📄 HTML report saved to: {html_path}")
        else:
            # Default output to current directory
            timestamp = report.timestamp.replace(":", "-").split(".")[0]
            base_name = f"ghost_run_{timestamp}"

            if output_format in ["json", "both"]:
                json_path = f"{base_name}.json"
                save_json_report(report, json_path)
                click.echo(f"📄 JSON report saved to: {json_path}")

            if output_format in ["html", "both"]:
                html_path = f"{base_name}.html"
                save_html_report(report, html_path)
                click.echo(f"📄 HTML report saved to: {html_path}")

        # Exit with appropriate code
        if report.budget_exceeded or len(report.conflicts) > 0:
            sys.exit(1)
        else:
            click.echo("✅ Simulation completed successfully!")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def init(output: Optional[str]):
    """Initialize a Ghost-Run configuration file."""

    config_template = {
        "budget_cap": 10.0,
        "rpm_limit": 60,
        "fail_on_conflict": False,
        "fail_on_budget_exceeded": True,
        "enable_cost_estimation": True,
        "enable_conflict_detection": True,
        "enable_policy_checking": True,
        "max_steps": 100,
        "timeout_seconds": 30,
    }

    if output:
        config_path = Path(output)
    else:
        config_path = Path("ghost-run-config.yaml")

    with open(config_path, "w") as f:
        yaml.dump(config_template, f, default_flow_style=False, indent=2)

    click.echo(f"📄 Ghost-Run configuration created: {config_path}")
    click.echo("Edit the file to customize your simulation settings.")


@cli.command()
@click.argument("report_file", type=click.Path(exists=True))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["json", "html"]),
    default="html",
    help="Output format",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def convert(report_file: str, output_format: str, output: Optional[str]):
    """Convert a Ghost-Run JSON report to HTML format."""

    try:
        # Load JSON report
        with open(report_file, "r") as f:
            report_data = json.load(f)

        # Reconstruct report object
        from .reports import ConflictReport, GhostReport, StepReport

        # Convert steps
        steps = []
        for step_data in report_data.get("steps", []):
            conflicts = []
            for conflict_data in step_data.get("conflicts", []):
                conflicts.append(ConflictReport(**conflict_data))

            step = StepReport(
                step_number=step_data["step_number"],
                node_name=step_data["node_name"],
                duration_ms=step_data["duration_ms"],
                cost=step_data["cost"],
                tokens=step_data["tokens"],
                conflicts=conflicts,
                budget_exceeded=step_data.get("budget_exceeded", False),
                error=step_data.get("error"),
                state_snapshot=step_data.get("state_snapshot"),
            )
            steps.append(step)

        # Convert conflicts
        conflicts = []
        for conflict_data in report_data.get("conflicts", []):
            conflicts.append(ConflictReport(**conflict_data))

        # Create report
        report = GhostReport(
            simulation_id=report_data["simulation_id"],
            total_steps=report_data["total_steps"],
            total_cost=report_data["total_cost"],
            total_tokens=report_data["total_tokens"],
            execution_time_ms=report_data["execution_time_ms"],
            llm_calls=report_data["llm_calls"],
            api_calls=report_data["api_calls"],
            effects_count=report_data["effects_count"],
            steps=steps,
            conflicts=conflicts,
            policy_violations=report_data.get("policy_violations", []),
            budget_exceeded=report_data.get("budget_exceeded", False),
            input_state=report_data.get("input_state", {}),
            timestamp=report_data.get("timestamp", ""),
        )

        # Generate output
        if output_format == "html":
            if output:
                html_path = Path(output)
            else:
                html_path = Path(report_file).with_suffix(".html")

            save_html_report(report, str(html_path))
            click.echo(f"📄 HTML report saved to: {html_path}")

        elif output_format == "json":
            if output:
                json_path = Path(output)
            else:
                json_path = Path(report_file)

            save_json_report(report, str(json_path))
            click.echo(f"📄 JSON report saved to: {json_path}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


def _load_graph_from_file(graph_file: str):
    """Load a LangGraph workflow from a Python file."""

    graph_path = Path(graph_file)

    # Add the directory to Python path
    import sys

    sys.path.insert(0, str(graph_path.parent))

    # Import the module
    module_name = graph_path.stem
    module = __import__(module_name)

    # Look for common graph variable names
    graph_vars = ["graph", "workflow", "app", "state_graph"]

    for var_name in graph_vars:
        if hasattr(module, var_name):
            graph = getattr(module, var_name)
            return graph

    # If not found, try to find any StateGraph instance
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if hasattr(attr, "__class__") and "StateGraph" in str(attr.__class__):
            return attr

    raise ValueError(
        f"Could not find LangGraph workflow in {graph_file}. "
        f"Make sure the file contains a variable named one of: {graph_vars}"
    )


def _display_summary(report):
    """Display a summary of the simulation results."""

    click.echo("\n" + "=" * 60)
    click.echo("🧾 GHOST-RUN SIMULATION SUMMARY")
    click.echo("=" * 60)

    # Status
    if report.budget_exceeded:
        status = "❌ FAILED (Budget Exceeded)"
    elif len(report.conflicts) > 0:
        status = "⚠️  WARNINGS (Conflicts Detected)"
    else:
        status = "✅ PASSED"

    click.echo(f"Status: {status}")
    click.echo(f"Simulation ID: {report.simulation_id}")
    click.echo(f"Timestamp: {report.timestamp}")

    # Metrics
    click.echo("\n📊 METRICS:")
    click.echo(f"  Total Steps: {report.total_steps}")
    click.echo(f"  Total Cost: ${report.total_cost:.3f}")
    click.echo(f"  Total Tokens: {report.total_tokens:,}")
    click.echo(f"  Execution Time: {report.execution_time_ms:.0f}ms")

    # Calls
    click.echo("\n📞 CALLS:")
    click.echo(f"  LLM Calls: {report.llm_calls}")
    click.echo(f"  API Calls: {report.api_calls}")
    click.echo(f"  Side Effects: {report.effects_count}")

    # Issues
    click.echo("\n🚨 ISSUES:")
    click.echo(f"  Conflicts: {len(report.conflicts)}")
    click.echo(f"  Policy Violations: {len(report.policy_violations)}")
    click.echo(f"  Budget Exceeded: {'Yes' if report.budget_exceeded else 'No'}")

    # Cost breakdown
    if report.total_cost > 0:
        cost_breakdown = report.get_cost_breakdown()
        click.echo("\n💰 COST BREAKDOWN:")
        for node, cost in cost_breakdown.items():
            click.echo(f"  {node}: ${cost:.3f}")

    # Conflicts summary
    if report.conflicts:
        click.echo("\n🚨 CONFLICTS SUMMARY:")
        conflicts_by_type = report.get_conflicts_by_type()
        for conflict_type, conflicts in conflicts_by_type.items():
            click.echo(f"  {conflict_type}: {len(conflicts)}")

    click.echo("=" * 60)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
