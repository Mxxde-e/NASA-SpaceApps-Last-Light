# Initial real-data pilot validation (v2.3)

For the current NASA screening and panel-power update, see [MENTOR_UPDATE.md](MENTOR_UPDATE.md). The record below describes the earlier implementation.

Validation performed locally on 15 November 2026 UTC (14 November in Halifax). This records implementation checks, not flight qualification or a landing-safety validation.

## Automated checks actually run

- **44 Python tests passed**, including analytic planes, lunar curvature/tangent horizon, ENU/azimuth conventions, wrapped distances, horizon interpolation, sensitivity visibility, exact battery saturation/reserve/depletion, transition refinement, missing coverage, missing visibility, changed source bytes, and request validation.
- The same suite checks actual NASA rasters, source values and projection, independent GDAL PDS registration, use of regional/surrounding/global terrain, kernel coverage, a canonical NAIF frame example, 50 independent Sun/Earth reference comparisons, exclusion radius, candidate separation, mandatory ground unknowns, empty results, same-site time changes, and a distant original reference date without unbounded intermediate sampling.
- **20 original Node model tests passed**, preserving the simulated demonstration and its ground-pressure/terrain filtering.
- The final React/Vite production build passed.

Commands: `python -m pytest`, `npm test`, `npm run build`. Python tests need the downloaded data for the integration portion. Included Horizons fixtures avoid API calls during tests.

## Independent Horizons comparison

Using the official Horizons web application, I independently configured the Sun (10) and Earth (399), a lunar observer at east longitude −137.50198°, latitude −89.46316°, and altitude **1.946761474609375 km**, including the 2 m instrument height. I requested airless apparent azimuth/elevation hourly from 2026-11-15 06:00 through 2026-11-16 06:00 UTC: 25 timestamps per body.

Horizons reported DE441 and a high-precision lunar mean-Earth frame. The app uses DE421-compatible terrain/orientation and CN+S corrections. The configurations therefore are close, but not identical in all physical effects. Tested tolerance: **0.0001°** for each angle.

| Body | Maximum azimuth difference | Maximum elevation difference |
|---|---:|---:|
| Sun | 0.000002681° | 0.000008131° |
| Earth | 0.000003788° | 0.000006895° |

All 50 comparisons passed. This validates those times/coordinates and conventions; it is not a global accuracy guarantee. Raw captured reference outputs are in `backend/tests/horizons-sun.txt` and `horizons-earth.txt`. Measured maxima: [validation/horizons-comparison.json](validation/horizons-comparison.json). Reference service: [JPL Horizons](https://ssd.jpl.nasa.gov/horizons/app.html#/).

## Terrain and numerical convergence

The 5 m source CRS, 3,200 × 3,200 shape, projection radius, affine transform, and selected pixel values were inspected. The 1,000 × 1,000-pixel study crop fits inside that grid. PDS raw values, 0.5 m/DN scale, polar pixel offsets, global dimensions, and registration were checked against GDAL's independent PDS reader. A radius offset mistakenly added to height would fail the scale test. Fifteen source assets have SHA-256 provenance and are verified at service startup.

Two actual points were recomputed with **0.125° azimuth spacing and half radial steps**, against the production 0.25° horizon. Mission integration was also refined from five minutes to one minute. In these checks:

- Maximum nominal horizon difference was **0.056°**; the largest difference across the sensitivity envelopes was **0.143°**. The largest 95th-percentile difference was **0.024°**.
- The original 24-hour mission retained its sunlight/energy metrics.
- At the tested alternative, the lower Sun-visible duration changed by **0.0203 h (about 73 seconds)**, and lower minimum energy by **1.02 Wh**.

These measured differences are evidence of remaining discretization sensitivity, not error bounds for other sites. The one-second bisection precision does not remove terrain-grid aliasing or source uncertainty. Details: [validation/convergence.json](validation/convergence.json). Pointwise ±2×RMS sensitivity and coarse-terrain allowances are not certified confidence limits.

## HTTP and end-to-end checks

The final local service passed checks for metadata/frame, PNG terrain rendering, out-of-footprint coordinates (422), an unknown job (404), a below-resolution area request (422), and an out-of-kernel-date job failing without a result. A complete real search returned three investigation candidates and zero qualifying options when ground support was mandatory. Repeating the request reused the result while preserving its computation date and exact scenario values.

The recorded service run took **32.06 s** with cached terrain available and a fresh result calculation; the repeat cache request took **0.19 s**. An earlier uncached end-to-end search took **150.9 s**. A later browser run with horizons/geometry warmed took **1.6 s**. These are observed local timings, not service guarantees. [HTTP checks](validation/http-checks.json) and [actual example result with provenance](validation/http-study.json).

Browser checks actually performed:

- Valid mission form submission; actual candidate cards, coordinates, comparison, and terrain map.
- Timeline jump to mission end, rewind, play/pause, and synchronized UTC/horizon/energy readouts.
- Original versus R2 map selection updated the active horizon and location.
- Mandatory known ground support displayed **0 qualifying options**, while review candidates explicitly remained unassessed.
- A zero-slope requirement produced an honest empty result; restoring the limit restored the cached candidates.
- Download study JSON succeeded; its three real scenarios, zero qualification, and 15 source checksums were verified. See [browser export](validation/browser-export.json).
- Mobile viewport **390 × 844**: square, undistorted terrain map; horizontally scrollable comparison table; no document-level horizontal overflow. Desktop layout was also inspected.
- Switching to the simulated demo retained its separate disclosure, fictional sites, mission setup, and working original interface.

## Limits and deployment state

Only one regional pilot is implemented. No whole-Moon search, trajectory reachability, rock-clearance analysis, ground-strength measurement, sinkage prediction, eclipse calculation, thermal model, or radio-link budget has been validated. Finer topography/imagery and independent geotechnical/mission evidence remain necessary. Production hosting and the Docker image have not been deployed or tested in a cloud environment. The previous hosted simulated prototype remains unchanged.
