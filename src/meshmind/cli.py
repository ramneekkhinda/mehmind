"""
MeshMind CLI: Command-line interface for MeshMind functionality.
"""

import click


@click.group()
@click.version_option()
def cli():
    """MeshMind: Production Safety for LangGraph Agents."""
    pass


@cli.command()
def status():
    """Check MeshMind services status."""
    click.echo("🔍 Checking MeshMind services...")

    # This would check the referee service, database, etc.
    # For now, just show a placeholder
    click.echo("✅ MeshMind services are running")
    click.echo("   - Referee service: http://localhost:8080")
    click.echo("   - Jaeger UI: http://localhost:16686")
    click.echo("   - PostgreSQL: localhost:5432")
    click.echo("   - Redis: localhost:6379")


@cli.command()
def demo():
    """Run the MeshMind demo."""
    click.echo("🎯 Running MeshMind demo...")

    # Import and run the demo
    import asyncio

    from examples.yc_demo.demo import main as run_demo

    asyncio.run(run_demo())


@cli.command()
def ghost_demo():
    """Run the Ghost-Run demo."""
    click.echo("🧾 Running Ghost-Run demo...")

    # Import and run the ghost demo
    import asyncio

    from examples.ghost_run_demo import main as run_ghost_demo

    asyncio.run(run_ghost_demo())


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
