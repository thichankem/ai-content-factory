"""Structural guards for the backend layout.

These tests do not check features; they protect the shape of the codebase so a
future refactor cannot quietly re-introduce a god object, duplicate a mixin
method, hand every engine its own copy of the same helper, or break the
model/service re-export surface that the rest of the project imports from.
"""

from __future__ import annotations

import ast
import pathlib

import numpy as np
import pytest

from content_factory import models, params, pixels, services, text
from content_factory.service import ContentFactoryService

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "content_factory"

# Modules whose job is to re-export, so their size is not a smell.
REEXPORT_MODULES = {"__init__.py"}

#: A single module above this is a sign the domain should be split again.
MODULE_LINE_BUDGET = 1100

#: Declarative registries may opt into a higher ceiling by declaring it here,
#: with a comment explaining why the domain cannot be split further. Empty on
#: purpose: the two modules that once needed it — ``agent_tools.py`` (the tool
#: registry) and ``media_tools.py`` (the ffmpeg engine) — were split into
#: per-domain / per-concern modules and now live well under the default budget.
#: A future registry that genuinely cannot be split can re-add itself here.
REGISTRY_MODULES: dict[str, int] = {}

#: Helpers that were duplicated across the media engines before they were
#: single-sourced. An engine may still bind one to its own exception type, but
#: it must do so by importing the shared implementation: a module that defines
#: one of these names *without* importing the corresponding function has
#: re-grown the copy this map exists to prevent.
SHARED_MEDIA_HELPERS = {
    "_clamp01": ("params", "clamp01"),
    "_luminance": ("pixels", "luminance"),
    "_num": ("params", "number"),
    "_remap": ("pixels", "remap"),
    "_seed": ("params", "seed"),
    "_to_uint8": ("pixels", "to_uint8"),
}

#: The modules that own the shared implementations, and so may define them.
SHARED_HELPER_HOMES = {"params.py", "pixels.py"}


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


def test_no_module_is_grandfathered_over_the_default_budget() -> None:
    # ``agent_tools.py`` and ``media_tools.py`` were the only two grandfathered
    # registries. Both are now split, so every module earns the default budget.
    assert REGISTRY_MODULES == {}
    assert _line_budget(SRC / "agent_tools.py") == MODULE_LINE_BUDGET
    assert _line_budget(SRC / "media_tools.py") == MODULE_LINE_BUDGET
    assert _line_budget(SRC / "seo" / "signals.py") == MODULE_LINE_BUDGET


def test_routers_do_not_define_request_models() -> None:
    violations = []
    for path in (SRC / "api" / "routers").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                (isinstance(base, ast.Name) and base.id == "BaseModel")
                or (isinstance(base, ast.Attribute) and base.attr == "BaseModel")
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


def _shared_imports(tree: ast.Module) -> set[str]:
    """Names a module imports from the shared ``params``/``pixels`` modules."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.level == 1
            and node.module in {"params", "pixels"}
        ):
            names.update(alias.name for alias in node.names)
    return names


def test_shared_media_helpers_are_never_reimplemented() -> None:
    """``params``/``pixels`` own the coercion and pixel maths, once.

    The engines each carried a private ``_num``/``_seed``/``_luminance``/``_remap``
    copy of the same code. A module that defines one of those names again —
    without importing the shared implementation — has re-grown the drift this
    catches.
    """
    reimplemented = []
    for path in _module_files():
        if path.name in SHARED_HELPER_HOMES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = _shared_imports(tree)
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            shared = SHARED_MEDIA_HELPERS.get(node.name)
            if shared is None or shared[1] in imported:
                continue
            reimplemented.append(
                f"{path.relative_to(SRC).as_posix()}:{node.name} "
                f"-> {shared[0]}.{shared[1]}"
            )
    assert reimplemented == []


def test_params_helpers_are_shared_and_stable() -> None:
    assert params.number({"freq": "250"}, "freq", 80.0) == 250.0
    assert params.number({}, "freq", 80.0) == 80.0
    with pytest.raises(params.ParamError, match="'freq' must be a number"):
        params.number({"freq": "loud"}, "freq", 80.0)
    with pytest.raises(RuntimeError, match="must be a number"):
        params.number({"freq": None}, "freq", 80.0, error=RuntimeError)
    assert params.flag({}, "on", True) is True
    assert params.flag({"on": 0}, "on", True) is False
    assert params.seed({}) == 0
    assert params.seed({"seed": "not-a-number"}) == 0
    assert params.seed({"seed": "7"}) == 7
    assert params.clamp01(1.7) == 1.0 and params.clamp01(-0.4) == 0.0

    class _Op:
        """The shape :mod:`params` must also accept: something carrying `.params`."""

        def __init__(self, **fields: float) -> None:
            self.params = fields

    assert params.number(_Op(amount=0.25), "amount", 0.0) == 0.25
    assert params.params_of(_Op(amount=0.25)) == {"amount": 0.25}


def test_pixels_helpers_are_shared_and_stable() -> None:
    white = np.ones((2, 2, 3), dtype=np.float32)
    assert pixels.luminance(white).shape == (2, 2)
    assert float(pixels.luminance(white).max()) == pytest.approx(1.0, abs=1e-6)
    assert pixels.to_uint8(np.array([0.0, 0.5, 1.0], dtype=np.float32)).tolist() == [
        0,
        127,
        255,
    ]
    assert pixels.as_rgb(np.zeros((2, 2, 3), dtype=np.uint8)).shape == (2, 2, 3)
    with pytest.raises(pixels.PixelError, match="HxWx3"):
        pixels.as_rgb(np.zeros((2, 2), dtype=np.uint8))

    from PIL import Image

    image = Image.new("RGB", (2, 2), (10, 20, 30))
    assert pixels.rgb_array(image).shape == (2, 2, 3)
    round_tripped = pixels.to_image(pixels.rgb_array(image))
    assert round_tripped.size == (2, 2)
    # A remap that maps every output pixel to itself must be a no-op.
    yy, xx = np.mgrid[0:2, 0:2]
    straight = pixels.remap(
        np.zeros((2, 2, 3), dtype=np.uint8),
        xx.astype(np.float32),
        yy.astype(np.float32),
    )
    assert straight.shape == (2, 2, 3)


def test_catalogues_share_the_grouping_helper() -> None:
    from content_factory import catalog

    docs = {
        "b_op": {"category": "second", "description": "B", "params": {}},
        "a_op": {"category": "first", "description": "A", "params": {}},
        "c_op": {"category": "extra", "description": "C", "params": {}},
    }
    grouped = catalog.grouped_catalog(docs, ["first", "second", "empty"], presets=["p"])
    # Declared categories always appear, in order, even when empty...
    assert grouped["categories"] == ["first", "second", "empty", "extra"]
    assert grouped["ops"]["empty"] == []
    # ...and a row carries what an agent calls and how to tune it.
    assert grouped["ops"]["first"] == [
        {"name": "a_op", "description": "A", "params": {}}
    ]
    assert grouped["presets"] == ["p"]


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
