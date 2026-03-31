"""
Admin seed script.
Usage: python -m scripts.seed_admin
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from core.database import AsyncSessionLocal
from core.security import hash_password
from models.user import User
import uuid


ADMIN_EMAIL = "admin@aimtop.ai"
ADMIN_PASSWORD = "admin1234!"
ADMIN_NAME = "Admin"


async def seed_admin():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Admin already exists: {ADMIN_EMAIL}")
            return

        admin = User(
            id=uuid.uuid4(),
            name=ADMIN_NAME,
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            role="admin",
            status="active",
        )
        db.add(admin)
        await db.commit()
        print(f"Admin created: {ADMIN_EMAIL}")


if __name__ == "__main__":
    asyncio.run(seed_admin())
