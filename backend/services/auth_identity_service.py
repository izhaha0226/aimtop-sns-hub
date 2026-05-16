from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.auth_identity import AuthIdentity


class AuthIdentityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_identities(
        self,
        client_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
    ) -> list[AuthIdentity]:
        stmt = select(AuthIdentity).order_by(AuthIdentity.created_at.desc())
        if client_id:
            stmt = stmt.where(AuthIdentity.client_id == client_id)
        if user_id:
            stmt = stmt.where(AuthIdentity.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_identity(self, identity_id: uuid.UUID) -> AuthIdentity | None:
        result = await self.db.execute(select(AuthIdentity).where(AuthIdentity.id == identity_id))
        return result.scalar_one_or_none()

    async def create_identity(self, user_id: uuid.UUID, **data) -> AuthIdentity:
        identity = AuthIdentity(user_id=user_id, last_seen_at=datetime.now(timezone.utc), **data)
        self.db.add(identity)
        await self.db.commit()
        await self.db.refresh(identity)
        return identity

    async def update_identity(self, identity: AuthIdentity, **data) -> AuthIdentity:
        for key, value in data.items():
            setattr(identity, key, value)
        identity.last_seen_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(identity)
        return identity
