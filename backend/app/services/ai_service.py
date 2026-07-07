"""
AI service orchestrator.

Coordinates all AI modules:
1. Classification (category + priority)
2. Embedding generation
3. Similar ticket search
4. Reply generation

API routes call this service, not individual AI modules.
This keeps the API layer thin and the AI logic centralized.
"""

from typing import Optional, Dict, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.ai.embeddings.embedder import embedder
from app.ai.classification.classifier import classifier
from app.ai.generation.generator import reply_generator
from app.ai.rag.retriever import retriever


class AIService:
    """
    Orchestrates all AI operations for tickets.
    
    This is the main entry point for AI features.
    API routes should use this service, not call
    AI modules directly.
    """
    
    def classify_ticket(
        self,
        db: Session,
        ticket_id: UUID,
        org_id: UUID,
    ) -> Dict:
        """
        Classify a ticket and save results to database.
        
        Steps:
        1. Fetch the ticket
        2. Send to Gemini for classification
        3. Save category, priority, and confidence to DB
        4. Return the results
        
        Returns:
            {"category": "bug", "priority": "high", "confidence": 0.92}
        """
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.org_id == org_id,
        ).first()
        
        if not ticket:
            return {"error": "Ticket not found"}
        
        # Classify using Gemini
        category, priority, confidence = classifier.classify(
            title=ticket.title,
            description=ticket.description,
        )
        
        # Save AI predictions to database
        ticket.ai_category = category
        ticket.ai_priority = priority
        ticket.ai_confidence = confidence
        db.commit()
        
        return {
            "category": category,
            "priority": priority,
            "confidence": confidence,
        }
    
    def predict_priority(
        self,
        db: Session,
        ticket_id: UUID,
        org_id: UUID,
    ) -> Dict:
        """
        Predict only the priority for a ticket.
        
        Faster than full classification when category
        is already known.
        """
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.org_id == org_id,
        ).first()
        
        if not ticket:
            return {"error": "Ticket not found"}
        
        priority, confidence = classifier.classify_priority_only(
            title=ticket.title,
            description=ticket.description,
        )
        
        ticket.ai_priority = priority
        ticket.ai_confidence = confidence
        db.commit()
        
        return {
            "priority": priority,
            "confidence": confidence,
        }
    
    def find_similar_tickets(
        self,
        db: Session,
        ticket_id: UUID,
        org_id: UUID,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Find tickets similar to the given ticket.
        
        Returns top K most similar tickets with scores.
        """
        return retriever.find_similar(
            db=db,
            ticket_id=str(ticket_id),
            org_id=str(org_id),
            top_k=top_k,
        )
    
    def search_similar_tickets(
        self,
        db: Session,
        org_id: UUID,
        query_text: str,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Search for tickets similar to a text query.
        
        Used when agent searches before creating a ticket.
        """
        return retriever.search_by_text(
            db=db,
            query_text=query_text,
            org_id=str(org_id),
            top_k=top_k,
        )
    
    def generate_reply(
        self,
        db: Session,
        ticket_id: UUID,
        org_id: UUID,
        include_similar: bool = True,
    ) -> Dict:
        """
        Generate an AI reply draft for a ticket.
        
        Steps:
        1. Fetch the ticket
        2. Optionally find similar resolved tickets
        3. Generate reply using Gemini
        4. Return the draft
        
        Args:
            include_similar: If True, uses similar tickets as context
                            for better replies
        """
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.org_id == org_id,
        ).first()
        
        if not ticket:
            return {"error": "Ticket not found"}
        
        similar_tickets = None
        if include_similar:
            # Get similar resolved tickets for context
            similar = retriever.find_similar(
                db=db,
                ticket_id=str(ticket_id),
                org_id=str(org_id),
                top_k=3,
                threshold=0.4,
            )
            
            if similar:
                similar_tickets = []
                for s in similar:
                    similar_tickets.append({
                        "title": s["title"],
                        "resolution": s.get("resolution", "No resolution recorded"),
                    })
        
        # Generate the reply
        result = reply_generator.generate_reply(
            title=ticket.title,
            description=ticket.description,
            similar_tickets=similar_tickets,
        )
        
        return result
    
    def auto_classify_on_create(
        self,
        db: Session,
        ticket: Ticket,
    ) -> None:
        """
        Automatically classify a ticket when it's created.
        
        Called by the ticket service after ticket creation.
        Runs synchronously - could be made async in production.
        """
        try:
            category, priority, confidence = classifier.classify(
                title=ticket.title,
                description=ticket.description,
            )
            
            ticket.ai_category = category
            ticket.ai_priority = priority
            ticket.ai_confidence = confidence
            
            # Also generate embedding for future similarity search
            text = f"{ticket.title} {ticket.description}"
            # We'll skip saving embedding for now (need pgvector)
            # ticket.embedding = embedder.embed_text(text)
            
            db.commit()
            
        except Exception as e:
            print(f"Auto-classification failed: {e}")
            # Don't block ticket creation if AI fails
            db.rollback()
    def analyze_sentiment(
        self,
        db: Session,
        ticket_id: UUID,
        org_id: UUID,
    ) -> Dict:
        """
        Analyze sentiment of a ticket and save to database.
        
        Returns:
            {"sentiment": "negative", "score": -0.85, "explanation": "..."}
        """
        from app.ai.sentiment import sentiment_analyzer
        
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.org_id == org_id,
        ).first()
        
        if not ticket:
            return {"error": "Ticket not found"}
        
        sentiment, score, explanation = sentiment_analyzer.analyze(
            title=ticket.title,
            description=ticket.description,
        )
        
        # Save to database
        ticket.sentiment = sentiment
        ticket.sentiment_score = score
        db.commit()
        
        return {
            "sentiment": sentiment,
            "score": score,
            "explanation": explanation,
        }
    def predict_escalation(
        self,
        db: Session,
        ticket_id: UUID,
        org_id: UUID,
    ) -> Dict:
        """Predict if a ticket is likely to escalate."""
        from app.ai.escalation import escalation_predictor
        
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.org_id == org_id,
        ).first()
        
        if not ticket:
            return {"error": "Ticket not found"}
        
        risk, score, signals, explanation = escalation_predictor.predict(
            title=ticket.title,
            description=ticket.description,
        )
        
        return {
            "escalation_risk": risk,
            "score": score,
            "signals": signals,
            "explanation": explanation,
        }
    
    def get_health_score(
        self,
        db: Session,
        org_id: UUID,
    ) -> Dict:
        """Calculate health score for an organization."""
        from app.ai.health_score import health_calculator
        
        return health_calculator.calculate(db, str(org_id))
    def find_root_causes(
        self,
        db: Session,
        org_id: UUID,
    ) -> List[Dict]:
        """Find root causes by clustering similar tickets."""
        from app.ai.root_cause import root_cause_detector
        
        return root_cause_detector.find_root_causes(db, str(org_id))
    
    def find_root_cause_for_ticket(
        self,
        db: Session,
        ticket_id: UUID,
        org_id: UUID,
    ) -> Dict:
        """Find tickets related to this ticket."""
        from app.ai.root_cause import root_cause_detector
        
        return root_cause_detector.find_root_cause_for_ticket(
            db, str(ticket_id), str(org_id)
        )
# Module-level singleton
ai_service = AIService()