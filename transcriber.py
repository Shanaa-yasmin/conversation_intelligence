"""
Audio Transcription Service
Supports: AssemblyAI (primary, diarization), OpenAI Whisper (fallback)
Requires API key - no mock mode
"""

import os
import base64
import json
import re
import httpx
from typing import Optional


class TranscriptionResult:
    def __init__(self, transcript: str, confidence: float, speakers: int, duration: str, utterances: list):
        self.transcript = transcript
        self.confidence = confidence
        self.speakers = speakers
        self.duration = duration
        self.utterances = utterances  # [{speaker, text, start, end}]


class AudioTranscriber:

    def __init__(self):
        self.assemblyai_key = os.getenv("ASSEMBLYAI_API_KEY", "")

    async def transcribe(self, audio_b64: str, audio_format: str) -> TranscriptionResult:
        """
        Main entry point. Uses AssemblyAI with speaker diarization (Agent vs Customer).
        Raises exception if ASSEMBLYAI_API_KEY is not configured.
        """
        if not self.assemblyai_key:
            raise Exception(
                "No transcription API key configured. "
                "Please set ASSEMBLYAI_API_KEY in .env file. "
                "Get your key from: https://www.assemblyai.com/"
            )

        return await self._transcribe_assemblyai(audio_b64, audio_format)

    async def _transcribe_assemblyai(self, audio_b64: str, audio_format: str) -> TranscriptionResult:
        """AssemblyAI — best for diarization"""
        audio_bytes = base64.b64decode(audio_b64)

        async with httpx.AsyncClient(timeout=120) as client:
            # Step 1: Upload audio
            print(f"[AssemblyAI] Uploading {len(audio_bytes)} bytes...")
            upload_resp = await client.post(
                "https://api.assemblyai.com/v2/upload",
                headers={"authorization": self.assemblyai_key},
                content=audio_bytes
            )
            upload_resp.raise_for_status()
            upload_url = upload_resp.json()["upload_url"]
            print(f"[AssemblyAI] Upload complete: {upload_url}")

            # Step 2: Submit transcription job
            print(f"[AssemblyAI] Submitting transcription job...")
            transcript_resp = await client.post(
                "https://api.assemblyai.com/v2/transcript",
                headers={"authorization": self.assemblyai_key, "content-type": "application/json"},
                json={
                    "audio_url": upload_url,
                    "speech_models": ["universal-2"],  # Use universal-2 model
                    "speaker_labels": True
                }
            )
            
            # Better error handling
            if transcript_resp.status_code != 200:
                error_detail = transcript_resp.text
                print(f"[AssemblyAI] Error response: {error_detail}")
                raise Exception(f"AssemblyAI API error: {error_detail}")
            
            job_id = transcript_resp.json()["id"]
            print(f"[AssemblyAI] Job ID: {job_id} - Polling for results...")

            # Step 3: Poll for result
            import asyncio
            for i in range(60):
                await asyncio.sleep(3)
                poll = await client.get(
                    f"https://api.assemblyai.com/v2/transcript/{job_id}",
                    headers={"authorization": self.assemblyai_key}
                )
                data = poll.json()
                status = data.get("status")
                
                if status == "completed":
                    print(f"[AssemblyAI] Transcription complete!")
                    return self._parse_assemblyai(data)
                elif status == "error":
                    error_msg = data.get('error', 'Unknown error')
                    print(f"[AssemblyAI] Transcription error: {error_msg}")
                    raise Exception(f"AssemblyAI error: {error_msg}")
                else:
                    if i % 5 == 0:  # Print progress every 15 seconds
                        print(f"[AssemblyAI] Status: {status}...")

        raise Exception("AssemblyAI transcription timed out after 3 minutes")

    def _parse_assemblyai(self, data: dict) -> TranscriptionResult:
        utterances = []
        full_lines = []
        speakers_seen = set()

        for u in data.get("utterances", []):
            speaker_label = "Agent" if u["speaker"] == "A" else "Customer"
            speakers_seen.add(u["speaker"])
            start_sec = u["start"] / 1000
            mins = int(start_sec // 60)
            secs = int(start_sec % 60)
            ts = f"{mins:02d}:{secs:02d}"

            utterances.append({
                "speaker": speaker_label,
                "text": u["text"],
                "timestamp": ts,
                "start_ms": u["start"],
                "end_ms": u["end"]
            })
            full_lines.append(f"{speaker_label}: {u['text']}")

        total_ms = data.get("audio_duration", 0) * 1000 if data.get("audio_duration") else 0
        total_secs = int(total_ms / 1000)
        duration = f"{total_secs // 60:02d}:{total_secs % 60:02d}"

        return TranscriptionResult(
            transcript="\n".join(full_lines),
            confidence=data.get("confidence", 0.9),
            speakers=len(speakers_seen),
            duration=duration,
            utterances=utterances
        )