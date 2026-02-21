"""
Enterprise Conversation Intelligence Analyzer
Re-architected to use:
- Deterministic NLP for sentiment/tone (VADER, TextBlob, spaCy)
- RAG-based compliance detection (FAISS + predefined policies)
- LLM only for high-level reasoning (summarization, risk synthesis, resolution prediction)
"""

import os
import json
import re
from groq import Groq
from sentiment_engine import SentimentEngine
from tone_engine import ToneEngine
from rag_engine import RAGEngine

client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
MODEL = "llama-3.3-70b-versatile"

# Initialize engines
sentiment_engine = SentimentEngine()
tone_engine = ToneEngine()
rag_engine = RAGEngine()


# ────────────────────────────────────────────
# LIMITED LLM PROMPTS (High-level reasoning only)
# ────────────────────────────────────────────

LANGUAGE_PROMPT = """Analyze the language(s) in this conversation.

CONVERSATION:
{conversation}

Respond ONLY with valid JSON:
{{
  "primary_language": "en",
  "language_name": "English",
  "confidence": 0.97,
  "code_switching_detected": false,
  "code_switching_languages": [],
  "agent_language": "en",
  "customer_language": "en",
  "language_mismatch": false,
  "risk_flag": false,
  "notes": "Brief observation"
}}

Use ISO 639-1 codes. Detect code-switching like Hinglish or Spanglish."""


SUMMARIZATION_PROMPT = """Summarize this customer service conversation in 2-3 sentences. Focus on issue and resolution status.

CONVERSATION:
{conversation}

Respond ONLY with valid JSON:
{{
  "conversation_summary": "2-3 sentence summary",
  "resolution_status": "resolved|unresolved|escalated"
}}"""


RISK_SYNTHESIS_PROMPT = """Given structured signals from compliance and sentiment analysis, synthesize overall risk assessment.

SIGNALS:
{signals}

Respond ONLY with valid JSON:
{{
  "overall_risk_score": 0.75,
  "risk_level": "low|medium|high|critical",
  "escalation_required": true|false,
  "escalation_priority": "routine|urgent|immediate",
  "recommended_action": "specific action recommendation",
  "risk_summary": "brief explanation of key risks"
}}"""


INTENT_ANALYSIS_PROMPT = """Analyze the customer's primary and secondary intents in this conversation.

CONVERSATION:
{conversation}

Identify:
1. Primary intent (main reason for contact)
2. Secondary intents (additional concerns)
3. Resolution status
4. Churn risk (if customer threatens to leave/cancel)
5. Urgency level

Respond ONLY with valid JSON:
{{
  "primary_intent": "billing_issue|technical_support|account_inquiry|complaint|cancellation|product_question|service_request",
  "secondary_intents": ["refund_request", "escalation"],
  "resolution_status": "resolved|unresolved|escalated|pending",
  "churn_intent_detected": true|false,
  "churn_statement": "Exact quote if churn threat detected",
  "urgency_level": "low|medium|high|critical"
}}"""


