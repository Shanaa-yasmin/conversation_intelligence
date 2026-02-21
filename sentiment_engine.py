"""
Sentiment & Emotion Analysis Engine
Uses deterministic NLP libraries: VADER, TextBlob, spaCy
No LLM dependency.
"""

import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import re
from typing import List, Dict, Tuple

# Download required NLTK data
try:
    nltk.data.find('sentiment/vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


class SentimentEngine:
    """
    Deterministic sentiment analysis using VADER and TextBlob.
    No LLM dependency.
    """

    def __init__(self):
        self.sia = SentimentIntensityAnalyzer()
        self.emotion_intensity_markers = {
            "extremely": 2.0,
            "very": 1.8,
            "really": 1.6,
            "quite": 1.4,
            "fairly": 1.2,
            "somewhat": 0.8
        }
        
        self.frustration_indicators = [
            "frustrated", "frustrated", "angry", "upset", "annoyed",
            "irritated", "exasperated", "fed up", "unhappy", "dissatisfied",
            "disappointed", "disgusted", "sick of", "tired of"
        ]
        
        self.empathy_indicators = [
            "apologize", "sorry", "understand", "appreciate", "thank",
            "help", "concern", "care", "assist", "support"
        ]

    def analyze_conversation(self, conversation: str, speakers: List[str] = None) -> Dict:
        """
        Analyze sentiment and emotion across entire conversation.
        Returns timeline and aggregate metrics.
        """
        lines = self._parse_conversation(conversation)
        
        if not speakers:
            speakers = list(set(line['speaker'] for line in lines))
        
        timeline = []
        speaker_sentiments = {speaker: [] for speaker in speakers}
        
        for line in lines:
            sentiment = self.analyze_statement(line['text'])
            entry = {
                'timestamp': line.get('timestamp', '00:00'),
                'speaker': line['speaker'],
                'text': line['text'][:100],
                'sentiment_score': sentiment['compound'],
                'tone': self._map_score_to_tone(sentiment['compound']),
                'intensity': sentiment.get('intensity', 1.0)
            }
            timeline.append(entry)
            speaker_sentiments[line['speaker']].append(sentiment['compound'])
        
        # Aggregate metrics
        customer_speaker = next((s for s in speakers if s.lower() in ['customer', 'caller']), speakers[0] if speakers else 'customer')
        agent_speaker = next((s for s in speakers if s.lower() in ['agent', 'representative']), speakers[1] if len(speakers) > 1 else 'agent')
        
        customer_scores = speaker_sentiments.get(customer_speaker, [])
        agent_scores = speaker_sentiments.get(agent_speaker, [])
        
        return {
            'timeline': timeline,
            'customer_sentiment': {
                'overall_score': sum(customer_scores) / len(customer_scores) if customer_scores else 0,
                'arc': self._sentiment_arc(customer_scores),
                'min_score': min(customer_scores) if customer_scores else 0,
                'max_score': max(customer_scores) if customer_scores else 0,
                'volatility': self._calculate_volatility(customer_scores)
            },
            'agent_tone': {
                'overall_score': sum(agent_scores) / len(agent_scores) if agent_scores else 0,
                'arc': self._sentiment_arc(agent_scores),
                'professionalism_score': self._professionalism_score(agent_speaker, timeline),
                'empathy_score': self._empathy_score(agent_speaker, timeline)
            },
            'frustration_level': self._detect_frustration(customer_speaker, timeline),
            'emotional_turning_points': self._detect_turning_points(timeline, customer_speaker)
        }

    def analyze_statement(self, text: str) -> Dict:
        """
        Analyze single statement using VADER and TextBlob.
        Returns compound score (-1 to 1) and intensity.
        """
        # VADER analysis
        vader_scores = self.sia.polarity_scores(text)
        compound = vader_scores['compound']
        
        # TextBlob polarity
        blob = TextBlob(text)
        textblob_polarity = blob.sentiment.polarity
        
        # Intensity detection
        intensity = self._detect_intensity(text)
        
        return {
            'compound': compound,
            'vader': vader_scores,
            'textblob_polarity': textblob_polarity,
            'intensity': intensity,
            'sentiment': self._map_score_to_sentiment(compound)
        }

    def _parse_conversation(self, conversation: str) -> List[Dict]:
        """
        Parse conversation into speaker:text format.
        Handles formats like:
        Agent: Hello
        Customer: Hi
        """
        lines = []
        for line in conversation.split('\n'):
            if ':' in line:
                parts = line.split(':', 1)
                speaker = parts[0].strip()
                text = parts[1].strip()
                lines.append({'speaker': speaker, 'text': text})
            elif line.strip():
                # Fallback: alternate speakers
                speaker = 'agent' if len(lines) % 2 == 0 else 'customer'
                lines.append({'speaker': speaker, 'text': line.strip()})
        return lines

    def _map_score_to_sentiment(self, score: float) -> str:
        """Map VADER compound score to sentiment label."""
        if score >= 0.5:
            return 'very_positive'
        elif score >= 0.05:
            return 'positive'
        elif score > -0.05:
            return 'neutral'
        elif score >= -0.5:
            return 'negative'
        else:
            return 'very_negative'

    def _map_score_to_tone(self, score: float) -> str:
        """Map sentiment score to tone label."""
        if score > 0.5:
            return 'positive'
        elif score > 0.1:
            return 'warm'
        elif score > -0.1:
            return 'neutral'
        elif score > -0.5:
            return 'frustrated'
        else:
            return 'hostile'

    def _detect_intensity(self, text: str) -> float:
        """Detect intensity amplifiers (very, extremely, etc)."""
        intensity = 1.0
        lower_text = text.lower()
        
        for marker, multiplier in self.emotion_intensity_markers.items():
            if marker in lower_text:
                intensity = max(intensity, multiplier)
        
        # Check for repetition (e.g., "no no no")
        if re.search(r'\b(\w+)(\s+\1){2,}\b', lower_text):
            intensity *= 1.5
        
        # Check for punctuation (!!!, ???)
        if '!!!' in text or '???' in text or '!!!!' in text:
            intensity *= 1.3
        
        return min(intensity, 2.0)

    def _detect_frustration(self, speaker: str, timeline: List[Dict]) -> float:
        """Measure frustration level for customer."""
        speaker_lines = [t for t in timeline if t['speaker'].lower() == speaker.lower()]
        
        if not speaker_lines:
            return 0.0
        
        frustration_score = 0.0
        frustration_count = 0
        
        for line in speaker_lines:
            if any(indicator in line['text'].lower() for indicator in self.frustration_indicators):
                frustration_score += abs(line['sentiment_score'])
                frustration_count += 1
        
        return min(frustration_score / len(speaker_lines) if speaker_lines else 0, 1.0)

    def _empathy_score(self, speaker: str, timeline: List[Dict]) -> float:
        """Measure empathy level for agent."""
        speaker_lines = [t for t in timeline if t['speaker'].lower() == speaker.lower()]
        
        if not speaker_lines:
            return 0.0
        
        empathy_count = 0
        for line in speaker_lines:
            if any(indicator in line['text'].lower() for indicator in self.empathy_indicators):
                empathy_count += 1
        
        return empathy_count / len(speaker_lines)

    def _professionalism_score(self, speaker: str, timeline: List[Dict]) -> float:
        """Score professionalism based on tone consistency."""
        speaker_lines = [t for t in timeline if t['speaker'].lower() == speaker.lower()]
        
        if not speaker_lines:
            return 0.5
        
        # Professional speech avoids extremes
        extreme_count = sum(1 for line in speaker_lines if abs(line['sentiment_score']) > 0.7)
        
        return 1.0 - (extreme_count / len(speaker_lines) * 0.5)

    def _sentiment_arc(self, scores: List[float]) -> str:
        """Describe sentiment trajectory through conversation."""
        if not scores or len(scores) < 2:
            return 'neutral'
        
        start = scores[0]
        end = scores[-1]
        middle = sum(scores[1:-1]) / len(scores[1:-1]) if len(scores) > 2 else start
        
        if start < 0 and end > 0:
            return 'negative_to_positive'
        elif start > 0 and end < 0:
            return 'positive_to_negative'
        elif start > 0.2 and end > 0.2:
            return 'sustained_positive'
        elif start < -0.2 and end < -0.2:
            return 'sustained_negative'
        else:
            return 'fluctuating'

    def _calculate_volatility(self, scores: List[float]) -> float:
        """Calculate sentiment volatility."""
        if len(scores) < 2:
            return 0.0
        
        diffs = [abs(scores[i] - scores[i-1]) for i in range(1, len(scores))]
        return sum(diffs) / len(diffs)

    def _detect_turning_points(self, timeline: List[Dict], customer_speaker: str) -> List[Dict]:
        """Identify emotional turning points with magnitude."""
        turning_points = []
        customer_timeline = [t for t in timeline if t['speaker'].lower() == customer_speaker.lower()]
        
        for i in range(1, len(customer_timeline)):
            prev_score = customer_timeline[i-1]['sentiment_score']
            curr_score = customer_timeline[i]['sentiment_score']
            shift = curr_score - prev_score
            
            if abs(shift) > 0.5:
                turning_points.append({
                    'timestamp': customer_timeline[i]['timestamp'],
                    'trigger': customer_timeline[i]['text'][:50],
                    'trigger_speaker': customer_speaker,
                    'customer_sentiment_before': prev_score,
                    'customer_sentiment_after': curr_score,
                    'sentiment_shift': 'improved' if shift > 0 else 'deteriorated',
                    'magnitude': abs(shift),
                    'recommendation': self._suggest_intervention(shift, curr_score)
                })
        
        return turning_points[:5]  # Return top 5 turning points

    def _suggest_intervention(self, shift: float, current_score: float) -> str:
        """Suggest intervention based on sentiment shift."""
        if shift < -0.5 and current_score < -0.5:
            return 'Immediate escalation recommended'
        elif shift < -0.3:
            return 'De-escalation techniques needed'
        elif shift > 0.5:
            return 'Continue current approach'
        else:
            return 'Monitor closely'
