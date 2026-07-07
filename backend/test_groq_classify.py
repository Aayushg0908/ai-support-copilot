from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

prompt = """Classify this support ticket.

Ticket: Cannot login to dashboard, getting error 500 after security update. All users affected.

Return ONLY a valid JSON object with these fields:
- category: one of [bug, support, billing, account, other]
- priority: one of [low, medium, high, critical]
- confidence: number between 0 and 1

Example response:
{"category": "bug", "priority": "high", "confidence": 0.95}"""

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.1,
    max_tokens=100,
)
print("Raw response:", response.choices[0].message.content)