def _call_groq(prompt: str) -> str:
    """Call Groq and return clean text response"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    text = response.choices[0].message.content.strip()
    text = re.sub(r'```json|```', '', text).strip()
    return text


# ────────────────────────────────────────────
# PUBLIC FUNCTIONS
# ────────────────────────────────────────────

async def detect_language(conversation: str) -> dict:
    """Detect language using Groq (LLM appropriate for this task)"""
    try:
        text = _call_groq(LANGUAGE_PROMPT.format(conversation=conversation[:3000]))
        return json.loads(text)
    except Exception as e:
        print(f"[Language] Error: {e}")
        return {
            "primary_language": "en",
            "language_name": "English",
            "confidence": 0.80,
            "code_switching_detected": False,
            "code_switching_languages": [],
            "agent_language": "en",
            "customer_language": "en",
            "language_mismatch": False,
            "risk_flag": False,
            "notes": "Language detection failed, defaulting to English"
        }


async def detect_domain(conversation: str) -> dict:
    """
    Detect domain from conversation using keyword heuristics.
    Uses predefined domains, no LLM-generated policies.
    """
    domain_keywords = {
        'banking': ['bank', 'account', 'credit', 'debit', 'loan', 'mortgage', 'otp', 'cvv', 'card'],
        'telecom': ['plan', 'roaming', '4g', '5g', 'network', 'call', 'data', 'recharge'],
        'ecommerce': ['order', 'delivery', 'refund', 'return', 'shipping', 'product', 'payment'],
        'healthcare': ['appointment', 'prescription', 'medical', 'doctor', 'hospital', 'health'],
        'insurance': ['policy', 'claim', 'coverage', 'premium', 'insurance', 'deductible']
    }
    
    lower_convo = conversation.lower()
    domain_scores = {}
    
    for domain, keywords in domain_keywords.items():
        matches = sum(lower_convo.count(keyword) for keyword in keywords)
        domain_scores[domain] = matches
    
    if not domain_scores or max(domain_scores.values()) == 0:
        return {'detected_domain': 'unknown', 'detection_confidence': 0.3, 'industry': 'other'}
    
    detected = max(domain_scores, key=domain_scores.get)
    confidence = min(domain_scores[detected] / max(1, sum(domain_scores.values()) / 2), 0.99)
    
    return {
        'detected_domain': detected,
        'detection_confidence': confidence,
        'industry': detected
    }


async def run_nlp_analysis(conversation: str, domain: str) -> dict:
    """
    Run all deterministic NLP analysis:
    - Sentiment analysis (VADER + TextBlob)
    - Tone detection (Rule-based)
    - Compliance detection (RAG)
    - Critical data exposure detection
    """
    
    sentiment_result = sentiment_engine.analyze_conversation(conversation)
    tone_result = tone_engine.analyze_conversation(conversation)
    compliance_result = rag_engine.detect_violations(conversation, domain)
    data_exposure_result = rag_engine.detect_critical_data_exposure(conversation)
    
    return {
        'sentiment_analysis': sentiment_result,
        'tone_analysis': tone_result,
        'compliance_deviation': compliance_result,
        'critical_data_exposure': data_exposure_result
    }


async def get_conversation_summary(conversation: str) -> dict:
    """Get conversation summary using LLM"""
    try:
        text = _call_groq(SUMMARIZATION_PROMPT.format(conversation=conversation[:4000]))
        return json.loads(text)
    except Exception as e:
        return {
            "conversation_summary": "Failed to generate summary",
            "resolution_status": "unknown"
        }


async def synthesize_risk(nlp_analysis: dict, summary: dict) -> dict:
    """
    Synthesize overall risk from:
    - Compliance violations
    - Sentiment + tone analysis
    - Customer frustration
    - Agents's professionalism
    """
    signals = {
        'compliance': nlp_analysis.get('compliance_deviation', {}),
        'sentiment': nlp_analysis.get('sentiment_analysis', {}),
        'tone': nlp_analysis.get('tone_analysis', {}),
        'data_exposure': nlp_analysis.get('critical_data_exposure', {}),
        'resolution_status': summary.get('resolution_status', 'unknown')
    }
    
    try:
        text = _call_groq(RISK_SYNTHESIS_PROMPT.format(signals=json.dumps(signals, indent=2)[:3000]))
        return json.loads(text)
    except Exception as e:
        # Fallback: calculate risk deterministically
        return _calculate_risk_score_deterministic(signals)


async def analyze_intent(conversation: str) -> dict:
    """
    Analyze customer intent using LLM.
    Identifies primary/secondary intents, churn risk, urgency.
    """
    try:
        text = _call_groq(INTENT_ANALYSIS_PROMPT.format(conversation=conversation[:3000]))
        result = json.loads(text)
        return result
    except Exception as e:
        print(f"[Intent] Error: {e}")
        # Fallback: basic keyword-based intent detection
        lower_conv = conversation.lower()
        
        # Detect churn threats
        churn_keywords = ['cancel', 'close account', 'switching', 'leaving', 'competitor']
        churn_detected = any(kw in lower_conv for kw in churn_keywords)
        
        # Detect urgency
        urgency_keywords = ['urgent', 'immediately', 'asap', 'emergency', 'critical']
        urgency = 'high' if any(kw in lower_conv for kw in urgency_keywords) else 'medium'
        
        # Basic intent classification
        if 'refund' in lower_conv or 'money back' in lower_conv:
            primary = 'refund_request'
        elif 'technical' in lower_conv or 'not working' in lower_conv:
            primary = 'technical_support'
        elif 'cancel' in lower_conv:
            primary = 'cancellation'
        elif 'bill' in lower_conv or 'charge' in lower_conv:
            primary = 'billing_issue'
        else:
            primary = 'general_inquiry'
        
        return {
            'primary_intent': primary,
            'secondary_intents': [],
            'resolution_status': 'unresolved',
            'churn_intent_detected': churn_detected,
            'churn_statement': None,
            'urgency_level': urgency
        }


# ────────────────────────────────────────────
# HELPER FUNCTIONS
# ────────────────────────────────────────────

def _calculate_risk_score_deterministic(signals: dict) -> dict:
    """Calculate risk score without LLM (fallback)"""
    compliance = signals.get('compliance', {})
    sentiment = signals.get('sentiment', {})
    tone = signals.get('tone', {})
    data_exposure = signals.get('data_exposure', {})
    
    risk_score = 0.0
    
    # Compliance risk
    critical_violations = compliance.get('critical_violations', 0)
    high_violations = compliance.get('high_violations', 0)
    risk_score += min(critical_violations * 0.3, 0.5)
    risk_score += min(high_violations * 0.1, 0.3)
    
    # Sentiment risk
    customer_sentiment = sentiment.get('customer_sentiment', {})
    customer_score = customer_sentiment.get('overall_score', 0)
    if customer_score < -0.5:
        risk_score += 0.2
    
    # Data exposure risk
    exposures = data_exposure.get('total_exposures', 0)
    risk_score += min(exposures * 0.2, 0.4)
    
    risk_score = min(risk_score, 1.0)
    
    escalate = risk_score > 0.6 or critical_violations > 0
    
    return {
        'overall_risk_score': risk_score,
        'risk_level': 'critical' if risk_score > 0.8 else 'high' if risk_score > 0.6 else 'medium' if risk_score > 0.3 else 'low',
        'escalation_required': escalate,
        'escalation_priority': 'immediate' if risk_score > 0.8 else 'urgent' if risk_score > 0.6 else 'routine',
        'recommended_action': 'Escalate immediately for compliance review' if risk_score > 0.7 else 'Monitor conversation closely',
        'risk_summary': f'{critical_violations} critical violations, customer sentiment {customer_score:.2f}'
    }