#!/usr/bin/env bash
# Live check of the container side of the extension, without touching your real containers or data.
#
# Builds both images as :dev, starts them with the exact `docker run` arguments the extension uses
# (taken from src/core/containers.ts), on spare ports, against a temporary Spec2Test folder, and checks:
#   - both MCP endpoints answer
#   - the projects folder is mounted and projects.json is readable inside the container
#   - a project added afterwards is visible without restarting the container
#
#   ./scripts/verify-image.sh            # build + run + check, then clean up
#   KEEP=1 ./scripts/verify-image.sh     # leave the containers and the temp folder for inspection
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
repo="$(cd "$here/.." && pwd)"
tmp="$(mktemp -d)"
home="$tmp/home"
ip_image="spec2test-input-processor:dev"
wc_image="spec2test-web-crawler:dev"
ip_name="spec2test-verify-input-processor"
wc_name="spec2test-verify-web-crawler"
ip_port=18003
wc_port=18000

cleanup() {
  if [ "${KEEP:-}" = "1" ]; then
    echo "Kept: containers $ip_name and $wc_name, folder $tmp"
    return
  fi
  docker rm -f "$ip_name" "$wc_name" >/dev/null 2>&1 || true
  rm -rf "$tmp"
}
trap cleanup EXIT

fail() { echo "FAIL: $*" >&2; docker logs --tail 40 "$ip_name" 2>&1 || true; exit 1; }
ok() { echo "ok   $*"; }

command -v docker >/dev/null || fail "docker is not installed"
docker info >/dev/null 2>&1 || fail "the Docker daemon is not running"

echo "== Building images"
docker build -t "$ip_image" "$repo/input-processor"
docker build -t "$wc_image" "$repo/web-crawler"

echo "== Generating the run arguments with the extension's own code"
(cd "$here" && npx --no-install esbuild src/core/containers.ts --bundle --platform=node --format=cjs --outfile="$tmp/containers.cjs" --log-level=error)

run_args() {
  node -e '
    const [file, kind, image, port, name, dataRoot] = process.argv.slice(1);
    const c = require(file);
    const spec = kind === "ip"
      ? c.inputProcessorSpec({ image, port: Number(port), dataRoot, tuning: {}, secrets: [], gpu: false })
      : c.webCrawlerSpec({ image, port: Number(port) });
    spec.container = name;
    console.log(c.buildRunArgs(spec).join("\n"));
  ' "$tmp/containers.cjs" "$@"
}

start() {
  local args=()
  while IFS= read -r line; do args+=("$line"); done < <(run_args "$@")
  docker rm -f "${args[3]}" >/dev/null 2>&1 || true
  docker "${args[@]}" >/dev/null
}

wait_for() {
  local url="$1" name="$2"
  for _ in $(seq 1 80); do
    if curl -s -o /dev/null --max-time 2 "$url"; then ok "$name answers on $url"; return; fi
    sleep 1.5
  done
  fail "$name did not answer on $url within two minutes"
}

echo "== Starting"
mkdir -p "$home/demo/inputs"
printf '{"projects":[{"name":"demo"}]}\n' > "$home/projects.json"
start ip "$ip_image" "$ip_port" "$ip_name" "$home"
start wc "$wc_image" "$wc_port" "$wc_name" "$home"
wait_for "http://127.0.0.1:$ip_port/mcp" "input-processor"
wait_for "http://127.0.0.1:$wc_port/mcp" "web-crawler"

echo "== Checking the mount"
docker exec "$ip_name" test -d /projects/demo/inputs || fail "/projects/demo/inputs is missing in the container"
ok "/projects/demo/inputs is mounted"
docker exec "$ip_name" grep -q '"demo"' /projects/projects.json || fail "projects.json is not readable in the container"
ok "projects.json is readable"

echo "== Adding a project without restarting"
started_before="$(docker inspect -f '{{.State.StartedAt}}' "$ip_name")"
mkdir -p "$home/second/inputs"
printf '{"projects":[{"name":"demo"},{"name":"second"}]}\n' > "$home/projects.json"
sleep 1
docker exec "$ip_name" grep -q '"second"' /projects/projects.json || fail "the new project is not visible in the container"
docker exec "$ip_name" test -d /projects/second/inputs || fail "/projects/second/inputs is not visible in the container"
[ "$started_before" = "$(docker inspect -f '{{.State.StartedAt}}' "$ip_name")" ] || fail "the container restarted"
ok "project 'second' is visible and the container kept running"

echo
echo "All checks passed. Processing a file needs an API key: do that part with the extension (e2e-checklist.md)."
