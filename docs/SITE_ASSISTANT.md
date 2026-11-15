# Site assistant: feature/site-assistant

Floating help panel, suggested questions, plain-text replies, safe section navigation, keyboard Escape/focus restoration, mobile sizing and session-only history. No autonomous mission search, browsing, or access to actual analysis results is enabled. The public guide is backend/site_guide.json and is shared with the frontend fallback.

## Safeguards

POST /api/chat accepts message (1–1200 characters), up to six user/assistant turns (1200 characters each), and real/demo mode. Unknown fields and system roles are rejected. The server fixes the HTTPS OpenRouter origin, model, instructions, 400-output-token cap, 64 KiB provider-response limit and permitted sections. Model text is rendered as plain text; HTML, links and tools are never executed. Errors fall back to verified guide help without exposing provider errors or secrets.

AI is off by default. When enabled, a persistent SQLite quota limits provider attempts globally to 100 per rolling 24 hours and eight per minute, with two concurrent calls. Failed attempts count. No conversations, IPs or secrets are stored in this database. These are request caps, not a guaranteed dollar budget: also set a small provider-side key spending limit. Use one Uvicorn worker; scaling needs shared concurrency coordination. Gateway limits protect guide and AI requests. Origin checking is not authentication and cannot stop direct HTTP clients. Other visitors can exhaust global quotas; guide help remains available.

The public notice warns against submitting private information. History lives in memory and clears on data-mode changes. No localStorage or server conversation logging is used. Provider retention terms still apply. Select a model whose terms permit public site-help chat; do not assume the agent-only free Inkling endpoint is suitable.

## Sensitive activation step (pending)

Create a dedicated model key with a small spending limit. Enter it directly into /etc/last-light-chat.env on the host (root-owned, mode 600), never into chat, GitHub, dist, a VITE_ variable, shell arguments or screenshots. Set OPENROUTER_API_KEY, CHAT_ENABLED=true and CHAT_MODEL to a verified supported model ID. The optional systemd EnvironmentFile loads it. Until configured, guide mode sends nothing to an AI provider. Python does not automatically load .env files.

Update nginx and systemd from deploy/, validate nginx -t, rebuild frontend, restart the service, and test live provider success/failure after key entry. Real model accuracy, latency and cost remain unverified until then. Do not merge/deploy to the presentation site before review.

## Teammate integration

Preserve assistant-setup, assistant-terrain, assistant-comparison and assistant-sources IDs. Simulated mode uses mission, comparison and method IDs. Navigation explains when a search must be run to reveal results. No mission inputs or data modes are changed by the assistant. Update the guide whenever dashboard labels or behavior change.

Checks: npm test; npm run build; python -m pytest backend/tests/test_chat.py. Provider tests mock the network and spend no model credits.
