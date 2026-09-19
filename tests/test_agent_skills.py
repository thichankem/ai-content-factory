"""Every skill recipe is checked against the registry it claims to drive.

A skill is documentation that an agent *executes*. Documentation drifts quietly
— this repo's own ``docs/TOOLS-FOR-AGENTS.md`` still says "61 tools" while the
registry holds 110+ — but a recipe that names a tool which no longer exists, or
forgets an argument that is now required, fails at the worst moment: in an
agent's transcript, halfway through someone's video.

So the catalog is tested like code:

* every step names a real tool,
* every step fills that tool's **required** arguments (and invents no others),
* both approval gates of the pipeline appear as human gates,
* the index stays a cheap level 1 (no recipes), and
* the same catalog is served over HTTP and through the tool registry.
"""

from __future__ import annotations

import pytest

from content_factory.agent_skills import SKILLS, read_skill, skill_index, skill_names
from content_factory.agent_tools import TOOL_REGISTRY

#: Tool names that must appear in the pipeline recipe, in this order.  The order
#: is the state machine's, not a preference: approving the script before it is
#: written, or rendering before ``generating``, is rejected server-side.
PIPELINE_ORDER = [
    "create_project",
    "research_project",
    "update_script",
    "analyze_script",
    "approve_stage",
    "build_video_project",
    "generate_voiceover",
    "start_generation",
    "render_video",
    "approve_stage",
    "publish_project",
]


def _steps():
    return [(skill, step) for skill in SKILLS for step in skill.steps]


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient

    from content_factory.api import create_app
    from content_factory.config import Settings

    settings = Settings(
        store_path=str(tmp_path / "projects.json"),
        uploads_dir=str(tmp_path / "uploads"),
        media_dir=str(tmp_path / "media"),
        library_dir=str(tmp_path / "library"),
        cache_dir=str(tmp_path / "cache"),
    )
    return TestClient(create_app(settings))


def test_every_step_names_a_real_tool() -> None:
    unknown = [
        f"{skill.name}: {step.tool}"
        for skill, step in _steps()
        if step.tool not in TOOL_REGISTRY
    ]
    assert not unknown, "skills call tools that do not exist:\n" + "\n".join(unknown)


def test_every_step_fills_the_required_arguments() -> None:
    """A required argument the skill omits is a step the agent cannot run."""
    gaps = []
    for skill, step in _steps():
        spec = TOOL_REGISTRY.get(step.tool)
        if spec is None:
            continue
        missing = sorted(set(spec.required) - set(step.args))
        if missing:
            gaps.append(f"{skill.name}: {step.tool} is missing {missing}")
    assert not gaps, "skills forget required arguments:\n" + "\n".join(gaps)


def test_no_step_invents_an_argument() -> None:
    """An argument the schema does not declare would be rejected at dispatch."""
    invented = []
    for skill, step in _steps():
        spec = TOOL_REGISTRY.get(step.tool)
        if spec is None:
            continue
        extra = sorted(set(step.args) - set(spec.properties))
        if extra:
            invented.append(f"{skill.name}: {step.tool} invents {extra}")
    assert not invented, "skills pass arguments that do not exist:\n" + "\n".join(
        invented
    )


def test_steps_do_not_use_unsupported_stage_values() -> None:
    """``approve_stage`` only accepts the two real gates."""
    for skill, step in _steps():
        if step.tool != "approve_stage":
            continue
        assert step.args.get("stage") in {"'script'", "'video'"}, skill.name


def test_the_pipeline_covers_the_real_order() -> None:
    """The flagship recipe walks the state machine, gates included."""
    pipeline = read_skill("topic-to-published-video")
    assert pipeline is not None
    names = pipeline.tools()
    # Walk the recipe once, in order, so a repeated tool (approve_stage appears
    # twice: script, then video) cannot be matched twice at one position.
    cursor = 0
    for tool in PIPELINE_ORDER:
        assert tool in names[cursor:], (tool, names)
        cursor = names.index(tool, cursor) + 1
    assert len(pipeline.human_gates) == 2


