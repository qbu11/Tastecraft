#!/usr/bin/env python3
"""
Publish Crew CLI - Run the content publishing pipeline.

Usage:
    python scripts/run_publish_crew.py --draft-id "draft-001" --platforms "xiaohongshu,wechat"
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.crew.crews.publish_crew import PublishCrew, PublishCrewInput, PublishCrewResult
from src.schemas import PlatformType

app = typer.Typer(
    name="publish-crew",
    help="Run the content publishing pipeline: adapt -> publish",
    add_completion=False,
)
console = Console()


def parse_platforms(platforms_str: str) -> list[str]:
    """Parse comma-separated platforms string."""
    valid_platforms = [p.value for p in PlatformType]
    platforms = [p.strip().lower() for p in platforms_str.split(",")]

    for platform in platforms:
        if platform not in valid_platforms:
            console.print(f"[red]Error: Invalid platform '{platform}'[/red]")
            console.print(f"[yellow]Valid platforms: {', '.join(valid_platforms)}[/yellow]")
            raise typer.Exit(1)

    return platforms


def load_draft(draft_id: str) -> dict:
    """Load draft data from file or database."""
    # Try loading from common file locations
    search_paths = [
        Path(f"data/content/{draft_id}.json"),
        Path(f"data/content/draft-{draft_id}.json"),
        Path(f"data/drafts/{draft_id}.json"),
    ]

    for path in search_paths:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            console.print(f"[green]Loaded draft from:[/green] {path}")
            return data

    # Return a placeholder if no file found
    console.print(f"[yellow]Draft file not found for '{draft_id}', using placeholder.[/yellow]")
    return {
        "id": draft_id,
        "title": f"Draft {draft_id}",
        "content": "Content placeholder - draft not found on disk.",
        "summary": "",
        "tags": [],
    }


def save_output(data: dict, output_path: Path) -> None:
    """Save output to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=serialize)

    console.print(f"[green]Output saved to:[/green] {output_path}")


