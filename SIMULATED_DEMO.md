# Last Light — simulated demo

This document describes only the separate Simulated demo mode. The current app also includes an approved real-data pilot; see [README.md](README.md).

**Lunar Landing Scenario Navigator** — a working React + Vite interaction prototype for preliminary lunar mission replanning.

**All geometry and terrain are simulated. No NASA data or APIs are connected.** Fictional study points are not approved or scientifically screened landing sites. This is not descent guidance, a landing-safety assessment, or a validated scientific product.

## Open and run

Use Node.js 20.19+ (or 22.12+) and npm:

```sh
npm install
npm run dev
```

Open the Local URL printed by Vite (normally **http://127.0.0.1:5173/**).

Alternatively, with pnpm installed: `pnpm install`, then `pnpm dev`. A pnpm lockfile is included. The included `dist/` is a complete production build and can be served by any static web server; opening its index.html directly through file:// will not load module assets correctly.

```sh
npm test          # deterministic calculation / constraint tests
npm run build    # production files in dist/
npm run preview  # open the printed Local URL to inspect dist/
```

## Try the demonstration

1. Start with sample A, 18 Nov 2026 06:00 UTC, versus a 24-hour delay. The 72-hour original has 51 Sun-visible hours and a 65% minimum charge. The delayed alternative has 27 Sun-visible hours and a 25% minimum charge, crossing the entered 30% reserve at +69 hours.
2. Change minimum reserve to 20%. The delayed scenario now meets the modeled requirements. Increase usable capacity or change load/generation to recompute both scenarios.
3. Click a terrain marker or choose Site / Both. Sample descriptions, horizon, metrics, and timelines update together.
4. Scrub the time slider (arrow keys supported), play/pause, rewind, and switch the horizon between original and alternative. Each scenario retains its own UTC timestamp.
5. Explore alternatives, then compare an option. With Landing delayed, the entered alternative time is the earliest arrival considered, in addition to the allowed date range. With Original location excluded, the finder never returns the original point at any time.
6. Try zero initial charge or very high load, then search: depleted scenarios fail; an empty search is reported honestly. Reset demo restores the opening example and precomputed options.

## Terrain and ground support

Terrain now filters the alternative finder and appears in the site profiles and comparison table. Editable limits cover patch slope, local height variation (relief), exposed-rock coverage, and assumed loose-layer depth. All values and default limits are invented demonstration inputs, not NASA screening criteria.

The support check compares each patch's **assumed** bearing capacity with an illustrative pressure:

```text
screening_pressure_kPa = landed_mass_kg × 1.62 × load_multiplier / total_footpad_area_m² / 1000
```

The defaults are 1,000 kg, 0.2 m² total footpad area, and a multiplier of 2, giving 16.2 kPa. This assumes equal loading and effective contact across all pads. It is not a landing-dynamics calculation or a prediction of sinkage. kPa means kilopascals.

Sample A has an invented 24 kPa capacity, B 32 kPa, and C **unknown** capacity. Unknown support cannot qualify, even if all other requirements pass; geometry and battery charts remain available. Rockiness, flatness, and loose-layer depth never determine bearing strength in the model. A different time cannot cure a terrain violation at the same sample patch.

Try setting maximum rock coverage to 1%: A's 4% coverage fails and same-site searches return no options. Restore the defaults and double landed mass: pressure rises to 32.4 kPa, above A's assumed capacity. Doubling contact area lowers pressure again. These are demonstrations, not engineering limits.

Background rationale: [NASA SPLICE terrain hazards](https://www.nasa.gov/safe-and-precise-landing-integrated-capabilities-evolution-splice/) and [NASA pressure–sinkage research](https://ntrs.nasa.gov/citations/20250005779). These are references, not connected datasets; no sample capacities or thresholds are sourced from them.

## Model and disclosure

- **Simulated inputs:** three fictional locations, sample slopes/elevations, synthetic direction-dependent horizon profiles, and accelerated Sun/Earth geometry cycles. The terrain mesh is illustrative and supplies no visibility calculations.
- **Entered hardware assumptions:** usable Wh, landing charge, constant W load, constant W generation while Sun-visible, and minimum reserve. Generation is zero during Sun-hidden intervals. No solar-angle, thermal, or radio-link model is included.
- **Derived outputs:** visibility bands, visible hours, longest hidden intervals within the mission, battery curve, minimum energy/charge, reserve crossing/depletion, terrain-limit violations, screening pressure and ground-capacity margin, requirements, differences, and ranked search results.
- **Coverage:** 15 Nov 2026 00:00 through 01 Dec 2026 00:00 UTC. Full missions must fit. All dates are explicitly UTC; input times align to 15-minute boundaries. Mission durations support 1–168 hours in 0.25-hour increments.
- Geometry is sampled and held constant for each 15-minute interval. The horizon and bands use the same samples. At the terminal cursor, the last interval's geometry is retained. Battery thresholds/depletion are interpolated within each constant-rate interval.
- Battery calculation: `min(capacity, energy + (generation - load) * interval_hours)`. Energy is capped at capacity. At depletion the energy trace ends at zero, operation is flagged stopped, and no restart is assumed. Later visibility still describes geometry, not continued operation.
- Hidden intervals touching the mission boundary are marked `*`. Their in-mission duration is known; duration before/after the mission is unknown. Missing coverage is **Not assessed**, never a pass.
- The baseline is a historical reference: the alternative date range and original-site exclusion apply only to alternatives. Power, communication, and terrain limits apply to both scenarios. All requirements refer to the modeled mission window and its fictional study patch.
- Search: three points, 6-hour candidate time steps anchored to the earliest allowed date, plus the entered alternative and latest allowed time. Time changes retain the original site; site changes retain original time; Both changes both. Mandatory violations are removed first. Rank by smallest absolute schedule change, then higher minimum battery margin, then point ID. This is a small deterministic search, not exhaustive optimization.
- Geometric Earth visibility does not guarantee a working radio link. Trajectory reachability, fuel optimization, actual ground bearing strength, footpad sinkage, unequal landing-gear loading, dust/plume effects, detailed thermal behavior, and descent safety are **not assessed**. The new support check compares assumptions only.

The app's expandable Method section links NASA JPL Horizons and API documentation, LRO/LOLA terrain products, Moon Trek, and QuickMap as **planned integrations, not connected sources**. No API keys, accounts, backend, or NASA dataset downloads are used. Optional Google Fonts fall back to system fonts when offline. There are no NASA logos or endorsement claims.

## Files

- `src/model.js`: shared deterministic geometry, integration, metrics, validation, explanations, search.
- `src/main.jsx`: React interface, schematic terrain/horizon, comparison, synchronized charts.
- `src/styles.css`: responsive interface, visible focus styles, reduced-motion support.
- `tests/model.test.js`: calculation and constraint tests.
- `dist/`: prebuilt static app.
- `.openai/hosting.json`: private Sites hosting identity (not required to run locally).

Verification performed is recorded in `VERIFICATION.md`.
