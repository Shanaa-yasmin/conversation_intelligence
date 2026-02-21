"""
Pydantic Models — Request & Response schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ─────────────────────────────────────────────
# REQUEST MODELS
# ─────────────────────────────────────────────

class ClientConfig(BaseModel):
    client_id: str = "default"
    domain: str = "auto"  # auto | banking | telecom | ecommerce | healthcare | insurance
    industry: Optional[str] = None


class AnalysisRequest(BaseModel):
    input_type: str = "text"           # "text" | "audio"
    conversation: Optional[str] = None  # Raw text conversation
    audio_file: Optional[str] = None   # Base64 encoded audio
    audio_format: Optional[str] = "mp3"
    client_config: Optional[Dict[str, Any]] = {}
    analysis_type: str = "comprehensive"


# ─────────────────────────────────────────────
# RESPONSE MODELS
# ─────────────────────────────────────────────

class ProcessingInfo(BaseModel):
    input_type: str
    transcription_confidence: Optional[float] = None
    speakers_detected: Optional[int] = None
    conversation_duration: Optional[str] = None
    raw_transcript: Optional[str] = None


class LanguageAnalysis(BaseModel):
    primary_language: str
    language_name: str
    confidence: float
    code_switching_detected: bool
    code_switching_languages: List[str]
    agent_language: Optional[str] = None
    customer_language: Optional[str] = None
    language_mismatch: bool
    risk_flag: bool
    notes: str


# Policy Generation removed - using predefined enterprise policies from policy_store/


class SentimentAnalysis(BaseModel):
    customer_sentiment_arc: str
    agent_tone_arc: str
    overall_customer_sentiment: float
    overall_agent_tone_score: float
    satisfaction_prediction: float
    churn_risk_from_sentiment: float


class PolicyViolation(BaseModel):
    policy_id: str
    policy_text: str
    violation_statement: str
    timestamp: str
    severity: str
    violation_type: str
    business_impact: str
    regulatory_risk: Optional[str] = None
    recommended_action: str


class ComplianceAnalysis(BaseModel):
    status: str
    compliance_score: float
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    violations: List[PolicyViolation]


class RiskFlags(BaseModel):
    security_breach: bool = False
    unauthorized_commitment: bool = False
    customer_angry: bool = False
    dismissive_agent: bool = False
    issue_unresolved: bool = False
    potential_churn: bool = False
    language_mismatch: bool = False


class RiskAssessment(BaseModel):
    overall_risk_score: float
    risk_level: str
    compliance_risk: float
    customer_satisfaction_risk: float
    churn_risk: float
    agent_performance_risk: float
    escalation_required: bool
    escalation_priority: str
    recommended_action: str
    flags: RiskFlags


class IntentAnalysis(BaseModel):
    primary_intent: str
    secondary_intents: List[str]
    resolution_status: str
    churn_intent_detected: bool
    churn_statement: Optional[str] = None
    urgency_level: str


class AgentPerformance(BaseModel):
    professionalism: float
    empathy: float
    policy_adherence: float
    issue_resolution: float
    communication_clarity: float
    overall_score: float
    grade: str
    coaching_areas: List[str]
    strengths: List[str]


class FullAnalysis(BaseModel):
    conversation_summary: str
    language_analysis: LanguageAnalysis
    sentiment_analysis: SentimentAnalysis
    compliance: ComplianceAnalysis
    risk_assessment: RiskAssessment
    agent_performance: AgentPerformance
    policy_generation: Optional[dict] = None  # Deprecated - using predefined policies
    intent_analysis: Optional[IntentAnalysis] = None


class AnalysisResponse(BaseModel):
    status: str
    processing: ProcessingInfo
    analysis: FullAnalysis
