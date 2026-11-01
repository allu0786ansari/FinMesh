#!/usr/bin/env bash
# Week 14, final narrative (A23) on real data, unattended:
#   bash scripts/week14_a23.sh 2>&1 | tee week14_a23.log
# Re-run the same command to resume: a step whose artifact already exists is skipped.
# Needs Ollama on this machine with llama3.2:3b (`ollama serve`, `ollama pull llama3.2:3b`).
# Stop this script before stopping `ollama serve`. FRESH=1 restarts both narratives from case 1.
set -euo pipefail
cd "$(dirname "$0")/.."
ART="$(uv run python -c 'from finmesh.paths import artifacts_dir; print(artifacts_dir())' 2>/dev/null)"
MODEL="${MODEL:-llama3.2:3b}"
OLLAMA="${OLLAMA_URL:-http://localhost:11434}"

step() {  # step <artifact> <command...>
  local artifact="$1"; shift
  if [ -f "$artifact" ]; then
    echo; echo "==> skip ($(basename "$artifact") exists): $*"
    return
  fi
  echo; echo "==> $(date '+%H:%M') $*"
  local t0=$SECONDS
  "$@"
  echo "    done in $(( (SECONDS - t0) / 60 )) min"
}

# A saved narrative made while the server was down holds only failed calls: discard it.
# FRESH=1 discards both A23 narratives and starts them again from case 1.
discard_if_broken() {  # discard_if_broken <artifact>
  local artifact="$1"
  [ -f "$artifact" ] || return 0
  if [ "${FRESH:-0}" = "1" ]; then
    echo "==> FRESH=1: removing $(basename "$artifact")"; rm -f "$artifact"; return 0
  fi
  if ! uv run python - "$artifact" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
cases = doc.get("result", doc).get("cases", [])
marks = ("Connection refused", "Errno 111", "Connection reset", "Remote end closed")
down = sum(any(m in e for m in marks for e in c.get("errors", [])) for c in cases)
print(f"    {sys.argv[1].rsplit('/', 1)[-1]}: {down} of {len(cases)} cases hit a stopped server")
sys.exit(1 if down else 0)
PY
  then
    echo "==> removing it: it was made while the model server was down"; rm -f "$artifact"
  fi
}

if ! curl -sf "$OLLAMA/api/tags" | grep -q "\"$MODEL\""; then
  echo "Ollama is not reachable at $OLLAMA, or $MODEL is not pulled."
  echo "Start it with:  ollama serve   (another terminal)  and  ollama pull $MODEL"
  exit 1
fi

for ds in HI-Medium LI-Medium; do
  # The final narrative (A23): worded evidence, claim consistency, blind A/B review sheet
  discard_if_broken "$ART/week14/narrative_${ds}_A23.json"
  step "$ART/week14/narrative_${ds}_A23.json" \
    uv run finmesh narrative --dataset "$ds" --protocol A23 --model "$MODEL" --url "$OLLAMA"
done
echo; echo "==> $(date '+%H:%M') pytest -m real_data"
uv run pytest -m real_data -q
echo; echo "week 14 final narrative (A23): all steps done"
