# Last Light

The approved local pilot has two separate modes:

- **Real-data study:** NASA precomputed sunlight/Earth/permanent-shadow maps, actual LOLA terrain, SPICE Sun/Earth geometry, and panel-based power/battery calculations. One 5 × 5 km Connecting Ridge study patch.
- **Simulated demo:** the original concept with three fictional locations and illustrative ground-pressure screening. See [SIMULATED_DEMO.md](SIMULATED_DEMO.md).

The existing hosted prototype has not been updated by this work. No paid services, accounts, or API keys are needed.

## Open on this computer

Double-click **Start-Last-Light.cmd**. It starts the local service and opens **http://127.0.0.1:8000** in your browser when terrain is ready. Keep its console open; close it or press Ctrl+C to stop. Port 8000 must be free. Dependencies and NASA data are already prepared in this checkout.

If the browser does not open automatically, visit that address after the console reports that the server is running. The app has a Retry connection button while data loads.

## Set up another computer

Requires Python **3.12+**, about 550 MB of downloaded NASA data, and space for the Python environment. From PowerShell in this folder:

```powershell
.\Setup-Last-Light.ps1 -Python 'C:\path\to\python.exe'
.\Start-Last-Light.cmd
```

Equivalent manual setup, also applicable to Linux/macOS:

```sh
python -m venv .venv
# Activate .venv using your platform's normal activation command.
python -m pip install -r backend/requirements.lock.txt
python -m backend.acquire
python -m backend.server
# Open http://127.0.0.1:8000
```

`dist/` is prebuilt, so Node is needed only to edit/rebuild the frontend. Acquisition downloads public files and records hashes; interrupted downloads can be retried. Startup verifies all source checksums and rejects mismatches. After acquisition, calculations make no Horizons or other remote API calls. Optional Google Fonts fall back to system fonts offline.

## Find another candidate

1. Choose **Real-data study**. Switch among NASA sunlight, Earth visibility, permanent shadow, and LOLA terrain. Set NASA long-term screening thresholds (the 20% defaults are illustrative user requirements). Pick the original point on the hillshade or enter coordinates and click **Locate entered coordinates**. The full 50 m patch must fit within the verified footprint.
2. Set UTC dates, mission duration, change type, relocation radius, and exclusions. **Use Now (UTC)** selects the next 15-minute boundary; it does not acquire new imagery.
3. Enter regional terrain limits, instrument height, panel area, efficiency, electrical losses, pointing, battery/load assumptions, and maximum Earth-hidden interval. Choose fixed tilt/azimuth or ideal two-axis Sun tracking, and choose the mission Earth-centre or any-disc visibility definition. Defaults are illustrative requirements, not NASA landing criteria.
4. Search, then compare R1–R3 with the original. Scrub/play the shared timeline and change the active horizon. A first uncached search can take a few minutes; repeat searches reuse verified caches. Progress is shown.
5. Enable **Require known ground support to qualify** to see the zero-qualification case. Investigation candidates remain visible for review with ground support explicitly unknown.

The finder first applies NASA screening limits to nearest 60 m source pixels on a 250 m search grid, then checks local terrain and mission geometry. It screens a 250 m grid and analyzes up to eight terrain-screened locations at least 500 m apart. Alternative times use six-hour spacing anchored to the earliest time, plus the latest endpoint. It returns up to three distinct locations; time-only mode can return several dates at the original location. It filters assessed limits before ranking by absolute schedule shift, relocation, then lower minimum battery. It is bounded, not exhaustive. Relocation distance does not prove flight reachability.

## Actual calculations and their limits

The service computes least-squares regional slope, relief, roughness, connected source-slope area, a horizon on a curved Moon, elevated surface-observer SPICE directions, visibility sensitivity, and exact piecewise-rate battery energy. It includes capacity saturation, reserve crossing, and depletion. See [MATHEMATICS.md](MATHEMATICS.md) and [VALIDATION.md](VALIDATION.md).

Real-data mode does not assign invented rock coverage, regolith depth, bearing capacity, or sinkage. Flat regional terrain does not establish solid bedrock or a rock-free footprint. Rock clearance, actual ground support, trajectory/fuel, plume excavation, thermal behavior, and descent safety remain unassessed. Earth visibility does not establish a radio link. Panel generation uses inverse-square solar irradiance, incidence on the panel normal, efficiency, losses, and an approximate visible solar-disc fraction. One-minute midpoint power samples drive battery integration. A separately labeled constant-generation comparison mode is retained. Thermal behavior, tracking mechanics, and eclipses remain unmodeled.

“Real time” means computation for now or another UTC date using archived terrain and versioned kernels. It does not mean live imagery or newly certified landing locations. Sensitivity envelopes are not guaranteed confidence bounds. NASA averages describe time with any part of the disc visible; mission Sun bands use the centre, while Earth centre/any-disc is selectable. Panel power estimates partial solar-disc area above a locally straight horizon. Eclipses remain unmodeled. DE421 matches the terrain frame; it is not the newest ephemeris. The map is a calculated hillshade, not photography or current illumination.

## NASA datasets and mission timing

NASA screening products are 60 m source pixels over an 18.6-year modeled cycle, produced in 2016 from older terrain observations. They do not change with the selected landing date or instrument height. They are not mission-specific sunlight hours, electrical output, or ground-station availability. Source pixels and definitions appear in the map, comparison, exports, and method panel. See [MENTOR_UPDATE.md](MENTOR_UPDATE.md) for the new validation and [NASA product documentation](https://pgda.gsfc.nasa.gov/products/69).

Enter landing times supplied by your mission plan. Launch delays are not automatically added to arrival times; the interface explains the launch-window/trajectory/landing relationship and links NASA/CSA introductory resources. No transfer-trajectory solver is included. Use **Download study JSON & source checksums** to save the selected analysis and all source provenance.

## Development

```sh
npm install              # only if node_modules is absent
npm run build            # frontend -> dist/
npm test                 # original simulated-model checks
python -m pytest         # analytic + actual NASA-data checks
```

For frontend editing, run `python -m backend.server` and `npm run dev`; Vite proxies `/api` to the local service. Otherwise Python serves `dist/` directly. Data tests skip until data is acquired. Included Horizons reference fixtures allow tests without Horizons API requests.

Versioned URLs, retrieval dates and SHA-256 hashes are in [provenance/sources.json](provenance/sources.json), and the live manifest is available in the interface. Large data files and `.venv` are excluded from the portable source archive; the acquisition script recreates them.

`backend/Dockerfile` is provided for later hosting evaluation. Build from this folder and mount prepared data at `/app/data`. No container or hosted backend has been provisioned or deployed. Production hosting requires Python and persistent data storage; the previous static host cannot execute the analysis by itself.
