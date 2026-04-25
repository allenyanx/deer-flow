"""SOUL.md 模板系统单元测试

测试模板渲染、自动选择算法和生成逻辑。
"""

import pytest
from deerteamx.graph.soul_templates import get_template, list_templates, SOUL_TEMPLATES
from deerteamx.graph.soul_auto_selector import auto_select_template
from deerteamx.services.team_service import TeamService


class TestSoulTemplates:
    """测试模板库功能"""
    
    def test_list_templates_returns_all_templates(self):
        """测试列出所有可用模板"""
        templates = list_templates()
        
        assert len(templates) == 6
        assert "default" in templates
        assert "expert_analyst" in templates
        assert "creative_creator" in templates
        assert "technical_developer" in templates
        assert "coordinator_manager" in templates
        assert "quality_assurance" in templates
    
    def test_get_template_returns_valid_template(self):
        """测试获取有效模板"""
        template = get_template("default")
        
        assert isinstance(template, str)
        assert len(template) > 0
        assert "{name}" in template
        assert "{goal}" in template
        assert "{backstory}" in template
    
    def test_get_template_raises_error_for_invalid_name(self):
        """测试获取无效模板名称时抛出异常"""
        with pytest.raises(ValueError) as exc_info:
            get_template("invalid_template")
        
        assert "Unknown template 'invalid_template'" in str(exc_info.value)
        assert "Available templates:" in str(exc_info.value)
    
    def test_all_templates_have_required_placeholders(self):
        """测试所有模板都包含必需的占位符"""
        for template_id, template in SOUL_TEMPLATES.items():
            assert "{name}" in template, f"Template {template_id} missing {{name}}"
            assert "{goal}" in template, f"Template {template_id} missing {{goal}}"
            assert "{backstory}" in template, f"Template {template_id} missing {{backstory}}"
    
    def test_template_rendering(self):
        """测试模板渲染"""
        template = get_template("default")
        
        rendered = template.format(
            name="Test Role",
            goal="Test Goal",
            backstory="Test Backstory"
        )
        
        assert "Test Role" in rendered
        assert "Test Goal" in rendered
        assert "Test Backstory" in rendered
        assert "{name}" not in rendered  # 占位符应被替换


class TestAutoSelector:
    """测试自动选择算法"""
    
    def test_auto_select_expert_analyst(self):
        """测试自动选择专家分析型模板"""
        role = {
            "name": "Data Analyst",
            "goal": "Analyze sales data and identify trends",
            "backstory": "You are a senior data scientist with expertise in statistical analysis."
        }
        
        selected = auto_select_template(role)
        assert selected == "expert_analyst"
    
    def test_auto_select_creative_creator(self):
        """测试自动选择创意创作型模板"""
        role = {
            "name": "Content Writer",
            "goal": "Create engaging marketing copy for social media",
            "backstory": "You are a creative writer specializing in digital marketing."
        }
        
        selected = auto_select_template(role)
        assert selected == "creative_creator"
    
    def test_auto_select_technical_developer(self):
        """测试自动选择技术开发型模板"""
        role = {
            "name": "Software Engineer",
            "goal": "Develop and maintain web applications",
            "backstory": "You are an experienced programmer with expertise in Python and JavaScript."
        }
        
        selected = auto_select_template(role)
        assert selected == "technical_developer"
    
    def test_auto_select_coordinator_manager(self):
        """测试自动选择协调管理型模板"""
        role = {
            "name": "Project Manager",
            "goal": "Coordinate team activities and manage project timelines",
            "backstory": "You are an experienced project manager with strong leadership skills."
        }
        
        selected = auto_select_template(role)
        assert selected == "coordinator_manager"
    
    def test_auto_select_quality_assurance(self):
        """测试自动选择质量控制型模板"""
        role = {
            "name": "QA Engineer",
            "goal": "Test software quality and validate requirements",
            "backstory": "You are a meticulous quality assurance specialist."
        }
        
        selected = auto_select_template(role)
        assert selected == "quality_assurance"
    
    def test_auto_select_default_when_no_match(self):
        """测试无匹配时使用默认模板"""
        role = {
            "name": "Generic Assistant",
            "goal": "Help users with their tasks",
            "backstory": "You are a helpful assistant."
        }
        
        selected = auto_select_template(role)
        assert selected == "default"
    
    def test_auto_select_handles_missing_fields(self):
        """测试自动选择处理缺失字段"""
        role = {}  # 空字典
        
        selected = auto_select_template(role)
        assert selected == "default"  # 应该回退到默认模板


