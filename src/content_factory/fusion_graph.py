"""Fusion graph: validate and evaluate a compositing DAG.

Mirrors ``docs/NLE-STUDIO-FULL-ARCHITECTURE.md`` §4.1-C. The graph is validated
*before* it is evaluated — a cycle or a socket wired to a missing node is a
configuration error, and telling the operator beats rendering a black frame.

Evaluation is a topological walk: each node transforms its inputs, a merge node
composites its two inputs, and an output node collects the result. The image
work is delegated to :mod:`content_factory.photo_compositor`, so both engines
share one blending vocabulary instead of two.
"""

from __future__ import annotations

from typing import Any

from PIL import Image

from . import photo_compositor

__all__ = [
    "FusionGraphError",
    "evaluate_graph",
    "graph_edges",
    "topological_order",
    "validate_graph",
]


class FusionGraphError(ValueError):
    """Raised when a graph is malformed or cannot be evaluated."""


def graph_edges(graph: dict[str, Any]) -> list[tuple[str, str]]:
    """Collect ``(source_id, target_id)`` wires from every socket.

    A socket records ``"node_id:socket_name"``, so only the part before the
    colon names the node the wire comes from.
    """
    wires: list[tuple[str, str]] = []
    for node in graph.get("nodes", []) or []:
        target = str(node.get("id"))
        for socket in node.get("inputs", []) or []:
            connected = socket.get("connected_to")
            if not connected:
                continue
            wires.append((str(connected).split(":")[0], target))
    return wires


def topological_order(
    nodes: list[dict[str, Any]], edges: list[tuple[str, str]]
) -> tuple[list[str], list[str]]:
    """Return ``(order, blocked_ids)`` for the graph's nodes.

    Order is deterministic: ready nodes are taken in list order, so the same
    graph always evaluates the same way. Nodes left over because they sit in a
    cycle come back as blocked, which is what the validator reports.
    """
    position = {str(node["id"]): index for index, node in enumerate(nodes)}
    dependencies = {
        node_id: {source for source, target in edges if target == node_id}
        for node_id in position
    }
    order: list[str] = []
    remaining = set(position)
    while remaining:
        ready = [
            node_id
            for node_id in remaining
            if not (set(dependencies[node_id]) & remaining)
        ]
        if not ready:
            break
        ready.sort(key=lambda node_id: position[node_id])
        order.extend(ready)
        remaining -= set(ready)
    return order, sorted(remaining)


def validate_graph(graph: dict[str, Any]) -> dict[str, Any]:
    """Check a graph before rendering: cycles, dangling wires, missing output."""
    nodes = graph.get("nodes", []) or []
    edges = graph_edges(graph)
    issues: list[str] = []

    if not nodes:
        issues.append("The graph has no nodes.")
    ids = [str(node.get("id")) for node in nodes]
    if len(set(ids)) != len(ids):
        issues.append("Two nodes share the same id.")

    known = set(ids)
    for source, target in edges:
        if source not in known:
            issues.append(f"A wire starts at unknown node '{source}'.")
        if target not in known:
            issues.append(f"A socket points at missing node '{target}'.")

    _, blocked = topological_order([{"id": node_id} for node_id in ids], edges)
    for node_id in blocked:
        issues.append(f"Node '{node_id}' is in a cycle and cannot run.")

    if not any(node.get("node_type") == "output" for node in nodes):
        issues.append("The graph has no MediaOut node to write a result from.")

    order, _ = topological_order([{"id": node_id} for node_id in ids], edges)
    return {
        "ready": not issues,
        "issues": issues,
        "node_count": len(nodes),
        "order": order,
    }


def evaluate_graph(
    graph: dict[str, Any], sources: dict[str, Image.Image], width: int, height: int
) -> dict[str, Any]:
    """Evaluate a validated graph and return ``(image, warnings, executed)``.

    Each node reads its wired inputs, applies its operation and stores its
    result; a merge node composites its two inputs with the blend operator the
    operator chose. Nodes that produce nothing usable are skipped and reported,
    so one bad asset does not fail the whole composite.
    """
    report = validate_graph(graph)
    if not report["ready"]:
        raise FusionGraphError("; ".join(report["issues"]))

    nodes = {str(node["id"]): node for node in graph.get("nodes", []) or []}
    edges = graph_edges(graph)
    order, _ = topological_order(list(nodes.values()), edges)

    frames: dict[str, Image.Image] = {}
    cache_hits = 0
    warnings: list[str] = []
    executed: list[str] = []

    for node_id in order:
        node = nodes[node_id]
        if not node.get("is_active", True):
            warnings.append(f"Node '{node_id}' is inactive and was skipped.")
            continue
        if node.get("is_cached"):
            cache_hits += 1

        kind = str(node.get("node_type", "effect"))
        if kind == "output":
            continue

        if kind == "input":
            asset = str(node.get("params", {}).get("asset_id", ""))
            frame = sources.get(asset) or next(iter(sources.values()), None)
            if frame is None:
                warnings.append(f"Input '{node_id}' has no source image; using black.")
                frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            frames[node_id] = frame
            executed.append(node_id)
            continue

        incoming = [source for source, target in edges if target == node_id]
        inputs = [frames[source_id] for source_id in incoming if source_id in frames]
        frames[node_id] = _evaluate_node(node, inputs, width, height)
        executed.append(node_id)

    result = next(
        (frames[node_id] for node_id in reversed(order) if node_id in frames),
        Image.new("RGBA", (width, height), (0, 0, 0, 0)),
    )
    return {
        "image": result,
        "warnings": warnings,
        "executed": executed,
        "cache_hits": cache_hits,
    }


def _evaluate_node(
    node: dict[str, Any], inputs: list[Image.Image], width: int, height: int
) -> Image.Image:
    """Render one node given its resolved inputs."""
    node_type = str(node.get("node_type", "effect"))
    params = node.get("params", {}) or {}
    if node_type == "input" or not inputs:
        return Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if node_type == "merge" and len(inputs) >= 2:
        return photo_compositor.blend_images(
            inputs[0], inputs[1], str(params.get("operator", "Over")).lower()
        )
    return inputs[0]
