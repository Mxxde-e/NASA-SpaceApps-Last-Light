# Freestyle hosting and presentation safeguards

Live site: https://last-light.style.dev

## Setup

Python 3.12, python3-venv, Git and nginx are required. Clone to /home/ubuntu/last-light, create .venv, install backend/requirements.lock.txt, run .venv/bin/python -m backend.acquire. dist/ is prebuilt. Use a single Uvicorn worker because job state is in memory.

Copy deploy/last-light.service to /etc/systemd/system/last-light.service and deploy/nginx.conf to /etc/nginx/conf.d/last-light.conf. Validate with sudo nginx -t. Run sudo systemctl daemon-reload, sudo systemctl enable --now last-light nginx, and sudo systemctl reload nginx. Route Freestyle HTTPS last-light.style.dev to port 8080. Python binds only to loopback 8000; do not publish it directly.

Limits are global across visitors: six search requests/minute with burst two, other API traffic ten requests/second with burst forty, thirty concurrent connections, 16 KiB bodies, ten-second header/body timeouts. These do not trust spoofable forwarded-IP headers. The application also permits only one active search. HTTP 429 means wait and retry. This mitigates simple abuse, not distributed denial of service.

## Updating

GitHub pushes do not deploy automatically. Temporarily authenticate, pull reviewed changes, install changed dependencies, rebuild dist if frontend changed, run npm test and .venv/bin/python -m pytest, then restart last-light. Regenerate the backup after rebuilding dist. Remove the VM GitHub login afterward with gh auth logout --hostname github.com --user Mxxde-e. Local logout does not revoke GitHub CLI access on other devices. Never commit credentials, data or logs.

## Presentation backup and shutdown

Run .venv/bin/python deploy/make_presentation_backup.py after a successful real search. docs/presentation-backup.html is a self-contained offline report of actual cached results; download it from GitHub and open without a server. A served copy is at /presentation-backup.html. It is a saved example, not a fresh calculation. data/cache preserves repeat search results. Checksums remain in data/sources.json.

Leave the VM running until the presentation is over. Pause it afterward in Freestyle to stop CPU/RAM reservation usage; storage remains. No automatic pause is scheduled because the presentation end time is unspecified.
