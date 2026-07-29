#!/usr/bin/env bash
set -Eeuo pipefail

if test "$#" -ne 1; then
  printf '%s\n' "usage: rollback-release.sh RELEASE_ROOT" >&2
  exit 2
fi
release_root="$1"
source "$(dirname "$0")/release-lib.sh"
test -L "$release_root/current" || release_fail "current_release_link_missing"
test -L "$release_root/previous" || release_fail "previous_release_link_missing"
current_release="$(release_assert_under_root "$release_root" "$release_root/current")"
previous_release="$(release_assert_under_root "$release_root" "$release_root/previous")"
release_validate "$current_release"
release_validate "$previous_release"
test "$current_release" != "$previous_release" || release_fail "rollback_target_same_as_current"

restore_current() {
  release_compose "$previous_release" down --remove-orphans >/dev/null 2>&1 || true
  release_wait_project_stopped
  release_compose "$current_release" up -d
  release_wait_local "$(release_public_origin "$current_release")" "$(release_live_enabled "$current_release")"
}

release_compose "$current_release" down --remove-orphans || {
  restore_current
  release_fail "current_release_stop_failed"
}
if ! release_wait_project_stopped; then
  restore_current
  release_fail "current_release_stop_not_settled"
fi
if ! release_compose "$previous_release" up -d; then
  restore_current
  release_fail "previous_release_start_failed"
fi
if ! release_wait_local "$(release_public_origin "$previous_release")" "$(release_live_enabled "$previous_release")"; then
  restore_current
  release_fail "previous_release_health_failed"
fi
if ! release_switch_state "$release_root" "$previous_release" "$current_release"; then
  restore_current
  release_fail "rollback_release_state_commit_failed"
fi
printf '%s\n' "release_rolled_back=$previous_release"