class TestSoulGeneration:
    """测试 SOUL.md 生成逻辑"""
    
    def test_generate_with_custom_content(self):
        """测试使用自定义内容"""
        custom_content = "# My Custom Role\n\nThis is my custom prompt."
        role = {
            "name": "Custom Role",
            "goal": "Custom goal",
            "backstory": "Custom backstory",
            "soul_content": custom_content
        }
        
        result = TeamService.generate_soul_content(role)
        assert result == custom_content
    
    def test_generate_with_specified_template(self):
        """测试使用指定模板"""
        role = {
            "name": "Data Analyst",
            "goal": "Analyze data",
            "backstory": "You are a data expert.",
        }
        
        result = TeamService.generate_soul_content(
            role,
            template_name="expert_analyst"
        )
        
        assert "Expert Analyst: Data Analyst" in result
        assert "Analytical Framework" in result
    
    def test_generate_with_auto_template(self):
        """测试自动选择模板"""
        role = {
            "name": "Software Developer",
            "goal": "Write clean code",
            "backstory": "You are an experienced programmer.",
        }
        
        result = TeamService.generate_soul_content(role)
        
        # 应该自动选择 technical_developer
        assert "Technical Expert: Software Developer" in result
        assert "Development Principles" in result
    
    def test_generate_appends_skills_section(self):
        """测试追加技能章节"""
        role = {
            "name": "Developer",
            "goal": "Code",
            "backstory": "Programmer",
            "skills": ["python", "javascript", "docker"]
        }
        
        result = TeamService.generate_soul_content(role)
        
        assert "## Available Skills" in result
        assert "- `python`" in result
        assert "- `javascript`" in result
        assert "- `docker`" in result
    
    def test_generate_appends_tools_section(self):
        """测试追加工具组章节"""
        role = {
            "name": "Developer",
            "goal": "Code",
            "backstory": "Programmer",
            "tool_groups": ["bash", "file_operations"]
        }
        
        result = TeamService.generate_soul_content(role)
        
        assert "## Available Tools" in result
        assert "- `bash`" in result
        assert "- `file_operations`" in result
    
    def test_generate_appends_delegation_section(self):
        """测试追加委派章节"""
        role = {
            "name": "Manager",
            "goal": "Lead team",
            "backstory": "Team leader",
            "allow_delegation": True
        }
        
        result = TeamService.generate_soul_content(role)
        
        assert "## Delegation Authority" in result
        assert "delegate subtasks" in result
    
    def test_generate_appends_model_config(self):
        """测试追加模型配置"""
        role = {
            "name": "Developer",
            "goal": "Code",
            "backstory": "Programmer",
            "model": "gpt-4-turbo"
        }
        
        result = TeamService.generate_soul_content(role)
        
        assert "## Technical Configuration" in result
        assert "**LLM Model**: `gpt-4-turbo`" in result
    
    def test_generate_with_all_sections(self):
        """测试生成包含所有章节的完整 SOUL.md"""
        role = {
            "name": "Senior Data Scientist",
            "goal": "Analyze complex datasets and provide actionable insights",
            "backstory": "You have 10+ years of experience in machine learning and statistical analysis.",
            "skills": ["data-analysis", "ml-modeling", "visualization"],
            "tool_groups": ["python_execution", "file_operations"],
            "model": "gpt-4",
            "allow_delegation": True
        }
        
        result = TeamService.generate_soul_content(
            role,
            template_name="expert_analyst"
        )
        
        # 验证基础模板内容
        assert "Expert Analyst: Senior Data Scientist" in result
        assert "Professional Background" in result
        assert "Mission Statement" in result
        
        # 验证追加章节
        assert "## Available Skills" in result
        assert "## Available Tools" in result
        assert "## Delegation Authority" in result
        assert "## Technical Configuration" in result
        
        # 验证具体内容
        assert "- `data-analysis`" in result
        assert "- `python_execution`" in result
        assert "**LLM Model**: `gpt-4`" in result
        
        # 验证长度合理
        assert len(result) > 1000  # 完整内容应该较长
    
    def test_generate_fallback_to_default_on_invalid_template(self):
        """测试无效模板名称时回退到默认模板"""
        role = {
            "name": "Test Role",
            "goal": "Test",
            "backstory": "Test",
        }
        
        result = TeamService.generate_soul_content(
            role,
            template_name="invalid_template"
        )
        
        # 应该回退到 default 模板
        assert "# Test Role" in result
        assert "Role Definition" in result  # default 模板的特征
    
    def test_generate_handles_empty_role(self):
        """测试处理空角色配置"""
        role = {}
        
        result = TeamService.generate_soul_content(role)
        
        # 应该有默认值
        assert isinstance(result, str)
        assert len(result) > 0


class TestIntegration:
    """集成测试"""
    
    def test_full_workflow_auto_select(self):
        """测试完整工作流：自动选择 + 生成"""
        # 模拟用户创建数据分析角色
        role = {
            "name": "Market Research Analyst",
            "goal": "Conduct comprehensive market research and competitive analysis",
            "backstory": "You are a seasoned market researcher with expertise in consumer behavior analysis and trend forecasting.",
            "skills": ["market-research", "data-analysis", "report-writing"],
            "model": "gpt-4"
        }
        
        # 1. 自动选择模板
        selected_template = auto_select_template(role)
        assert selected_template == "expert_analyst"
        
        # 2. 生成 SOUL.md
        soul_content = TeamService.generate_soul_content(role)
        
        # 3. 验证结果
        assert "Expert Analyst: Market Research Analyst" in soul_content
        assert "market research" in soul_content.lower()
        assert "## Available Skills" in soul_content
        assert "- `market-research`" in soul_content
        assert "**LLM Model**: `gpt-4`" in soul_content
        
        print(f"\n✅ Generated SOUL.md ({len(soul_content)} chars)")
        print("=" * 80)
        print(soul_content[:500])  # 打印前500字符用于调试
    
    def test_full_workflow_custom_template(self):
        """测试完整工作流：指定模板 + 生成"""
        role = {
            "name": "Full Stack Developer",
            "goal": "Build scalable web applications",
            "backstory": "Experienced developer with expertise in React and Node.js.",
            "skills": ["react", "nodejs", "typescript"],
            "tool_groups": ["bash", "file_operations", "python_execution"]
        }
        
        # 显式指定模板
        soul_content = TeamService.generate_soul_content(
            role,
            template_name="technical_developer"
        )
        
        # 验证使用了指定的模板
        assert "Technical Expert: Full Stack Developer" in soul_content
        assert "Development Principles" in soul_content
        assert "Code Quality" in soul_content
        
        # 验证追加了技能和工具
        assert "- `react`" in soul_content
        assert "- `bash`" in soul_content
        
        print(f"\n✅ Generated SOUL.md with technical_developer template ({len(soul_content)} chars)")
