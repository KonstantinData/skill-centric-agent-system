#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 4 ] || [ "$#" -gt 5 ]; then
  echo "Usage: $0 <dev|staging|prod> <control_api_url> <control_api_token_b64> <run_label> [task_suite]" >&2
  exit 1
fi

TARGET_ENVIRONMENT="$1"
CONTROL_API_URL="$2"
CONTROL_API_TOKEN_B64="$3"
RUN_LABEL="$4"
TASK_SUITE="${5:-generic}"

case "${TARGET_ENVIRONMENT}" in
  dev|staging|prod) ;;
  *)
    echo "Unsupported environment: ${TARGET_ENVIRONMENT}" >&2
    exit 1
    ;;
esac

REPO_ROOT="$(pwd)"
ARTIFACT_ROOT="/opt/scas/runtime/${TARGET_ENVIRONMENT}/live-gates/${RUN_LABEL}"
RUNTIME_DATABASE="scas_runtime"
if [ "${TARGET_ENVIRONMENT}" != "dev" ]; then
  RUNTIME_DATABASE="scas_runtime_${TARGET_ENVIRONMENT}"
fi

sudo_if_needed() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  else
    sudo "$@"
  fi
}

as_postgres_with_runtime_env() {
  sudo --preserve-env=SCAS_CONTROL_API_URL,SCAS_CONTROL_API_TOKEN,OPENAI_API_KEY,SCAS_RUNTIME_DATABASE_URL,SCAS_RUNTIME_ARTIFACT_ROOT,SCAS_REPOSITORY_ROOT -u postgres "$@"
}

sudo_if_needed install -d -o postgres -g postgres -m 750 "/opt/scas/runtime/${TARGET_ENVIRONMENT}"
sudo_if_needed install -d -o postgres -g postgres -m 750 "/opt/scas/runtime/${TARGET_ENVIRONMENT}/live-gates"
sudo_if_needed install -d -o postgres -g postgres -m 750 "${ARTIFACT_ROOT}"

if [ ! -d "${REPO_ROOT}/.venv" ]; then
  if ! python3 -m venv "${REPO_ROOT}/.venv"; then
    sudo_if_needed env DEBIAN_FRONTEND=noninteractive apt-get update
    sudo_if_needed env DEBIAN_FRONTEND=noninteractive apt-get install -y \
      python3-venv \
      python3.12-venv
    python3 -m venv "${REPO_ROOT}/.venv"
  fi
fi

"${REPO_ROOT}/.venv/bin/python" -m pip install --upgrade pip
"${REPO_ROOT}/.venv/bin/python" -m pip install -e "${REPO_ROOT}[runtime]"
chmod -R a+rX "${REPO_ROOT}/.venv"

CONTROL_API_TOKEN="$(printf '%s' "${CONTROL_API_TOKEN_B64}" | base64 -d)"
install -d -m 755 "${REPO_ROOT}/live-runtime-evidence"

export SCAS_CONTROL_API_URL="${CONTROL_API_URL}"
export SCAS_CONTROL_API_TOKEN="${CONTROL_API_TOKEN}"
if [ -n "${OPENAI_API_KEY:-}" ]; then
  export OPENAI_API_KEY
fi
export SCAS_RUNTIME_DATABASE_URL="postgresql:///${RUNTIME_DATABASE}?host=/var/run/postgresql"
export SCAS_RUNTIME_ARTIFACT_ROOT="${ARTIFACT_ROOT}"
export SCAS_REPOSITORY_ROOT="${REPO_ROOT}"
export TARGET_ENVIRONMENT

as_postgres_with_runtime_env \
  "${REPO_ROOT}/.venv/bin/python" scripts/runtime/live_dev_e2e.py \
    --environment "${TARGET_ENVIRONMENT}" \
    --task-suite "${TASK_SUITE}" \
  | tee "${REPO_ROOT}/live-runtime-evidence/live-${TARGET_ENVIRONMENT}-e2e.json"

"${REPO_ROOT}/.venv/bin/python" scripts/runtime/live_retrieval_vectorize_smoke.py

as_postgres_with_runtime_env \
  "${REPO_ROOT}/.venv/bin/python" scripts/runtime/postgres_concurrency_smoke.py \
    --events 20 \
    --profile-file examples/profiles/code-review-profile.json \
  | tee "${REPO_ROOT}/live-runtime-evidence/live-${TARGET_ENVIRONMENT}-postgres-concurrency.json"

echo "Live runtime gate completed for ${TARGET_ENVIRONMENT}."
