#!/usr/bin/env python3
"""Test script to verify all imports work correctly after model refactoring."""

import sys
from pathlib import Path

# Add backend to path
backend_root = Path(__file__).parent
sys.path.insert(0, str(backend_root))

def test_all_imports():
    """Test that all critical modules can be imported without errors."""
    print("=" * 60)
    print("Testing DeerTeamX imports after model refactoring")
    print("=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Import models from base
    print("\n[1/5] Testing models.base imports...")
    try:
        from deerteamx.models.base import Base, User, Team, Execution, TeamVersion, Template
        print("  ✓ Successfully imported all models from base.py")
        
        # Verify table names
        assert User.__tablename__ == "users"
        assert Team.__tablename__ == "teams"
        assert Execution.__tablename__ == "executions"
        assert TeamVersion.__tablename__ == "team_versions"
        assert Template.__tablename__ == "templates"
        print("  ✓ All table names are correct")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        tests_failed += 1
    
    # Test 2: Import from models package
    print("\n[2/5] Testing models package exports...")
    try:
        from deerteamx.models import Base, User, Team, Execution, TeamVersion, Template
        print("  ✓ Successfully imported from models package")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        tests_failed += 1
    
    # Test 3: Import executor
    print("\n[3/5] Testing runtime.executor imports...")
    try:
        from deerteamx.runtime.executor import TeamExecutor
        from deerteamx.models.base import Execution
        print("  ✓ Successfully imported TeamExecutor and Execution")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        tests_failed += 1
    
    # Test 4: Import version manager
    print("\n[4/5] Testing version.manager imports...")
    try:
        from deerteamx.version.manager import VersionManager
        from deerteamx.models.base import TeamVersion, Team
        print("  ✓ Successfully imported VersionManager and models")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        tests_failed += 1
    
    # Test 5: Import template manager
    print("\n[5/5] Testing template.manager imports...")
    try:
        from deerteamx.template.manager import TemplateManager
        from deerteamx.models.base import Template, Team
        print("  ✓ Successfully imported TemplateManager and models")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        tests_failed += 1
    
    # Test 6: Check for duplicate table definitions
    print("\n[Bonus] Checking for duplicate table definitions...")
    try:
        from deerteamx.models.base import Base
        tables = list(Base.metadata.tables.keys())
        unique_tables = set(tables)
        
        if len(tables) == len(unique_tables):
            print(f"  ✓ No duplicates found. Tables: {sorted(tables)}")
            tests_passed += 1
        else:
            duplicates = [t for t in tables if tables.count(t) > 1]
            print(f"  ✗ Found duplicate tables: {set(duplicates)}")
            tests_failed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        tests_failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {tests_passed} passed, {tests_failed} failed")
    print("=" * 60)
    
    if tests_failed == 0:
        print("\n✅ All tests passed! Models refactoring successful.")
        return True
    else:
        print(f"\n❌ {tests_failed} test(s) failed. Please review the errors above.")
        return False

if __name__ == "__main__":
    success = test_all_imports()
    sys.exit(0 if success else 1)
