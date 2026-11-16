# Last Light

Last Light is a lunar landing scenario navigator for students, researchers and early-stage mission analysts. Compare candidate locations and landing times using NASA terrain, Sun/Earth visibility and estimated battery behaviour, with the assumptions and unresolved questions visible alongside the results.

**[Open the live application](https://last-light.style.dev/)** · **[View a saved real-study report](https://last-light.style.dev/presentation-backup.html)**

The regional prototype covers one **5 × 5 km Connecting Ridge footprint near the lunar south pole**. Its rankings support further investigation; they do not establish landing safety, a whole-Moon optimum or NASA approval.

## Study modes

The application has two separate modes:

- **Real-data study:** NASA precomputed sunlight/Earth/permanent-shadow maps, actual LOLA terrain, SPICE Sun/Earth geometry, and panel-based power/battery calculations. One 5 × 5 km Connecting Ridge study patch.
- **Simulated demo:** the original concept with three fictional locations and illustrative ground-pressure screening. See [SIMULATED_DEMO.md](SIMULATED_DEMO.md).

## Mission Studio interface

The **Mission Studio** interface has a mission inspector beside the actual-elevation terrain view, with a shared timeline underneath. The top bar switches between light and dark themes and remembers the choice in this browser. Small circled question marks explain controls and results on hover, keyboard focus or tap; Escape dismisses them. The numerical calculator and structured mission planner can run locally without a paid API service or model key. The public deployment uses hosted compute and storage; operating it can incur hosting costs. GitHub pushes do not deploy automatically. See [Hosting and deployment](#hosting-and-deployment) and the [Freestyle deployment guide](deploy/FREESTYLE.md).

## Explore and compare results

- Switch between **3D terrain** and **NASA maps**. The curved-Moon mesh samples actual 5 m LOLA elevations every 50 m for display, at true vertical scale. Analysis still uses the original terrain grids. Missing display triangles are omitted.
- Run a study, select Original or R1–R3, and use the shared explorer playback. **Look toward Sun / Earth** places the camera at the selected surface observer. The pink angular guide shows the computed horizon; muted curves show sensitivity. The guide radius is schematic, while its angular directions are computed. Orbit view is an overview, not an observer's sky measurement. Shading is illustrative.
- Expand mission settings as needed. Choose **Keep the schedule**, **Preserve power**, **Maintain Earth visibility**, or **Minimize relocation**. Assessed hard limits filter first; the chosen priority ranks passing evaluated scenarios lexicographically. Each candidate shows ordered ranking criteria and actual metrics. It is a bounded search, not an exhaustive optimum.
- **Evidence → Run / show reference checks** compares the running engine with 50 independently captured Horizons direction outputs at one observer and 25 times per body. The panel reports measured angular differences, the 0.0001° tolerance, scope, and limits. It does not validate terrain occlusion, radio links, or landing safety.
- Builds retain the saved `docs/presentation-backup.html` at `dist/presentation-backup.html`. The backup remains a saved example; changing the live study does not silently replace it.

Detailed methods and validation are in [IMPROVEMENTS.md](IMPROVEMENTS.md). The interface design and verification are documented in [MISSION_STUDIO.md](MISSION_STUDIO.md).

## Chat, mission planning and accessibility

The assistant provides site-guide explanations and a real-study planning flow. Ask for a landing date including the year, surface duration and ranking priority, review the proposed settings, then choose **Calculate real options**. The planner submits those settings to the existing numerical engine. **Autofill & run** loads a returned candidate into the main workspace for evaluation.

The calculator, structured controls and supported offline language parsing work without an AI key. Optional AI interpretation and explanations use OpenRouter when the server has `OPENROUTER_API_KEY` and `CHAT_ENABLED=true`. The configured default model is `baidu/ernie-5.5-flash-preview:free`; availability and provider limits can change. If AI is disabled, unavailable or quota-limited, site help falls back to the guide and mission preparation retains its offline parsing and structured controls. The model proposes inputs or explains the application; candidate metrics and qualification decisions come from the numerical engine.

Model credentials belong only on the server. The hosted service reads `/etc/last-light-chat.env` through systemd. Local Python does not automatically load `.env` files. See [the planner, configuration and accessibility guide](docs/SITE_ASSISTANT.md) for details.

**Mic** fills an editable question before you send it. Dictation requires browser support and microphone permission and may use the browser's recognition provider. Typed entry remains available. **Larger text and controls**, a keyboard skip link and a text/table alternative to the terrain and timeline provide additional ways to use the interface.

## Run locally

A fresh clone does **not** include the Python environment, downloaded NASA data or generated caches. Run setup before using the launcher. You need Python **3.12+**, approximately **550 MB** for the source data, additional space for the Python environment/caches, and internet access for the initial downloads.

Clone the repository and enter its directory:

```sh
git clone https://github.com/Mxxde-e/NASA-SpaceApps-Last-Light.git
cd NASA-SpaceApps-Last-Light
```

On Windows, run from PowerShell:

```powershell
.\Setup-Last-Light.ps1
.\Start-Last-Light.cmd
```

If needed, select a specific Python executable with `.\Setup-Last-Light.ps1 -Python 'C:\path\to\python.exe'`.

For manual setup on Linux/macOS or Windows:

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.lock.txt
python -m backend.acquire
python -m backend.server
# Open http://127.0.0.1:8000
```

Use the installed Python 3.12+ command (`python` or `python3`) to create the environment, then activate it before installing packages. The Windows launcher opens the browser after terrain is ready. For the manual server command, open the URL yourself. Keep the console running; press Ctrl+C to stop. Port 8000 must be free. The interface offers a Retry connection button while data loads.

This repository includes a prebuilt `dist/`, so Node.js is required only to edit/rebuild the frontend or run its tests. Acquisition downloads public files and records hashes; interrupted downloads can be retried. Startup verifies source checksums and rejects mismatches. Once data is acquired, numerical studies and the included Horizons reference checks use local files without remote science API calls. Optional AI, browser dictation and Google Fonts can still use external services; fonts fall back to system fonts offline.

## Find another candidate

1. Choose **Real-data study**, then **NASA maps** to switch among NASA sunlight, Earth visibility, permanent shadow, and LOLA terrain. Expand NASA screening thresholds (the 20% defaults are illustrative user requirements). Pick the original point on the map or enter coordinates and click **Locate entered coordinates**. The full 50 m patch must fit within the verified footprint.
2. Set UTC dates, mission duration, change type, relocation radius, and exclusions. **Use Now (UTC)** selects the next 15-minute boundary; it does not acquire new imagery.
3. Enter regional terrain limits, instrument height, panel area, efficiency, electrical losses, pointing, battery/load assumptions, and maximum Earth-hidden interval. Choose fixed tilt/azimuth or ideal two-axis Sun tracking, and choose the mission Earth-centre or any-disc visibility definition. Defaults are illustrative requirements, not NASA landing criteria.
4. Search, then compare R1–R3 with the original. Scrub/play the shared timeline and change the active horizon. A first uncached search can take a few minutes; repeat searches reuse verified caches. Progress is shown.
5. Enable **Require known ground support to qualify** to see the zero-qualification case. Investigation candidates remain visible for review with ground support explicitly unknown.

The finder first applies NASA screening limits to nearest 60 m source pixels on a 250 m search grid, then checks local terrain and mission geometry. It screens a 250 m grid and analyzes up to eight terrain-screened locations at least 500 m apart. Alternative times use six-hour spacing anchored to the earliest time, plus the latest endpoint. It returns up to three distinct locations; time-only mode can return several dates at the original location. It filters assessed limits before applying the selected ranking priority. The interface initially selects Preserve power: higher minimum battery in the lower sensitivity case, then higher generated energy in that case, then a shorter dark interval in the upper sensitivity case. Remaining tie-breakers are smaller landing-time shift and shorter relocation. Keep the schedule remains available and is the API fallback when no priority is supplied. Ground support remains unknown even when all assessed limits pass. It is bounded, not exhaustive. Relocation distance does not prove flight reachability.

## Actual calculations and their limits

The service computes least-squares regional slope, relief, roughness, connected source-slope area, a horizon on a curved Moon, elevated surface-observer SPICE directions, visibility sensitivity, and exact piecewise-rate battery energy. It includes capacity saturation, reserve crossing, and depletion. See [MATHEMATICS.md](MATHEMATICS.md) and [VALIDATION.md](VALIDATION.md).

Real-data mode does not assign invented rock coverage, regolith depth, bearing capacity, or sinkage. Flat regional terrain does not establish solid bedrock or a rock-free footprint. Rock clearance, actual ground support, trajectory/fuel, plume excavation, thermal behavior, and descent safety remain unassessed. Earth visibility does not establish a radio link. Panel generation uses inverse-square solar irradiance, incidence on the panel normal, efficiency, losses, and an approximate visible solar-disc fraction. One-minute midpoint power samples drive battery integration. A separately labeled constant-generation comparison mode is retained. Thermal behavior, tracking mechanics, and eclipses remain unmodeled.

“Real time” means computation for now or another UTC date using archived terrain and versioned kernels. It does not mean live imagery or newly certified landing locations. Sensitivity envelopes are not guaranteed confidence bounds. NASA averages describe time with any part of the disc visible; mission Sun bands use the centre, while Earth centre/any-disc is selectable. Panel power estimates partial solar-disc area above a locally straight horizon. Eclipses remain unmodeled. DE421 matches the terrain frame; it is not the newest ephemeris. The map is a calculated hillshade, not photography or current illumination.

## NASA datasets and mission timing

| Resource | Role |
| --- | --- |
| [High-resolution LOLA topography](https://pgda.gsfc.nasa.gov/products/78) | Connecting Ridge elevation, source slopes, return counts and uncertainty products. |
| [LOLA gridded products in the NASA PDS archive](https://pds-geosciences.wustl.edu/missions/lro/lola.htm) | Surrounding and global terrain for the regional horizon calculation. |
| [Lunar Polar Illumination](https://pgda.gsfc.nasa.gov/products/69) | Archived sunlight, Earth-visibility and permanent-shadow screening maps. |
| [NASA/JPL NAIF SPICE](https://naif.jpl.nasa.gov/naif/) | Date-specific surface-observer geometry using versioned kernels. |
| [NASA/JPL Horizons](https://ssd.jpl.nasa.gov/horizons/) | Captured reference directions for the scoped geometry checks. |

NASA screening products are 60 m source pixels over an 18.6-year modeled cycle, produced in 2016 from older terrain observations. They do not change with the selected landing date or instrument height. They are not mission-specific sunlight hours, electrical output, or ground-station availability. Source pixels and definitions appear in the map, comparison, exports, and method panel. See [MENTOR_UPDATE.md](MENTOR_UPDATE.md) for the new validation and [NASA product documentation](https://pgda.gsfc.nasa.gov/products/69).

Enter landing times supplied by your mission plan. Launch delays are not automatically added to arrival times; the interface explains the launch-window/trajectory/landing relationship and links NASA/CSA introductory resources. No transfer-trajectory solver is included. Use **Download study JSON & source checksums** to save the selected analysis and all source provenance.

## Development

```sh
npm install              # install frontend dependencies
npm run build            # frontend -> dist/
npm test                 # simulated model, chat client and terrain-geometry checks
python -m pytest         # backend, planner, analytic and available NASA-data checks
```

Frontend development requires Node.js **20.19+**, as declared in `package.json`. Run `python -m backend.server` and `npm run dev` in separate terminals; Vite proxies `/api` to the local service. Otherwise Python serves `dist/` directly. Data tests skip until data is acquired. Included Horizons reference fixtures allow tests without Horizons API requests. `npm test` runs the Node test files; the separate [assistant browser-check workflow](.github/workflows/site-assistant.yml) installs Playwright and runs the browser checks. Passing software tests does not establish flight accuracy or landing safety.

Versioned URLs, retrieval dates and SHA-256 hashes are in [provenance/sources.json](provenance/sources.json), and the live manifest is available in the interface. Large data files and `.venv` are excluded from the portable source archive; the acquisition script recreates them.

## Hosting and deployment

The public application is deployed on a **Freestyle Linux virtual machine**. Freestyle routes HTTPS traffic to nginx on port 8080. nginx reverse-proxies frontend and API requests to the Python FastAPI/Uvicorn service on loopback port 8000. FastAPI serves the built `dist/` frontend and runs the API, while systemd manages the service. See [deploy/FREESTYLE.md](deploy/FREESTYLE.md) for setup, updates and safeguards.

The prototype permits **one active numerical search at a time**. An overlapping request receives a busy/HTTP 429 response. Jobs are tracked in memory, and completed studies are cached on disk using request, algorithm and source-checksum fingerprints. A first uncached search may take several minutes. This deployment does not provide a durable distributed job queue or demonstrate capacity for large numbers of simultaneous users.

The [saved real-study report](https://last-light.style.dev/presentation-backup.html) is a previous calculation, separate from new live studies. Its public link still requires the host and network. A downloaded copy of [docs/presentation-backup.html](docs/presentation-backup.html) can be viewed offline.

GitHub commits and merges do **not** automatically redeploy this VM. Deployment requires pulling reviewed changes, updating dependencies where needed, rebuilding the frontend, running the relevant checks and restarting the service. A README-only change does not require an application rebuild or service restart.

Hosting requires compute and persistent storage and may incur charges. Public endpoint availability depends on the VM and provider configuration; the repository remains the source for local setup. The calculator itself requires no external AI subscription or model key.

`backend/Dockerfile` is an alternative deployment option, separate from the current VM service. Build it from the repository root and mount prepared data at `/app/data`. The Python calculations require a backend with access to the prepared data; static frontend hosting alone cannot execute them.

## SI-assisted development

ChatGPT/Codex and image-generation tools assisted development, debugging, UI concept exploration and documentation. Lovable assisted presentation design. These development uses are separate from the optional deployed assistant. The implemented numerical engine produces study results, and the team remains responsible for the code, assumptions and interpretation.
