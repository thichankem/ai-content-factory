# Antigravity AI Agent Rules

Rules and behavioral guidelines for Google Antigravity (AGY) and vision-enabled AI agents operating in this repository.

## 👁️ Multimodal AI Vision Capabilities
- **Leverage Native Vision**: As Antigravity, you possess true multimodal AI vision. Always visually inspect generated preview frames, thumbnails, and contact sheets using `view_file` on `.jpg`/`.png` files rather than relying solely on raw text numbers.
- **Visual Gate 2 Review**: Before approving video production or marking a visual task complete, extract keyframes and inspect typography, HUD safe margins (80% Title / 90% Action / TikTok 9:16 exclusion zones), color contrast, and subtitle bounding boxes.
- **Aesthetic Excellence**: Strive for cinematic, rich aesthetics with deep blacks, vibrant contrast, smooth transitions, and high-impact visual hooks.

## 🏛️ Pipeline & Human Gates
- **Authoritative State Machine**: The state machine in `src/content_factory/state.py` is immutable and authoritative.
- **Source Rights**: `source_rights_confirmed` must NEVER be set to `true` autonomously by any agent without explicit human confirmation.
- **Two Review Gates**:
  1. Gate 1 (`script_review` -> `script_approved`): Requires human review of script and sources.
  2. Gate 2 (`video_review` -> `video_approved`): Requires human review of the rendered video and audio mix.

## 🛠️ Tool Calling & Integrations
- **HTTP Tools Registry**: Access the 61 tools via `POST http://127.0.0.1:8080/tools/call` and inspect schemas via `GET http://127.0.0.1:8080/tools`.
- **MCP Server**: Connect to `mcp_server.py` via stdio or `--sse` on port 8765.
- **Offline Markdown Bridge**: Consume `brief.md` and reply with fenced markdown blocks (`script`, `json scenes`, `json style`).

## 💻 Environment & Quality Standards
- Python virtual environment: Use `.venv/Scripts/python.exe` on Windows.
- Quality gates: Run `python -m ruff check src tests`, `python -m ruff format --check src tests`, `python -m mypy src`, and `python -m pytest`.
