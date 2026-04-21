"""Unit tests for DeerTeamX execution engine."""

import sys
from pathlib import Path

# Ensure backend root is first in sys.path
backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root in sys.path:
    sys.path.remove(backend_root)
sys.path.insert(0, backend_root)

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from deerteamx.runtime.executor import TeamExecutor
from deerteamx.models.execution import Execution


class TestTeamExecutor:
    """Test team execution lifecycle logic."""

    @pytest.mark.asyncio
    async def test_execute_team_generates_ids(self):
        """Test that execute_team generates unique IDs and saves to DB."""
        mock_db = AsyncMock()
        executor = TeamExecutor(mock_db)

        team_config = {
            "roles": [{"role_id": "r1", "agent_name": "test-agent"}],
            "tasks": [{"task_id": "t1", "dependencies": []}]
        }

        with patch('asyncio.create_task'):
            execution_id = await executor.execute_team(
                team_id="team-1",
                team_config=team_config,
                input_data={"query": "test"},
                user_id="user-1"
            )

        # Verify ID format
        assert execution_id.startswith("exec-")
        
        # Verify DB interaction
        assert mock_db.add.called
        added_exec = mock_db.add.call_args[0][0]
        assert added_exec.team_id == "team-1"
        assert added_exec.status == "pending"
        assert added_exec.thread_id.startswith("thread-")

    @pytest.mark.asyncio
    async def test_update_status_atomic(self):
        """Test atomic status update with timestamps."""
        mock_db = AsyncMock()
        mock_db.begin.return_value.__aenter__ = AsyncMock()
        mock_db.begin.return_value.__aexit__ = AsyncMock()
        
        executor = TeamExecutor(mock_db)
        
        await executor._update_status("exec-test", "running")
        
        # Verify SQL update was constructed
        assert mock_db.execute.called

    def test_extract_token_stats(self):
        """Test token stats extraction (currently simplified)."""
        result = {"messages": []}
        stats = TeamExecutor._extract_token_stats(result)
        
        assert "total_input_tokens" in stats
        assert isinstance(stats["total_input_tokens"], int)


class TestExecutionModel:
    """Test Execution data model logic."""

    def test_to_dict_conversion(self):
        """Test model serialization to dictionary."""
        now = datetime.utcnow()
        execution = Execution(
            execution_id="exec-test",
            team_id="team-1",
            thread_id="thread-1",
            status="completed",
            created_at=now,
            total_input_tokens=100
        )
        
        data = execution.to_dict()
        
        assert data["execution_id"] == "exec-test"
        assert data["token_stats"]["total_input_tokens"] == 100
        assert "created_at" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
