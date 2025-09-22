#!/usr/bin/env python3
"""Database initialization script for PresGen-Assess."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
from src.common.config import settings, get_database_url, get_async_database_url


async def create_database_if_not_exists():
    """Create the database if it doesn't exist."""

    # Extract database name from URL
    db_url = settings.database_url
    if "postgresql" in db_url:
        # Parse the URL to get database name
        parts = db_url.split("/")
        if len(parts) >= 4:
            db_name = parts[-1]
            # Create URL without database name for initial connection
            base_url = "/".join(parts[:-1]) + "/postgres"

            try:
                # Connect to postgres database to create target database
                engine = create_engine(base_url.replace("+asyncpg", ""))

                with engine.connect() as conn:
                    # Check if database exists
                    result = conn.execute(
                        text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
                    )

                    if not result.fetchone():
                        # Create database
                        conn.execute(text("COMMIT"))  # End any transaction
                        conn.execute(text(f"CREATE DATABASE {db_name}"))
                        print(f"✅ Created database: {db_name}")
                    else:
                        print(f"ℹ️  Database already exists: {db_name}")

                engine.dispose()

            except Exception as e:
                print(f"❌ Error creating database: {e}")
                print(f"   Make sure PostgreSQL is running and credentials are correct")
                print(f"   Database URL: {base_url}")
                return False

    return True


async def test_database_connection():
    """Test the database connection."""
    try:
        async_engine = create_async_engine(get_async_database_url())

        async with async_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            if row and row[0] == 1:
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Database connection test failed")
                return False

    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False
    finally:
        await async_engine.dispose()


def setup_alembic():
    """Set up Alembic configuration."""
    from pathlib import Path
    import os

    # Update alembic.ini with correct database URL
    alembic_ini_path = Path(__file__).parent.parent / "alembic.ini"

    if alembic_ini_path.exists():
        content = alembic_ini_path.read_text()

        # Replace the sqlalchemy.url line
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('sqlalchemy.url'):
                lines[i] = f"sqlalchemy.url = {get_database_url()}"
                break

        alembic_ini_path.write_text('\n'.join(lines))
        print("✅ Updated alembic.ini with database URL")
    else:
        print("⚠️  alembic.ini not found")


async def main():
    """Main initialization function."""
    print("🚀 Initializing PresGen-Assess database...")
    print(f"📊 Database URL: {settings.database_url}")

    # Step 1: Create database if it doesn't exist
    if not await create_database_if_not_exists():
        sys.exit(1)

    # Step 2: Test connection
    if not await test_database_connection():
        sys.exit(1)

    # Step 3: Set up Alembic
    setup_alembic()

    print("\n✅ Database initialization complete!")
    print("\nNext steps:")
    print("1. Create initial migration: alembic revision --autogenerate -m 'Initial migration'")
    print("2. Apply migration: alembic upgrade head")
    print("3. Start the application: uvicorn src.service.http:app --reload")


if __name__ == "__main__":
    asyncio.run(main())