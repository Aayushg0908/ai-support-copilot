"""
Similar ticket retriever using embedding similarity.

When an agent views a ticket, this finds the most similar
past tickets based on semantic meaning (not just keywords).

This enables:
- "This ticket looks like #890 which was resolved by clearing cache"
- Reducing duplicate work on similar issues
- Knowledge reuse across the team
"""

from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.ticket import Ticket
from app.ai.embeddings.embedder import embedder


class TicketRetriever:
    """
    Finds similar tickets using embedding similarity.
    
    Process:
    1. Take the query ticket's title + description
    2. Convert to embedding vector
    3. Compare against all other tickets' embeddings
    4. Return top K most similar tickets
    
    This is semantic search - it finds tickets by MEANING,
    not just keyword matching.
    """
    
    def find_similar(
        self,
        db: Session,
        ticket_id: str,
        org_id: str,
        top_k: int = 5,
        threshold: float = 0.3,
    ) -> List[Dict]:
        """
        Find tickets similar to the given ticket.
        
        Args:
            db: Database session
            ticket_id: The ticket to find similarities for
            org_id: Organization ID (scope search to org)
            top_k: Maximum number of similar tickets to return
            threshold: Minimum similarity score (0.0 to 1.0)
                       Lower values return more tickets but
                       might include irrelevant ones.
        
        Returns:
            List of similar tickets with:
            - id: Ticket ID
            - title: Ticket title
            - status: Current status
            - priority: Priority level
            - similarity: Similarity score (0-1)
            - resolution: How it was resolved (if resolved)
        """
        # Get the query ticket
        query_ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.org_id == org_id,
        ).first()
        
        if not query_ticket:
            return []
        
        # Generate embedding for the query ticket if not already stored
        if not hasattr(query_ticket, '_embedding_cache'):
            query_text = f"{query_ticket.title} {query_ticket.description}"
            query_ticket._embedding_cache = embedder.embed_text(query_text)
        
        query_embedding = query_ticket._embedding_cache
        
        # Get all other tickets in the org that have descriptions
        other_tickets = db.query(Ticket).filter(
            Ticket.org_id == org_id,
            Ticket.id != ticket_id,
            Ticket.description.isnot(None),
        ).order_by(desc(Ticket.created_at)).limit(200).all()  # Limit for performance
        
        if not other_tickets:
            return []
        
        # Generate embeddings for all other tickets
        ticket_data = []
        embeddings = []
        
        for ticket in other_tickets:
            text = f"{ticket.title} {ticket.description}"
            ticket_embedding = embedder.embed_text(text)
            embeddings.append(ticket_embedding)
            ticket_data.append(ticket)
        
        # Find most similar
        similar_indices = embedder.find_most_similar(
            query_embedding=query_embedding,
            candidate_embeddings=embeddings,
            top_k=top_k,
        )
        
        # Build results
        results = []
        for idx, similarity in similar_indices:
            if similarity < threshold:
                continue  # Skip low-similarity matches
            
            ticket = ticket_data[idx]
            
            # Build resolution summary from comments or status
            resolution = None
            if ticket.status.value in ("resolved", "closed"):
                resolution = f"Resolved on {ticket.resolved_at.strftime('%Y-%m-%d') if ticket.resolved_at else 'unknown date'}"
            
            results.append({
                "id": str(ticket.id),
                "title": ticket.title,
                "status": ticket.status.value,
                "priority": ticket.priority.value,
                "similarity": round(similarity, 4),
                "resolution": resolution,
                "created_at": ticket.created_at.isoformat(),
            })
        
        return results
    
    def search_by_text(
        self,
        db: Session,
        query_text: str,
        org_id: str,
        top_k: int = 5,
        threshold: float = 0.3,
    ) -> List[Dict]:
        """
        Search for tickets similar to a text query.
        
        Useful when an agent wants to search before creating a ticket:
        "Has anyone reported this login issue before?"
        
        Args:
            query_text: The search query (title + description)
            org_id: Organization ID
            top_k: Max results
            threshold: Minimum similarity
        
        Returns:
            List of matching tickets
        """
        # Generate embedding for search query
        query_embedding = embedder.embed_text(query_text)
        
        # Get tickets to search through
        tickets = db.query(Ticket).filter(
            Ticket.org_id == org_id,
            Ticket.description.isnot(None),
        ).order_by(desc(Ticket.created_at)).limit(200).all()
        
        if not tickets:
            return []
        
        # Generate embeddings
        ticket_data = []
        embeddings = []
        for ticket in tickets:
            text = f"{ticket.title} {ticket.description}"
            ticket_embedding = embedder.embed_text(text)
            embeddings.append(ticket_embedding)
            ticket_data.append(ticket)
        
        # Find similar
        similar_indices = embedder.find_most_similar(
            query_embedding=query_embedding,
            candidate_embeddings=embeddings,
            top_k=top_k,
        )
        
        # Build results
        results = []
        for idx, similarity in similar_indices:
            if similarity < threshold:
                continue
            
            ticket = ticket_data[idx]
            results.append({
                "id": str(ticket.id),
                "title": ticket.title,
                "status": ticket.status.value,
                "priority": ticket.priority.value,
                "similarity": round(similarity, 4),
                "created_at": ticket.created_at.isoformat(),
            })
        
        return results


# Module-level singleton
retriever = TicketRetriever()