def display_result(result: PublishCrewResult) -> None:
    """Display the publish result in a formatted way."""
    status_color = "green" if result.is_success() else "red"
    status_text = "SUCCESS" if result.is_success() else "FAILED"

    console.print()
    console.print(Panel(
        f"[{status_color}]{status_text}[/{status_color}] | "
        f"Execution time: {result.execution_time:.2f}s",
        title="[bold]Publish Crew Result[/bold]",
        border_style=status_color,
    ))

    if result.error:
        console.print(f"[red]Error:[/red] {result.error}")
        return

    # Publish records table
    if result.publish_records:
        table = Table(title="Publish Results")
        table.add_column("Platform", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("URL", style="blue")
        table.add_column("Published At", style="dim")

        for record in result.publish_records:
            platform = record.get("platform", "unknown")
            status = record.get("status", "unknown")
            url = record.get("published_url", "N/A")
            published_at = record.get("published_at", "N/A")

            status_style = "green" if status == "published" else "red"
            table.add_row(
                platform,
                f"[{status_style}]{status}[/{status_style}]",
                url if url != "N/A" else "[dim]N/A[/dim]",
                published_at,
            )

        console.print(table)

    # Summary
    if result.data and "summary" in result.data:
        summary = result.data["summary"]
        console.print(Panel(
            f"Total: {summary.get('total', 0)} | "
            f"[green]Success: {summary.get('successful', 0)}[/green] | "
            f"[red]Failed: {summary.get('failed', 0)}[/red] | "
            f"Rate: {summary.get('success_rate', '0%')}",
            title="[bold]Summary[/bold]",
            border_style="blue",
        ))

    # Platform-specific results
    if result.all_success:
        console.print("\n[green bold]All platforms published successfully![/green bold]")
    else:
        if result.successful_platforms:
            console.print(f"\n[green]Successful:[/green] {', '.join(result.successful_platforms)}")
        if result.failed_platforms:
            console.print(f"[red]Failed:[/red] {', '.join(result.failed_platforms)}")


@app.command()
def run(
    draft_id: Annotated[str, typer.Option("--draft-id", "-d", help="Draft ID to publish")],
    platforms: Annotated[str, typer.Option(
        "--platforms", "-p",
        help="Comma-separated target platforms (e.g., 'xiaohongshu,wechat')"
    )] = "xiaohongshu",
    schedule: Annotated[str | None, typer.Option(
        "--schedule", "-s",
        help="Schedule publish time (ISO format, e.g., '2026-03-20T10:00:00')"
    )] = None,
    output: Annotated[Path | None, typer.Option(
        "--output", "-o",
        help="Output file path for results (JSON)"
    )] = None,
    dry_run: Annotated[bool, typer.Option(
        "--dry-run",
        help="Simulate execution without actually publishing"
    )] = False,
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Enable verbose output"
    )] = False,
    no_retry: Annotated[bool, typer.Option(
        "--no-retry",
        help="Disable automatic retry on failure"
    )] = False,
    max_retries: Annotated[int, typer.Option(
        "--max-retries",
        help="Maximum number of retries per platform"
    )] = 3,
) -> None:
    """
    Run the publish crew to distribute content to platforms.

    The crew will:
    1. Load the content draft
    2. Adapt content for each target platform
    3. Publish to all platforms (in parallel)

    Example:
        python scripts/run_publish_crew.py \\
            --draft-id "draft-001" \\
            --platforms "xiaohongshu,wechat" \\
            --schedule "2026-03-20T10:00:00"
    """
    # Parse and validate platforms
    platform_list = parse_platforms(platforms)

    # Validate schedule time
    scheduled_time = None
    if schedule:
        try:
            scheduled_time = datetime.fromisoformat(schedule)
            if scheduled_time < datetime.now():
                console.print("[yellow]Warning: Scheduled time is in the past.[/yellow]")
        except ValueError:
            console.print(f"[red]Error: Invalid schedule format '{schedule}'. Use ISO format.[/red]")
            raise typer.Exit(1)

    # Display input summary
    schedule_display = scheduled_time.isoformat() if scheduled_time else "Immediate"
    console.print(Panel(
        f"[bold]Draft ID:[/bold] {draft_id}\n"
        f"[bold]Platforms:[/bold] {', '.join(platform_list)}\n"
        f"[bold]Schedule:[/bold] {schedule_display}\n"
        f"[bold]Retry:[/bold] {'Disabled' if no_retry else f'Enabled (max {max_retries})'}",
        title="[bold]Publish Crew Input[/bold]",
        border_style="blue",
    ))

    if dry_run:
        console.print("\n[yellow]DRY RUN - Simulating publish...[/yellow]")

        mock_result = {
            "status": "success",
            "dry_run": True,
            "draft_id": draft_id,
            "platforms": platform_list,
            "schedule": schedule_display,
            "timestamp": datetime.now().isoformat(),
            "estimated_duration": "1-3 minutes",
            "steps": [
                "1. Load draft content",
                "2. Adapt content for each platform (PlatformAdapter)",
                f"3. Publish to {len(platform_list)} platform(s) (PlatformPublisher)",
            ],
            "simulated_results": [
                {"platform": p, "status": "published", "url": f"https://{p}.example.com/post/xxx"}
                for p in platform_list
            ],
        }

        if output:
            save_output(mock_result, output)
        else:
            console.print_json(data=mock_result)

        console.print("\n[green]Dry run completed successfully![/green]")
        return

    # Load draft
    content_draft = load_draft(draft_id)

    # Create crew input
    crew_input = PublishCrewInput(
        content_id=draft_id,
        content_draft=content_draft,
        target_platforms=platform_list,
        schedule_time=schedule,
        enable_retry=not no_retry,
    )

    # Run the crew
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Preparing publish...[/cyan]",
                total=100,
            )

            crew = PublishCrew.create(
                enable_retry=not no_retry,
                max_retries=max_retries,
                verbose=verbose,
            )

            progress.update(task, advance=10, description="[cyan]Adapting content...[/cyan]")

            result = crew.execute(crew_input)

            progress.update(task, advance=90, description="[cyan]Finalizing...[/cyan]")
            progress.update(task, completed=100)

        # Display results
        display_result(result)

        # Save output
        if output and result.is_success():
            output_data = {
                "status": result.status.value,
                "draft_id": draft_id,
                "platforms": platform_list,
                "schedule": schedule_display,
                "adapted_contents": result.adapted_contents,
                "publish_records": result.publish_records,
                "execution_time": result.execution_time,
                "timestamp": datetime.now().isoformat(),
            }
            save_output(output_data, output)

        if not result.is_success():
            raise typer.Exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def status(
    draft_id: Annotated[str, typer.Option("--draft-id", "-d", help="Draft ID to check")],
) -> None:
    """Check the publish status of a draft."""
    console.print(f"[cyan]Checking publish status for:[/cyan] {draft_id}")

    # Look for publish result files
    result_paths = [
        Path(f"data/publish/{draft_id}.json"),
        Path(f"data/publish/result-{draft_id}.json"),
    ]

    for path in result_paths:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            console.print_json(data=data)
            return

    console.print(f"[yellow]No publish records found for '{draft_id}'[/yellow]")


@app.command()
def version() -> None:
    """Show version information."""
    console.print("[bold cyan]Publish Crew CLI[/bold cyan] v0.1.0")
    console.print("Part of Crew Media Ops")


if __name__ == "__main__":
    app()
