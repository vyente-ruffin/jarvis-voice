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

// Generate unique suffix for globally unique names
var uniqueSuffix = uniqueString(resourceGroup().id)
var acrName = '${baseName}acr${uniqueSuffix}'
var lawName = '${baseName}-law-${uniqueSuffix}'
var caeName = '${baseName}-cae-${uniqueSuffix}'
var caName = '${baseName}-api'

// Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
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

// Container Apps Environment
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
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
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: caName
  location: location
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
          username: containerRegistry.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
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

// Outputs
output acrLoginServer string = containerRegistry.properties.loginServer
output acrName string = containerRegistry.name
output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
