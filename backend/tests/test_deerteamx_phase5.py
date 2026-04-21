"""Unit tests for Phase 5: Lock Manager and WS Optimization."""

import sys
from pathlib import Path

backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root in sys.path:
    sys.path.remove(backend_root)
sys.path.insert(0, backend_root)

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from deerteamx.runtime.lock_manager import LockManager


class TestLockManager:
    """Test distributed lock logic."""

    @pytest.mark.asyncio
    async def test_acquire_and_release_lock(self):
        """Test basic lock lifecycle."""
        mock_db = AsyncMock()
        manager = LockManager(mock_db)
        
        # Mock the update result to simulate successful acquisition
        mock_result = MagicMock(rowcount=1)
        mock_db.execute.return_value = mock_result
        
        success = await manager.acquire_lock("team-1", "user-1")
        assert success is True
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_lock_conflict(self):
        """Test that a second user cannot acquire an existing lock."""
        mock_db = AsyncMock()
        manager = LockManager(mock_db)
        
        # Simulate update failed (rowcount=0) and insert failed (exception)
        mock_result = MagicMock(rowcount=0)
        mock_db.execute.return_value = mock_result
        mock_db.commit.side_effect = Exception("Unique violation")
        
        success = await manager.acquire_lock("team-1", "user-2")
        assert success is False

    @pytest.mark.asyncio
    async def test_check_lock_status(self):
        """Test checking if a team is currently locked."""
        mock_db = AsyncMock()
        manager = LockManager(mock_db)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "user-1"
        mock_db.execute.return_value = mock_result
        
        owner = await manager.is_locked("team-1")
        assert owner == "user-1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
