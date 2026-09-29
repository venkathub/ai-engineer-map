#!/usr/bin/env sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
COMMAND=serve
HOST=127.0.0.1
PORT=8000
RUN_CHECKS=1

if [ "${1:-}" = hoe ]; then
  shift
  command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required." >&2; exit 1; }
  cd "$PROJECT_DIR"
  if [ "$#" -eq 0 ]; then
    set -- check
  fi
  exec python3 scripts/hoe.py "$@"
fi

usage() {
  cat <<'EOF'
AI Engineer Map runner

Usage:
  ./run.sh [serve] [--host HOST] [--port PORT] [--no-check]
  ./run.sh check
  ./run.sh lab
  ./run.sh hoe <check|list|inspect|run|verify> [OPTIONS]
  ./run.sh gpu-check
  ./run.sh help

Commands:
  serve      Validate, then start the static site (default)
  check      Validate curriculum and run every test
  lab        Run the dependency-free retrieval lab
  hoe        Inspect, run, or verify hands-on exercises
  gpu-check  Run the CUDA smoke test on a configured GPU host

Examples:
  ./run.sh
  ./run.sh --port 9000
  ./run.sh serve --host 0.0.0.0 --no-check
  ./run.sh check
  ./run.sh hoe list --status automated
  ./run.sh hoe inspect embeddings
  ./run.sh hoe check --provider openai --gpu jarvislabs
  ./run.sh gpu-check
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    serve|check|lab|gpu-check|help) COMMAND=$1 ;;
    --host)
      [ "$#" -ge 2 ] || { echo "Missing value for --host" >&2; exit 2; }
      HOST=$2
      shift
      ;;
    --port)
      [ "$#" -ge 2 ] || { echo "Missing value for --port" >&2; exit 2; }
      PORT=$2
      shift
      ;;
    --no-check) RUN_CHECKS=0 ;;
    -h|--help) COMMAND=help ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

case "$PORT" in
  *[!0-9]*|'') echo "Port must be a positive integer." >&2; exit 2 ;;
esac
[ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ] || { echo "Port must be between 1 and 65535." >&2; exit 2; }

command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required." >&2; exit 1; }
cd "$PROJECT_DIR"

case "$COMMAND" in
  help) usage ;;
  check) exec "$PROJECT_DIR/scripts/check.sh" ;;
  lab) exec python3 labs/rag-retrieval/exercise.py ;;
  gpu-check) exec python3 gpu/jarvislabs/smoke_test.py ;;
  serve)
    if [ "$RUN_CHECKS" -eq 1 ]; then
      "$PROJECT_DIR/scripts/check.sh"
    fi
    echo
    echo "AI Engineer Map is available at http://$HOST:$PORT"
    echo "Press Ctrl+C to stop."
    exec python3 -m http.server "$PORT" --bind "$HOST"
    ;;
esac
