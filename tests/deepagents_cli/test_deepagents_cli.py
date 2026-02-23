"""
Unit tests for DeepAgents CLI configuration.

These tests verify:
1. The .deepagents/ folder structure is correct
2. AGENTS.md contains required instructions
3. doc-search skill is properly configured
4. Constraints are properly defined
"""

import pytest
from pathlib import Path


# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestDeepAgentsFolder:
    """Test the .deepagents/ folder structure."""
    
    def test_deepagents_folder_exists(self):
        """Verify .deepagents/ folder exists."""
        deepagents_dir = PROJECT_ROOT / ".deepagents"
        assert deepagents_dir.exists(), ".deepagents/ folder should exist"
        assert deepagents_dir.is_dir()
    
    def test_agents_md_exists(self):
        """Verify AGENTS.md exists in .deepagents/."""
        agents_md = PROJECT_ROOT / ".deepagents" / "AGENTS.md"
        assert agents_md.exists(), ".deepagents/AGENTS.md should exist"
    
    def test_skills_folder_exists(self):
        """Verify skills/ folder exists."""
        skills_dir = PROJECT_ROOT / ".deepagents" / "skills"
        assert skills_dir.exists(), ".deepagents/skills/ folder should exist"
        assert skills_dir.is_dir()


class TestDocSearchSkill:
    """Test the doc-search skill configuration."""
    
    @pytest.fixture
    def skill_md(self):
        """Load the SKILL.md content."""
        skill_path = PROJECT_ROOT / ".deepagents" / "skills" / "doc-search" / "SKILL.md"
        if skill_path.exists():
            return skill_path.read_text()
        return None
    
    def test_doc_search_skill_exists(self):
        """Verify doc-search skill folder exists."""
        skill_dir = PROJECT_ROOT / ".deepagents" / "skills" / "doc-search"
        assert skill_dir.exists(), "doc-search skill folder should exist"
    
    def test_skill_md_exists(self):
        """Verify SKILL.md exists in doc-search skill."""
        skill_md = PROJECT_ROOT / ".deepagents" / "skills" / "doc-search" / "SKILL.md"
        assert skill_md.exists(), "SKILL.md should exist in doc-search skill"
    
    def test_skill_has_name(self, skill_md):
        """Verify skill has a name in frontmatter."""
        assert skill_md is not None
        assert "name: doc-search" in skill_md
    
    def test_skill_has_description(self, skill_md):
        """Verify skill has a description."""
        assert skill_md is not None
        assert "description:" in skill_md
    
    def test_skill_mentions_data_folder(self, skill_md):
        """Verify skill references the data/ folder."""
        assert skill_md is not None
        assert "data/" in skill_md
    
    def test_skill_mentions_deepagents_docs(self, skill_md):
        """Verify skill mentions deepagents documentation."""
        assert skill_md is not None
        assert "deepagents" in skill_md.lower()
    
    def test_skill_mentions_langgraph_docs(self, skill_md):
        """Verify skill mentions langgraph documentation."""
        assert skill_md is not None
        assert "langgraph" in skill_md.lower()


class TestAgentsMd:
    """Test the AGENTS.md configuration."""
    
    @pytest.fixture
    def agents_md(self):
        """Load the AGENTS.md content."""
        agents_path = PROJECT_ROOT / ".deepagents" / "AGENTS.md"
        if agents_path.exists():
            return agents_path.read_text()
        return None
    
    def test_agents_md_mentions_read_only(self, agents_md):
        """Verify AGENTS.md mentions read-only constraint."""
        assert agents_md is not None
        assert "READ-ONLY" in agents_md or "read-only" in agents_md.lower()
    
    def test_agents_md_mentions_data_folder(self, agents_md):
        """Verify AGENTS.md references the data/ folder."""
        assert agents_md is not None
        assert "data/" in agents_md
    
    def test_agents_md_forbids_write_file(self, agents_md):
        """Verify AGENTS.md forbids write_file on data/."""
        assert agents_md is not None
        assert "write_file" in agents_md.lower()
    
    def test_agents_md_forbids_edit_file(self, agents_md):
        """Verify AGENTS.md forbids edit_file on data/."""
        assert agents_md is not None
        assert "edit_file" in agents_md.lower()
    
    def test_agents_md_requires_citations(self, agents_md):
        """Verify AGENTS.md requires citations."""
        assert agents_md is not None
        assert "citation" in agents_md.lower() or "cite" in agents_md.lower()


class TestConstraints:
    """Test that constraints are properly defined."""
    
    @pytest.fixture
    def skill_md(self):
        """Load the SKILL.md content."""
        skill_path = PROJECT_ROOT / ".deepagents" / "skills" / "doc-search" / "SKILL.md"
        if skill_path.exists():
            return skill_path.read_text()
        return None
    
    def test_forbids_web_search(self, skill_md):
        """Verify skill forbids web_search."""
        assert skill_md is not None
        assert "web_search" in skill_md
    
    def test_forbids_fetch_url(self, skill_md):
        """Verify skill forbids fetch_url."""
        assert skill_md is not None
        assert "fetch_url" in skill_md
    
    def test_requires_ls_or_glob(self, skill_md):
        """Verify skill requires using ls or glob to check files."""
        assert skill_md is not None
        assert "ls" in skill_md or "glob" in skill_md


class TestDataFolderStructure:
    """Test that the data folder has expected structure."""
    
    def test_data_folder_exists(self):
        """Verify data/ folder exists."""
        data_dir = PROJECT_ROOT / "data"
        assert data_dir.exists(), "data/ folder should exist"
    
    def test_deepagents_raw_md_exists(self):
        """Verify data/deepagents_raw_md/ folder exists."""
        docs_dir = PROJECT_ROOT / "data" / "deepagents_raw_md"
        assert docs_dir.exists(), "data/deepagents_raw_md/ should exist"
    
    def test_langgraph_raw_md_exists(self):
        """Verify data/langgraph_raw_md/ folder exists."""
        docs_dir = PROJECT_ROOT / "data" / "langgraph_raw_md"
        assert docs_dir.exists(), "data/langgraph_raw_md/ should exist"
    
    def test_deepagents_has_md_files(self):
        """Verify deepagents folder has markdown files."""
        docs_dir = PROJECT_ROOT / "data" / "deepagents_raw_md"
        md_files = list(docs_dir.glob("*.md"))
        assert len(md_files) > 0, "deepagents folder should have .md files"
    
    def test_langgraph_has_md_files(self):
        """Verify langgraph folder has markdown files."""
        docs_dir = PROJECT_ROOT / "data" / "langgraph_raw_md"
        md_files = list(docs_dir.glob("*.md"))
        assert len(md_files) > 0, "langgraph folder should have .md files"
