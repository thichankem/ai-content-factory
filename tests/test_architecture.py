"""Structural guards for the backend layout.

These tests do not check features; they protect the shape of the codebase so a
future refactor cannot quietly re-introduce a god object, duplicate a mixin
method, or break the model/service re-export surface that the rest of the
project imports from.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from content_factory import models, services, text
from content_factory.service import ContentFactoryService

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "content_factory"

# Modules whose job is to re-export, so their size is not a smell.
REEXPORT_MODULES = {"__init__.py"}

#: A single module above this is a sign the domain should be split again.
MODULE_LINE_BUDGET = 1100

#: Declarative registries get a higher ceiling, and must declare it here: the
#: shape is one readable entry per capability (tool name, description, JSON
#: schema, handler), which is documentation rather than logic. The ceiling is
#: still enforced, so a registry cannot grow without bound either.
REGISTRY_MODULES = {
    "agent_tools.py": 1900,
    "media_tools.py": 1400,
}


def _module_files() -> list[pathlib.Path]:
    return sorted(path for path in SRC.rglob("*.py") if path.name != "__init__.py")


def _line_budget(path: pathlib.Path) -> int:
    return REGISTRY_MODULES.get(path.relative_to(SRC).as_posix(), MODULE_LINE_BUDGET)


def _classes_in(path: pathlib.Path) -> dict[str, list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: dict[str, list[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        found[node.name] = [
            child.name
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
    return found


def test_no_module_exceeds_the_line_budget() -> None:
    oversized = {}
    for path in _module_files():
        length = len(path.read_text(encoding="utf-8").splitlines())
        if length > _line_budget(path):
            oversized[str(path.relative_to(SRC))] = length
    assert oversized == {}, f"split these modules: {oversized}"


def test_registry_budgets_are_path_specific() -> None:
    assert _line_budget(SRC / "agent_tools.py") == 1900
    assert _line_budget(SRC / "services" / "agent_tools.py") == MODULE_LINE_BUDGET
    assert _line_budget(SRC / "seo" / "signals.py") == MODULE_LINE_BUDGET


def test_routers_do_not_define_request_models() -> None:
    violations = []
    for path in (SRC / "api" / "routers").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                isinstance(base, ast.Name)
                and base.id == "BaseModel"
                or isinstance(base, ast.Attribute)
                and base.attr == "BaseModel"
                for base in node.bases
            ):
                violations.append(f"{path.name}:{node.name}")
    assert violations == []


def test_service_is_composed_from_disjoint_mixins() -> None:
    owners: dict[str, list[str]] = {}
    for path in sorted((SRC / "services").glob("*.py")):
        if path.name in {"__init__.py", "errors.py"}:
            continue
        for klass, methods in _classes_in(path).items():
            for method in methods:
                owners.setdefault(method, []).append(klass)
    duplicated = {name: classes for name, classes in owners.items() if len(classes) > 1}
    assert duplicated == {}, f"mixins define the same method twice: {duplicated}"
    assert len(owners) > 130, "the service layers lost methods"


def test_every_mixin_method_is_reachable_on_the_service() -> None:
    service = ContentFactoryService
    missing: list[str] = []
    for path in sorted((SRC / "services").glob("*.py")):
        if path.name in {"__init__.py", "errors.py"}:
            continue
        for klass, methods in _classes_in(path).items():
            if klass not in {base.__name__ for base in service.__mro__}:
                continue
            missing.extend(
                f"{klass}.{name}" for name in methods if not hasattr(service, name)
            )
    assert missing == []


def test_public_service_api_is_stable() -> None:
    """The names the HTTP layer and the agent tools build on."""
    required = {
        "approve",
        "build_video_project",
        "create_project",
        "generate_campaign",
        "generate_voiceover",
        "get_project",
        "ingest_text",
        "list_projects",
        "render_plan",
        "render_video",
        "retrieve_kb",
        "run_workflow",
        "timeline_report",
        "update_script",
    }
    missing = sorted(
        name for name in required if not hasattr(ContentFactoryService, name)
    )
    assert missing == []


def test_models_package_reexports_the_whole_domain() -> None:
    declared = set(models.__all__)
    assert {"Project", "VideoProject", "KnowledgeBase", "Workflow"} <= declared
    for name in declared:
        assert getattr(models, name, None) is not None, name
    # The domain is split by concern, not dumped in one module.
    assert len(list((SRC / "models").glob("*.py"))) >= 10


def test_text_helpers_are_shared_and_stable() -> None:
    assert text.normalize_title("The Titanic!") == "thetitanic"
    assert text.slugify("The Titanic!") == "the-titanic"
    assert text.tokenize("The Titanic sank", min_length=2, stopwords={"the"}) == [
        "titanic",
        "sank",
    ]
    assert text.word_tokens("Chiến dịch Điện Biên Phủ") == [
        "chiến",
        "dịch",
        "điện",
        "biên",
        "phủ",
    ]


@pytest.mark.parametrize("module", sorted(services.__all__))
def test_services_all_names_resolve(module: str) -> None:
    assert getattr(services, module) is not None
