#!/usr/bin/env bash
# ============================================================================
# AIVON - cập nhật lên bản mới nhất từ GitHub.
#   ./update.sh            (tự nhận Docker hay native)
#   ./update.sh docker     (ép chế độ Docker)
#   ./update.sh native     (ép chế độ native/systemd)
# ============================================================================
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
MODE="${1:-auto}"
SUDO=""; [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1 && SUDO="sudo"

# Tên bản Aivon Ở THƯ MỤC NÀY. Nhiều bản trên cùng VPS thì mỗi bản một .env riêng; không đọc
# .env ở đây thì `./update.sh` của bản này đi restart container/dịch vụ của bản khác.
if [ -z "${AIVON_NAME:-}" ] && [ -f .env ]; then
  AIVON_NAME="$(sed -n 's/^[[:space:]]*AIVON_NAME[[:space:]]*=[[:space:]]*//p' .env | tail -1)"
fi
NAME="${AIVON_NAME:-aivon}"

echo "==> Pulling the latest code from GitHub..."
git pull --ff-only

is_docker() {
  command -v docker >/dev/null 2>&1 && [ -f docker-compose.yml ] && \
  docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$NAME"
}

if [ "$MODE" = "docker" ] || { [ "$MODE" = "auto" ] && is_docker; }; then
  echo "==> Docker → pulling the new image from GHCR and restarting..."
  # Đang bật HTTPS (Caddy)? Giữ nguyên override để cập nhật KHÔNG gỡ mất Caddy.
  HTTPS_ARGS=""
  if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$NAME-caddy"; then
    HTTPS_ARGS="-f docker-compose.yml -f docker-compose.https.yml"
    echo "==> Caddy (HTTPS) detected → keeping the HTTPS setup."
  fi
  # Đứng sau proxy dùng chung (nhiều bản, mỗi bản một tên miền) thì giữ luôn override multi,
  # không thì lượt cập nhật này gỡ mất nhãn Caddy và bản đó rơi khỏi proxy.
  if [ -f docker-compose.multi.yml ] && docker network inspect aivon-web >/dev/null 2>&1; then
    HTTPS_ARGS="-f docker-compose.yml -f docker-compose.multi.yml"
    echo "==> Shared proxy (aivon-web) detected → keeping the multi-instance setup."
  fi
  docker compose $HTTPS_ARGS pull
  docker compose $HTTPS_ARGS up -d
  echo "==> Done. Follow the logs:  docker compose logs -f"
else
  echo "==> Native → updating Python libraries and restarting the service..."
  [ -d .venv ] && ./.venv/bin/pip install -r requirements.txt -q || true
  # Updating Python alone leaves the ChatGPT model catalog on an old Codex CLI.
  if command -v npm >/dev/null 2>&1; then
    if ! npm install -g @openai/codex@latest && ! $SUDO npm install -g @openai/codex@latest; then
      echo "[!] Could not update Codex; the ChatGPT model list may be out of date."
    fi
  else
    echo "[!] npm not found; update Codex by hand to get the newest ChatGPT models."
  fi
  if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q "^$NAME\.service"; then
    $SUDO systemctl restart "$NAME"
    echo "==> Restarted. Follow the logs:  journalctl -u $NAME -f"
  elif [ "$(uname)" = "Darwin" ] && \
       launchctl print "gui/$(id -u)/${AIVON_LAUNCHD_LABEL:-com.aivon.os}" >/dev/null 2>&1; then
    # Mac chạy dưới launchd (KeepAlive): kill PID rồi tự chạy nohup là đua bind cổng với bản
    # launchd respawn ([Errno 48], vụ 14/08/2026). Để launchd tự đổi ca bằng kickstart -k.
    TARGET="gui/$(id -u)/${AIVON_LAUNCHD_LABEL:-com.aivon.os}"
    echo "==> launchd ($TARGET) detected → kickstart -k..."
    launchctl kickstart -k "$TARGET"
    echo "==> Asked launchd to restart Aivon. Logs: server/aivon.log"
  else
    # Mac / Linux không systemd: kill tiến trình đang giữ cổng rồi chạy lại nền (như install.sh)
    PORT="${AIVON_PORT:-7979}"
    PIDS="$(lsof -ti tcp:"$PORT" 2>/dev/null || true)"
    if [ -n "$PIDS" ]; then
      echo "==> Stopping the old process (PID: $PIDS)..."
      kill $PIDS 2>/dev/null || true
      sleep 2
    fi
    ( cd server && AIVON_STATE_DIR="$PWD" nohup ../.venv/bin/python -m uvicorn main:app \
        --host "${AIVON_HOST:-127.0.0.1}" --port "$PORT" > aivon.log 2>&1 & )
    echo "==> Restarted (nohup). Logs: server/aivon.log"
  fi
fi
