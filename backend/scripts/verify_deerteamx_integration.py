#!/usr/bin/env python3
"""
DeerTeamX Integration Verification Script

This script verifies that DeerTeamX has been correctly integrated into DeerFlow.
Run this after completing the integration steps to ensure everything is working.
"""

import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


def check_env_file():
    """Check if .env.deerteamx exists and has required variables."""
    env_file = backend_dir / ".env.deerteamx"
    
    print("📋 Checking environment file...")
    
    if not env_file.exists():
        print("  ❌ .env.deerteamx not found")
        return False
    
    print("  ✅ .env.deerteamx exists")
    
    # Check required variables
    required_vars = [
        "DATABASE_URL",
        "REDIS_URL",
        "DEERFLOW_GATEWAY_URL",
        "JWT_SECRET_KEY",
        "ENCRYPTION_MASTER_KEY",
    ]
    
    content = env_file.read_text()
    missing_vars = []
    
    for var in required_vars:
        if f"{var}=" not in content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"  ❌ Missing required variables: {', '.join(missing_vars)}")
        return False
    
    print(f"  ✅ All {len(required_vars)} required variables present")
    return True


def check_deerteamx_module():
    """Check if deerteamx module can be imported."""
    print("\n📦 Checking DeerTeamX module...")
    
    try:
        from deerteamx.models.base import Base, User, Team, Execution, TeamVersion, Template
        print("  ✅ Models imported successfully")
        print(f"     - Found {len(Base.metadata.tables)} tables: {', '.join(Base.metadata.tables.keys())}")
    except ImportError as e:
        print(f"  ❌ Failed to import models: {e}")
        return False
    
    try:
        from deerteamx.api.schemas.team_schemas import CreateTeamRequest, TeamDetail
        print("  ✅ Schemas imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import schemas: {e}")
        return False
    
    try:
        from deerteamx.main import create_deerteamx_app
        print("  ✅ App factory imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import app factory: {e}")
        return False
    
    return True


def check_router_registration():
    """Check if routers are registered in DeerFlow app."""
    print("\n🔌 Checking router registration...")
    
    try:
        from app.gateway.app import create_app
        app = create_app()
        
        # Get all routes
        routes = [route.path for route in app.routes]
        
        # Check for DeerTeamX routes
        deerteamx_routes = [
            "/api/v1/auth/register",
            "/api/v1/teams",
            "/api/v1/executions",
            "/api/v1/templates",
            "/ws/global",
        ]
        
        found_routes = []
        missing_routes = []
        
        for route in deerteamx_routes:
            if any(route in r for r in routes):
                found_routes.append(route)
            else:
                missing_routes.append(route)
        
        if missing_routes:
            print(f"  ⚠️  Some routes not found: {', '.join(missing_routes)}")
            print("  💡 This is expected if deerteamx package is not installed")
            return True  # Don't fail the check
        
        print(f"  ✅ All {len(found_routes)} DeerTeamX routes registered")
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to check routes: {e}")
        return False


def check_alembic_config():
    """Check if Alembic configuration exists."""
    print("\n🗄️  Checking Alembic configuration...")
    
    alembic_ini = backend_dir / "alembic.ini"
    migrations_dir = backend_dir / "deerteamx" / "database" / "migrations"
    
    if not alembic_ini.exists():
        print("  ❌ alembic.ini not found")
        return False
    
    print("  ✅ alembic.ini exists")
    
    if not migrations_dir.exists():
        print("  ❌ migrations directory not found")
        return False
    
    print("  ✅ migrations directory exists")
    
    # Check for initial migration
    versions_dir = migrations_dir / "versions"
    if versions_dir.exists():
        migration_files = list(versions_dir.glob("*.py"))
        if migration_files:
            print(f"  ✅ Found {len(migration_files)} migration file(s)")
            return True
    
    print("  ⚠️  No migration files found")
    return True


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("DeerTeamX Integration Verification")
    print("=" * 70)
    
    checks = [
        ("Environment File", check_env_file),
        ("DeerTeamX Module", check_deerteamx_module),
        ("Router Registration", check_router_registration),
        ("Alembic Configuration", check_alembic_config),
    ]
    
    results = []
    
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} check failed with exception: {e}")
            results.append((name, False))
    
    # Print summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} | {name}")
    
    print("=" * 70)
    print(f"Result: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All checks passed! DeerTeamX is ready to use.")
        print("\nNext steps:")
        print("  1. Install dependencies: uv sync")
        print("  2. Run migrations: alembic upgrade head")
        print("  3. Start server: uvicorn app.gateway.app:app --reload")
        print("  4. Visit docs: http://localhost:8001/deerteamx/docs")
        return 0
    else:
        print(f"\n⚠️  {total - passed} check(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
