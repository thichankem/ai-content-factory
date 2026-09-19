"""An agent must be able to find a tool without reading all of them.

The manifest is the factory's whole surface — over a hundred tools with full
JSON Schemas. Dropping that into a context window to run one media job is the
same mistake as ``list_contacts`` when the agent needed ``search_contacts``: it
spends the budget it needs for the work. These tests pin the other half of the
contract:

* a job described in words finds the tool that does it,
* the manifest can be filtered, paginated and asked for in one-line form, and
* every refusal tells the caller *where to look next* — an error an agent can
  act on, not a dead end.

The invariants here are what keep the registry usable as it grows.
"""

from __future__ import annotations

import json

import pytest

from content_factory.agent_tools import (
    TOOL_MANIFEST,
    TOOL_REGISTRY,
    ToolError,
    build_tool_manifest,
    dispatch_tool,
    search_tools,
)

#: Queries phrased the way a user (or an agent's own plan) would phrase them.
JOB_QUERIES = {
    "duck the music under the narration": {"audio_mix", "duck_music"},
    "cut the video on the beat": {"music_beat_grid", "split_media", "auto_cut_to_beat"},
    "measure how loud this file is": {"media_loudness", "analyze_audio"},
    "score the title and tags for youtube": {"seo_score", "seo_score_project"},
    "look inside a media file without playing it": {"describe_media", "inspect_media"},
    "make a grid of video frames": {"media_contact_sheet", "collage_images"},
}


@pytest.fixture
def service(tmp_path):
    from content_factory.config import Settings
    from content_factory.service import ContentFactoryService

    return ContentFactoryService(
        Settings(
            store_path=str(tmp_path / "projects.json"),
            uploads_dir=str(tmp_path / "uploads"),
            media_dir=str(tmp_path / "media"),
            library_dir=str(tmp_path / "library"),
            cache_dir=str(tmp_path / "cache"),
        )
    )


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


@pytest.mark.parametrize(("query", "expected"), sorted(JOB_QUERIES.items()))
def test_a_job_in_words_finds_the_tool_that_does_it(query, expected) -> None:
    """The search is a tool-finder, not a substring filter."""
    names = {entry["name"] for entry in search_tools(query, limit=8)}
    assert names & expected, f"{query!r} -> {sorted(names)}"


def test_every_tool_is_its_own_best_match() -> None:
    """Searching a tool by name always puts it first, for all of them.

    This is the property that makes search a *replacement* for scanning the
    manifest: if any tool could be shadowed by a longer name that merely
    contains it, an agent following the index would call the wrong thing.
    """
    for spec in TOOL_REGISTRY.values():
        hits = search_tools(spec.name, limit=1)
        assert hits and hits[0]["name"] == spec.name, spec.name


def test_search_returns_compact_entries() -> None:
    """Matches carry what is needed to choose, not the whole schema."""
    hits = search_tools("audio mix", limit=3)
    assert hits
    for entry in hits:
        assert set(entry) == {"name", "description", "category", "required"}
        assert entry["name"] in TOOL_REGISTRY
        assert entry["description"].strip()


def test_search_is_honest_about_no_matches() -> None:
    """A query with nothing behind it returns nothing, not a random tool."""
    assert search_tools("zzzqqq wwwwv") == []
    assert search_tools("") == []


def test_filler_words_are_ignored() -> None:
    """A query of nothing but filler matches nothing, not the whole catalog."""
    assert search_tools("what is the best one for this")[-3:] != search_tools("")
    assert search_tools("the of and to") == []
    assert search_tools("a an the") == []


def test_short_terms_only_match_whole_words() -> None:
    """ "one" must not match ``voice_clone``: that is how noise gets in."""
    hits = {entry["name"] for entry in search_tools("one", limit=25)}
    assert "voice_clone" not in hits


def test_the_keyword_table_only_names_real_tools() -> None:
    """A synonym for a tool that does not exist is a lie waiting to ship."""
    from content_factory.agent_tools import TOOL_KEYWORDS

    assert set(TOOL_KEYWORDS) <= set(TOOL_REGISTRY)
    for phrases in TOOL_KEYWORDS.values():
        assert phrases, "an empty entry is a typo, not a synonym"
        assert all(phrase.islower() for phrase in phrases)