def test_skills_that_approve_declare_a_human_gate() -> None:
    """If a recipe touches an approval, it must say a person owns it."""
    for skill in SKILLS:
        if any(step.tool == "approve_stage" for step in skill.steps):
            assert skill.human_gates, skill.name
            assert any("human" in line.lower() for line in skill.guardrails)


def test_guardrails_are_imperatives() -> None:
    """Every skill ships at least one hard rule; a recipe without rules drifts."""
    for skill in SKILLS:
        assert skill.guardrails, skill.name
        for line in skill.guardrails:
            assert line.strip().endswith("."), (skill.name, line)


def test_index_is_level_one_only() -> None:
    """The index is cheap: no recipes, no guardrails, no schema."""
    for entry in skill_index():
        assert "recipe" not in entry
        assert "guardrails" not in entry
        assert set(entry) == {
            "name",
            "description",
            "when_to_use",
            "steps",
            "tools",
            "requires_human",
        }
        assert entry["steps"] == len(entry["tools"])


def test_descriptions_stay_a_single_line() -> None:
    """Level 1 is a line per skill — a paragraph per skill is not an index."""
    for skill in SKILLS:
        assert "\n" not in skill.description
        assert 40 <= len(skill.description) <= 220, skill.name


def test_names_are_unique_and_lookup_is_exact() -> None:
    assert len(skill_names()) == len(set(skill_names()))
    for name in skill_names():
        assert read_skill(name) is not None
        assert read_skill(f" {name} ") is not None
    assert read_skill("no-such-skill") is None


def test_full_entry_keeps_the_recipe_in_order() -> None:
    for skill in SKILLS:
        entry = skill.manifest_entry()
        assert [step["tool"] for step in entry["recipe"]] == skill.tools()
        for step in entry["recipe"]:
            # A step with arguments must list them; a tool that takes none
            # (seo_rules, list_kbs) is allowed an empty map.
            if TOOL_REGISTRY[step["tool"]].required:
                assert step["args"], (skill.name, step["tool"])


def test_skills_are_served_over_http(client) -> None:
    """An HTTP-only agent reads the same catalog as an MCP one."""
    index = client.get("/skills").json()
    assert index["count"] == len(SKILLS)
    assert index["tools_endpoint"] == "/tools"

    name = index["skills"][0]["name"]
    body = client.get(f"/skills/{name}").json()
    assert body["recipe"] and body["guardrails"]

    missing = client.get("/skills/no-such-skill")
    assert missing.status_code == 404
    assert "no-such-skill" in missing.json()["detail"]

    assert client.get("/skills").status_code == 200


def test_skills_are_readable_through_the_tool_registry(client) -> None:
    """The tool door and the HTTP door answer with the same recipe."""
    listed = client.post("/tools/call", json={"tool": "list_skills", "args": {}}).json()
    assert listed["count"] == len(SKILLS)

    name = listed["skills"][-1]["name"]
    via_tool = client.post(
        "/tools/call", json={"tool": "read_skill", "args": {"name": name}}
    ).json()
    assert via_tool["name"] == name
    assert via_tool["recipe"] == read_skill(name).manifest_entry()["recipe"]

    bad = client.post(
        "/tools/call", json={"tool": "read_skill", "args": {"name": "nope"}}
    )
    assert bad.status_code == 422
    assert "list_skills" in bad.json()["detail"]


def test_skills_reference_tools_an_agent_can_actually_find() -> None:
    """Every tool a recipe calls is discoverable by searching for that skill.

    Otherwise the recipe and the search index disagree about the same job, and
    an agent that arrives through search never learns the steps exist.
    """
    from content_factory.agent_tools import search_tools

    for skill in SKILLS:
        found = {entry["name"] for entry in search_tools(skill.name, limit=20)}
        assert found, skill.name
