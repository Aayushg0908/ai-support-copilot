"""
Comment business logic.

Handles all comment operations:
- Creating comments (top-level and replies)
- Listing comments (flat or threaded)
- Updating comments
- Deleting comments (soft delete or hard delete)

Threaded comments are built by the service from flat database rows.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.comment import Comment
from app.models.ticket import Ticket
from app.models.user import User
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ValidationException,
)


class CommentService:
    """Handles all comment-related operations."""
    
    def create(
        self,
        db: Session,
        ticket_id: UUID,
        user_id: UUID,
        body: str,
        parent_id: Optional[UUID] = None,
        is_internal: bool = False,
    ) -> Comment:
        """
        Create a new comment on a ticket.
        
        Validates:
        - Ticket exists
        - If parent_id provided, parent comment exists and belongs to same ticket
        """
        # Verify ticket exists
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise NotFoundException(resource="Ticket", identifier=ticket_id)
        
        # If replying to another comment, verify it exists and belongs to same ticket
        if parent_id:
            parent_comment = db.query(Comment).filter(
                Comment.id == parent_id,
                Comment.ticket_id == ticket_id,  # Must be on same ticket
            ).first()
            if not parent_comment:
                raise ValidationException(
                    detail="Parent comment not found or belongs to a different ticket"
                )
        
        # Create the comment
        comment = Comment(
            ticket_id=ticket_id,
            user_id=user_id,
            body=body.strip(),
            parent_id=parent_id,
            is_internal=is_internal,
        )
        
        db.add(comment)
        db.flush()
        return comment
    
    def get_by_id(
        self,
        db: Session,
        comment_id: UUID,
    ) -> Comment:
        """
        Get a single comment by ID.
        """
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise NotFoundException(resource="Comment", identifier=comment_id)
        return comment
    
    def list_comments(
        self,
        db: Session,
        ticket_id: UUID,
        page: int = 1,
        per_page: int = 50,
        threaded: bool = False,
    ) -> tuple[list[dict], int]:
        """
        List comments on a ticket.
        
        Args:
            ticket_id: Which ticket's comments
            page: Page number
            per_page: Items per page
            threaded: If True, nest replies under parents
        
        Returns:
            Tuple of (comments_list, total_count)
            
        If threaded=True, only returns top-level comments
        with replies nested inside them.
        """
        # Get all comments for this ticket
        query = db.query(
            Comment,
            User.full_name.label("user_name"),
        ).outerjoin(
            User, User.id == Comment.user_id
        ).filter(
            Comment.ticket_id == ticket_id
        ).order_by(Comment.created_at.asc())
        
        total = query.count()
        
        if threaded:
            # Threaded mode: get all comments and build tree
            all_comments = query.all()
            return self._build_threaded_comments(all_comments), total
        
        # Flat mode: paginate
        offset = (page - 1) * per_page
        results = query.offset(offset).limit(per_page).all()
        
        comments = []
        for comment, user_name in results:
            comments.append({
                "comment": comment,
                "user_name": user_name,
            })
        
        return comments, total
    
    def _build_threaded_comments(
        self,
        all_comments: list,
    ) -> list[dict]:
        """
        Build a threaded comment tree from flat database rows.
        
        Algorithm:
        1. Separate top-level comments from replies
        2. For each top-level comment, recursively find its replies
        3. Return the tree structure
        
        This runs in Python instead of SQL because SQL
        isn't good at recursive tree building.
        """
        # Separate comments from user names
        comments_with_names = []
        for comment, user_name in all_comments:
            comments_with_names.append({
                "comment": comment,
                "user_name": user_name,
            })
        
        # Create a lookup map: comment_id → comment_dict
        comment_map = {}
        for item in comments_with_names:
            comment_map[item["comment"].id] = item
        
        # Separate top-level from replies
        top_level = []
        for item in comments_with_names:
            if item["comment"].parent_id is None:
                top_level.append(item)
            else:
                # Add to parent's replies list
                parent = comment_map.get(item["comment"].parent_id)
                if parent:
                    if "replies" not in parent:
                        parent["replies"] = []
                    parent["replies"].append(item)
        
        return top_level
    
    def update(
        self,
        db: Session,
        comment_id: UUID,
        user_id: UUID,
        body: str,
    ) -> Comment:
        """
        Update a comment's body.
        
        Only the author can edit their own comment.
        """
        comment = self.get_by_id(db, comment_id)
        
        # Only the author can edit
        if comment.user_id != user_id:
            raise ForbiddenException(
                detail="You can only edit your own comments"
            )
        
        comment.body = body.strip()
        db.flush()
        return comment
    
    def delete(
        self,
        db: Session,
        comment_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Delete a comment.
        
        Only the author can delete their own comment.
        Replies to this comment are also deleted (CASCADE).
        """
        comment = self.get_by_id(db, comment_id)
        
        # Only the author can delete
        if comment.user_id != user_id:
            raise ForbiddenException(
                detail="You can only delete your own comments"
            )
        
        # Hard delete - removes from database
        # Replies are automatically deleted by CASCADE
        db.delete(comment)
        db.flush()


# Module-level instance
comment_service = CommentService()