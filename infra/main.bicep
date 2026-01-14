@description('The location for all resources')
param location string = resourceGroup().location

@description('Base name for all resources')
param baseName string = 'jarvis'

@description('Voice Live API endpoint')
@secure()
param voiceLiveEndpoint string

@description('Voice Live API key')
@secure()
param voiceLiveApiKey string

@description('Voice Live model name')
param voiceLiveModel string = 'gpt-4o-mini-realtime-preview'

@description('Voice Live voice name')
param voiceLiveVoice string = 'en-US-AvaNeural'

@description('Memory API URL')
param memoryApiUrl string = 'https://mem0-api.greenstone-413be1c4.eastus.azurecontainerapps.io'

@description('Memory timeout in seconds')
param memoryTimeoutSeconds string = '3'

@description('Enable memory feature')
param enableMemory string = 'true'

// Generate unique suffix for globally unique names
var uniqueSuffix = uniqueString(resourceGroup().id)
var acrName = '${baseName}acr${uniqueSuffix}'
var lawName = '${baseName}-law-${uniqueSuffix}'
var caeName = '${baseName}-cae-${uniqueSuffix}'
var caName = '${baseName}-api'
var appInsightsName = '${baseName}-appi-${uniqueSuffix}'

// Container Registry
// Using latest API version 2025-04-01
// Uses managed identity for pull access (no admin credentials)
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2025-04-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    // anonymousPullEnabled is NOT enabled per security best practices
  }
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: lawName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Application Insights
// Workspace-based Application Insights for telemetry
resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// Container Apps Environment
// Using latest API version 2025-01-01
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: caeName
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

// Container App
// Using latest API version 2025-01-01
resource containerApp 'Microsoft.App/containerApps@2025-01-01' = {
  name: caName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: 'system'
        }
      ]
      secrets: [
        {
          name: 'voice-live-endpoint'
          value: voiceLiveEndpoint
        }
        {
          name: 'voice-live-api-key'
          value: voiceLiveApiKey
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'jarvis-api'
          image: '${containerRegistry.properties.loginServer}/${caName}:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'AZURE_VOICE_LIVE_ENDPOINT'
              secretRef: 'voice-live-endpoint'
            }
            {
              name: 'AZURE_VOICE_LIVE_API_KEY'
              secretRef: 'voice-live-api-key'
            }
            {
              name: 'AZURE_VOICE_LIVE_MODEL'
              value: voiceLiveModel
            }
            {
              name: 'AZURE_VOICE_LIVE_VOICE'
              value: voiceLiveVoice
            }
            {
              name: 'MEMORY_API_URL'
              value: memoryApiUrl
            }
            {
              name: 'MEMORY_TIMEOUT_SECONDS'
              value: memoryTimeoutSeconds
            }
            {
              name: 'ENABLE_MEMORY'
              value: enableMemory
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: applicationInsights.properties.ConnectionString
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 5
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scaler'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

// Role assignment for Container App to pull from ACR
// AcrPull role: 7f951dda-4ed3-4680-a7ca-43fe172d538d
resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: containerRegistry
  name: guid(containerRegistry.id, containerApp.id, '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: containerApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output acrLoginServer string = containerRegistry.properties.loginServer
output acrName string = containerRegistry.name
output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output applicationInsightsName string = applicationInsights.name
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
