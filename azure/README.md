# Azure RAG + Ollama Deployment

This folder deploys `rag-service` and Ollama to Azure Container Apps. The rest of Receptify stays in Kubernetes.

## What It Deploys

- Log Analytics workspace
- Azure Container Apps environment
- Azure Storage account and Azure Files share for Ollama model data
- Azure Files share for RAG FAQ/context data
- Public HTTPS Container App for `ollama/ollama`
- Public HTTPS Container App for `rag-service`

Both public endpoints are restricted by source IP. Set `allowedSourceCidr` to the public IP of the Kubernetes server or outbound gateway that will call RAG, with `/32`.

## Configure Parameters

Create a local parameter file:

```bash
cp azure/params.example.json azure/params.local.json
```

Find your Kubernetes server or outbound gateway public IP:

```bash
curl -4 ifconfig.me
```

Set it in `azure/params.local.json`:

```json
"allowedSourceCidr": {
  "value": "YOUR_SERVER_PUBLIC_IP/32"
}
```

Do not commit `azure/params.local.json`.

## Deploy

The default target is:

- Resource group: `receptify-rg`
- Region: `eastus2`

Run:

```bash
./azure/deploy.sh
```

The deployment outputs include:

```text
ragBaseUrl
ollamaBaseUrl
```

`azure/deploy.sh` uploads `context/ai-ivr-context.txt` to the Azure Files share mounted by RAG. Override the source file with:

```bash
FAQ_FILE=/path/to/ai-ivr-context.txt ./azure/deploy.sh
```

## Connect Kubernetes

Use `ragBaseUrl` in Kubernetes:

```bash
cp k8s/external-services.example.yaml k8s/external-services.local.yaml
```

Then edit:

```yaml
RAG_URL: https://YOUR_RAG_CONTAINER_APP_FQDN
```

Run:

```bash
./k8s/deploy.sh
```

The Kubernetes deploy script no longer applies `k8s/rag-service.yaml` or `k8s/ollama.yaml`.

## Verify

From your Kubernetes server:

```bash
curl https://YOUR_RAG_FQDN/health
curl https://YOUR_OLLAMA_FQDN/api/tags
```

From any other IP, Azure should reject the requests because of `allowedSourceCidr`.
