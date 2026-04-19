#!/usr/bin/env python3
"""
DeerTeamX Database Setup Script

This script automates the database and user creation for DeerTeamX.
It handles:
1. Creating PostgreSQL user (if not exists)
2. Creating database (if not exists)
3. Granting necessary privileges
4. Running Alembic migrations

Usage:
    python scripts/setup_database.py [--dry-run] [--skip-migration]

Options:
    --dry-run          Show what would be done without executing
    --skip-migration   Skip running Alembic migrations after setup
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional


# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def run_command(cmd: list[str], description: str, dry_run: bool = False) -> bool:
    """Run a shell command with error handling."""
    print(f"\n🔧 {description}")
    print(f"   Command: {' '.join(cmd)}")
    
    if dry_run:
        print("   ⏭️  [DRY RUN] Skipping execution")
        return True
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.stdout:
            print(f"   ✅ Success: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        # Check if error is "already exists" (idempotent)
        if "already exists" in e.stderr.lower():
            print(f"   ℹ️  Already exists, skipping")
            return True
        print(f"   ❌ Failed: {e.stderr.strip()}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False


def check_postgres_connection() -> bool:
    """Check if PostgreSQL is accessible."""
    print("\n🔍 Checking PostgreSQL connection...")
    try:
        result = subprocess.run(
            ["sudo", "-u", "postgres", "psql", "-c", "SELECT 1;"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("   ✅ PostgreSQL is accessible")
            return True
        else:
            print(f"   ❌ PostgreSQL connection failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print("   ❌ PostgreSQL client (psql) not found")
        print("   💡 Install it: sudo apt-get install postgresql-client")
        return False
    except Exception as e:
        print(f"   ❌ Connection check failed: {e}")
        return False


def create_user(dry_run: bool = False) -> bool:
    """Create PostgreSQL user if not exists."""
    sql = """
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'deerteamx_user') THEN
            CREATE ROLE deerteamx_user WITH LOGIN PASSWORD 'deerteamx_password';
            RAISE NOTICE 'User created';
        ELSE
            RAISE NOTICE 'User already exists';
        END IF;
    END
    $$;
    """
    
    cmd = ["sudo", "-u", "postgres", "psql", "-c", sql]
    return run_command(cmd, "Creating PostgreSQL user 'deerteamx_user'", dry_run)


def create_database(dry_run: bool = False) -> bool:
    """Create database if not exists."""
    sql = """
    SELECT 'CREATE DATABASE deerteamx_db'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'deerteamx_db')\gexec
    """
    
    cmd = ["sudo", "-u", "postgres", "psql", "-c", sql]
    return run_command(cmd, "Creating database 'deerteamx_db'", dry_run)


def grant_privileges(dry_run: bool = False) -> bool:
    """Grant privileges to user."""
    commands = [
        (
            ["sudo", "-u", "postgres", "psql", "-c", 
             "GRANT ALL PRIVILEGES ON DATABASE deerteamx_db TO deerteamx_user;"],
            "Granting database privileges"
        ),
        (
            ["sudo", "-u", "postgres", "psql", "-d", "deerteamx_db", "-c",
             "GRANT ALL ON SCHEMA public TO deerteamx_user;"],
            "Granting schema privileges"
        ),
        (
            ["sudo", "-u", "postgres", "psql", "-d", "deerteamx_db", "-c",
             "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO deerteamx_user;"],
            "Setting default table privileges"
        ),
        (
            ["sudo", "-u", "postgres", "psql", "-d", "deerteamx_db", "-c",
             "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO deerteamx_user;"],
            "Setting default sequence privileges"
        ),
    ]
    
    all_success = True
    for cmd, description in commands:
        if not run_command(cmd, description, dry_run):
            all_success = False
    
    return all_success


def run_alembic_migration(dry_run: bool = False) -> bool:
    """Run Alembic migrations using uv run to ensure correct dependency versions."""
    print("\n🗄️  Running Alembic migrations...")
    
    # Load environment variables
    env_file = backend_dir / ".env.deerteamx"
    if env_file.exists():
        print(f"   📋 Loading environment from .env.deerteamx")
        env = os.environ.copy()
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env[key.strip()] = value.strip()
    else:
        print("   ⚠️  .env.deerteamx not found, using system environment")
        env = os.environ.copy()
    
    if dry_run:
        print("   ⏭️  [DRY RUN] Would run: uv run alembic upgrade head")
        return True
    
    try:
        # Use uv run to ensure correct SQLAlchemy version
        result = subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"   ✅ Migrations applied successfully")
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        print(f"      {line}")
            return True
        else:
            print(f"   ❌ Migration failed:")
            print(f"      {result.stderr}")
            return False
    except FileNotFoundError:
        print("   ❌ Alembic not found")
        print("   💡 Install it: uv add alembic")
        return False
    except Exception as e:
        print(f"   ❌ Migration error: {e}")
        return False


def verify_setup() -> bool:
    """Verify that database setup is complete."""
    print("\n🔍 Verifying database setup...")
    
    env_file = backend_dir / ".env.deerteamx"
    if not env_file.exists():
        print("   ❌ .env.deerteamx not found")
        return False
    
    # Extract DATABASE_URL
    db_url = None
    with open(env_file) as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                db_url = line.split('=', 1)[1].strip()
                break
    
    if not db_url:
        print("   ❌ DATABASE_URL not found in .env.deerteamx")
        return False
    
    # Test connection
    try:
        import asyncpg
        import asyncio
        
        async def test_connection():
            conn = await asyncpg.connect(db_url)
            await conn.close()
            return True
        
        asyncio.run(test_connection())
        print("   ✅ Database connection successful")
        return True
    except ImportError:
        print("   ⚠️  asyncpg not installed, skipping connection test")
        print("   💡 Install it: uv add asyncpg")
        return True  # Don't fail the verification
    except Exception as e:
        print(f"   ❌ Connection test failed: {e}")
        return False


def main():
    """Main setup routine."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup DeerTeamX database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--skip-migration", action="store_true", help="Skip Alembic migrations")
    args = parser.parse_args()
    
    print("=" * 70)
    print("DeerTeamX Database Setup")
    print("=" * 70)
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")
    
    # Step 1: Check PostgreSQL
    if not check_postgres_connection():
        print("\n❌ Cannot connect to PostgreSQL. Please ensure:")
        print("   1. PostgreSQL is installed and running")
        print("   2. You have sudo privileges")
        print("   3. PostgreSQL service is active: sudo systemctl status postgresql")
        return 1
    
    # Step 2: Create user
    if not create_user(args.dry_run):
        print("\n❌ Failed to create user")
        return 1
    
    # Step 3: Create database
    if not create_database(args.dry_run):
        print("\n❌ Failed to create database")
        return 1
    
    # Step 4: Grant privileges
    if not grant_privileges(args.dry_run):
        print("\n❌ Failed to grant privileges")
        return 1
    
    # Step 5: Run migrations (unless skipped)
    if not args.skip_migration:
        if not run_alembic_migration(args.dry_run):
            print("\n❌ Migration failed, but database was created")
            print("   💡 You can run migrations manually later: alembic upgrade head")
    
    # Step 6: Verify
    if not args.dry_run:
        if not verify_setup():
            print("\n⚠️  Setup completed but verification failed")
            print("   💡 Check your .env.deerteamx configuration")
    
    print("\n" + "=" * 70)
    print("✅ Database setup completed successfully!")
    print("=" * 70)
    
    if not args.dry_run:
        print("\nNext steps:")
        print("  1. Start Redis: redis-server --daemonize yes")
        print("  2. Run verification: python scripts/verify_deerteamx_integration.py")
        print("  3. Start server: uvicorn app.gateway.app:app --reload")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
