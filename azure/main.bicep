targetScope = 'resourceGroup'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Short resource name prefix.')
param prefix string = 'receptify'

@description('Ollama container image tag.')
param ollamaImageTag string = 'latest'

@description('RAG service container image.')
param ragImage string = 'ghcr.io/danipopa/rag-service:latest'

@description('CIDR allowed to reach the public Ollama endpoint. Use your server public IP with /32.')
param allowedSourceCidr string

@description('Optional CIDR for the RAG Container App outbound IP, used to allow RAG to call the public Ollama endpoint.')
param ragOutboundSourceCidr string = ''

@description('Persistent Azure Files share size for Ollama model data, in GiB.')
@minValue(20)
param ollamaStorageQuotaGiB int = 20

@description('Persistent Azure Files share size for RAG FAQ/context data, in GiB.')
@minValue(1)
param ragStorageQuotaGiB int = 5

@description('Ollama CPU allocation. Consumption plan supports specific CPU/memory pairs.')
@allowed([
  '0.5'
  '1.0'
  '2.0'
])
param ollamaCpu string = '2.0'

@description('Ollama memory allocation. For 2.0 CPU use 4.0Gi on the Consumption plan.')
@allowed([
  '1.0Gi'
  '2.0Gi'
  '4.0Gi'
])
param ollamaMemory string = '4.0Gi'

@description('RAG CPU allocation. Consumption plan supports specific CPU/memory pairs.')
@allowed([
  '0.25'
  '0.5'
  '1.0'
])
param ragCpu string = '0.5'

@description('RAG memory allocation.')
@allowed([
  '0.5Gi'
  '1.0Gi'
  '2.0Gi'
])
param ragMemory string = '1.0Gi'

@description('Minimum Container App replicas.')
@minValue(0)
@maxValue(1)
param minReplicas int = 1

@description('Maximum Container App replicas. Keep this at 1 when using Azure Files-backed storage.')
@minValue(1)
@maxValue(1)
param maxReplicas int = 1

var logAnalyticsName = '${prefix}-ollama-logs'
var environmentName = '${prefix}-ollama-env'
var storageAccountName = toLower('${take(replace(prefix, '-', ''), 8)}${uniqueString(resourceGroup().id)}')
var ollamaShareName = 'ollama'
var ragShareName = 'rag'
var ollamaIpRestrictions = empty(ragOutboundSourceCidr) ? [
  {
    name: 'allow-server'
    description: 'Only allow the Receptify server to call Ollama.'
    action: 'Allow'
    ipAddressRange: allowedSourceCidr
  }
  {
    name: 'allow-containerapps-internal'
    description: 'Allow Azure Container Apps internal traffic.'
    action: 'Allow'
    ipAddressRange: '100.64.0.0/10'
  }
] : [
  {
    name: 'allow-server'
    description: 'Only allow the Receptify server to call Ollama.'
    action: 'Allow'
    ipAddressRange: allowedSourceCidr
  }
  {
    name: 'allow-rag-app'
    description: 'Allow the RAG Container App to call Ollama.'
    action: 'Allow'
    ipAddressRange: ragOutboundSourceCidr
  }
  {
    name: 'allow-containerapps-internal'
    description: 'Allow Azure Container Apps internal traffic.'
    action: 'Allow'
    ipAddressRange: '100.64.0.0/10'
  }
]

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource ollamaShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileService
  name: ollamaShareName
  properties: {
    shareQuota: ollamaStorageQuotaGiB
  }
}

resource ragShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileService
  name: ragShareName
  properties: {
    shareQuota: ragStorageQuotaGiB
  }
}

resource ollamaEnvironmentStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: environment
  name: 'ollama-data'
  properties: {
    azureFile: {
      accountName: storageAccount.name
      accountKey: storageAccount.listKeys().keys[0].value
      shareName: ollamaShare.name
      accessMode: 'ReadWrite'
    }
  }
}

resource ragEnvironmentStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: environment
  name: 'rag-data'
  properties: {
    azureFile: {
      accountName: storageAccount.name
      accountKey: storageAccount.listKeys().keys[0].value
      shareName: ragShare.name
      accessMode: 'ReadWrite'
    }
  }
}

