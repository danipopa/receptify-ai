#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE=receptify

echo "==> [1/6] Creating namespace..."
kubectl apply -f "$SCRIPT_DIR/namespace.yaml"

echo "==> [2/6] Creating ClusterIssuer (cert-manager TLS)..."
kubectl apply -f "$SCRIPT_DIR/cert-issuer.yaml"

# Create secret only if it doesn't already exist
if kubectl get secret receptify-api-secret -n "$NAMESPACE" &>/dev/null; then
  echo "==> [3/6] Secret 'receptify-api-secret' already exists — skipping."
else
  echo "==> [3/6] Creating secret 'receptify-api-secret'..."

  MASTER_KEY_FILE="$(dirname "$SCRIPT_DIR")/receptify-api/config/master.key"
  if [[ ! -f "$MASTER_KEY_FILE" ]]; then
    echo "ERROR: $MASTER_KEY_FILE not found. Cannot continue."
    exit 1
  fi

  DB_PASS=$(openssl rand -base64 20 | tr -d '=+/')
  JWT_SECRET=$(openssl rand -hex 32)
  MASTER_KEY=$(cat "$MASTER_KEY_FILE")

  echo ""
  echo "  ┌─────────────────────────────────────────────┐"
  echo "  │  SAVE THESE — you will need them later!     │"
  echo "  │  DB_PASSWORD : $DB_PASS"
  echo "  │  JWT_SECRET  : $JWT_SECRET"
  echo "  └─────────────────────────────────────────────┘"
  echo ""

  kubectl create secret generic receptify-api-secret \
    --namespace "$NAMESPACE" \
    --from-literal=DB_USERNAME=receptify \
    --from-literal=DB_PASSWORD="$DB_PASS" \
    --from-literal=JWT_SECRET="$JWT_SECRET" \
    --from-literal=RAILS_MASTER_KEY="$MASTER_KEY" \
    --from-literal=PAYPAL_CLIENT_ID="${PAYPAL_CLIENT_ID:-CHANGEME}" \
    --from-literal=PAYPAL_CLIENT_SECRET="${PAYPAL_CLIENT_SECRET:-CHANGEME}"
fi

# Create FreeSWITCH ESL secret only if it doesn't already exist
if kubectl get secret freeswitch-secret -n "$NAMESPACE" &>/dev/null; then
  echo "==> [3b] Secret 'freeswitch-secret' already exists — skipping."
else
  echo "==> [3b] Creating secret 'freeswitch-secret'..."
  kubectl create secret generic freeswitch-secret \
    --namespace "$NAMESPACE" \
    --from-literal=esl-password="${FS_ESL_PASSWORD:-R3c3pt1fy#ESL@xP9kZm2X}"
fi

echo "==> [4/6] Creating storage directory on host..."
mkdir -p \
  /home/storage/ns/receptify/postgresql \
  /home/storage/ns/receptify/freeswitch/conf \
  /home/storage/ns/receptify/fs-bridge-wav \
  /home/storage/ns/receptify/rag \
  /home/storage/ns/receptify/ollama

echo "==> [5/6] Deploying PostgreSQL..."
kubectl apply -f "$SCRIPT_DIR/postgres.yaml"

echo "==> [5/6] Waiting for PostgreSQL to be ready..."
kubectl rollout status statefulset/postgres -n "$NAMESPACE" --timeout=120s

echo "==> [6/6] Deploying all remaining services..."
kubectl apply -f "$SCRIPT_DIR/receptify-api.yaml"
kubectl apply -f "$SCRIPT_DIR/receptify-frontend.yaml"
kubectl apply -f "$SCRIPT_DIR/agent.yaml"
kubectl apply -f "$SCRIPT_DIR/fs-bridge.yaml"
kubectl apply -f "$SCRIPT_DIR/ollama.yaml"
kubectl apply -f "$SCRIPT_DIR/rag-service.yaml"
kubectl apply -f "$SCRIPT_DIR/stt-service.yaml"
kubectl apply -f "$SCRIPT_DIR/tts-service.yaml"

echo ""
echo "==> Done! Watching pods..."
kubectl get pods -n "$NAMESPACE"
