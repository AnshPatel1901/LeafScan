"""
Development seed script — creates a demo user account.
Run: python scripts/seed.py

Only for local development. Never run against production.
"""

import asyncio
import os
import sys

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import get_async_session
from app.repositories.user_repository import UserRepository


async def seed():
    print(f"Seeding database: {settings.DATABASE_URL}")
    async for session in get_async_session():
        repo = UserRepository(session)
        username = "demo_farmer"
        if await repo.username_exists(username):
            print(f"  ✓  User '{username}' already exists — skipping")
        else:
            user = await repo.create(
                username=username,
                password_hash=hash_password("DemoPass@1"),
            )
            print(f"  ✓  Created user: {user.username} (id={user.id})")
        break  # One session is enough

    print("\nDone. You can now login with:")
    print("  username: demo_farmer")
    print("  password: DemoPass@1")


if __name__ == "__main__":
    asyncio.run(seed())
