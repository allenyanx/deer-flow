"""Test agent_name normalization and soul_content field."""

import pytest
from deerteamx.services.team_service import TeamService


class TestAgentNameNormalization:
    """Test _normalize_agent_name method."""
    
    def test_normalize_with_underscores(self):
        """Test normalization of underscores to hyphens."""
        assert TeamService._normalize_agent_name("code_reviewer") == "code-reviewer"
    
    def test_normalize_with_spaces(self):
        """Test normalization of spaces to hyphens."""
        assert TeamService._normalize_agent_name("Data Analyst") == "data-analyst"
    
    def test_normalize_with_mixed_case(self):
        """Test normalization of mixed case to lowercase."""
        assert TeamService._normalize_agent_name("CodeScanner_V1") == "codescanner-v1"
    
    def test_normalize_already_valid(self):
        """Test that already valid names remain unchanged."""
        assert TeamService._normalize_agent_name("code-scanner-v1") == "code-scanner-v1"
    
    def test_normalize_special_characters(self):
        """Test removal of special characters."""
        assert TeamService._normalize_agent_name("code@reviewer#v1") == "codereviewerv1"
    
    def test_normalize_multiple_hyphens(self):
        """Test collapsing multiple hyphens."""
        assert TeamService._normalize_agent_name("code---reviewer") == "code-reviewer"
    
    def test_normalize_leading_trailing_hyphens(self):
        """Test stripping leading and trailing hyphens."""
        assert TeamService._normalize_agent_name("-code-reviewer-") == "code-reviewer"
    
    def test_normalize_complex_case(self):
        """Test complex normalization scenario."""
        result = TeamService._normalize_agent_name("Senior_Code Reviewer @V2.0!")
        assert result == "senior-code-reviewer-v20"


class TestSoulContentField:
    """Test soul_content field in RoleConfig schema."""
    
    def test_role_config_accepts_soul_content(self):
        """Test that RoleConfig accepts soul_content field."""
        from deerteamx.api.schemas.team_schemas import RoleConfig
        
        role = RoleConfig(
            role_id="test-role",
            agent_name="test-agent",
            name="Test Agent",
            goal="Test goal",
            soul_content="# Test Agent\n\nThis is a test."
        )
        
        assert role.soul_content == "# Test Agent\n\nThis is a test."
    
    def test_role_config_soul_content_optional(self):
        """Test that soul_content is optional."""
        from deerteamx.api.schemas.team_schemas import RoleConfig
        
        role = RoleConfig(
            role_id="test-role",
            agent_name="test-agent",
            name="Test Agent",
            goal="Test goal"
        )
        
        assert role.soul_content is None
    
    def test_role_config_rejects_invalid_agent_name(self):
        """Test that invalid agent_name is rejected by Pydantic validation."""
        from deerteamx.api.schemas.team_schemas import RoleConfig
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            RoleConfig(
                role_id="test-role",
                agent_name="Invalid_Agent_Name",  # Contains uppercase and underscore
                name="Test Agent",
                goal="Test goal"
            )
        
        # Check that validation error mentions the pattern
        assert "agent_name" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
