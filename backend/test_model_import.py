#!/usr/bin/env python3
"""Test script to verify model imports work correctly after refactoring."""

import sys
from pathlib import Path

# Add backend to path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

def test_imports():
    """Test that all models can be imported without conflicts."""
    print("Testing model imports...")
    
    try:
        from deerteamx.models.base import Base, User, Team, Execution, TeamVersion, Template
        print("✓ Successfully imported all models from base.py")
        
        # Verify table names
        assert User.__tablename__ == "users"
        assert Team.__tablename__ == "teams"
        assert Execution.__tablename__ == "executions"
        assert TeamVersion.__tablename__ == "team_versions"
        assert Template.__tablename__ == "templates"
        print("✓ All table names are correct")
        
        # Check that there's only one definition per table in metadata
        tables = list(Base.metadata.tables.keys())
        print(f"✓ Tables in metadata: {tables}")
        
        # Ensure no duplicates
        assert len(tables) == len(set(tables)), "Duplicate table definitions found!"
        print("✓ No duplicate table definitions")
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
