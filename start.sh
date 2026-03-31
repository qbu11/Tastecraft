#!/usr/bin/env bash
# ==============================================================================
# Crew Media Ops — 本地开发启动脚本
#
# 用法: bash start.sh          启动前后端
#       bash start.sh stop     停止所有服务
#       bash start.sh status   查看服务状态
#       bash start.sh logs     查看后端日志
# ==============================================================================

set -euo pipefail

# ── 配置 ──
BACKEND_PORT=8100
FRONTEND_PORT=5173
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_SESSION="crew-backend"
FRONTEND_SESSION="crew-frontend"
TMUX="/c/Users/puzzl/AppData/Local/Microsoft/WinGet/Packages/arndawg.tmux-windows_Microsoft.Winget.Source_8wekyb3d8bbwe/tmux"

# ── 颜色 ──
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# ── 检查 tmux ──
check_tmux() {
    if [ ! -f "$TMUX" ]; then
        log_error "tmux 未找到: $TMUX"
        log_warn "请安装: winget install arndawg.tmux-windows"
        exit 1
    fi
}

# ── 停止服务 ──
stop_services() {
    log_info "停止服务..."
    "$TMUX" kill-session -t "$BACKEND_SESSION" 2>/dev/null && log_info "后端已停止" || true
    "$TMUX" kill-session -t "$FRONTEND_SESSION" 2>/dev/null && log_info "前端已停止" || true
    log_info "所有服务已停止"
}

# ── 查看状态 ──
show_status() {
    echo ""
    echo "=== Crew Media Ops 服务状态 ==="
    echo ""

    if "$TMUX" has-session -t "$BACKEND_SESSION" 2>/dev/null; then
        log_info "后端  : 运行中 (tmux: $BACKEND_SESSION, port: $BACKEND_PORT)"
    else
        log_error "后端  : 未运行"
    fi

    if "$TMUX" has-session -t "$FRONTEND_SESSION" 2>/dev/null; then
        log_info "前端  : 运行中 (tmux: $FRONTEND_SESSION, port: $FRONTEND_PORT)"
    else
        log_error "前端  : 未运行"
    fi

    echo ""
    echo "访问地址: http://localhost:$FRONTEND_PORT"
    echo "API 文档: http://localhost:$BACKEND_PORT/docs"
    echo ""
}

# ── 查看日志 ──
show_logs() {
    local target="${1:-backend}"
    if [ "$target" = "backend" ]; then
        "$TMUX" capture-pane -t "$BACKEND_SESSION" -p -S -50
    elif [ "$target" = "frontend" ]; then
        "$TMUX" capture-pane -t "$FRONTEND_SESSION" -p -S -50
    fi
}

# ── 启动服务 ──
start_services() {
    check_tmux

    # 检查是否已在运行
    if "$TMUX" has-session -t "$BACKEND_SESSION" 2>/dev/null; then
        log_warn "后端已在运行，先停止..."
        "$TMUX" kill-session -t "$BACKEND_SESSION" 2>/dev/null
    fi
    if "$TMUX" has-session -t "$FRONTEND_SESSION" 2>/dev/null; then
        log_warn "前端已在运行，先停止..."
        "$TMUX" kill-session -t "$FRONTEND_SESSION" 2>/dev/null
    fi

    # 启动后端
    log_info "启动后端 (port: $BACKEND_PORT)..."
    "$TMUX" new-session -d -s "$BACKEND_SESSION"
    "$TMUX" send-keys -t "$BACKEND_SESSION" "cd $PROJECT_DIR && uv run uvicorn src.api.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload" C-m

    # 等后端起来
    sleep 2

    # 启动前端
    log_info "启动前端 (port: $FRONTEND_PORT)..."
    "$TMUX" new-session -d -s "$FRONTEND_SESSION"
    "$TMUX" send-keys -t "$FRONTEND_SESSION" "cd $PROJECT_DIR/frontend && pnpm dev" C-m

    # 等前端起来
    sleep 3

    echo ""
    log_info "启动完成!"
    echo ""
    echo "  前端: http://localhost:$FRONTEND_PORT"
    echo "  后端: http://localhost:$BACKEND_PORT"
    echo "  API:  http://localhost:$BACKEND_PORT/docs"
    echo ""
    echo "  查看状态: bash start.sh status"
    echo "  查看日志: bash start.sh logs"
    echo "  停止服务: bash start.sh stop"
    echo ""
}

# ── 主入口 ──
case "${1:-start}" in
    start)   start_services ;;
    stop)    stop_services ;;
    status)  show_status ;;
    logs)    show_logs "${2:-backend}" ;;
    *)
        echo "用法: bash start.sh [start|stop|status|logs]"
        exit 1
        ;;
esac
