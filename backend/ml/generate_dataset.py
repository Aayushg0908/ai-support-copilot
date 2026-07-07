"""
Generate training data for ticket classification using Groq.
"""

"""
Generate training data for ticket classification using Groq.
"""

import json
import math
import sys
import os
from dotenv import load_dotenv

# Load .env from backend folder
backend_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, backend_dir)
load_dotenv(os.path.join(backend_dir, '.env'))

from groq import Groq
from app.core.config import settings
CATEGORIES = {
    "bug": "Software errors, crashes, features not working correctly",
    "feature_request": "Requests for new functionality or improvements",
    "support": "How-to questions, troubleshooting help needed",
    "billing": "Payment issues, invoices, subscription questions",
    "account": "Login problems, profile management, permissions",
    "performance": "System slowness, timeouts, resource issues",
    "security": "Security concerns, vulnerabilities, suspicious activity",
    "onboarding": "Setup help, installation, getting started",
    "integration": "API issues, webhooks, third-party connections",
    "refund": "Refund or cancellation requests",
    "general_inquiry": "General questions not fitting other categories",
    "complaint": "Customer dissatisfaction or frustration",
    "feedback": "Suggestions, praise, product feedback",
    "other": "Miscellaneous issues"
}

EXAMPLES_PER_CATEGORY = 300
BATCH_SIZE = 25  # 25 per API call, 12 batches per category


def generate_tickets_for_category(category, description, count):
    """Generate sample tickets using Groq."""
    
    client = Groq(api_key=settings.GROQ_API_KEY)
    
    prompt = f"""Generate {count} unique realistic customer support tickets for category: {category} ({description}).

Each ticket must have:
- title: Short realistic title
- description: 2-4 sentences describing the issue
- priority: One of [low, medium, high, critical]

Return ONLY a JSON array, no other text:
[
    {{"title": "Example title", "description": "Example description.", "priority": "medium", "category": "{category}"}},
    ...
]"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=4000,
        )
        
        text = response.choices[0].message.content.strip()
        
        # Extract JSON
        start = text.find('[')
        end = text.rfind(']') + 1
        
        if start >= 0 and end > start:
            json_text = text[start:end]
            # Fix any unclosed braces
            open_braces = json_text.count('{') - json_text.count('}')
            json_text = json_text.rstrip(',') + '}' * open_braces + ']'
            
            data = json.loads(json_text)
            for ticket in data:
                ticket["category"] = category
            return data
        
        return []
        
    except Exception as e:
        print(f"Error: {e}")
        return []


def generate_full_dataset(output_path="training_data.json"):
    """Generate tickets for all categories."""
    all_data = []
    batches = math.ceil(EXAMPLES_PER_CATEGORY / BATCH_SIZE)
    
    for category, description in CATEGORIES.items():
        print(f"\nGenerating {EXAMPLES_PER_CATEGORY} for: {category}")
        category_data = []
        
        for batch in range(batches):
            print(f"  Batch {batch + 1}/{batches}...", end=" ")
            tickets = generate_tickets_for_category(category, description, BATCH_SIZE)
            category_data.extend(tickets)
            print(f"{len(tickets)} tickets")
        
        all_data.extend(category_data)
        print(f"  Total for {category}: {len(category_data)}")
    
    with open(output_path, "w") as f:
        json.dump(all_data, f, indent=2)
    
    print(f"\n✅ Total: {len(all_data)} tickets")
    print(f"✅ Saved to: {output_path}")


if __name__ == "__main__":
    generate_full_dataset()