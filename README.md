# Azure Voice Live API - Real-time Voice Chat

A Python implementation of Azure Voice Live API for real-time voice conversations with GPT-4 models, featuring natural barge-in (interruption) support.

## Overview

This project uses **Azure Voice Live API** (not the standard OpenAI Realtime API) because it provides:

- **Built-in barge-in support** - Instantly stops AI audio when user speaks
- **Echo cancellation** - Prevents feedback loops from speakers to microphone
- **Deep noise suppression** - Filters background noise for cleaner speech detection
- **Enhanced VAD** - Server-side Voice Activity Detection for better turn-taking

## Architecture

```
┌─────────────┐     WebSocket      ┌──────────────────────┐
│   PyAudio   │◄──────────────────►│  Azure Voice Live    │
│  (Mic/Spk)  │   PCM16 24kHz      │  API (eastus2)       │
└─────────────┘                    │                      │
                                   │  ┌────────────────┐  │
                                   │  │ GPT-4 Realtime │  │
                                   │  │    Model       │  │
                                   │  └────────────────┘  │
                                   │                      │
                                   │  ┌────────────────┐  │
                                   │  │ Echo Cancel +  │  │
                                   │  │ Noise Suppress │  │
                                   │  └────────────────┘  │
                                   └──────────────────────┘
```

## Azure Resources

### Required Resource

| Resource | Type | Location | Purpose |
|----------|------|----------|---------|
| `voicelive-service` | Azure AI Services (multi-service) | eastus2 | Hosts Voice Live API |

### Resource Group

- **Name**: `rg-voicelive`
- **Location**: `eastus2`

### How Resources Were Created

```bash
# Create resource group
az group create --name rg-voicelive --location eastus2

# Create AI Services resource (multi-service, not just OpenAI)
az cognitiveservices account create \
  --name voicelive-service \
  --resource-group rg-voicelive \
  --location eastus2 \
  --kind AIServices \
  --sku S0 \
  --yes

# Get endpoint
az cognitiveservices account show \
  --name voicelive-service \
  --resource-group rg-voicelive \
  --query "properties.endpoint" -o tsv

# Get API key
az cognitiveservices account keys list \
  --name voicelive-service \
  --resource-group rg-voicelive \
  --query "key1" -o tsv
```

**Important**: Voice Live uses `AIServices` kind (multi-service), not `OpenAI` kind. The models are fully managed - no deployment needed.

## Installation

### Prerequisites

- Python 3.10+
- macOS/Linux (PyAudio works best on these platforms)
- Azure subscription with AI Services resource

### Setup

#### macOS

```bash
# Install portaudio (required for PyAudio)
brew install portaudio

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Windows

```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies (PyAudio wheel is included)
pip install -r requirements.txt
```

**Note**: If PyAudio fails to install on Windows, download the appropriate wheel from [PyAudio Unofficial Binaries](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) and install with `pip install <filename>.whl`

#### Linux (Ubuntu/Debian)

```bash
# Install portaudio and python dev headers
sudo apt-get install portaudio19-dev python3-dev

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `azure-ai-voicelive[aiohttp]` | Voice Live SDK with async WebSocket support |
| `pyaudio` | Audio capture (microphone) and playback (speaker) |
| `python-dotenv` | Environment variable loading from `.env` file |
| `azure-identity` | Azure authentication (optional, for token-based auth) |

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your Azure credentials:

```env
# Required
AZURE_VOICELIVE_ENDPOINT=https://eastus2.api.cognitive.microsoft.com/
AZURE_VOICELIVE_API_KEY=your_api_key_here

# Optional (defaults shown)
AZURE_VOICELIVE_MODEL=gpt-4o-mini-realtime-preview
AZURE_VOICELIVE_VOICE=en-US-AvaNeural
AZURE_VOICELIVE_INSTRUCTIONS=You are a helpful voice assistant. Be conversational and concise. Respond naturally.
```

**Note**: `.env` is gitignored to prevent committing secrets. Only `.env.example` should be committed.

### Available Models

| Model | Description |
|-------|-------------|
| `gpt-4o-mini-realtime-preview` | Faster, lower cost |
| `gpt-4o-realtime-preview` | More capable |
| `gpt-realtime` | Alias for default realtime model |

### Available Voices

**Azure Neural Voices:**
- `en-US-AvaNeural`
- `en-US-GuyNeural`
- `en-US-JennyNeural`

**OpenAI Voices:**
- `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`

## Usage

```bash
source .venv/bin/activate
python voice-live-chat.py
```

### Expected Output

```
🔌 Connecting to Voice Live API...

==================================================
🎤 VOICE LIVE ASSISTANT READY
Start speaking - you can interrupt anytime!
Press Ctrl+C to exit
==================================================

✅ Connected: sess_xxx
🎤 Listening... (you can interrupt!)
🤔 Processing...
[AI response transcript appears here]
🎤 Ready...
```

