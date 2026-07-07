"""
Root cause detection by clustering similar tickets.

Groups related tickets using embedding similarity
to identify underlying problems.
"""

from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.ai.embeddings.embedder import embedder


class RootCauseDetector:
    """Groups similar tickets to find root causes."""
    
    def find_root_causes(
        self,
        db: Session,
        org_id: str,
        min_cluster_size: int = 2,
        similarity_threshold: float = 0.4,
    ) -> List[Dict]:
        """
        Find groups of similar tickets (potential root causes).
        
        Returns clusters of related tickets that may share
        an underlying cause.
        """
        tickets = db.query(Ticket).filter(
            Ticket.org_id == org_id,
            Ticket.description.isnot(None),
        ).limit(200).all()
        
        if len(tickets) < min_cluster_size:
            return []
        
        # Generate embeddings for all tickets
        texts = [f"{t.title} {t.description}" for t in tickets]
        embeddings = embedder.embed_texts(texts)
        
        # Simple clustering: group tickets that are similar to each other
        clusters = []
        used = set()
        
        for i, ticket in enumerate(tickets):
            if i in used:
                continue
            
            # Find tickets similar to this one
            similar_indices = embedder.find_most_similar(
                query_embedding=embeddings[i],
                candidate_embeddings=embeddings,
                top_k=20,
            )
            
            # Filter by threshold and unused
            cluster = [ticket]
            used.add(i)
            
            for idx, similarity in similar_indices:
                if idx != i and idx not in used and similarity >= similarity_threshold:
                    cluster.append(tickets[idx])
                    used.add(idx)
            
            if len(cluster) >= min_cluster_size:
                # Generate a name for this root cause
                titles = [t.title for t in cluster]
                common_words = self._find_common_words(titles)
                
                clusters.append({
                    "id": f"rc-{len(clusters) + 1}",
                    "name": common_words or "Related Issues",
                    "ticket_count": len(cluster),
                    "tickets": [
                        {
                            "id": str(t.id),
                            "title": t.title,
                            "status": t.status.value,
                        }
                        for t in cluster
                    ],
                    "common_theme": common_words,
                })
        
        # Sort by cluster size (largest first)
        clusters.sort(key=lambda x: x["ticket_count"], reverse=True)
        
        return clusters
    
    def find_root_cause_for_ticket(
        self,
        db: Session,
        ticket_id: str,
        org_id: str,
        similarity_threshold: float = 0.35,
    ) -> Dict:
        """Find other tickets related to this one."""
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.org_id == org_id,
        ).first()
        
        if not ticket:
            return {"ticket_id": ticket_id, "related_tickets": []}
        
        # Get all other tickets
        other_tickets = db.query(Ticket).filter(
            Ticket.org_id == org_id,
            Ticket.id != ticket_id,
        ).limit(100).all()
        
        if not other_tickets:
            return {"ticket_id": ticket_id, "related_tickets": []}
        
        # Generate embeddings
        query_text = f"{ticket.title} {ticket.description}"
        query_embedding = embedder.embed_text(query_text)
        
        other_texts = [f"{t.title} {t.description}" for t in other_tickets]
        other_embeddings = embedder.embed_texts(other_texts)
        
        # Find similar
        similar = embedder.find_most_similar(
            query_embedding=query_embedding,
            candidate_embeddings=other_embeddings,
            top_k=10,
        )
        
        related = []
        for idx, similarity in similar:
            if similarity >= similarity_threshold:
                related.append({
                    "id": str(other_tickets[idx].id),
                    "title": other_tickets[idx].title,
                    "similarity": round(similarity, 4),
                })
        
        return {
            "ticket_id": ticket_id,
            "related_tickets": related,
            "total_related": len(related),
        }
    
    def _find_common_words(self, titles: List[str]) -> str:
        """Extract common meaningful words from titles."""
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at"}
        word_counts = {}
        
        for title in titles:
            words = title.lower().split()
            for word in words:
                word = word.strip(".,!?():;\"'")
                if len(word) > 3 and word not in stop_words:
                    word_counts[word] = word_counts.get(word, 0) + 1
        
        common = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        top_words = [w for w, c in common[:3] if c >= 2]
        
        return " ".join(top_words).title() if top_words else ""


# Module-level singleton
root_cause_detector = RootCauseDetector()