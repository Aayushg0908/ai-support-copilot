"""
Sentiment analysis for support tickets.

Analyzes the emotional tone of ticket content.
Returns a sentiment label and score:
- positive: Customer is happy or satisfied
- neutral: Customer is neutral or informational
- negative: Customer is frustrated, angry, or upset

The sentiment_score ranges from -1.0 (very negative) to 1.0 (very positive).
"""

import json
from typing import Tuple
from groq import Groq
from app.core.config import settings


SENTIMENT_PROMPT = """Analyze the sentiment of this support ticket. Determine the customer's emotional tone.

TICKET:
Title: {title}
Description: {description}

Analyze for:
1. Emotional words (angry, frustrated, happy, grateful, etc.)
2. Urgency signals (ASAP, immediately, urgent)
3. Politeness level
4. Overall satisfaction

Return ONLY valid JSON:
{{
    "sentiment": "positive/negative/neutral",
    "score": 0.8,
    "explanation": "Brief explanation of why this sentiment was chosen"
}}

Score ranges:
- 0.7 to 1.0: Very positive (praising, grateful)
- 0.3 to 0.7: Somewhat positive
- -0.3 to 0.3: Neutral
- -0.7 to -0.3: Somewhat negative (frustrated, annoyed)
- -1.0 to -0.7: Very negative (angry, threatening)
"""


class SentimentAnalyzer:
    """
    Analyzes customer sentiment from ticket content.
    
    Uses Groq to understand emotional nuance that
    simple keyword matching would miss.
    """
    
    def __init__(self):
        if settings.GROQ_API_KEY:
            self.client = Groq(api_key=settings.GROQ_API_KEY)
        else:
            self.client = None
    
    def analyze(self, title: str, description: str) -> Tuple[str, float, str]:
        """
        Analyze sentiment of a ticket.
        
        Returns:
            (sentiment_label, sentiment_score, explanation)
        
        Example:
            ("negative", -0.85, "Customer is angry about 3-hour downtime")
        """
        if not self.client:
            return "neutral", 0.0, "Groq API not configured"
        
        try:
            prompt = SENTIMENT_PROMPT.format(
                title=title,
                description=description[:2000],
            )
            
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=150,
            )
            
            return self._parse_response(response.choices[0].message.content)
            
        except Exception as e:
            print(f"Sentiment analysis failed: {e}")
            return "neutral", 0.0, str(e)
    
    def _parse_response(self, text: str) -> Tuple[str, float, str]:
        """Parse Groq's JSON response."""
        try:
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                text = text[start:end].strip()
            
            data = json.loads(text)
            
            sentiment = data.get("sentiment", "neutral")
            score = float(data.get("score", 0.0))
            explanation = data.get("explanation", "")
            
            if sentiment not in ("positive", "negative", "neutral"):
                sentiment = "neutral"
            
            score = max(-1.0, min(1.0, score))
            
            return sentiment, score, explanation
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Failed to parse sentiment: {e}")
            return "neutral", 0.0, ""


# Module-level singleton
sentiment_analyzer = SentimentAnalyzer()