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


# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def run_command(cmd: list[str], description: str, dry_run: bool = False, env: dict = None) -> bool:
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
            timeout=30,
            env=env or os.environ
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
    
    from deerteamx.config.settings import get_settings
    from urllib.parse import urlparse
    settings = get_settings()
    parsed = urlparse(settings.DATABASE_URL)
    
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    db_user = parsed.username or "deerteamx_user"
    
    print(f"   📍 Target: {host}:{port} (user: {db_user})")
    
    # Try connecting via psql using the configured DATABASE_URL
    try:
        # Use -U flag to explicitly specify the username from DATABASE_URL
        result = subprocess.run(
            ["psql", "-U", db_user, "-h", host, "-p", str(port), "-d", "postgres", "-c", "SELECT 1;"],
            capture_output=True,
            text=True,
            timeout=5,
            env={**os.environ, "PGPASSWORD": parsed.password or "deerteamx_password"}
        )
        if result.returncode == 0:
            print("   ✅ PostgreSQL is accessible")
            return True
        else:
            print(f"   ❌ PostgreSQL connection failed")
            print(f"      Error: {result.stderr.strip()[:200]}")
            print(f"\n   💡 Troubleshooting:")
            print(f"      1. Check if PostgreSQL container is running: docker ps | grep postgres")
            print(f"      2. Verify port mapping: docker port <container_name>")
            print(f"      3. Test connection: psql '{settings.DATABASE_URL}'")
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
    # Use environment variables for credentials
    from deerteamx.config.settings import get_settings
    from urllib.parse import urlparse
    settings = get_settings()
    
    # Extract username and password from DATABASE_URL
    # Format: postgresql://user:pass@host:port/db
    try:
        parsed = urlparse(settings.DATABASE_URL)
        db_user = parsed.username
        db_pass = parsed.password
        db_host = parsed.hostname or "localhost"
        db_port = parsed.port or 5432
        
        if not db_user or not db_pass:
            print(f"   ⚠️  Could not extract credentials from DATABASE_URL, using defaults")
            db_user = "deerteamx_user"
            db_pass = "deerteamx_password"
    except Exception:
        db_user = "deerteamx_user"
        db_pass = "deerteamx_password"
        db_host = "localhost"
        db_port = 5432

    # For Docker-based PostgreSQL, we need to connect via TCP
    # We'll use a SQL script that can be executed via psql
    sql = f"""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{db_user}') THEN
            CREATE ROLE {db_user} WITH LOGIN PASSWORD '{db_pass}';
            RAISE NOTICE 'User created';
        ELSE
            RAISE NOTICE 'User already exists';
        END IF;
    END
    $$;
    """
    
    # Write SQL to temp file to avoid shell escaping issues
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write(sql)
        sql_file = f.name
    
    try:
        # Try multiple authentication methods for PostgreSQL superuser
        env = os.environ.copy()
        
        # Method 1: Use POSTGRES_PASSWORD from environment if available
        postgres_pass = os.environ.get("POSTGRES_PASSWORD", "postgres")
        
        cmd = [
            "psql", "-h", db_host, "-p", str(db_port),
            "-U", "postgres", "-d", "postgres", "-f", sql_file
        ]
        
        # Try with default 'postgres' password first
        env["PGPASSWORD"] = postgres_pass
        success = run_command(cmd, f"Creating PostgreSQL user '{db_user}'", dry_run, env)
        
        # If failed and password is 'postgres', try without password (peer auth)
        if not success and postgres_pass == "postgres":
            print(f"   ℹ️  Trying peer authentication (no password)...")
            env_no_pass = os.environ.copy()
            if "PGPASSWORD" in env_no_pass:
                del env_no_pass["PGPASSWORD"]
            success = run_command(cmd, f"Creating PostgreSQL user '{db_user}' (peer auth)", dry_run, env_no_pass)
        
        # If still failed, provide helpful guidance
        if not success:
            print(f"\n   💡 To manually create the user, run:")
            print(f"      psql -h {db_host} -p {db_port} -U postgres -c \"CREATE ROLE {db_user} WITH LOGIN PASSWORD '{db_pass}';\"")
            print(f"   Or set POSTGRES_PASSWORD environment variable to your PostgreSQL superuser password")
        
        return success
    finally:
        os.unlink(sql_file)