## Key Implementation Details

### Barge-in (Interruption) Handling

The key to natural conversation is immediate audio cutoff when the user speaks:

```python
elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
    print("🎤 Listening... (you can interrupt!)")
    ap.skip_pending_audio()  # Immediately clears playback queue
```

The `skip_pending_audio()` method increments a sequence counter that causes all queued audio packets to be skipped, providing instant interruption.

### Audio Configuration

```python
# PCM16, 24kHz, mono - required by Voice Live API
format = pyaudio.paInt16
channels = 1
rate = 24000
chunk_size = 1200  # 50ms chunks
```

### Session Configuration

```python
session_config = RequestSession(
    modalities=[Modality.TEXT, Modality.AUDIO],
    instructions="Your system prompt here",
    voice=AzureStandardVoice(name="en-US-AvaNeural"),
    input_audio_format=InputAudioFormat.PCM16,
    output_audio_format=OutputAudioFormat.PCM16,
    turn_detection=ServerVad(
        threshold=0.5,
        prefix_padding_ms=300,
        silence_duration_ms=500
    ),
    # Key features for natural conversation:
    input_audio_echo_cancellation=AudioEchoCancellation(),
    input_audio_noise_reduction=AudioNoiseReduction(type="azure_deep_noise_suppression"),
)
```

### Event Types

| Event | Description |
|-------|-------------|
| `SESSION_UPDATED` | Session ready, start audio capture |
| `INPUT_AUDIO_BUFFER_SPEECH_STARTED` | User started speaking - trigger barge-in |
| `INPUT_AUDIO_BUFFER_SPEECH_STOPPED` | User stopped speaking |
| `RESPONSE_CREATED` | AI response started |
| `RESPONSE_AUDIO_DELTA` | Audio chunk received - queue for playback |
| `RESPONSE_AUDIO_TRANSCRIPT_DELTA` | Text transcript chunk |
| `RESPONSE_AUDIO_DONE` | AI finished speaking |
| `RESPONSE_DONE` | Response complete |
| `ERROR` | Error occurred |

## Function Calling / Tools

Voice Live supports function calling for integrating external tools:

```python
from azure.ai.voicelive.models import FunctionTool

tools = [
    FunctionTool(
        name="get_weather",
        description="Get current weather for a location",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and state or country"
                }
            },
            "required": ["location"]
        }
    )
]

# Add to session config
session_config = RequestSession(
    # ... other config ...
    tools=tools,
    tool_choice="auto"
)

# Handle function calls in event loop
elif event.type == ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE:
    # Parse arguments, call your function, return result
    result = your_function(json.loads(event.arguments))
    await connection.conversation.item.create(
        item=FunctionCallOutputItem(
            call_id=event.call_id,
            output=json.dumps(result)
        )
    )
    await connection.response.create()
```

## Comparison: Voice Live vs OpenAI Realtime API

| Feature | OpenAI Realtime API | Azure Voice Live API |
|---------|---------------------|----------------------|
| Barge-in | Manual (`response.cancel` + `truncate`) | Built-in (`skip_pending_audio()`) |
| Echo cancellation | None | `AudioEchoCancellation()` |
| Noise reduction | None | `azure_deep_noise_suppression` |
| VAD | Basic `server_vad` | Enhanced server-side VAD |
| Resource type | `OpenAI` kind | `AIServices` kind (multi-service) |
| Model deployment | Required | Fully managed |

## Limits

- **Session duration**: 30 minutes maximum
- **Audio format**: PCM16, 24kHz, mono only

## Documentation Links

### Official Microsoft Documentation

- [Voice Live API Overview](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live)
- [Voice Live Quickstart (Python)](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-quickstart?pivots=programming-language-python)
- [Voice Live Function Calling](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-voice-live-function-calling)
- [Voice Live with Agents](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-agents-quickstart)

### SDK References

- [azure-ai-voicelive PyPI](https://pypi.org/project/azure-ai-voicelive/)
- [azure-ai-voicelive API Reference](https://learn.microsoft.com/en-us/python/api/overview/azure/ai-voicelive-readme)
- [GitHub Samples](https://aka.ms/voicelive/github-python)

### Related Documentation

- [Azure AI Services Multi-service Resource](https://learn.microsoft.com/en-us/azure/ai-services/multi-service-resource)
- [Region Support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions)

## Troubleshooting

### "Missing required parameter: 'session.type'"

This is a benign warning that can be ignored. The session still works.

### No audio output

1. Check speaker volume and default audio device
2. Ensure PyAudio is using the correct output device
3. Try running with `--verbose` to see detailed logs

### Session timeout after 30 minutes

This is expected. Create a new session to continue.

### PyAudio installation issues on macOS

```bash
brew install portaudio
pip install pyaudio
```

## License

MIT
