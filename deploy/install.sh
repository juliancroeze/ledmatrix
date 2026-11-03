#!/usr/bin/env bash
# One-time setup on the Raspberry Pi (safe to run again):
#   sudo bash deploy/install.sh
#
# - installs the Python packages
# - runs the dashboard as a service that starts on boot (ledmatrix.service)
# - checks GitHub every minute and deploys new commits on the branch
#   (ledmatrix-update.timer)
#
# Options (environment variables):
#   LEDMATRIX_BRANCH=main     branch the Pi follows
#   LEDMATRIX_ARGS="--https"  arguments for index.py (use "" for plain http)

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this with sudo:  sudo bash deploy/install.sh" >&2
    exit 1
fi

REPO="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
OWNER="$(stat -c %U "$REPO")"
BRANCH="${LEDMATRIX_BRANCH:-main}"
ARGS="${LEDMATRIX_ARGS---https}"
FROM_UPDATE="${1:-}"

if [ ! -d "$REPO/.git" ]; then
    echo "$REPO is not a git checkout. Clone the repository first (see README)." >&2
    exit 1
fi

echo "== LED matrix: installing from $REPO (branch $BRANCH, owner $OWNER)"

# Files the dashboard created while running as root block git/SFTP; give them back.
chown -R "$OWNER:$OWNER" "$REPO"
runuser -u "$OWNER" -- git config --global --add safe.directory "$REPO" 2>/dev/null || true

if [ "$FROM_UPDATE" != "--from-update" ]; then
    echo "== Python packages"
    pip3 install -q -r "$REPO/src/scripts/requirements.txt" \
        || pip3 install -q --break-system-packages -r "$REPO/src/scripts/requirements.txt"

    if ! python3 -c "import rgbmatrix" 2>/dev/null; then
        echo "!! The rgbmatrix Python module is not installed. Build it once from the" >&2
        echo "!! upstream library (hzeller/rpi-rgb-led-matrix): make build-python && sudo make install-python" >&2
    fi
fi

echo "== systemd services"
render() { sed -e "s|@REPO@|$REPO|g" -e "s|@ARGS@|$ARGS|g" -e "s|@BRANCH@|$BRANCH|g" "$1"; }
render "$REPO/deploy/ledmatrix.service"        > /etc/systemd/system/ledmatrix.service
render "$REPO/deploy/ledmatrix-update.service" > /etc/systemd/system/ledmatrix-update.service
render "$REPO/deploy/ledmatrix-update.timer"   > /etc/systemd/system/ledmatrix-update.timer
systemctl daemon-reload

if [ "$FROM_UPDATE" != "--from-update" ]; then
    # A dashboard started by hand would hold the LED pins and port 8000.
    pkill -f "python3 index.py" 2>/dev/null || true
    sleep 1
    systemctl enable --now ledmatrix.service
    systemctl enable --now ledmatrix-update.timer
    systemctl restart ledmatrix.service
    echo
    echo "Done. The dashboard runs as a service and follows the '$BRANCH' branch on GitHub."
    echo "  Status:        systemctl status ledmatrix"
    echo "  Dashboard log: journalctl -u ledmatrix -f"
    echo "  Update log:    journalctl -u ledmatrix-update"
fi
