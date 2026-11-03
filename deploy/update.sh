#!/usr/bin/env bash
# Pulls the latest commit of the deploy branch (default: main) and restarts the
# dashboard when something changed. Run every minute by ledmatrix-update.timer.
# Logs: journalctl -u ledmatrix-update
#
# Everything lives inside main() so bash has read the whole script before
# `git reset` can replace this file with a newer version.

main() {
    set -uo pipefail
    local repo branch owner local_rev remote_rev changed
    repo="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
    branch="${LEDMATRIX_BRANCH:-main}"
    owner="$(stat -c %U "$repo")"

    # Run git as the owner of the checkout so files never become root-owned.
    g() { runuser -u "$owner" -- git -C "$repo" "$@"; }

    if ! g fetch --quiet origin "$branch"; then
        echo "Could not reach GitHub, will try again next minute."
        return 0
    fi

    local_rev="$(g rev-parse HEAD)"
    remote_rev="$(g rev-parse "origin/$branch")"
    [ "$local_rev" = "$remote_rev" ] && return 0

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

    if grep -q '^deploy/' <<<"$changed"; then
        echo "Deploy files changed, reinstalling services"
        bash "$repo/deploy/install.sh" --from-update
    fi

    systemctl restart ledmatrix.service
    echo "Dashboard restarted on ${remote_rev:0:7}"
}

main "$@"
exit $?
