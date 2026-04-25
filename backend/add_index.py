#!/usr/bin/env python3
"""Add missing index for team_locks table."""

import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from deerteamx.config.settings import get_settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def add_index():
    """Add idx_team_locks_expires_at index."""
    
    print("Adding index to team_locks table...")
    
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    
    try:
        async with engine.connect() as conn:
            # Create index
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_team_locks_expires_at 
                ON team_locks (expires_at);
            """))
            
            await conn.commit()
            print("✓ Index created successfully!")
            
            # Verify
            result = await conn.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'team_locks'
                ORDER BY indexname;
            """))
            
            print("\nCurrent indexes on team_locks:")
            for row in result:
                print(f"  • {row[0]}")
                
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()
    
    return True


if __name__ == "__main__":
    result = asyncio.run(add_index())
    sys.exit(0 if result else 1)
