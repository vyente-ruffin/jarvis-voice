# Jarvis Voice Assistant

A web-based real-time voice assistant using Azure Voice Live API with long-term memory, deployed to Azure Container Apps.

**Live URL:** https://jarvis-api.lemonbay-c4ff031f.eastus2.azurecontainerapps.io

## Architecture

```
Browser (any device)           Azure Container Apps            Azure Voice Live API
┌──────────────────────┐      ┌─────────────────────┐         ┌──────────────────┐
│  Web Audio API       │      │  FastAPI Server     │         │  GPT-4 Realtime  │
│  - getUserMedia      │ WSS  │  - /ws/voice        │   WSS   │  - TTS/STT       │
│  - AudioContext      │◄────►│  - /health          │◄───────►│  - Echo cancel   │
│  - 48kHz → 24kHz     │ JSON │  - Static files     │  PCM16  │  - Noise supprs  │
│    resampling        │      │                     │         │  - Server VAD    │
└──────────────────────┘      └─────────────────────┘         └──────────────────┘
     PCM16 base64                  Relay + encode                 Raw PCM16
```

## Azure Resources

### Resource Group: `rg-youni-dev` (eastus2)

| Resource | Type | Name | Purpose |
|----------|------|------|---------|
| Container Registry | Microsoft.ContainerRegistry | `jarvisacrafttmtxdb5reg` | Docker images |
| Log Analytics | Microsoft.OperationalInsights | `jarvis-law-*` | Logging |
| Container Apps Environment | Microsoft.App/managedEnvironments | `jarvis-cae-afttmtxdb5reg` | Hosts containers |
| Container App | Microsoft.App/containerApps | `jarvis-api` | Voice assistant |
| Container App | Microsoft.App/containerApps | `agent-memory-server` | Memory API |
| Container App | Microsoft.App/containerApps | `redis` | Vector database (internal) |

### External Resource (pre-existing)

| Resource | Type | Location | Purpose |
|----------|------|----------|---------|
| `jarvis-voice-openai` | Azure OpenAI | eastus2 | Voice Live API endpoint |

## Project Structure

```
├── src/
│   ├── __init__.py
│   ├── server.py          # FastAPI WebSocket server
│   ├── voice_live.py      # Voice Live SDK wrapper
│   └── static/
│       ├── index.html     # JARVIS UI
│       ├── styles.css     # CRT/hexagonal styling
│       └── app.js         # Audio capture/playback
├── tests/
│   ├── test_server.py     # Server unit tests
│   └── test_voice_live.py # Voice Live unit tests
├── infra/
│   └── main.bicep         # Azure infrastructure
├── Dockerfile
├── azure.yaml             # Azure Developer CLI config
├── requirements.txt
└── voice-live-chat.py     # Local CLI version (alternative)
```

## WebSocket Protocol

For LLMs integrating this into larger applications:

### Client → Server

```json
{"type": "audio", "data": "<base64 PCM16 24kHz mono>"}
{"type": "mute", "muted": true|false}
```

### Server → Client

```json
{"type": "connected"}
{"type": "status", "state": "ready|listening|processing"}
{"type": "audio", "data": "<base64 PCM16 24kHz mono>"}
{"type": "transcript", "text": "..."}
{"type": "clear_audio"}  // Barge-in signal - stop playback
{"type": "mute_status", "muted": true|false}
{"type": "error", "message": "..."}
```

### Audio Format

- **Sample rate:** 24000 Hz
- **Channels:** 1 (mono)
- **Format:** PCM16 (signed 16-bit little-endian)
- **Encoding:** Base64 for JSON transport

## Deployment

### Prerequisites

- Azure CLI (`az`)
- Docker with buildx
- Azure subscription with AI Services resource

### Deploy from Scratch

```bash
# 1. Create resource group
az group create --name rg-youni-dev --location eastus2

# 2. Deploy infrastructure
az deployment group create \
  --resource-group rg-youni-dev \
  --template-file infra/main.bicep \
  --parameters voiceLiveEndpoint="https://jarvis-voice-openai.openai.azure.com" \
               voiceLiveApiKey="YOUR_API_KEY"

# 3. Get ACR name from output
ACR_NAME=$(az acr list -g rg-youni-dev --query "[0].name" -o tsv)

# 4. Build and push Docker image
az acr login --name $ACR_NAME
docker buildx build --platform linux/amd64 \
  -t $ACR_NAME.azurecr.io/jarvis-api:latest --push .

# 5. Update container app with image
az containerapp update --name jarvis-api --resource-group rg-youni-dev \
  --image $ACR_NAME.azurecr.io/jarvis-api:latest
```

