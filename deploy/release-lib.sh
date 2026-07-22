#!/usr/bin/env bash
set -Eeuo pipefail

release_fail() {
  printf '%s\n' "$1" >&2
  return 1
}

release_resolve() {
  python3 - "$1" <<'PY'
import os, sys
print(os.path.realpath(sys.argv[1]))
PY
}

release_assert_under_root() {
  local release_root="$1"
  local release_dir="$2"
  local resolved_root resolved_release
  resolved_root="$(release_resolve "$release_root")"
  resolved_release="$(release_resolve "$release_dir")"
  case "$resolved_release" in
    "$resolved_root"/releases/*) ;;
    *) release_fail "release_path_outside_root" ;;
  esac
  test -d "$resolved_release" || release_fail "release_directory_missing"
  printf '%s\n' "$resolved_release"
}

release_validate() {
  local release_dir="$1"
  if test -f "$release_dir/release-manifest.json"; then
    python3 "$release_dir/tools/release_manifest.py" \
      --verify "$release_dir/release-manifest.json" >/dev/null
  elif test -f "$release_dir/legacy-release.json"; then
    python3 - "$release_dir/legacy-release.json" <<'PY'
import json, pathlib, sys
value = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
if value.get("schema_version") != "traceable-legacy-release-v1":
    raise SystemExit("legacy_release_manifest_invalid")
if value.get("provider_enabled") is not False:
    raise SystemExit("legacy_provider_not_disabled")
PY
  else
    release_fail "release_manifest_missing"
  fi
  test -f "$release_dir/deploy/compose.yaml" || release_fail "release_compose_missing"
  test -f "$release_dir/deploy/switch_release_state.py" \
    || release_fail "release_state_switcher_missing"
  test -f "$release_dir/release.env" || release_fail "release_environment_missing"
  test "$(stat -c '%a' "$release_dir/release.env")" = "600" \
    || release_fail "release_environment_mode_invalid"
}

release_compose() {
  local release_dir="$1"
  shift
  docker compose \
    --project-name traceable-support \
    --env-file "$release_dir/release.env" \
    -f "$release_dir/deploy/compose.yaml" \
    "$@"
}

release_health() {
  local web_base="$1"
  local api_base="$2"
  local public_origin="$3"
  local route health_body
  health_body="/tmp/traceable-health-body.$$-${RANDOM}.json"
  trap 'rm -f "$health_body"' RETURN
  for route in / /design /app /privacy; do
    curl --fail --silent --show-error --max-time 10 "$web_base$route" >/dev/null
  done
  curl --fail --silent --show-error --max-time 10 \
    "$api_base/api/v1/health" |
    python3 -c 'import json,sys; value=json.load(sys.stdin); assert value == {"status":"ok","service":"traceable-support-public-api","live_experience":"replay_only"}'

  local body status
  body='{"task_type":"qa","input_mode":"free_text","text":"CZ-R1如何复位？","product_model":"CZ-R1","consent":true}'
  status="$(curl --silent --show-error --max-time 10 --output "$health_body" \
    --write-out '%{http_code}' -X POST "$api_base/api/v1/runs" \
    -H "Origin: $public_origin" -H 'Content-Type: application/json' --data-binary "$body")"
  test "$status" = "503" || release_fail "replay_fail_closed_status_invalid"
  python3 - "$health_body" <<'PY'
import json, pathlib, sys
value=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
assert value["error"]["code"] == "live_experience_unavailable"
PY

  status="$(curl --silent --show-error --max-time 10 --output /dev/null --write-out '%{http_code}' \
    -X POST "$api_base/api/v1/runs" -H 'Origin: https://invalid.example' \
    -H 'Content-Type: application/json' --data-binary "$body")"
  test "$status" = "403" || release_fail "replay_cors_status_invalid"
  rm -f "$health_body"
  trap - RETURN
}

release_wait_local() {
  local public_origin="$1"
  local attempt
  for attempt in $(seq 1 30); do
    if release_health "http://127.0.0.1:3000" "http://127.0.0.1:8000" "$public_origin" 2>/dev/null; then
      return 0
    fi
    sleep 1
  done
  release_fail "release_health_timeout"
}

release_switch_state() {
  local release_root="$1"
  local current_release="$2"
  local previous_release="$3"
  python3 "$(dirname "${BASH_SOURCE[0]}")/switch_release_state.py" \
    --release-root "$release_root" \
    --current "$current_release" \
    --previous "$previous_release" \
    --server-env "$current_release/release.env"
}

release_public_origin() {
  python3 - "$1/release.env" <<'PY'
import pathlib, sys
for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if line.startswith("PUBLIC_ORIGIN="):
        print(line.split("=", 1)[1])
        break
else:
    raise SystemExit("public_origin_missing")
PY
}

release_preflight_images() {
  local release_dir="$1"
  local public_origin web_image api_image web_name api_name web_port api_port user
  public_origin="$(release_public_origin "$release_dir")"
  read -r web_image api_image < <(python3 - "$release_dir/release-manifest.json" <<'PY'
import json, pathlib, sys
value=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
print(value["images"]["web"], value["images"]["api_replay"])
PY
)
  release_compose "$release_dir" pull
  for image in "$web_image" "$api_image"; do
    user="$(docker image inspect --format '{{.Config.User}}' "$image")"
    test -n "$user" && test "$user" != "0" && test "$user" != "root" \
      || release_fail "image_user_invalid"
  done

  docker volume create traceable-support-data-canonical >/dev/null
  docker run --rm --network none --user 0:0 --read-only \
    --cap-drop ALL --cap-add CHOWN --security-opt no-new-privileges \
    -v traceable-support-data-canonical:/var/lib/traceable \
    --entrypoint chown "$api_image" -R 10001:10001 /var/lib/traceable

  web_name="traceable-preflight-web-${RANDOM}-$$"
  api_name="traceable-preflight-api-${RANDOM}-$$"
  docker run -d --name "$api_name" --read-only \
    --tmpfs /tmp:rw,noexec,nosuid,size=64m \
    --tmpfs /var/lib/traceable:rw,noexec,nosuid,uid=10001,gid=10001,size=64m \
    --cap-drop ALL --security-opt no-new-privileges \
    -e "TRACEABLE_PUBLIC_ORIGIN=$public_origin" \
    -e TRACEABLE_PUBLIC_LIVE_ENABLED=false \
    -p 127.0.0.1::8000 "$api_image" >/dev/null
  docker run -d --name "$web_name" --read-only \
    --tmpfs /tmp:rw,noexec,nosuid,size=64m \
    --cap-drop ALL --security-opt no-new-privileges \
    -p 127.0.0.1::3000 "$web_image" >/dev/null
  api_port="$(docker port "$api_name" 8000/tcp | sed -E 's/^.*:([0-9]+)$/\1/')"
  web_port="$(docker port "$web_name" 3000/tcp | sed -E 's/^.*:([0-9]+)$/\1/')"
  local ok=0 attempt
  for attempt in $(seq 1 30); do
    if release_health "http://127.0.0.1:$web_port" "http://127.0.0.1:$api_port" "$public_origin" 2>/dev/null; then
      ok=1
      break
    fi
    sleep 1
  done
  docker rm -f "$web_name" "$api_name" >/dev/null 2>&1 || true
  test "$ok" = "1" || release_fail "image_preflight_failed"
}
