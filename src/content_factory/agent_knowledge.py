"""Knowledge-engine agent tools, split out of ``agent_tools.py``.

The two NotebookLM-style tools (``kb_ask``, ``kb_ingest_url``) live here so
``agent_tools.py`` stays under its line budget while the registry still exposes
them through the same manifest.
"""

from __future__ import annotations

from typing import Any, Literal

from .agent_schema import ToolSpec, _p
from .models import KBAskRequest, KBIngestUrl, KBTurn
from .workflow import _run_sync


def _h_kb_ask(service: Any, args: Any) -> Any:
    """Ask a grounded question against a knowledge base (with citations)."""
    history: list[KBTurn] = []
    for turn in args.raw().get("history", []):
        if isinstance(turn, dict):
            role: Literal["user", "assistant"] = (
                "assistant"
                if str(turn.get("role", "user")).lower() == "assistant"
                else "user"
            )
            history.append(KBTurn(role=role, content=str(turn.get("content", ""))))
    request = KBAskRequest(
        query=args.string("query"),
        top_k=args.integer("top_k", 6),
        use_vector=args.boolean("use_vector", True),
        use_keywords=args.boolean("use_keywords", True),
        rerank=args.boolean("rerank", True),
        history=history,
    )
    return _run_sync(service.ask_kb(args.ident("kb_id"), request))


def _h_kb_ingest_url(service: Any, args: Any) -> Any:
    """Ingest a web page as a knowledge-base source."""
    return service.ingest_url(
        args.ident("kb_id"),
        KBIngestUrl(url=args.string("url"), title=args.optional_string("title")),
    )


def knowledge_tool_specs() -> list[Any]:
    """Build the two knowledge tool specs."""
    return [
        ToolSpec(
            "kb_ask",
            "NotebookLM-style grounded Q&A: answer from a KB with [n] citations.",
            "research",
            "ask_kb",
            _h_kb_ask,
            {
                "kb_id": _p("string", "Knowledge base id."),
                "query": _p("string", "The question to answer from the KB sources."),
                "top_k": _p(
                    "integer", "How many source chunks to ground on (default 6)."
                ),
                "history": _p(
                    "array",
                    "Optional prior turns [{role, content}] for follow-up context.",
                ),
            },
            ("kb_id", "query"),
        ),
        ToolSpec(
            "kb_ingest_url",
            "Ingest a web page as a knowledge-base source (NotebookLM web source).",
            "research",
            "ingest_url",
            _h_kb_ingest_url,
            {
                "kb_id": _p("string", "Knowledge base id."),
                "url": _p("string", "Public HTTPS URL of the page to ingest."),
                "title": _p(
                    "string", "Optional title; derived from the URL if omitted."
                ),
            },
            ("kb_id", "url"),
        ),
    ]
