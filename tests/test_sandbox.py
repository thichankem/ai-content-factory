"""Path sandbox: confinement of MCP tool file access."""

from __future__ import annotations

from content_factory.sandbox import Sandbox, SandboxError


def test_resolve_allows_inside_root(tmp_path) -> None:
    root = tmp_path / "assets"
    root.mkdir()
    box = Sandbox([root])
    target = box.resolve(root / "sub" / "file.mp4")
    assert target == (root / "sub" / "file.mp4").resolve()


def test_resolve_rejects_outside_root(tmp_path) -> None:
    root = tmp_path / "assets"
    root.mkdir()
    box = Sandbox([root])
    try:
        box.resolve(tmp_path / "elsewhere" / "secret.txt")
    except SandboxError:
        return
    raise AssertionError("expected SandboxError for an escaping path")


def test_contains_returns_bool_without_raising(tmp_path) -> None:
    root = tmp_path / "assets"
    root.mkdir()
    box = Sandbox([root])
    assert box.contains(root / "ok.txt") is True
    assert box.contains(tmp_path / "no.txt") is False


def test_roots_are_resolved_absolutely(tmp_path) -> None:
    root = tmp_path / "assets"
    root.mkdir()
    box = Sandbox([root])
    assert box.roots == [root.resolve()]
