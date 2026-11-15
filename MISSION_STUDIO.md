# Option C — White Mission Studio

Implemented on top of main commit `19ff7c1` (the integrated dashboard and site assistant).

## Interface

- White/silver surfaces, teal actions, a slim Explore/Compare/Evidence rail and a dark terrain stage follow Option C. The terrain remains the actual elevation mesh at true vertical scale, with neutral illustrative lighting.
- A mission inspector holds the study footprint, expandable UTC landing window, surface duration and ranking priority. Advanced settings retains every detailed scientific input, including the original plan's separate landing time.
- The initial UI priority is **Preserve power**. Users can still choose any of the existing ranking rules. No ranking algorithm or scientific calculation changed.
- The selected original or R1–R3 candidate appears beside the terrain. Its coordinates, actual landing UTC, mission visibility, battery sensitivity range, relocation and limitations come from the existing API result.
- The compact timeline shares its cursor with terrain, horizon and detailed charts. Visibility bands preserve uncertainty; the lower-case battery trace stops at depletion. Detailed original/alternative comparisons, source maps, evidence checks, power curves, JSON export and mathematics remain available.
- Light is the initial palette. The top-bar Light/Dark control changes fields, results, charts, help and the assistant, and saves the preference in browser local storage when available. An early guarded initializer avoids a flash of the other palette on reload. Storage failure does not prevent theme switching.
- Small circled question-mark buttons explain controls and metrics. Hover, keyboard focus or tap opens a short tip; Escape, blur or scrolling dismisses it. Tips render above surrounding panels, stay inside the viewport and can be hovered to read. Native form labels remain separate from the help buttons.
- The simulated demo retains its distinct fictional-data label, follows the chosen palette and uses the same circled field-help control. The assistant's public guide uses the new control names.
- Phone layouts stack mission settings before the terrain; tablet layouts place the terrain above side-by-side settings and candidate details. Detailed comparisons can scroll horizontally within their own container.

## Verification

- Production Vite build passes. The existing lazy-loaded Three.js chunk still produces Vite's size advisory (about 553 kB / 138 kB gzip); the terrain renderer is loaded separately from the main interface.
- All 25 JavaScript calculation/terrain tests pass.
- All 90 Python tests pass with the downloaded NASA rasters and kernels available.
- Browser checks cover theme switching and reload persistence; help click/focus/Escape; desktop, 714 px tablet and 390 px phone widths; landing-window inputs; advanced coordinates and exclusions; candidate selection; shared time cursor end/rewind/play/pause; NASA maps; comparisons; and the assistant's guide/navigation.
- A real cached 24-hour study at original latitude −89.46316°, east longitude −137.50198°, original landing 2026-11-15 06:00 UTC, alternative window ending 2026-11-16 06:00 UTC and a 500 m exclusion returned three investigation candidates. Requiring known ground support correctly displayed zero qualifying options. The UI reported 304 screened grid points, 9 analyzed locations and 32 evaluated site/time combinations.

## Scope

The NASA data, geometry, terrain analysis, battery integration and qualification rules are preserved. No example values from the concept image are substituted for computed results. Ground strength, sinkage, obstacles and flight reachability remain unassessed. A GitHub merge updates repository source and prebuilt `dist/` assets; it does not deploy the Freestyle service. Existing deployment safeguards and the saved presentation backup are retained.