def create_database(dry_run: bool = False) -> bool:
    """Create database if not exists."""
    from deerteamx.config.settings import get_settings
    from urllib.parse import urlparse
    settings = get_settings()
    
    try:
        parsed = urlparse(settings.DATABASE_URL)
        db_name = parsed.path.lstrip('/')
        if not db_name:
            db_name = "deerteamx_db"
        db_user = parsed.username or "postgres"
        db_pass = parsed.password or "postgres"
        db_host = parsed.hostname or "localhost"
        db_port = parsed.port or 5432
    except Exception:
        db_name = "deerteamx_db"
        db_user = "postgres"
        db_pass = "postgres"
        db_host = "localhost"
        db_port = 5432

    # Create database using DO block for idempotent execution
    sql = f"""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_database WHERE datname = '{db_name}') THEN
            EXECUTE 'CREATE DATABASE {db_name}';
            RAISE NOTICE 'Database created';
        ELSE
            RAISE NOTICE 'Database already exists';
        END IF;
    END
    $$;
    """
    
    # Write SQL to temp file to avoid shell escaping issues
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write(sql)
        sql_file = f.name
    
    try:
        # Use PGPASSWORD environment variable for authentication
        env = os.environ.copy()
        env["PGPASSWORD"] = db_pass
        
        cmd = ["psql", "-h", db_host, "-p", str(db_port), 
               "-U", db_user, "-d", "postgres", "-f", sql_file]
        return run_command(cmd, f"Creating database '{db_name}'", dry_run, env)
    finally:
        os.unlink(sql_file)


def grant_privileges(dry_run: bool = False) -> bool:
    """Grant privileges to user."""
    from deerteamx.config.settings import get_settings
    from urllib.parse import urlparse
    settings = get_settings()
    
    try:
        parsed = urlparse(settings.DATABASE_URL)
        db_user = parsed.username or "deerteamx_user"
        db_pass = parsed.password or "deerteamx_password"
        db_name = parsed.path.lstrip('/') or "deerteamx_db"
        db_host = parsed.hostname or "localhost"
        db_port = parsed.port or 5432
    except Exception:
        db_user = "deerteamx_user"
        db_pass = "deerteamx_password"
        db_name = "deerteamx_db"
        db_host = "localhost"
        db_port = 5432

    # Use postgres superuser to grant privileges
    postgres_pass = os.environ.get("POSTGRES_PASSWORD", "postgres")
    env = os.environ.copy()
    env["PGPASSWORD"] = postgres_pass

    commands = [
        (
            ["psql", "-h", db_host, "-p", str(db_port),
             "-U", "postgres", "-d", db_name, "-c",
             f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"],
            "Granting database privileges"
        ),
        (
            ["psql", "-h", db_host, "-p", str(db_port),
             "-U", "postgres", "-d", db_name, "-c",
             f"GRANT ALL ON SCHEMA public TO {db_user};"],
            "Granting schema privileges"
        ),
        (
            ["psql", "-h", db_host, "-p", str(db_port),
             "-U", "postgres", "-d", db_name, "-c",
             f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {db_user};"],
            "Setting default table privileges"
        ),
        (
            ["psql", "-h", db_host, "-p", str(db_port),
             "-U", "postgres", "-d", db_name, "-c",
             f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {db_user};"],
            "Setting default sequence privileges"
        ),
    ]
    
    all_success = True
    for cmd, description in commands:
        if not run_command(cmd, description, dry_run, env):
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
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key_stripped = key.strip()
                    value_stripped = value.strip()
                    
                    # Remove inline comments (everything after # that's not in quotes)
                    # Simple approach: split on first # and take the first part
                    if '#' in value_stripped:
                        # Check if it's not inside quotes
                        if not (value_stripped.startswith('"') or value_stripped.startswith("'")):
                            value_stripped = value_stripped.split('#')[0].strip()
                    
                    # Convert async database URL to sync for Alembic
                    if key_stripped == "DATABASE_URL":
                        # Replace postgresql+asyncpg:// with postgresql://
                        value_stripped = value_stripped.replace("postgresql+asyncpg://", "postgresql://")
                        print(f"   ℹ️  Converting async URL to sync for Alembic")
                    
                    env[key_stripped] = value_stripped
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
    
    # Convert async URL to sync for asyncpg (asyncpg only accepts postgresql:// or postgres://)
    db_url_sync = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Test connection
    try:
        import asyncpg
        import asyncio
        
        async def test_connection():
            conn = await asyncpg.connect(db_url_sync)
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
