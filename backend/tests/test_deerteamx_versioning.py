"""Unit tests for DeerTeamX version management and diff engine."""

import sys
from pathlib import Path

# Ensure backend root is first in sys.path
backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root in sys.path:
    sys.path.remove(backend_root)
sys.path.insert(0, backend_root)

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from deerteamx.version.manager import VersionManager
from deerteamx.version.diff import DiffEngine


class TestVersionManager:
    """Test version management logic."""

    @pytest.mark.asyncio
    async def test_bump_version_logic(self):
        """Test semantic version incrementing."""
        assert VersionManager._bump_version("v1.0.0", "patch") == "v1.0.1"
        assert VersionManager._bump_version("v1.0.1", "minor") == "v1.1.0"
        assert VersionManager._bump_version("v1.9.9", "major") == "v2.0.0"
        assert VersionManager._bump_version("v0.0.0", "patch") == "v0.0.1"

    @pytest.mark.asyncio
    async def test_create_version_snapshot(self):
        """Test creating a new version snapshot."""
        mock_db = AsyncMock()
        manager = VersionManager(mock_db)

        config = {"roles": [{"name": "Analyst"}]}
        
        # Mock the internal _get_latest_version method
        with patch.object(manager, '_get_latest_version', return_value=None):
            version = await manager.create_version(
                team_id="team-1",
                config=config,
                user_id="user-1",
                change_type="minor",
                message="Initial setup"
            )

        assert version.version_tag == "v0.1.0"
        assert version.config_snapshot == config
        assert mock_db.add.called

    @pytest.mark.asyncio
    async def test_rollback_preparation(self):
        """Test rollback logic prepares the correct config."""
        mock_db = AsyncMock()
        manager = VersionManager(mock_db)

        target_config = {"roles": [{"name": "OldRole"}]}
        mock_version = MagicMock(version_tag="v1.0.0", config_snapshot=target_config)

        with patch.object(manager, 'get_version_detail', return_value=mock_version):
            with patch.object(manager, 'create_version') as mock_create:
                result = await manager.rollback_to_version("team-1", "v1.0.0", "user-1")
                
                assert result["target_config"] == target_config
                # Verify a new version was created to record the rollback
                assert mock_create.call_args[1]["message"] == "Rollback to v1.0.0"


class TestDiffEngine:
    """Test configuration diff calculation."""

    def test_calculate_simple_diff(self):
        """Test basic difference detection."""
        old = {"model": "gpt-3", "temp": 0.7}
        new = {"model": "gpt-4", "temp": 0.7}
        
        diff = DiffEngine.calculate_diff(old, new)
        assert "model" in diff

    def test_format_diff_for_ui(self):
        """Test diff formatting into flat list."""
        diff_result = {"roles": [{"model": "gpt-4"}]}
        changes = DiffEngine.format_diff_for_ui(diff_result)
        
        assert len(changes) > 0
        assert any("roles" in c["path"] for c in changes)

    def test_no_diff_detection(self):
        """Test that identical configs produce no diff."""
        config = {"name": "Team A"}
        diff = DiffEngine.calculate_diff(config, config)
        # Depending on jsondiff implementation, this should be empty or {}
        assert not diff or diff == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
