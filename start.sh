#!/bin/bash
# TasteCraft — development start script
# Usage: bash start.sh [start|docker|docker-dev|stop|migrate|migrate-create <msg>|status|logs]

set -euo pipefail

BACKEND_PORT=8000
FRONTEND_PORT=5173
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

case "${1:-start}" in
  start)
    echo "Starting TasteCraft development environment..."
    echo "  Backend:  http://localhost:$BACKEND_PORT"
    echo "  Frontend: http://localhost:$FRONTEND_PORT"
    echo ""

    # Start backend
    cd "$PROJECT_DIR/backend"
    uv run uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload &
    BACKEND_PID=$!
    cd "$PROJECT_DIR"

    # Start frontend
    cd "$PROJECT_DIR/frontend"
    pnpm dev --host &
    FRONTEND_PID=$!
    cd "$PROJECT_DIR"

    echo "Backend PID:  $BACKEND_PID"
    echo "Frontend PID: $FRONTEND_PID"

    # Wait for either to exit
    wait
    ;;

  docker)
    echo "Starting TasteCraft with Docker Compose (production)..."
    cd "$PROJECT_DIR"
    docker compose up --build
    ;;

  docker-dev)
    echo "Starting TasteCraft dev environment with Docker..."
    cd "$PROJECT_DIR"
    docker compose -f docker-compose.dev.yml up --build
    ;;

  stop)
    echo "Stopping TasteCraft..."
    pkill -f "uvicorn app.main" 2>/dev/null || true
    pkill -f "pnpm dev" 2>/dev/null || true
    cd "$PROJECT_DIR" && docker compose down 2>/dev/null || true
    echo "Stopped."
    ;;

  migrate)
    echo "Running database migrations..."
    cd "$PROJECT_DIR/backend" && uv run alembic upgrade head
    ;;

  migrate-create)
    if [ -z "${2:-}" ]; then
      echo "Usage: $0 migrate-create <message>"
      exit 1
    fi
    echo "Creating new migration: $2"
    cd "$PROJECT_DIR/backend" && uv run alembic revision --autogenerate -m "$2"
    ;;

  status)
    echo "=== TasteCraft Status ==="
    echo ""
    echo "Backend (port $BACKEND_PORT):"
    if lsof -i ":$BACKEND_PORT" >/dev/null 2>&1 || netstat -ano 2>/dev/null | grep -q ":$BACKEND_PORT"; then
      echo "  RUNNING"
    else
      echo "  STOPPED"
    fi
    echo ""
    echo "Frontend (port $FRONTEND_PORT):"
    if lsof -i ":$FRONTEND_PORT" >/dev/null 2>&1 || netstat -ano 2>/dev/null | grep -q ":$FRONTEND_PORT"; then
      echo "  RUNNING"
    else
      echo "  STOPPED"
    fi
    echo ""
    echo "Docker containers:"
    docker compose ps 2>/dev/null || echo "  No Docker containers running"
    echo ""
    echo "Alembic migration status:"
    cd "$PROJECT_DIR/backend" && uv run alembic current 2>/dev/null || echo "  Unable to check"
    ;;

  *)
    echo "TasteCraft Start Script"
    echo ""
    echo "Usage: $0 {command}"
    echo ""
    echo "Commands:"
    echo "  start           Start backend + frontend (dev mode, default)"
    echo "  docker          Start all services via Docker Compose (production)"
    echo "  docker-dev      Start with Docker (dev mode, hot reload)"
    echo "  stop            Stop all running services"
    echo "  migrate         Run database migrations (alembic upgrade head)"
    echo "  migrate-create  Create new migration (e.g., $0 migrate-create 'add foo table')"
    echo "  status          Show status of all services"
    ;;
esac
