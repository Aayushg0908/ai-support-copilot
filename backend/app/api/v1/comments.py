"""
Comment API endpoints.

All comment routes are nested under tickets because
comments always belong to a ticket.

Public URLs:
POST   /api/v1/tickets/{ticket_id}/comments        - Add comment
GET    /api/v1/tickets/{ticket_id}/comments        - List comments
PUT    /api/v1/comments/{comment_id}               - Edit comment
DELETE /api/v1/comments/{comment_id}               - Delete comment
"""

from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps.auth import get_current_user
from app.models.user import User
from app.schemas.comment import (
    CommentCreateRequest,
    CommentUpdateRequest,
    CommentResponse,
    CommentListResponse,
    CommentMessageResponse,
)
from app.services.comment_service import comment_service

# Note: Some routes use /tickets/{ticket_id}/comments prefix
# and some use /comments/{comment_id} prefix
router = APIRouter(tags=["Comments"])


@router.post(
    "/tickets/{ticket_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    ticket_id: UUID,
    request: CommentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a comment to a ticket.
    
    Can be a top-level comment or a reply to another comment.
    Set is_internal=True for agent-only notes.
    """
    comment = comment_service.create(
        db=db,
        ticket_id=ticket_id,
        user_id=current_user.id,
        body=request.body,
        parent_id=request.parent_id,
        is_internal=request.is_internal,
    )
    db.commit()
    
    return CommentResponse(
        id=comment.id,
        ticket_id=comment.ticket_id,
        user_id=comment.user_id,
        parent_id=comment.parent_id,
        body=comment.body,
        is_internal=comment.is_internal,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        user_name=current_user.full_name,
        replies=[],
    )


@router.get(
    "/tickets/{ticket_id}/comments",
    response_model=CommentListResponse,
)
def list_comments(
    ticket_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    threaded: bool = Query(False, description="Return nested threaded view"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List comments on a ticket.
    
    Set threaded=true to get nested replies.
    Set threaded=false (default) for flat paginated list.
    """
    comments, total = comment_service.list_comments(
        db=db,
        ticket_id=ticket_id,
        page=page,
        per_page=per_page,
        threaded=threaded,
    )
    
    # Build response based on threaded or flat
    comment_responses = []
    for item in comments:
        comment = item["comment"]
        user_name = item.get("user_name")
        replies = item.get("replies", [])
        
        # Build nested replies if threaded
        reply_responses = []
        for reply in replies:
            reply_comment = reply["comment"]
            reply_responses.append(
                CommentResponse(
                    id=reply_comment.id,
                    ticket_id=reply_comment.ticket_id,
                    user_id=reply_comment.user_id,
                    parent_id=reply_comment.parent_id,
                    body=reply_comment.body,
                    is_internal=reply_comment.is_internal,
                    created_at=reply_comment.created_at,
                    updated_at=reply_comment.updated_at,
                    user_name=reply.get("user_name"),
                    replies=[],
                )
            )
        
        comment_responses.append(
            CommentResponse(
                id=comment.id,
                ticket_id=comment.ticket_id,
                user_id=comment.user_id,
                parent_id=comment.parent_id,
                body=comment.body,
                is_internal=comment.is_internal,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                user_name=user_name,
                replies=reply_responses,
            )
        )
    
    return CommentListResponse(
        comments=comment_responses,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.put(
    "/comments/{comment_id}",
    response_model=CommentResponse,
)
def update_comment(
    comment_id: UUID,
    request: CommentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Edit a comment's body.
    
    Only the comment author can edit it.
    """
    comment = comment_service.update(
        db=db,
        comment_id=comment_id,
        user_id=current_user.id,
        body=request.body,
    )
    db.commit()
    
    return CommentResponse(
        id=comment.id,
        ticket_id=comment.ticket_id,
        user_id=comment.user_id,
        parent_id=comment.parent_id,
        body=comment.body,
        is_internal=comment.is_internal,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        user_name=current_user.full_name,
        replies=[],
    )


@router.delete(
    "/comments/{comment_id}",
    response_model=CommentMessageResponse,
)
def delete_comment(
    comment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a comment.
    
    Only the comment author can delete it.
    Replies to this comment are also deleted (CASCADE).
    """
    comment_service.delete(
        db=db,
        comment_id=comment_id,
        user_id=current_user.id,
    )
    db.commit()
    
    return CommentMessageResponse(
        message="Comment deleted successfully"
    )