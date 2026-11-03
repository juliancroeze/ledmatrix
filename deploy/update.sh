#!/usr/bin/env bash
# Keeps the Pi on the latest commit of the deploy branch (default: main).
#
#   update.sh           check once and update if needed
#   update.sh --watch   keep checking every LEDMATRIX_INTERVAL seconds (default 20);
#                       this is what ledmatrix-update.service runs
#
# Each check only asks GitHub for the branch's latest commit ID (git ls-remote,
# a few hundred bytes). Code is only downloaded when that ID has changed.
# Logs: journalctl -u ledmatrix-update
#
# Everything lives inside functions so bash has read the whole script before
# `git reset` can replace this file with a newer version.

check_once() {
    local local_rev remote_rev changed

    if ! remote_rev="$(g ls-remote --quiet origin "refs/heads/$branch" 2>/dev/null | cut -f1)" || [ -z "$remote_rev" ]; then
        if [ "$offline" = 0 ]; then echo "Can't reach GitHub, will keep trying."; fi
        offline=1
        return 0
    fi
    if [ "$offline" = 1 ]; then echo "GitHub reachable again."; fi
    offline=0

    local_rev="$(g rev-parse HEAD)"
    [ "$local_rev" = "$remote_rev" ] && return 0

    # Something changed: now download it.
    g fetch --quiet origin "$branch" || { echo "Download failed, will retry."; return 0; }
    remote_rev="$(g rev-parse "origin/$branch")"
    changed="$(g diff --name-only "$local_rev" "$remote_rev")"
    echo "Updating ${local_rev:0:7} -> ${remote_rev:0:7} ($(g log -1 --format=%s "$remote_rev"))"

    # The Pi always mirrors the branch exactly; local edits on the Pi are discarded.
    g checkout --quiet "$branch" 2>/dev/null || g checkout --quiet -B "$branch" "origin/$branch"
    g reset --hard --quiet "origin/$branch"

    if grep -q 'src/scripts/requirements.txt' <<<"$changed"; then
        echo "requirements.txt changed, installing Python packages"
        pip3 install -q -r "$repo/src/scripts/requirements.txt" \
            || pip3 install -q --break-system-packages -r "$repo/src/scripts/requirements.txt"
    fi

    local deploy_changed=0
    if grep -q '^deploy/' <<<"$changed"; then
        echo "Deploy files changed, reinstalling services"
        bash "$repo/deploy/install.sh" --from-update
        deploy_changed=1
    fi

    systemctl restart ledmatrix.service
    echo "Dashboard restarted on ${remote_rev:0:7}"

    if [ "$deploy_changed" = 1 ]; then
        # Restart this updater too, so it runs the new version of this script.
        systemctl restart --no-block ledmatrix-update.service
    fi
}

main() {
    set -uo pipefail
    repo="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
    branch="${LEDMATRIX_BRANCH:-main}"
    interval="${LEDMATRIX_INTERVAL:-20}"
    owner="$(stat -c %U "$repo")"
    offline=0

    # Run git as the owner of the checkout so files never become root-owned.
    g() { runuser -u "$owner" -- git -C "$repo" "$@"; }

    if [ "${1:-}" = "--watch" ]; then
        echo "Following '$branch' on GitHub, checking every ${interval}s"
        while true; do
            check_once
            sleep "$interval"
        done
    else
        check_once
    fi
}

main "$@"
exit $?
