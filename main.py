"""
Enterprise Conversation Intelligence System
Main FastAPI Application
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import base64
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from models import AnalysisRequest, AnalysisResponse
from pipeline import ConversationPipeline

app = FastAPI(
    title="Enterprise Conversation Intelligence System",
    description="AI-powered conversation analyzer: auto-detects domain, generates policies, tracks sentiment/tone, detects violations, scores risk, predicts resolution time.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = ConversationPipeline()


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "system": "Enterprise Conversation Intelligence System",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "POST /analyze": "Analyze a conversation (text or audio)",
            "POST /analyze/audio": "Upload audio file directly",
            "GET /health": "Health check",
            "GET /domains": "List supported domains",
            "GET /docs": "Swagger UI documentation"
        }
    }


@app.get("/health")
async def health():
    api_key = os.getenv("GROQ_API_KEY", "")
    return {
        "status": "healthy",
        "groq_api_key_configured": bool(api_key),
        "assemblyai_configured": bool(os.getenv("ASSEMBLYAI_API_KEY", ""))
    }


@app.get("/domains")
async def domains():
    return {
        "supported_domains": [
            {"domain": "banking", "description": "Banking & Finance", "example_policies": ["No OTP verbally", "PCI-DSS", "KYC verification"]},
            {"domain": "telecom", "description": "Telecommunications", "example_policies": ["Roaming disclosure", "SLA guarantees", "Consent for plan changes"]},
            {"domain": "ecommerce", "description": "E-commerce & Retail", "example_policies": ["Return cost disclosure", "Refund timelines", "Warranty terms"]},
            {"domain": "healthcare", "description": "Healthcare", "example_policies": ["HIPAA compliance", "Patient data privacy", "Diagnosis disclaimers"]},
            {"domain": "insurance", "description": "Insurance", "example_policies": ["Policy misrepresentation", "Claim promise restrictions", "Disclosure requirements"]},
            {"domain": "auto", "description": "Auto-detect from conversation", "example_policies": ["Dynamically generated"]}
        ]
    }


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_conversation(request: AnalysisRequest):
    """
    Main analysis endpoint.
    Accepts text or base64-encoded audio.
    Runs the full pipeline: transcription → language → domain → policies → sentiment → compliance → risk → resolution.
    """
    try:
        result = await pipeline.run(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/audio")
async def analyze_audio_file(
    file: UploadFile = File(...),
    client_id: str = "default",
    domain: str = "auto",
    include_resolution_prediction: bool = True
):
    """
    Upload an audio file directly (mp3, wav, m4a).
    Transcribes, then runs full pipeline.
    """
    try:
        audio_bytes = await file.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        ext = file.filename.split(".")[-1].lower() if file.filename else "mp3"

        request = AnalysisRequest(
            input_type="audio",
            audio_file=audio_b64,
            audio_format=ext,
            client_config={"client_id": client_id, "domain": domain},
            analysis_type="comprehensive",
            include_resolution_prediction=include_resolution_prediction
        )

        result = await pipeline.run(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)