#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-receptify-rg}"
LOCATION="${LOCATION:-eastus2}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-receptify-containerapps}"
PARAMETERS_FILE="${1:-azure/params.local.json}"
FAQ_FILE="${FAQ_FILE:-context/ai-ivr-context.txt}"

if [[ ! -f "$PARAMETERS_FILE" ]]; then
  echo "Missing parameters file: $PARAMETERS_FILE" >&2
  echo "Create one from azure/params.example.json and fill in the secret values." >&2
  exit 1
fi

az extension add --name containerapp --upgrade >/dev/null

az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.Storage

az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION"

az deployment group create \
  --name "$DEPLOYMENT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --template-file azure/main.bicep \
  --parameters "$PARAMETERS_FILE" \
  --query properties.outputs

STORAGE_ACCOUNT="$(az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$DEPLOYMENT_NAME" \
  --query properties.outputs.storageAccount.value \
  --output tsv)"

RAG_SHARE="$(az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$DEPLOYMENT_NAME" \
  --query properties.outputs.ragShare.value \
  --output tsv)"

RAG_BASE_URL="$(az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$DEPLOYMENT_NAME" \
  --query properties.outputs.ragBaseUrl.value \
  --output tsv)"

if [[ -f "$FAQ_FILE" ]]; then
  echo "==> Uploading RAG FAQ/context file to Azure Files..."
  STORAGE_KEY="$(az storage account keys list \
    --resource-group "$RESOURCE_GROUP" \
    --account-name "$STORAGE_ACCOUNT" \
    --query '[0].value' \
    --output tsv)"

  az storage file upload \
    --account-name "$STORAGE_ACCOUNT" \
    --account-key "$STORAGE_KEY" \
    --share-name "$RAG_SHARE" \
    --source "$FAQ_FILE" \
    --path ai-ivr-context.txt \
    --only-show-errors >/dev/null
else
  echo "WARNING: FAQ file not found: $FAQ_FILE" >&2
  echo "RAG will use its built-in fallback text until you upload /faq/ai-ivr-context.txt." >&2
fi

echo ""
echo "RAG_URL=$RAG_BASE_URL"
echo "Use this value in k8s/external-services.local.yaml before running k8s/deploy.sh."
