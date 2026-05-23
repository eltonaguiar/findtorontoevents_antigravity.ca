"""Swarm CLI entry point."""

import click

from swarms.cli.commands import (
    coding_command,
    pr_review_command,
    actions_command,
    research_command,
    ensemble_command,
    hierarchical_command,
    memory_command,
    skill_command,
)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def cli(ctx, verbose):
    """Multi-agent swarm system for coding, review, research, and more."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


cli.add_command(coding_command, name="coding")
cli.add_command(pr_review_command, name="pr-review")
cli.add_command(actions_command, name="actions")
cli.add_command(research_command, name="research")
cli.add_command(ensemble_command, name="ensemble")
cli.add_command(hierarchical_command, name="hierarchical")
cli.add_command(memory_command, name="memory")
cli.add_command(skill_command, name="skill")


if __name__ == "__main__":
    cli()
