"""
Ticket classification using Groq API.
"""

import json
from typing import Tuple
from groq import Groq

from app.core.config import settings


CLASSIFICATION_PROMPT = """You are an expert support ticket triage system. Analyze the following ticket and classify it.

TICKET:
Title: {title}
Description: {description}

INSTRUCTIONS:
1. Choose the SINGLE best category.
2. Choose the SINGLE most appropriate priority.
3. Provide a confidence score (0.0 to 1.0).

CATEGORIES:
- bug: Something is broken, not working, or producing errors
- feature_request: Customer wants new functionality
- support: General help, how-to questions, troubleshooting
- billing: Payments, invoices, subscriptions, pricing
- account: Login issues, account access, profile management
- performance: Slow loading, timeouts, high resource usage
- security: Security vulnerabilities, suspicious activity
- onboarding: Setup help, installation, getting started
- integration: API issues, webhooks, third-party connections
- refund: Refund or cancellation requests
- general_inquiry: General questions
- complaint: Customer dissatisfaction or frustration
- feedback: Suggestions, praise, or product feedback
- other: Does not clearly fit any category above

PRIORITY LEVELS:
- critical: Complete system outage, data loss, security breach, affects ALL users
- high: Major feature broken, no workaround, affects MANY users
- medium: Feature partially broken, workaround exists
- low: Minor issue, cosmetic bug, feature request

Return ONLY valid JSON, no other text:
{{"category": "bug", "priority": "high", "confidence": 0.92}}
"""


class TicketClassifier:
    def __init__(self):
        self.client = None
        self._setup_client()
    
    def _setup_client(self):
        if settings.GROQ_API_KEY:
            self.client = Groq(api_key=settings.GROQ_API_KEY)
    
    def classify(self, title: str, description: str) -> Tuple[str, str, float]:
        if not self.client:
            return "other", "medium", 0.0
        
        try:
            prompt = CLASSIFICATION_PROMPT.format(
                title=title,
                description=description[:2000],
            )
            
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=100,
            )
            
            raw_text = response.choices[0].message.content
            print(f"=== RAW CLASSIFY RESPONSE ===")
            print(raw_text)
            print(f"=== END ===")
                        
            result = self._parse_response(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"Classification failed: {e}")
            return "other", "medium", 0.0
    
    def _parse_response(self, text: str) -> Tuple[str, str, float]:
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
            category = data.get("category", "other")
            priority = data.get("priority", "medium")
            confidence = float(data.get("confidence", 0.0))
            
            return category, priority, confidence
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Failed to parse: {e}")
            return "other", "medium", 0.0
    
    def classify_priority_only(self, title: str, description: str) -> Tuple[str, float]:
        category, priority, confidence = self.classify(title, description)
        return priority, confidence


classifier = TicketClassifier()