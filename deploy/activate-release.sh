#!/usr/bin/env bash
set -Eeuo pipefail

if test "$#" -ne 2; then
  printf '%s\n' "usage: activate-release.sh RELEASE_ROOT RELEASE_DIR" >&2
  exit 2
fi
release_root="$1"
requested_release="$2"
source "$(dirname "$0")/release-lib.sh"
release_dir="$(release_assert_under_root "$release_root" "$requested_release")"
release_validate "$release_dir"
test -f "$release_dir/release-manifest.json" || release_fail "canonical_release_required"
release_preflight_images "$release_dir"
public_origin="$(release_public_origin "$release_dir")"

old_release=""
if test -L "$release_root/current"; then
  old_release="$(release_resolve "$release_root/current")"
  if test "$old_release" = "$release_dir"; then
    release_wait_local "$public_origin"
    printf '%s\n' "release_already_active=$release_dir"
    exit 0
  fi
  release_validate "$old_release"
fi
test -n "$old_release" || release_fail "current_release_anchor_missing"

restore_old() {
  release_compose "$release_dir" down --remove-orphans >/dev/null 2>&1 || true
  release_wait_project_stopped
  if test -n "$old_release"; then
    release_compose "$old_release" up -d
    release_wait_local "$(release_public_origin "$old_release")"
  fi
}

if test -n "$old_release"; then
  release_compose "$old_release" down --remove-orphans || {
    restore_old
    release_fail "current_release_stop_failed"
  }
  if ! release_wait_project_stopped; then
    restore_old
    release_fail "current_release_stop_not_settled"
  fi
fi
if ! release_compose "$release_dir" up -d; then
  restore_old
  release_fail "candidate_release_start_failed"
fi
if ! release_wait_local "$public_origin"; then
  restore_old
  release_fail "candidate_release_health_failed"
fi

if ! release_switch_state "$release_root" "$release_dir" "$old_release"; then
  restore_old
  release_fail "candidate_release_state_commit_failed"
fi
printf '%s\n' "release_activated=$release_dir"
