"""
Escalation prediction for support tickets.

Predicts if a ticket is likely to escalate (customer gets angrier,
involves management, threatens to cancel).
"""

import json
from typing import Tuple
from groq import Groq
from app.core.config import settings


ESCALATION_PROMPT = """Analyze if this support ticket is likely to escalate.

TICKET:
Title: {title}
Description: {description}

ESCALATION LEVELS:
- critical: Customer is actively threatening to cancel, mentioning legal action, or demanding immediate management intervention. Clear consequences stated.
- high: Customer is very frustrated, mentioning managers or competitors, but hasn't taken action yet. Strong warning signs.
- medium: Customer is frustrated or concerned, mentioned escalation as a possibility. Some risk present but not immediate.
- low: Customer is calm, satisfied, or just asking questions. No escalation signals.

SIGNALS TO LOOK FOR:
- Threat to cancel/subscribe
- Mention of competitors
- Legal action mentions
- Management/escalation mentions
- Long wait times
- Previous unresolved tickets

Return ONLY valid JSON:
{{
    "escalation_risk": "low/medium/high/critical",
    "score": 0.85,
    "signals": ["signal1", "signal2"],
    "explanation": "Brief explanation"
}}
"""


class EscalationPredictor:
    def __init__(self):
        if settings.GROQ_API_KEY:
            self.client = Groq(api_key=settings.GROQ_API_KEY)
        else:
            self.client = None
    
    def predict(self, title: str, description: str) -> Tuple[str, float, list, str]:
        if not self.client:
            return "low", 0.0, [], "API not configured"
        
        try:
            prompt = ESCALATION_PROMPT.format(
                title=title,
                description=description[:2000],
            )
            
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=200,
            )
            
            return self._parse_response(response.choices[0].message.content)
            
        except Exception as e:
            print(f"Escalation prediction failed: {e}")
            return "low", 0.0, [], str(e)
    
    def _parse_response(self, text: str) -> Tuple[str, float, list, str]:
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
            
            risk = data.get("escalation_risk", "low")
            score = float(data.get("score", 0.0))
            signals = data.get("signals", [])
            explanation = data.get("explanation", "")
            
            return risk, score, signals, explanation
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Failed to parse escalation: {e}")
            return "low", 0.0, [], ""


escalation_predictor = EscalationPredictor()