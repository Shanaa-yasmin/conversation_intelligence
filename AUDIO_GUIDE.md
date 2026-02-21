# 🎤 Audio Transcription Guide

Your system has **full audio transcription support** for real audio files!

**⚠️ IMPORTANT: Requires API key** (AssemblyAI or OpenAI)

---

## 🚀 Quick Start

### Upload Your Audio File

```bash
python test_audio.py your_audio_file.mp3
```

**Supported formats:** mp3, wav, m4a, webm, flac, ogg

---

## 🔑 Setup Required

Before using audio transcription, you must configure an API key:

### 1. Get API Key (Choose One)

**Option A: AssemblyAI** (Recommended)
- Website: https://www.assemblyai.com/
- Free tier: 3 hours/month
- Best for speaker diarization

**Option B: OpenAI Whisper**
- Website: https://platform.openai.com/
- Pay per use: ~$0.006/minute
- Good general transcription

### 2. Add to .env File

Edit `.env` file and add your key:

```env
# AssemblyAI (recommended)
ASSEMBLYAI_API_KEY=your_actual_key_here

# Or OpenAI
OPENAI_API_KEY=sk-your_actual_key_here
```

### 3. Restart Server

```bash
python main.py
```

---

## 🎯 How It Works

### Audio Processing Flow:

```
Audio File → Base64 Encoding → Transcription Service → Text → Full Analysis
                                     ↓
                    AssemblyAI (primary) → Whisper (fallback)
```

### Transcription Services:

1. **AssemblyAI** (Primary - Recommended)
   - Best for speaker diarization (Agent vs Customer)
   - High accuracy
   - Requires API key: `ASSEMBLYAI_API_KEY`

2. **OpenAI Whisper** (Fallback)
   - Good general transcription
   - Requires API key: `OPENAI_API_KEY`

**Note:** At least one API key is required for transcription.

---

## 🔑 Setup API Keys (Optional)

If you want to use real transcription services:

### 1. Get API Keys

- **AssemblyAI**: https://www.assemblyai.com/ (recommended)
- **OpenAI**: https://platform.openai.com/

### 2. Add to `.env` file

Create `.env` in the `conversation_intelligence/` folder:

```env
GROQ_API_KEY=gsk_your_key_here
ASSEMBLYAI_API_KEY=your_assemblyai_key_here  # Optional
OPENAI_API_KEY=your_openai_key_here          # Optional
```

**Note:** If no transcription API keys are set, the system automatically uses mock transcription.

---

## 📡 API Endpoints

### Method 1: Direct File Upload (Easiest)

```bash
curl -X POST http://localhost:8000/analyze/audio \
  -F "file=@conversation.mp3" \
  -F "client_id=test_001" \
  -F "domain=banking"
```

### Method 2: Base64 Encoded (Via /analyze endpoint)

```python
import httpx
import base64

# Read and encode audio
with open("audio.mp3", "rb") as f:
    audio_b64 = base64.b64encode(f.read()).decode("utf-8")

# Send request
payload = {
    "input_type": "audio",
    "audio_file": audio_b64,
    "audio_format": "mp3",
    "client_config": {"client_id": "test", "domain": "auto"},
    "analysis_type": "comprehensive",
    "include_resolution_prediction": True
}

response = httpx.post("http://localhost:8000/analyze", json=payload)
```

---

## 📊 Example Response

```json
{
  "status": "success",
  "processing_info": {
    "input_type": "audio",
    "transcription_confidence": 0.92,
    "speakers_detected": 2,
    "conversation_duration": "2:34",
    "raw_transcript": "Agent: Thank you for calling..."
  },
  "analysis": {
    "language_analysis": {...},
    "sentiment_analysis": {...},
    "compliance": {
      "status": "violated",
      "violations": [
        {
          "policy_id": "BANK_SEC_3.2.1",
          "violation_statement": "Agent requested OTP verbally",
          "severity": "critical"
        }
      ]
    },
    "risk_assessment": {...},
    "agent_performance": {...}
  }
}
```

---

## 🧪 Testing

### Run the test script:

```bash
# Start server (Terminal 1)
python main.py

# Test audio (Terminal 2)
python test_audio.py
```

### With your own file:

```bash
python test_audio.py path/to/your/audio.mp3
```

Results saved to: `test_results/audio_test_result.json`

---

## 🎙️ Recording Tips

For best transcription results:

- **Clear audio**: Minimize background noise
- **Good quality**: 16kHz+ sample rate
- **Duration**: Under 10 minutes recommended
- **Volume**: Normalized audio levels
- **Format**: MP3, WAV, or M4A

---

## 🔍 Troubleshooting

### "No transcription API keys configured"
- This is normal! Mock transcription still works
- Add ASSEMBLYAI_API_KEY or OPENAI_API_KEY for real transcription

- Add ASSEMBLYAI_API_KEY or OPENAI_API_KEY to .env file
- Get free key from: https://www.assemblyai.com/
- Restart server after adding key
- Use lower bitrate MP3 (32-128 kbps)

### "Transcription timeout"
- Try shorter audio files
- Check internet connection
- Verify API keys are valid

---

## 💡 Example Use Cases

### Customer Service Call Recording
```bash
python test_audio.py customer_call_2024_02_21.mp3
```

### Sales Conversation Analysis
```bash
python test_audio.py sales_demo_recording.wav
```

### Compliance Audit Review
```bash
python test_audio.py audit_sample_call.m4a
```

---

## ✅ What You Get

After transcription, you receive:

✅ **Full text transcript** with speaker labels (Agent/Customer)  
✅ **Sentiment analysis** of customer and agent  
✅ **Policy violation detection** with exact policy IDs  
✅ **Risk assessment** and escalation flags  
✅ **Agent performance grade** (A-F)  
✅ **Resolution time prediction**  
✅ **Conversation summary**  

All from your audio file!

---

## 🚀 Next Steps
Get API key**: https://www.assemblyai.com/ (free tier available)
2. **Add to .env**: `ASSEMBLYAI_API_KEY=your_key_here`
3. **Restart server**: `python main.py`
4. **Test with audio**: `python test_audio.py your_file.mp3`
5. **Integrate intoional): AssemblyAI for best results
4. **Integrate into your app**: Use the `/analyze/audio` endpoint

---

**Your audio transcription is ready to use! 🎉**
