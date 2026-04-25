#!/usr/bin/env python3
"""Test database connection and verify team_locks table."""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from deerteamx.config.settings import get_settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def test_database():
    """Test database connection and check for team_locks table."""
    
    print("=" * 80)
    print("DeerTeamX Database Connection Test")
    print("=" * 80)
    
    # Get settings
    settings = get_settings()
    print(f"\n1. Loading configuration from .env.deerteamx")
    print(f"   DATABASE_URL: {settings.DATABASE_URL}")
    
    # Create async engine
    print(f"\n2. Creating async engine...")
    engine = create_async_engine(settings.DATABASE_URL)
    
    try:
        async with engine.connect() as conn:
            print(f"   ✓ Database connection successful!")
            
            # Check if team_locks table exists
            print(f"\n3. Checking for team_locks table...")
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'team_locks'
                );
            """))
            
            table_exists = result.scalar()
            
            if table_exists:
                print(f"   ✓ team_locks table EXISTS")
                
                # Get table structure
                print(f"\n4. Table structure:")
                columns_result = await conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'team_locks'
                    ORDER BY ordinal_position;
                """))
                
                print(f"   {'Column':<20} {'Type':<30} {'Nullable':<10}")
                print(f"   {'-'*20} {'-'*30} {'-'*10}")
                for row in columns_result:
                    print(f"   {row[0]:<20} {row[1]:<30} {row[2]:<10}")
                
                # Check indexes
                print(f"\n5. Indexes:")
                indexes_result = await conn.execute(text("""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = 'team_locks';
                """))
                
                for row in indexes_result:
                    print(f"   • {row[0]}")
                    
            else:
                print(f"   ✗ team_locks table does NOT exist")
                print(f"\n   You need to run the migration:")
                print(f"   alembic upgrade head")
                
    except Exception as e:
        print(f"\n   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()
    
    print(f"\n" + "=" * 80)
    print("Test completed successfully!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    result = asyncio.run(test_database())
    sys.exit(0 if result else 1)