resource ollama 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ollama'
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 11434
        transport: 'http'
        allowInsecure: true
        ipSecurityRestrictions: ollamaIpRestrictions
      }
    }
    template: {
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
      volumes: [
        {
          name: 'ollama-data'
          storageType: 'AzureFile'
          storageName: ollamaEnvironmentStorage.name
        }
      ]
      initContainers: [
        {
          name: 'pull-models'
          image: 'ollama/ollama:${ollamaImageTag}'
          command: [
            '/bin/sh'
            '-c'
          ]
          args: [
            'ollama serve & pid="$!"; until ollama list >/dev/null 2>&1; do sleep 1; done; ollama pull nomic-embed-text; ollama pull llama3.2:1b; kill "$pid"; wait "$pid" || true'
          ]
          env: [
            {
              name: 'OLLAMA_HOST'
              value: '0.0.0.0:11434'
            }
          ]
          volumeMounts: [
            {
              volumeName: 'ollama-data'
              mountPath: '/root/.ollama'
            }
          ]
        }
      ]
      containers: [
        {
          name: 'ollama'
          image: 'ollama/ollama:${ollamaImageTag}'
          env: [
            {
              name: 'OLLAMA_HOST'
              value: '0.0.0.0:11434'
            }
            {
              name: 'OLLAMA_KEEP_ALIVE'
              value: '24h'
            }
            {
              name: 'OLLAMA_MAX_LOADED_MODELS'
              value: '2'
            }
            {
              name: 'OLLAMA_NUM_PARALLEL'
              value: '1'
            }
          ]
          probes: [
            {
              type: 'Readiness'
              httpGet: {
                path: '/api/tags'
                port: 11434
              }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/api/tags'
                port: 11434
              }
              initialDelaySeconds: 30
              periodSeconds: 20
            }
          ]
          resources: {
            cpu: json(ollamaCpu)
            memory: ollamaMemory
          }
          volumeMounts: [
            {
              volumeName: 'ollama-data'
              mountPath: '/root/.ollama'
            }
          ]
        }
      ]
    }
  }
}

resource rag 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'rag-service'
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 9091
        transport: 'http'
        allowInsecure: false
        ipSecurityRestrictions: [
          {
            name: 'allow-server'
            description: 'Only allow the Receptify Kubernetes cluster/server to call RAG.'
            action: 'Allow'
            ipAddressRange: allowedSourceCidr
          }
        ]
      }
    }
    template: {
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
      volumes: [
        {
          name: 'rag-data'
          storageType: 'AzureFile'
          storageName: ragEnvironmentStorage.name
        }
      ]
      containers: [
        {
          name: 'rag-service'
          image: ragImage
          env: [
            {
              name: 'FAQ_FILE'
              value: '/faq/ai-ivr-context.txt'
            }
            {
              name: 'EMBEDDING_MODEL'
              value: 'nomic-embed-text'
            }
            {
              name: 'LLM_MODEL'
              value: 'llama3.2:1b'
            }
            {
              name: 'OLLAMA_HOST'
              value: ollama.properties.configuration.ingress.fqdn
            }
            {
              name: 'OLLAMA_TIMEOUT'
              value: '60'
            }
            {
              name: 'RAG_CHUNK_WORDS'
              value: '60'
            }
            {
              name: 'RAG_TOP_K'
              value: '4'
            }
            {
              name: 'LLM_NUM_PREDICT'
              value: '16'
            }
            {
              name: 'LLM_TEMPERATURE'
              value: '0.1'
            }
            {
              name: 'LOG_LEVEL'
              value: 'INFO'
            }
          ]
          probes: [
            {
              type: 'Readiness'
              httpGet: {
                path: '/ready'
                port: 9091
              }
              initialDelaySeconds: 30
              periodSeconds: 10
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 9091
              }
              initialDelaySeconds: 60
              periodSeconds: 15
            }
          ]
          resources: {
            cpu: json(ragCpu)
            memory: ragMemory
          }
          volumeMounts: [
            {
              volumeName: 'rag-data'
              mountPath: '/faq'
            }
          ]
        }
      ]
    }
  }
  dependsOn: [
    ollama
  ]
}

output ollamaFqdn string = ollama.properties.configuration.ingress.fqdn
output ollamaBaseUrl string = 'https://${ollama.properties.configuration.ingress.fqdn}'
output ragFqdn string = rag.properties.configuration.ingress.fqdn
output ragBaseUrl string = 'https://${rag.properties.configuration.ingress.fqdn}'
output storageAccount string = storageAccount.name
output ragShare string = ragShare.name
