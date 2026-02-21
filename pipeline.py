"""
Conversation Intelligence Pipeline (Re-architected)
Orchestrates:
1. Transcription (audio → text)
2. Language detection (LLM)
3. Domain detection (heuristic)
4. NLP Analysis (sentiment, tone, compliance via RAG)
5. Risk synthesis (LLM for reasoning)
6. Intent analysis (LLM-based intent detection)
"""

from models import (
    AnalysisRequest, AnalysisResponse,
    ProcessingInfo, LanguageAnalysis,
    SentimentAnalysis,
    ComplianceAnalysis, PolicyViolation,
    RiskAssessment, RiskFlags,
    AgentPerformance, IntentAnalysis,
    FullAnalysis
)
from transcriber import AudioTranscriber
from analyzer import (
    detect_language, detect_domain, run_nlp_analysis,
    get_conversation_summary, synthesize_risk,
    analyze_intent
)


class ConversationPipeline:

    def __init__(self):
        self.transcriber = AudioTranscriber()

    async def run(self, request: AnalysisRequest) -> AnalysisResponse:
        """Execute the full re-architected pipeline"""

        # ── STEP 0: Get conversation text ──────────────────
        processing_info = await self._get_conversation(request)
        conversation = processing_info["conversation"]

        # ── STEP 1: Language detection (LLM) ────────────────
        language_analysis = await detect_language(conversation)

        # ── STEP 2: Domain detection (heuristic) ──────────────
        domain_detection = await detect_domain(conversation)
        domain = domain_detection['detected_domain']

        # ── STEP 3: NLP Analysis (deterministic) ──────────────
        # Uses VADER, TextBlob, spaCy for sentiment/tone
        # Uses RAG + FAISS for compliance detection
        nlp_analysis = await run_nlp_analysis(conversation, domain)

        # ── STEP 4: Conversation Summary (LLM) ──────────────
        conversation_summary = await get_conversation_summary(conversation)

        # ── STEP 5: Risk Synthesis (LLM + structured data) ──
        risk_assessment = await synthesize_risk(nlp_analysis, conversation_summary)

        # ── STEP 6: Intent Analysis (LLM-based intent detection) ──
        intent_analysis = await analyze_intent(conversation)

        # ── STEP 7: Build structured response ──────────────
        return self._build_response(
            processing_info=processing_info,
            language_analysis=language_analysis,
            domain_detection=domain_detection,
            nlp_analysis=nlp_analysis,
            conversation_summary=conversation_summary,
            risk_assessment=risk_assessment,
            intent_analysis=intent_analysis
        )

    async def _get_conversation(self, request: AnalysisRequest) -> dict:
        """Handle text or audio input"""
        if request.input_type == "audio" and request.audio_file:
            result = await self.transcriber.transcribe(
                request.audio_file,
                request.audio_format or "mp3"
            )
            return {
                "conversation": result.transcript,
                "input_type": "audio",
                "transcription_confidence": result.confidence,
                "speakers_detected": result.speakers,
                "conversation_duration": result.duration,
                "raw_transcript": result.transcript
            }
        else:
            conversation = request.conversation or ""
            return {
                "conversation": conversation,
                "input_type": "text",
                "transcription_confidence": None,
                "speakers_detected": self._count_speakers(conversation),
                "conversation_duration": None,
                "raw_transcript": None
            }

    def _count_speakers(self, conversation: str) -> int:
        speakers = set()
        for line in conversation.split("\n"):
            if ":" in line:
                speaker = line.split(":")[0].strip()
                if speaker:
                    speakers.add(speaker.lower())
        return max(len(speakers), 1)

    def _build_response(
        self, processing_info: dict, language_analysis: dict,
        domain_detection: dict, nlp_analysis: dict,
        conversation_summary: dict, risk_assessment: dict,
        intent_analysis: dict
    ) -> AnalysisResponse:
        """Build the full AnalysisResponse from re-architected components"""

        # Processing info
        proc = ProcessingInfo(
            input_type=processing_info["input_type"],
            transcription_confidence=processing_info.get("transcription_confidence"),
            speakers_detected=processing_info.get("speakers_detected"),
            conversation_duration=processing_info.get("conversation_duration"),
            raw_transcript=processing_info.get("raw_transcript")
        )

        # Language analysis
        lang = LanguageAnalysis(
            primary_language=language_analysis.get("primary_language", "en"),
            language_name=language_analysis.get("language_name", "English"),
            confidence=language_analysis.get("confidence", 0.9),
            code_switching_detected=language_analysis.get("code_switching_detected", False),
            code_switching_languages=language_analysis.get("code_switching_languages", []),
            agent_language=language_analysis.get("agent_language"),
            customer_language=language_analysis.get("customer_language"),
            language_mismatch=language_analysis.get("language_mismatch", False),
            risk_flag=language_analysis.get("risk_flag", False),
            notes=language_analysis.get("notes", "")
        )

        # Sentiment analysis (from NLP engines)
        sentiment_data = nlp_analysis.get('sentiment_analysis', {})
        tone_data = nlp_analysis.get('tone_analysis', {})

        customer_sent = sentiment_data.get('customer_sentiment', {})
        agent_tone = sentiment_data.get('agent_tone', {})

        sentiment = SentimentAnalysis(
            customer_sentiment_arc=customer_sent.get('arc', 'neutral'),
            agent_tone_arc=agent_tone.get('arc', 'professional'),
            overall_customer_sentiment=float(customer_sent.get("overall_score", 0.0)),
            overall_agent_tone_score=float(agent_tone.get("overall_score", 0.5)),
            satisfaction_prediction=max(0, 1 + float(customer_sent.get("overall_score", 0))),  # Derived from sentiment
            churn_risk_from_sentiment=max(0, min(1, 0.5 + abs(float(customer_sent.get("overall_score", 0)))))  # Risk increases with negative sentiment
        )

        # Compliance analysis (from RAG engine)
        compliance_raw = nlp_analysis.get('compliance_deviation', {})
        violations = [
            PolicyViolation(
                policy_id=v.get("policy_id", "UNKNOWN"),
                policy_text=v.get("clause", ""),
                violation_statement=v.get("detected_phrase", ""),
                timestamp="auto",
                severity=v.get("severity", "medium"),
                violation_type="explicit",
                business_impact=v.get("remediation", ""),
                regulatory_risk=v.get("regulatory_basis", ""),
                recommended_action=v.get("remediation", "")
            )
            for v in compliance_raw.get("violations", [])[:10]
        ]

        compliance_status = "compliant" if compliance_raw.get('compliance_status') == 'compliant' else "violated"
        
        compliance = ComplianceAnalysis(
            status=compliance_status,
            compliance_score=1.0 - compliance_raw.get('severity_score', 0.0),
            critical_count=compliance_raw.get('critical_violations', 0),
            high_count=len([v for v in compliance_raw.get('violations', []) if v.get('severity') == 'high']),
            medium_count=len([v for v in compliance_raw.get('violations', []) if v.get('severity') == 'medium']),
            low_count=len([v for v in compliance_raw.get('violations', []) if v.get('severity') == 'low']),
            violations=violations
        )

        # Risk assessment (synthesized from NLP and LLM reasoning)
        risk_flags = RiskFlags(
            security_breach=bool(nlp_analysis.get('critical_data_exposure', {}).get('total_exposures', 0) > 0),
            unauthorized_commitment=bool(any(v['policy_id'] in ['BANK_LOAN_7.1.1', 'TELECOM_SLA_2.1.1']
                                             for v in compliance_raw.get('violations', []))),
            customer_angry=sentiment_data.get('frustration_level', 0) > 0.6,
            dismissive_agent=tone_data.get('tone_distribution', {}).get('dismissive', 0) > 0,
            issue_unresolved=conversation_summary.get('resolution_status', 'unknown') == 'unresolved',
            potential_churn=sentiment_data.get('frustration_level', 0) > 0.7,
            language_mismatch=language_analysis.get("language_mismatch", False)
        )

        risk = RiskAssessment(
            overall_risk_score=float(risk_assessment.get("overall_risk_score", 0.5)),
            risk_level=risk_assessment.get("risk_level", "medium"),
            compliance_risk=float(compliance_raw.get('severity_score', 0.0)),
            customer_satisfaction_risk=max(0, min(1, 0.5 + abs(float(customer_sent.get("overall_score", 0))))),
            churn_risk=sentiment_data.get('frustration_level', 0),
            agent_performance_risk=1 - tone_data.get('tone_consistency', 0.5),
            escalation_required=risk_assessment.get("escalation_required", False),
            escalation_priority=risk_assessment.get("escalation_priority", "routine"),
            recommended_action=risk_assessment.get("recommended_action", "Continue monitoring"),
            flags=risk_flags
        )

        # Agent performance (derived from tone and compliance adherence)
        ap = AgentPerformance(
            professionalism=tone_data.get('tone_consistency', 0.5),
            empathy=tone_data.get('tone_distribution', {}).get('empathy', 0) * 0.3 + 0.4,  # Normalized
            policy_adherence=1.0 - compliance_raw.get('severity_score', 0.0),
            issue_resolution=1.0 if conversation_summary.get('resolution_status') == 'resolved' else 0.0,
            communication_clarity=0.7,  # Default, can be refined
            overall_score=(
                (tone_data.get('tone_consistency', 0.5) +
                 tone_data.get('tone_distribution', {}).get('empathy', 0) * 0.2 +
                 (1.0 - compliance_raw.get('severity_score', 0.0)) +
                 (1.0 if conversation_summary.get('resolution_status') == 'resolved' else 0.0)) / 4
            ),
            grade=self._score_to_grade(
                (tone_data.get('tone_consistency', 0.5) +
                 (1.0 - compliance_raw.get('severity_score', 0.0))) / 2
            ),
            coaching_areas=self._identify_coaching_areas(tone_data, compliance_raw),
            strengths=self._identify_strengths(tone_data, compliance_raw)
        )

        # Final response
        analysis = FullAnalysis(
            conversation_summary=conversation_summary.get('conversation_summary', "Conversation analyzed"),
            language_analysis=lang,
            policy_generation=None,  # No longer generated, using predefined policies
            sentiment_analysis=sentiment,
            compliance=compliance,
            risk_assessment=risk,
            intent_analysis=IntentAnalysis(**intent_analysis),
            agent_performance=ap
        )

        return AnalysisResponse(
            status="success",
            processing=proc,
            analysis=analysis
        )

    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade"""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"

    def _identify_coaching_areas(self, tone_data: dict, compliance_raw: dict) -> list:
        """Identify coaching areas from tone and compliance"""
        areas = []
        
        if tone_data.get('tone_distribution', {}).get('dismissive', 0) > 0:
            areas.append("Improve customer empathy")
        
        if compliance_raw.get('critical_violations', 0) > 0:
            areas.append("Review compliance policies")
        
        if not tone_data.get('tone_consistency', 0.5) > 0.7:
            areas.append("Maintain consistent professional tone")
        
        return areas[:3]

    def _identify_strengths(self, tone_data: dict, compliance_raw: dict) -> list:
        """Identify agent strengths"""
        strengths = []
        
        if not compliance_raw.get('violations', []):
            strengths.append("Excellent compliance adherence")
        
        if tone_data.get('tone_consistency', 0.5) > 0.7:
            strengths.append("Consistent professional tone")
        
        return strengths[:2]

