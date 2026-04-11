"""Daemon commands — start/stop the scheduler daemon."""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(no_args_is_help=True)
console = Console()


def _pid_file() -> str:
    """Return path to the daemon PID file."""
    from tastecraft.core.config import get_settings
    settings = get_settings()
    pid_dir = settings.home_dir
    pid_dir.mkdir(parents=True, exist_ok=True)
    return str(pid_dir / "daemon.pid")


def _write_pid(pid: int) -> None:
    """Write PID to file."""
    path = _pid_file()
    with open(path, "w") as f:
        f.write(str(pid))


def _read_pid() -> int | None:
    """Read PID from file. Returns None if file doesn't exist or is invalid."""
    path = _pid_file()
    try:
        with open(path) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def _remove_pid() -> None:
    """Remove PID file."""
    path = _pid_file()
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _is_process_alive(pid: int) -> bool:
    """Check if a process with the given PID is alive."""
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, timeout=5,
            )
            return str(pid) in result.stdout
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


def _kill_process(pid: int) -> bool:
    """Terminate a process by PID."""
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True, timeout=10,
            )
            return True
        except Exception:
            return False
    else:
        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except (OSError, ProcessLookupError):
            return False


@app.command(name="start")
def start(
    ctx: typer.Context,
    background: bool = typer.Option(False, "--background", help="Run as background process"),
) -> None:
    """Start the TasteCraft scheduler daemon."""
    if background:
        proc = subprocess.Popen(
            [sys.executable, "-m", "tastecraft", "daemon", "start"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _write_pid(proc.pid)
        console.print(f"[green]Daemon started in background (PID: {proc.pid}).[/green]")
        return

    # Foreground mode — write own PID
    _write_pid(os.getpid())
    asyncio.run(_start_daemon(ctx))


async def _start_daemon(ctx: typer.Context) -> None:
    from tastecraft.core.config import get_settings
    from tastecraft.core.logging import setup_logging
    from tastecraft.models.base import init_db
    from tastecraft.services.scheduler import TasteCraftScheduler

    settings = get_settings()
    setup_logging(log_file=settings.logs_dir / "daemon.log")
    await init_db(settings.database_url)

    scheduler = TasteCraftScheduler()
    await scheduler.start()

    console.print("[green]TasteCraft daemon started. Press Ctrl+C to stop.[/green]")
    jobs = scheduler.list_jobs()
    if jobs:
        table = Table(title="Scheduled Jobs")
        table.add_column("Job ID")
        table.add_column("Next Run")
        table.add_column("Trigger")
        for j in jobs:
            table.add_row(
                j["id"],
                str(j.get("next_run", "N/A")),
                j.get("trigger", ""),
            )
        console.print(table)

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        await scheduler.stop()
        _remove_pid()
        console.print("\n[yellow]Daemon stopped.[/yellow]")


@app.command(name="status")
def status(ctx: typer.Context) -> None:
    """Check daemon status."""
    pid = _read_pid()
    if pid is None:
        console.print("[yellow]Daemon is not running (no PID file).[/yellow]")
        return

    if _is_process_alive(pid):
        console.print(f"[green]Daemon is running (PID: {pid}).[/green]")
    else:
        console.print(f"[yellow]Daemon is not running (stale PID: {pid}). Cleaning up.[/yellow]")
        _remove_pid()


@app.command(name="stop")
def stop(ctx: typer.Context) -> None:
    """Stop the TasteCraft scheduler daemon."""
    pid = _read_pid()
    if pid is None:
        console.print("[yellow]Daemon is not running (no PID file).[/yellow]")
        return

    if not _is_process_alive(pid):
        console.print(f"[yellow]Daemon process {pid} is already dead. Cleaning up PID file.[/yellow]")
        _remove_pid()
        return

    if _kill_process(pid):
        _remove_pid()
        console.print(f"[green]Daemon stopped (PID: {pid}).[/green]")
    else:
        console.print(f"[red]Failed to stop daemon (PID: {pid}). Try killing manually.[/red]")
