"""
Tone & Emotion Detection Engine
Rule-based detection using lexicons and punctuation patterns.
No LLM dependency.
"""

import re
from typing import List, Dict


class ToneEngine:
    """
    Deterministic tone detection using lexicons and linguistic patterns.
    Classifies: Aggressive, Frustrated, Neutral, Empathetic, Apologetic, Escalatory
    """

    def __init__(self):
        # Tone lexicons
        self.aggressive_words = {
            'demand', 'insist', 'must', 'have to', 'need to', 'you better',
            'threat', 'warn', 'serious', 'angry', 'furious', 'furious'
        }
        
        self.frustrated_words = {
            'frustrated', 'annoyed', 'irritated', 'irritated', 'tired', 'fed up',
            'sick of', 'why me', 'again', 'still', 'yet', 'ridiculous', 'unacceptable'
        }
        
        self.empathetic_words = {
            'understand', 'appreciate', 'sorry', 'apologize', 'concern', 'care',
            'empathy', 'compassion', 'help', 'assist', 'support', 'grateful'
        }
        
        self.apologetic_words = {
            'apologize', 'sorry', 'regret', 'forgive', 'excuse', 'mistake',
            'error', 'wrong', 'mea culpa', 'unreasonable', 'unfair'
        }
        
        self.escalatory_words = {
            'manager', 'supervisor', 'complaint', 'escalate', 'legal',
            'lawsuit', 'sue', 'authority', 'report', 'higher', 'boss'
        }
        
        self.dismissive_words = {
            'whatever', 'honestly', 'frankly', 'clearly', 'obviously',
            'obviously', 'dont care', 'fine', 'whatever', 'nevermind'
        }

    def analyze_conversation(self, conversation: str, agent_speaker: str = None) -> Dict:
        """
        Analyze dominant tones throughout conversation.
        Returns timeline with tone flags and summary.
        """
        lines = self._parse_conversation(conversation)
        
        if not agent_speaker:
            agent_speaker = next((l['speaker'] for l in lines if l['speaker'].lower() in ['agent', 'representative']), 'agent')
        
        tone_flags = []
        tone_distribution = {}
        
        for line in lines:
            if line['speaker'].lower() != agent_speaker.lower():
                continue
            
            tones = self.analyze_statement(line['text'])
            
            for tone, score in tones.items():
                if score > 0.3:  # Confidence threshold
                    tone_flags.append({
                        'speaker': line['speaker'],
                        'tone': tone,
                        'timestamp': line.get('timestamp', '00:00'),
                        'statement': line['text'][:50],
                        'score': score,
                        'severity': self._rate_severity(tone, score),
                        'risk_contribution': self._risk_score(tone)
                    })
                    tone_distribution[tone] = tone_distribution.get(tone, 0) + 1
        
        # Sort by severity and recency
        tone_flags.sort(key=lambda x: (x['severity'] == 'critical', x['severity'] == 'high'), reverse=True)
        
        return {
            'tone_flags': tone_flags[:10],  # Top 10 flags
            'dominant_tone': self._determine_dominant_tone(tone_distribution),
            'tone_distribution': tone_distribution,
            'tone_consistency': self._measure_consistency(tone_flags),
            'red_flags_summary': self._summarize_flags(tone_flags)
        }

    def analyze_statement(self, text: str) -> Dict[str, float]:
        """
        Analyze single statement for multiple tones.
        Returns tone scores (0.0 to 1.0) for each tone category.
        """
        lower_text = text.lower()
        
        return {
            'aggressive': self._score_tone(lower_text, self.aggressive_words),
            'frustrated': self._score_tone(lower_text, self.frustrated_words),
            'empathetic': self._score_tone(lower_text, self.empathetic_words),
            'apologetic': self._score_tone(lower_text, self.apologetic_words),
            'escalatory': self._score_tone(lower_text, self.escalatory_words),
            'dismissive': self._score_tone(lower_text, self.dismissive_words),
            'neutral': self._neutral_score(lower_text)
        }

    def _score_tone(self, text: str, word_set: set) -> float:
        """Score presence of tone indicators."""
        matches = sum(1 for word in word_set if word in text)
        
        if matches == 0:
            return 0.0
        
        # Base score from word frequency
        base_score = min(matches * 0.15, 0.8)
        
        # Amplify based on intensity markers
        intensity_multiplier = self._detect_linguistic_intensity(text)
        
        return min(base_score * intensity_multiplier, 1.0)

    def _neutral_score(self, text: str) -> float:
        """Score neutrality (absence of emotional language)."""
        emotional_words = (
            self.aggressive_words | self.frustrated_words |
            self.empathetic_words | self.apologetic_words |
            self.escalatory_words | self.dismissive_words
        )
        
        matches = sum(1 for word in emotional_words if word in text)
        
        # More neutral if fewer emotional words
        return max(0.0, 1.0 - (matches * 0.2))

    def _detect_linguistic_intensity(self, text: str) -> float:
        """Detect intensity amplifiers and modifiers."""
        intensity = 1.0
        
        # Exclamation marks
        exclamations = text.count('!')
        if exclamations >= 3:
            intensity *= 1.5
        elif exclamations >= 1:
            intensity *= 1.2
        
        # Question marks (can indicate frustration)
        questions = text.count('?')
        if questions >= 2:
            intensity *= 1.1
        
        # ALL CAPS
        caps_ratio = sum(1 for c in text if c.isupper()) / len(text) if text else 0
        if caps_ratio > 0.3:
            intensity *= 1.3
        
        # Word repetition
        words = text.split()
        if len(words) > 0:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            if any(count >= 3 for count in word_counts.values()):
                intensity *= 1.2
        
        return min(intensity, 2.5)

    def _parse_conversation(self, conversation: str) -> List[Dict]:
        """Parse conversation into speaker:text format."""
        lines = []
        for line in conversation.split('\n'):
            if ':' in line:
                parts = line.split(':', 1)
                speaker = parts[0].strip()
                text = parts[1].strip()
                lines.append({'speaker': speaker, 'text': text})
            elif line.strip():
                speaker = 'agent' if len(lines) % 2 == 0 else 'customer'
                lines.append({'speaker': speaker, 'text': line.strip()})
        return lines

    def _rate_severity(self, tone: str, score: float) -> str:
        """Rate severity of tone flag."""
        if tone in ['aggressive', 'escalatory'] and score > 0.6:
            return 'critical'
        elif tone in ['aggressive', 'escalatory', 'frustrated'] and score > 0.5:
            return 'high'
        elif tone == 'dismissive' and score > 0.5:
            return 'medium'
        else:
            return 'low'

    def _risk_score(self, tone: str) -> float:
        """Convert tone to risk contribution (0.0-1.0)."""
        risk_map = {
            'aggressive': 0.9,
            'escalatory': 0.85,
            'frustrated': 0.6,
            'dismissive': 0.4,
            'empathetic': -0.3,
            'apologetic': -0.2,
            'neutral': 0.0
        }
        return risk_map.get(tone, 0.0)

    def _determine_dominant_tone(self, tone_distribution: Dict[str, int]) -> str:
        """Identify most frequent tone."""
        if not tone_distribution:
            return 'neutral'
        
        return max(tone_distribution, key=tone_distribution.get)

    def _measure_consistency(self, tone_flags: List[Dict]) -> float:
        """Measure tone consistency (low variance = consistent)."""
        if len(tone_flags) < 2:
            return 1.0
        
        tones = [flag['tone'] for flag in tone_flags]
        unique_tones = len(set(tones))
        
        # Perfect consistency = 1.0, high variance = lower score
        return 1.0 - (unique_tones / len(tones) * 0.5)

    def _summarize_flags(self, tone_flags: List[Dict]) -> str:
        """Generate human-readable summary of tone flags."""
        if not tone_flags:
            return "No significant tone issues detected."
        
        critical_flags = [f for f in tone_flags if f['severity'] == 'critical']
        high_flags = [f for f in tone_flags if f['severity'] == 'high']
        
        summary_parts = []
        
        if critical_flags:
            summary_parts.append(f"CRITICAL: {len(critical_flags)} aggressive/escalatory moments detected")
        
        if high_flags:
            summary_parts.append(f"HIGH: {len(high_flags)} frustrated/escalatory statements")
        
        if not summary_parts:
            return "Minor tone variations, overall professional."
        
        return ". ".join(summary_parts) + "."

    def get_tone_recommendations(self, tone_analysis: Dict) -> List[str]:
        """Generate recommendations based on tone analysis."""
        recommendations = []
        
        if 'aggressive' in tone_analysis['tone_distribution']:
            recommendations.append("Train agent on de-escalation techniques")
        
        if 'dismissive' in tone_analysis['tone_distribution']:
            recommendations.append("Improve customer empathy and active listening")
        
        if tone_analysis['tone_consistency'] < 0.5:
            recommendations.append("Agent tone is inconsistent; provide coaching")
        
        if 'escalatory' in tone_analysis['tone_distribution']:
            recommendations.append("Monitor for potential escalations")
        
        return recommendations
