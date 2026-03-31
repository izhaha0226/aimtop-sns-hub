from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db
from models.content import Content
from models.approval import Approval
from models.user import User
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_result = await db.execute(
        select(func.count()).select_from(Content).where(Content.status != "trashed")
    )
    total_contents = total_result.scalar()

    pending_result = await db.execute(
        select(func.count()).select_from(Content).where(Content.status == "pending_approval")
    )
    pending_approvals = pending_result.scalar()

    published_result = await db.execute(
        select(func.count()).select_from(Content).where(
            Content.status == "published",
            Content.published_at >= today_start,
        )
    )
    published_today = published_result.scalar()

    scheduled_result = await db.execute(
        select(func.count()).select_from(Content).where(Content.status == "scheduled")
    )
    scheduled_count = scheduled_result.scalar()

    draft_result = await db.execute(
        select(func.count()).select_from(Content).where(Content.status == "draft")
    )
    draft_count = draft_result.scalar()

    return {
        "total_contents": total_contents,
        "pending_approvals": pending_approvals,
        "published_today": published_today,
        "scheduled": scheduled_count,
        "drafts": draft_count,
    }


@router.get("/recent-activity")
async def recent_activity(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    contents_result = await db.execute(
        select(Content)
        .where(Content.status != "trashed")
        .order_by(Content.updated_at.desc())
        .limit(10)
    )
    recent_contents = contents_result.scalars().all()

    approvals_result = await db.execute(
        select(Approval).order_by(Approval.created_at.desc()).limit(10)
    )
    recent_approvals = approvals_result.scalars().all()

    return {
        "recent_contents": [
            {
                "id": str(c.id),
                "title": c.title,
                "status": c.status,
                "post_type": c.post_type,
                "updated_at": c.updated_at.isoformat(),
            }
            for c in recent_contents
        ],
        "recent_approvals": [
            {
                "id": str(a.id),
                "content_id": str(a.content_id),
                "action": a.action,
                "created_at": a.created_at.isoformat(),
            }
            for a in recent_approvals
        ],
    }
