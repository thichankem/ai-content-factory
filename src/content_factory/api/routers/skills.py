"""Skill catalog endpoints: the recipes an agent follows, level 1 and level 2.

The tools list *what* can be done; these endpoints say *how* a job is done, in
order, with the arguments each step needs and the gates a human owns.  Two
levels on purpose — an agent pre-loads the index, then reads one body:

* ``GET /skills`` — name, purpose, tools, step count (cheap to keep in context).
* ``GET /skills/{name}`` — the full recipe with guardrails.

Both read ``agent_skills``, the same catalog the ``list_skills`` / ``read_skill``
tools serve, and the one ``tests/test_agent_skills.py`` checks against the real
tool registry.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ...agent_skills import SKILLS, read_skill, skill_index
from ...service import ContentFactoryService


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.get("/skills")
    def skills_index() -> dict[str, Any]:
        """The skill index: choose a recipe without loading every body."""
        return {
            "count": len(SKILLS),
            "endpoint": "/skills/{name}",
            "tools_endpoint": "/tools",
            "skills": skill_index(),
        }

    @router.get("/skills/{name}")
    def skill_detail(name: str) -> dict[str, Any]:
        """One full recipe: ordered steps, arguments, gates and guardrails."""
        skill = read_skill(name)
        if skill is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Unknown skill '{name}'. GET /skills names the {len(SKILLS)} "
                    "available."
                ),
            )
        return skill.manifest_entry()

    return router