### Update Existing Deployment

```bash
# Build and push new version
az acr login --name jarvisacrafttmtxdb5reg
docker buildx build --platform linux/amd64 \
  -t jarvisacrafttmtxdb5reg.azurecr.io/jarvis-api:latest --push .

# Update container app
az containerapp update --name jarvis-api --resource-group rg-youni-dev \
  --image jarvisacrafttmtxdb5reg.azurecr.io/jarvis-api:latest
```

### Update Voice Live Credentials

```bash
az containerapp secret set --name jarvis-api --resource-group rg-youni-dev \
  --secrets "voice-live-endpoint=YOUR_ENDPOINT" \
            "voice-live-api-key=YOUR_KEY"
az containerapp revision restart --name jarvis-api --resource-group rg-youni-dev \
  --revision $(az containerapp revision list -n jarvis-api -g rg-youni-dev --query "[0].name" -o tsv)
```

## Local Development

```bash
# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Voice Live credentials

# Run server
uvicorn src.server:app --reload --port 8000

# Run tests
pytest tests/ -v
```

## Environment Variables

### Azure Voice Live

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_VOICE_LIVE_ENDPOINT` | Yes | Voice Live API endpoint |
| `AZURE_VOICE_LIVE_API_KEY` | Yes | Voice Live API key |
| `AZURE_VOICE_LIVE_MODEL` | No | Model (default: `gpt-4o-mini-realtime-preview`) |
| `AZURE_VOICE_LIVE_VOICE` | No | Voice (default: `en-US-AvaNeural`) |
| `AZURE_VOICE_LIVE_INSTRUCTIONS` | No | System prompt |

### Memory Integration (Redis Agent Memory Server)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MEMORY_SERVER_URL` | No | `https://agent-memory-server.lemonbay-c4ff031f.eastus2.azurecontainerapps.io` | Redis agent-memory-server API |
| `MEMORY_TIMEOUT_SECONDS` | No | `30` | Timeout for memory API calls in seconds |
| `ENABLE_MEMORY` | No | `true` | Enable/disable memory feature |

## Key Implementation Details

### SDK Audio Format

The Azure Voice Live SDK documentation states `event.delta` is "base64-encoded" but **returns raw PCM bytes**. You must base64 encode for JSON:

```python
# Correct
audio_base64 = base64.b64encode(event.delta).decode('utf-8')

# Wrong - will crash
audio_base64 = event.delta.decode('utf-8')
```

### Browser Audio Resampling

Browsers capture at 48kHz but Voice Live requires 24kHz:

```javascript
function resampleTo24kHz(samples, fromRate) {
  const ratio = fromRate / 24000;
  const newLength = Math.round(samples.length / ratio);
  const result = new Float32Array(newLength);
  for (let i = 0; i < newLength; i++) {
    const srcIndex = i * ratio;
    const floor = Math.floor(srcIndex);
    const ceil = Math.min(floor + 1, samples.length - 1);
    const t = srcIndex - floor;
    result[i] = samples[floor] * (1 - t) + samples[ceil] * t;
  }
  return result;
}
```

### Barge-in Handling

When user speaks during AI response, server sends `clear_audio` - client must immediately stop playback:

```javascript
case 'clear_audio':
  audioQueue.length = 0;  // Clear pending audio
  isPlaying = false;
  break;
```

## Alternative: Local CLI Version

For local development without web browser, use `voice-live-chat.py`:

```bash
# Install PyAudio (macOS)
brew install portaudio
pip install pyaudio

# Run
python voice-live-chat.py
```

## Monitoring

```bash
# View logs
az containerapp logs show --name jarvis-api --resource-group rg-youni-dev --tail 100

# Check health
curl https://jarvis-api.lemonbay-c4ff031f.eastus2.azurecontainerapps.io/health
```

## Limits

- **Session duration:** 30 minutes max (Voice Live limit)
- **Audio format:** PCM16 24kHz mono only
- **HTTPS required:** Microphone access requires secure context

## License

MIT