def test_synonyms_find_a_tool_its_name_would_not() -> None:
    """ "storyboard" appears in no tool name, yet it is how people ask for one."""
    hits = {entry["name"] for entry in search_tools("make a storyboard", limit=5)}
    assert "media_contact_sheet" in hits


def test_search_respects_the_limit() -> None:
    assert len(search_tools("media", limit=3)) == 3
    assert len(search_tools("media", limit=1)) == 1


def test_index_detail_drops_the_schemas() -> None:
    """``detail=index`` is one line per tool: the token-efficient way in."""
    index = build_tool_manifest(detail="index")
    full = build_tool_manifest()
    assert index["count"] == full["count"] == len(TOOL_MANIFEST)
    assert index["detail"] == "index"
    assert all("input_schema" not in entry for entry in index["tools"])
    assert len(json.dumps(index)) < len(json.dumps(full)) / 2


def test_manifest_filters_by_category_and_pages_honestly() -> None:
    """``total`` and ``has_more`` let a caller tell a page from the whole set."""
    page = build_tool_manifest(category="seo", limit=3)
    assert page["returned"] == 3
    assert page["total"] == len(
        [spec for spec in TOOL_REGISTRY.values() if spec.category == "seo"]
    )
    assert page["has_more"] is True
    assert {entry["category"] for entry in page["tools"]} == {"seo"}

    whole = build_tool_manifest(category="seo")
    assert whole["has_more"] is False
    assert whole["returned"] == whole["total"]


def test_manifest_query_and_category_compose() -> None:
    """Filtering twice must not resurrect tools from the other filter."""
    hits = build_tool_manifest(q="score", category="seo", detail="index")
    assert hits["tools"], "the seo category scores tools by name"
    for entry in hits["tools"]:
        assert entry["category"] == "seo"


def test_registry_tools_come_first_and_are_self_describing() -> None:
    """An agent with a small tool budget can still reach the other hundred."""
    names = [tool["name"] for tool in TOOL_MANIFEST]
    assert names[:3] == ["search_tools", "list_skills", "read_skill"]
    for tool in TOOL_MANIFEST:
        assert tool["description"].strip(), tool["name"]
        assert tool["category"].strip(), tool["name"]
        assert tool["service"].strip(), tool["name"]


def test_registry_tools_work_without_a_service() -> None:
    """Discovery answers from the registry alone, so it works on any install."""
    found = dispatch_tool(None, "search_tools", {"query": "beat", "limit": 2})
    assert len(found["tools"]) == 2
    skills = dispatch_tool(None, "list_skills", {})
    assert skills["count"] >= 5
    recipe = dispatch_tool(None, "read_skill", {"name": skills["skills"][0]["name"]})
    assert recipe["recipe"]


def test_unknown_tool_points_at_the_next_look(service) -> None:
    """A typo is recoverable: the message says how to find the real tool."""
    with pytest.raises(ToolError) as excinfo:
        dispatch_tool(service, "duck_the_music", {})
    message = str(excinfo.value)
    assert str(len(TOOL_MANIFEST)) in message
    assert "duck_music" in message or "search_tools" in message


def test_a_missing_argument_names_the_schema_route(service) -> None:
    """The refusal must ship the fix, not just the complaint."""
    with pytest.raises(ToolError) as excinfo:
        dispatch_tool(service, "cut_media", {"ref": "x"})
    message = str(excinfo.value)
    assert "end_seconds" in message
    assert "GET /tools/cut_media" in message


def test_http_manifest_is_filterable(client) -> None:
    index = client.get("/tools", params={"detail": "index", "limit": 5}).json()
    assert index["returned"] == 5
    assert index["has_more"] is True
    assert all("input_schema" not in entry for entry in index["tools"])

    one = client.get("/tools/audio_mix").json()
    assert one["name"] == "audio_mix"
    assert one["input_schema"]["type"] == "object"

    assert client.get("/tools/nope").status_code == 404
    assert client.get("/tools", params={"detail": "wat"}).status_code == 422
    assert "search_tools" in client.get("/tools").json()["usage_notes"][-2]
