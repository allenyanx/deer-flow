#!/usr/bin/env python3
"""
DeerTeamX Database Initialization Script

This script provides a unified entry point for initializing the DeerTeamX database.
It wraps the setup_database.py logic and adds additional checks and user-friendly output.

Usage:
    python scripts/init_db.py [--dry-run] [--skip-migration] [--reset]

Options:
    --dry-run          Show what would be done without executing
    --skip-migration   Skip running Alembic migrations after setup
    --reset            Drop all tables and re-create them (DANGEROUS!)
"""

import os
import sys
import subprocess
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def print_banner():
    """Print initialization banner."""
    print("\n" + "=" * 70)
    print("  🦌 DeerTeamX Database Initialization")
    print("=" * 70)
    print(f"  Backend Directory: {backend_dir}")
    print(f"  Environment File:  {backend_dir / '.env.deerteamx'}")
    print("=" * 70 + "\n")


def check_env_file():
    """Check if .env.deerteamx exists."""
    env_file = backend_dir / ".env.deerteamx"
    if not env_file.exists():
        print("❌ .env.deerteamx not found!")
        print("💡 Please copy .env.deerteamx.example to .env.deerteamx and configure it:")
        print(f"   cp {backend_dir / '.env.deerteamx.example'} {env_file}")
        return False
    
    # Check if DATABASE_URL is configured
    with open(env_file) as f:
        content = f.read()
        if "DATABASE_URL=" not in content or "your_secure_password" in content:
            print("⚠️  WARNING: DATABASE_URL seems to be using default/placeholder values.")
            print("   Please update .env.deerteamx with your actual database credentials.\n")
    
    return True


def run_setup_script(dry_run: bool = False, skip_migration: bool = False):
    """Run the main setup_database.py script."""
    cmd = [sys.executable, str(backend_dir / "scripts" / "setup_database.py")]
    if dry_run:
        cmd.append("--dry-run")
    if skip_migration:
        cmd.append("--skip-migration")
    
    print("🚀 Starting database setup process...")
    try:
        result = subprocess.run(cmd, cwd=backend_dir, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Database setup failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"\n❌ Error running setup script: {e}")
        return False


def reset_database():
    """Drop all tables and re-create them."""
    print("\n⚠️  DANGER: You are about to RESET the database!")
    print("   This will DELETE ALL DATA in the DeerTeamX database.")
    confirm = input("   Type 'YES' to confirm: ")
    
    if confirm != "YES":
        print("   ⏭️  Reset cancelled.")
        return False
    
    print("   🗑️  Dropping all tables...")
    try:
        from deerteamx.database.session import engine
        from deerteamx.models.base import Base
        
        import asyncio
        
        async def drop_tables():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        
        asyncio.run(drop_tables())
        print("   ✅ All tables dropped.")
        
        # Re-run migrations
        print("   🔄 Re-running migrations...")
        return run_setup_script(skip_migration=False)
        
    except Exception as e:
        print(f"   ❌ Reset failed: {e}")
        return False


def main():
    """Main initialization routine."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize DeerTeamX database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--skip-migration", action="store_true", help="Skip Alembic migrations")
    parser.add_argument("--reset", action="store_true", help="Reset database (drop all tables)")
    args = parser.parse_args()
    
    print_banner()
    
    # Step 0: Check environment file
    if not check_env_file():
        return 1
    
    # Step 1: Handle reset if requested
    if args.reset:
        if not reset_database():
            return 1
        print("\n✅ Database reset completed successfully!")
        return 0
    
    # Step 2: Run standard setup
    if not run_setup_script(args.dry_run, args.skip_migration):
        return 1
    
    print("\n" + "=" * 70)
    print("✅ Database initialization completed successfully!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Verify integration: python scripts/verify_deerteamx_integration.py")
    print("  2. Start server: uvicorn deerteamx.main:app --reload")
    print("  3. Access API docs: http://localhost:8000/docs")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
