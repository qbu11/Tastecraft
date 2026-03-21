#!/usr/bin/env python3
"""
Analytics Crew CLI - Run the content analytics pipeline.

Usage:
    python scripts/run_analytics_crew.py --content-id "xxx" --period "7d"
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich import print as rprint

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.crew.crews.analytics_crew import AnalyticsCrew, AnalyticsCrewInput, AnalyticsCrewResult
from src.schemas import PlatformType, TimePeriod

app = typer.Typer(
    name="analytics-crew",
    help="Run the content analytics pipeline: collect -> analyze -> recommend",
    add_completion=False,
)
console = Console()


def parse_period(period: str) -> tuple[datetime, datetime]:
    """Parse period string and return start/end datetimes."""
    period_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "1d": timedelta(days=1),
        "3d": timedelta(days=3),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    if period not in period_map:
        console.print(f"[red]Error: Invalid period '{period}'.[/red]")
        console.print(f"[yellow]Valid periods: {', '.join(period_map.keys())}[/yellow]")
        raise typer.Exit(1)

    end_time = datetime.now()
    start_time = end_time - period_map[period]
    return start_time, end_time


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


def display_result(result: AnalyticsCrewResult, period: str) -> None:
    """Display the analytics result in a formatted way."""
    status_color = "green" if result.is_success() else "red"
    status_text = "SUCCESS" if result.is_success() else "FAILED"

    console.print()
    console.print(Panel(
        f"[{status_color}]{status_text}[/{status_color}] | "
        f"Period: {period} | "
        f"Execution time: {result.execution_time:.2f}s",
        title="[bold]Analytics Crew Result[/bold]",
        border_style=status_color,
    ))

    if result.error:
        console.print(f"[red]Error:[/red] {result.error}")
        return

    # Key metrics
    if result.analysis_report:
        metrics = result.analysis_report.get("metrics_summary", {})
        if metrics:
            console.print("\n[bold cyan]📊 Key Metrics[/bold cyan]")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green", justify="right")

            table.add_row("Total Views", f"{metrics.get('total_views', 0):,}")
            table.add_row("Total Likes", f"{metrics.get('total_likes', 0):,}")
            table.add_row("Avg Engagement Rate", f"{metrics.get('avg_engagement_rate', 0):.2f}%")
            table.add_row("Content Analyzed", str(metrics.get('total_content', 0)))

            console.print(table)

    # Top performers
    if result.top_performers:
        console.print("\n[bold cyan]🏆 Top Performers[/bold cyan]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Title", style="cyan", max_width=40)
        table.add_column("Platform", style="yellow")
        table.add_column("Views", style="green", justify="right")
        table.add_column("Engagement", style="blue", justify="right")

        for item in result.top_performers[:5]:
            title = item.get("title", "N/A")[:40]
            platform = item.get("platform", "unknown")
            views = item.get("views", 0)
            engagement = item.get("engagement_rate", 0)

            table.add_row(
                title,
                platform,
                f"{views:,}",
                f"{engagement:.2f}%",
            )

        console.print(table)

    # Key findings
    if result.key_findings:
        console.print("\n[bold cyan]🔍 Key Findings[/bold cyan]")
        for i, finding in enumerate(result.key_findings[:5], 1):
            console.print(f"  {i}. {finding}")

    # Recommendations
    if result.recommendations:
        console.print("\n[bold cyan]💡 Recommendations[/bold cyan]")

        # Group by priority
        high_priority = [r for r in result.recommendations if r.get("priority") == "high"]
        medium_priority = [r for r in result.recommendations if r.get("priority") == "medium"]

        if high_priority:
            console.print("\n  [red bold]High Priority:[/red bold]")
            for rec in high_priority[:3]:
                action = rec.get("action", "N/A")
                console.print(f"    - {action}")

        if medium_priority:
            console.print("\n  [yellow bold]Medium Priority:[/yellow bold]")
            for rec in medium_priority[:3]:
                action = rec.get("action", "N/A")
                console.print(f"    - {action}")

    # Quick stats
    console.print()
    console.print(Panel(
        f"Collected {len(result.collected_data)} data points | "
        f"Generated {len(result.recommendations)} recommendations",
        title="[bold]Summary[/bold]",
        border_style="blue",
    ))


@app.command()
def run(
    content_id: Annotated[str, typer.Option(
        "--content-id", "-c",
        help="Content ID to analyze (comma-separated for multiple)"
    )],
    period: Annotated[str, typer.Option(
        "--period", "-p",
        help="Analysis period: 1h, 6h, 24h, 1d, 3d, 7d, 30d"
    )] = "7d",
    platforms: Annotated[str | None, typer.Option(
        "--platforms",
        help="Filter by platforms (comma-separated)"
    )] = None,
    output: Annotated[Path | None, typer.Option(
        "--output", "-o",
        help="Output file path for results (JSON)"
    )] = None,
    report_format: Annotated[str, typer.Option(
        "--format", "-f",
        help="Report format: json, markdown"
    )] = "json",
    dry_run: Annotated[bool, typer.Option(
        "--dry-run",
        help="Simulate execution without running the crew"
    )] = False,
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Enable verbose output"
    )] = False,
) -> None:
    """
    Run the analytics crew to analyze content performance.

    The crew will:
    1. Collect performance data from platforms
    2. Analyze trends and patterns
    3. Generate optimization recommendations

    Example:
        python scripts/run_analytics_crew.py \\
            --content-id "content-001,content-002" \\
            --period "7d" \\
            --output "data/analytics/report-001.json"
    """
    # Parse content IDs
    content_ids = [cid.strip() for cid in content_id.split(",")]

    # Parse period
    period_start, period_end = parse_period(period)

    # Parse platforms
    platform_list = None
    if platforms:
        valid_platforms = [p.value for p in PlatformType]
        platform_list = [p.strip().lower() for p in platforms.split(",")]
        for p in platform_list:
            if p not in valid_platforms:
                console.print(f"[red]Error: Invalid platform '{p}'[/red]")
                raise typer.Exit(1)

    # Display input summary
    platform_display = ", ".join(platform_list) if platform_list else "All"
    console.print(Panel(
        f"[bold]Content IDs:[/bold] {', '.join(content_ids)}\n"
        f"[bold]Period:[/bold] {period} ({period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')})\n"
        f"[bold]Platforms:[/bold] {platform_display}\n"
        f"[bold]Report Format:[/bold] {report_format}",
        title="[bold]Analytics Crew Input[/bold]",
        border_style="blue",
    ))

    if dry_run:
        console.print("\n[yellow]DRY RUN - Simulating analytics...[/yellow]")

        mock_result = {
            "status": "success",
            "dry_run": True,
            "content_ids": content_ids,
            "period": period,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "platforms": platform_list,
            "timestamp": datetime.now().isoformat(),
            "estimated_duration": "1-3 minutes",
            "steps": [
                "1. Collect data from platforms (DataCollector)",
                "2. Analyze performance metrics (DataAnalyzer)",
                "3. Generate recommendations (StrategyAdvisor)",
            ],
            "simulated_metrics": {
                "total_views": 15000,
                "total_likes": 1200,
                "total_comments": 89,
                "avg_engagement_rate": 8.5,
            },
        }

        if output:
            save_output(mock_result, output)
        else:
            console.print_json(data=mock_result)

        console.print("\n[green]Dry run completed successfully![/green]")
        return

    # Create crew input
    crew_input = AnalyticsCrewInput(
        content_ids=content_ids,
        time_range=period,
        platforms=platform_list or ["xiaohongshu"],
        metrics=["views", "likes", "comments", "shares", "engagement_rate"],
        report_format=report_format,
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
                "[cyan]Starting analytics...[/cyan]",
                total=100,
            )

            crew = AnalyticsCrew.create(verbose=verbose)

            progress.update(task, advance=10, description="[cyan]Collecting data...[/cyan]")

            result = crew.execute(crew_input)

            progress.update(task, advance=90, description="[cyan]Finalizing report...[/cyan]")
            progress.update(task, completed=100)

        # Display results
        display_result(result, period)

        # Save output
        if output and result.is_success():
            output_data = {
                "status": result.status.value,
                "content_ids": content_ids,
                "period": period,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "platforms": platform_list,
                "collected_data": result.collected_data,
                "analysis_report": result.analysis_report,
                "recommendations": result.recommendations,
                "execution_time": result.execution_time,
                "timestamp": datetime.now().isoformat(),
            }

            if report_format == "markdown":
                output_path = output.with_suffix(".md")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result.to_markdown_report())
                console.print(f"[green]Markdown report saved to:[/green] {output_path}")
            else:
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
def quick(
    content_id: Annotated[str, typer.Option(
        "--content-id", "-c",
        help="Content ID for quick stats"
    )],
) -> None:
    """Get quick statistics for a single content."""
    console.print(f"[cyan]Fetching quick stats for:[/cyan] {content_id}")

    # This would normally call the data collection tool directly
    # For now, show a placeholder
    console.print(Panel(
        f"[bold]Content ID:[/bold] {content_id}\n"
        f"[bold]Views:[/bold] 15,234\n"
        f"[bold]Likes:[/bold] 1,245\n"
        f"[bold]Comments:[/bold] 89\n"
        f"[bold]Engagement Rate:[/bold] 8.7%",
        title="[bold]Quick Stats[/bold]",
        border_style="green",
    ))


@app.command()
def periods() -> None:
    """List all supported analysis periods."""
    table = Table(title="Supported Analysis Periods")
    table.add_column("Period", style="cyan")
    table.add_column("Description", style="green")

    descriptions = {
        "1h": "Last hour",
        "6h": "Last 6 hours",
        "24h": "Last 24 hours",
        "1d": "Last day",
        "3d": "Last 3 days",
        "7d": "Last 7 days (1 week)",
        "30d": "Last 30 days (1 month)",
    }

    for period, desc in descriptions.items():
        table.add_row(period, desc)

    console.print(table)


@app.command()
def version() -> None:
    """Show version information."""
    console.print("[bold cyan]Analytics Crew CLI[/bold cyan] v0.1.0")
    console.print("Part of Crew Media Ops")


if __name__ == "__main__":
    app()
