"""Unit tests for DeerTeamX integration with DeerFlow."""

import sys
from pathlib import Path

# Ensure backend root is first in sys.path
backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root in sys.path:
    sys.path.remove(backend_root)
sys.path.insert(0, backend_root)

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from deerteamx.graph.builder import StaticTeamGraphBuilder
from deerteamx.importers.crewai import CrewAIImporter


class TestCrewAIImporter:
    """Test CrewAI configuration import logic."""

    def test_parse_consensus_mode_with_defaults(self):
        """Test consensus mode mapping and default parameter handling."""
        importer = CrewAIImporter()
        yaml_content = """
crew:
  name: Consensus Team
  process: consensus
roles:
  - name: Reviewer
    goal: Check code
    backstory: Expert
tasks:
  - description: Review PR
    expected_output: Report
    agent: Reviewer
"""
        config, warnings, errors = importer.parse(yaml_content)
        
        assert config["execution_mode"] == "consensus"
        assert config["consensus_params"]["threshold"] == 0.75
        assert config["consensus_params"]["max_iterations"] == 3
        assert len(errors) == 0

    def test_parse_sequential_mode(self):
        """Test sequential mode basic mapping."""
        importer = CrewAIImporter()
        yaml_content = """
crew:
  name: Simple Team
  process: sequential
roles:
  - name: Writer
    goal: Write content
    backstory: Creative
tasks:
  - description: Write blog
    expected_output: Text
    agent: Writer
"""
        config, _, _ = importer.parse(yaml_content)
        assert config["execution_mode"] == "static"
        assert config["consensus_params"] is None

    def test_slugify_conversion(self):
        """Test ID slugification logic."""
        assert CrewAIImporter._slugify("Data Analyst") == "data-analyst"
        assert CrewAIImporter._slugify("Code_Reviewer_V2") == "code_reviewer_v2"


class TestStaticTeamGraphBuilder:
    """Test static team graph construction logic."""

    @pytest.mark.asyncio
    async def test_ensure_custom_agent_exists_with_skills(self):
        """Test agent existence check and atomic skills update (Scheme A)."""
        team_config = {
            "roles": [{"role_id": "r1", "agent_name": "test-agent", "skills": ["skill-a"]}],
            "tasks": []
        }
        builder = StaticTeamGraphBuilder(team_config)

        # Mock httpx.AsyncClient responses
        mock_resp_get = MagicMock(status_code=404)
        mock_resp_post = MagicMock(status_code=201)
        mock_resp_skills = MagicMock(status_code=200)

        with patch('httpx.AsyncClient') as MockClient:
            client_instance = AsyncMock()
            client_instance.get.return_value = mock_resp_get
            client_instance.post.return_value = mock_resp_post
            client_instance.put.return_value = mock_resp_skills
            
            # Mock async context manager
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = client_instance
            MockClient.return_value = mock_cm

            await builder._ensure_custom_agent_exists("test-agent", {"skills": ["skill-a"]})

            # Verify API calls
            client_instance.post.assert_called_once()
            client_instance.put.assert_called_once()
            call_args = client_instance.put.call_args
            assert call_args[1]["json"]["skills"] == ["skill-a"]

    def test_find_entry_task_logic(self):
        """Test entry task identification based on dependencies."""
        team_config = {
            "roles": [],
            "tasks": [
                {"task_id": "t1", "dependencies": []},
                {"task_id": "t2", "dependencies": ["t1"]}
            ]
        }
        builder = StaticTeamGraphBuilder(team_config)
        assert builder._find_entry_task() == "t1"

    def test_build_role_context(self):
        """Test context building with predecessor outputs."""
        team_config = {
            "roles": [{"role_id": "r1", "name": "Role 1", "goal": "Goal 1"}],
            "tasks": [{"task_id": "t1", "dependencies": []}]
        }
        builder = StaticTeamGraphBuilder(team_config)
        
        state = {
            "role_outputs": {
                "t1": {"messages": [{"content": "Output from t1"}]}
            }
        }
        role = {"role_id": "r2", "name": "Role 2", "goal": "Goal 2"}
        
        # Manually add a dependency for testing
        builder.tasks.append({"task_id": "t2", "dependencies": ["t1"]})
        
        context = builder._build_role_context(role, state)
        assert "前置任务 [t1] 的输出" in context
        assert "Output from t1" in context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
