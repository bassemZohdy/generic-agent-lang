"""SKILL.md loader and skill-to-tool converter for generic-agent-lang."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml
from langchain_core.tools import BaseTool, StructuredTool

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """Parsed skill metadata and instructions."""

    name: str
    description: str
    instructions: str
    directory: Path


def parse_skill_md(file_path: Path) -> Skill:
    """Parse a SKILL.md file containing frontmatter and body."""
    text = file_path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            frontmatter_raw = parts[1]
            instructions = parts[2].strip()
            data = yaml.safe_load(frontmatter_raw) or {}
            name = str(data.get("name") or file_path.parent.name)
            description = str(data.get("description") or f"Skill from {name}")
            return Skill(
                name=name,
                description=description,
                instructions=instructions,
                directory=file_path.parent,
            )

    return Skill(
        name=file_path.parent.name,
        description=f"Skill from {file_path.parent.name}",
        instructions=text.strip(),
        directory=file_path.parent,
    )


def load_skills_from_dir(skills_dir: str | Path, prefix: str = "") -> List[BaseTool]:
    """Scan directory for skill folders containing SKILL.md and construct LangChain tools."""
    base = Path(skills_dir).expanduser()
    if not base.is_dir():
        logger.warning("Skills directory %r does not exist or is not a directory", str(skills_dir))
        return []

    tools: List[BaseTool] = []
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        skill_file = entry / "SKILL.md"
        if not skill_file.exists():
            continue

        try:
            skill = parse_skill_md(skill_file)
            tool_name = f"{prefix}{skill.name}".replace("-", "_")

            def make_skill_runner(s: Skill):
                def runner(query: str = "") -> str:
                    return (
                        f"<skill_context name='{s.name}'>\n"
                        f"{s.instructions}\n"
                        f"Query: {query}\n"
                        f"</skill_context>"
                    )
                return runner

            st = StructuredTool.from_function(
                func=make_skill_runner(skill),
                name=tool_name,
                description=skill.description,
            )
            tools.append(st)
        except Exception as err:
            logger.warning("Failed to load skill from %s: %s", entry, err)

    return tools
