"""
AI reply generator using Groq API.
"""

import json
from typing import Optional, List
from groq import Groq

from app.core.config import settings


REPLY_PROMPT = """You are an expert support agent. Draft a professional reply to this ticket.

CUSTOMER TICKET:
Title: {title}
Description: {description}

{similar_tickets_section}
{knowledge_base_section}

INSTRUCTIONS:
1. Be empathetic and professional
2. Provide clear next steps
3. Reference similar solved tickets if available
4. Keep the tone helpful and friendly

Return ONLY valid JSON:
{{"reply": "The draft reply here...", "confidence": 0.85, "sources_used": [], "tone": "empathetic"}}
"""


class ReplyGenerator:
    def __init__(self):
        self.client = None
        self._setup_client()
    
    def _setup_client(self):
        if settings.GROQ_API_KEY:
            self.client = Groq(api_key=settings.GROQ_API_KEY)
    
    def generate_reply(
        self,
        title: str,
        description: str,
        similar_tickets: Optional[List[dict]] = None,
        knowledge_articles: Optional[List[dict]] = None,
    ) -> dict:
        if not self.client:
            return self._fallback_reply()
        
        try:
            similar_section = ""
            if similar_tickets:
                similar_section = "SIMILAR RESOLVED TICKETS:\n"
                for i, ticket in enumerate(similar_tickets[:3], 1):
                    similar_section += f"{i}. {ticket.get('title', 'N/A')}\n"
                    similar_section += f"   Resolution: {ticket.get('resolution', 'N/A')}\n\n"
            
            kb_section = ""
            if knowledge_articles:
                kb_section = "RELEVANT ARTICLES:\n"
                for i, article in enumerate(knowledge_articles[:2], 1):
                    kb_section += f"{i}. {article.get('title', 'N/A')}\n"
            
            prompt = REPLY_PROMPT.format(
                title=title,
                description=description[:3000],
                similar_tickets_section=similar_section,
                knowledge_base_section=kb_section,
            )
            
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000,
            )
            
            return self._parse_response(response.choices[0].message.content)
            
        except Exception as e:
            print(f"Reply generation failed: {e}")
            return self._fallback_reply()
    
    def generate_quick_reply(self, title: str, description: str) -> dict:
        return self.generate_reply(title, description)
    
    def _parse_response(self, text: str) -> dict:
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
            return {
                "reply": data.get("reply", ""),
                "confidence": float(data.get("confidence", 0.5)),
                "sources_used": data.get("sources_used", []),
                "tone": data.get("tone", "neutral"),
            }
        except (json.JSONDecodeError, KeyError, ValueError):
            return self._fallback_reply()
    
    def _fallback_reply(self) -> dict:
        return {
            "reply": "Thank you for reaching out. We have received your ticket and our support team will review it shortly.",
            "confidence": 0.0,
            "sources_used": [],
            "tone": "neutral",
        }


reply_generator = ReplyGenerator()