# Dashboard and explainable search, real-v4.0

Built on the user's `854ddf3` commit. Freestyle deployment settings and the saved presentation report are retained. This branch changes source and prebuilt assets; it does not deploy the live service or merge into main.

## Real terrain visualization

`GET /api/terrain-mesh` samples every tenth pixel from the verified 5 m regional elevation raster, producing 10,000 vertices at 50 m spacing. Vertices use the actual lunar sphere and a single shared east/north/up reference at the study centre:

    world = (1,737,400 m + elevation) × unit(longitude, latitude)
    ENU = [east; north; up] × (world − reference_world)
    scene = [east, up, −north]

There is no vertical exaggeration. Missing vertices are not triangulated. Display reduction does not change slope, connected-area, horizon, SPICE, or energy calculations. Analysis uses the full original grids.

Markers use the same transformation. A Sun/Earth direction is first resolved in the selected site's local ENU basis, then transformed into the scene reference. Surface-view camera height matches the request. Sun/Earth sphere radii use the angular radii from SPICE geometry. The computed horizon is drawn as an angular guide on a schematic 10 km-radius sky surface. Its angular values include terrain out to 300 km; this is not a claim that the visible 5 km mesh contains that terrain. Orbit view is an overview; surface views are the relevant perspective for the sky guide. Lighting is illustrative, not a shadow/power solver. The numerical horizon chart and NASA maps remain available.

The viewer is loaded separately from the rest of the page and renders on interaction, resize, or cursor changes, rather than continuously animating while idle. A graphics failure offers the NASA map view.

## Filter before rank

`rankingPriority` defaults to `schedule` for API compatibility. After the existing NASA, terrain, battery and Earth-visibility requirements, passing evaluated scenarios are sorted by the following keys, smallest first. The default tie-break on battery explicitly favors a **higher lower-case minimum**.

| Priority | Ordered key |
| --- | --- |
| schedule | absolute schedule shift, relocation metres, negative lower minimum battery percent |
| power | negative lower minimum battery percent, negative lower generated Wh, upper longest dark hours, absolute schedule shift, relocation metres |
| communication | upper longest Earth-hidden hours, negative lower Earth-visible hours, absolute schedule shift, relocation metres, negative lower minimum battery percent |
| relocation | relocation metres, absolute schedule shift, negative lower minimum battery percent |

These are lexicographic preferences, not weighted scores that mix metres, hours and energy. Up to three spatially distinct candidates are retained after sorting. The eight-location shortlist is still bounded and chosen geographically; a power/visibility priority does not claim to discover the optimum over all regional points. Ties remain deterministic. Missing or uncertain assessed requirements do not enter the ranked set.

Known ground support remains a separate mandatory requirement: when requested, qualification count is zero, while investigation candidates stay visible and explicitly unassessed. No geotechnical measurement is invented.

Candidate JSON includes its ordered ranking criteria. Rejection counts are reason occurrences across screened grid points and evaluated site/time cases; one option can contribute multiple reasons. Counts are not totals of distinct excluded landing sites.

## Runtime reference evidence

`GET /api/evidence` compares the running geometry engine with the two included independently captured JPL Horizons reference files. There are 25 hourly timestamps per body from 15 November 2026 06:00 to 16 November 2026 06:00 UTC, at longitude −137.50198°, latitude −89.46316°, surface elevation 1944.761474609375 m plus a 2 m instrument height. The tolerance is 0.0001° per angle. Azimuth differences wrap correctly at 0/360°.

The response includes measured maximum angular differences, counts, pass status, and the check's UTC time. Results are cached for that service instance. This is a comparison to stored reference outputs, not a new Horizons API request. The scope is one observer and those timestamps, with differing DE441/DE421 ephemeris/frame details. Terrain occlusion, full radio availability, other locations/times, power hardware and landing safety are not established by these checks.

## Verification

- 78 Python tests passed, including the existing real-data suite and new priority filtering/order, curved-Moon mesh reconstruction, missing-triangle and runtime-reference checks.
- 25 Node tests passed, including the original simulated model and new scene observer-height, basis, azimuth, curvature and polar/wrap checks.
- Production build passed. The separate 3D chunk is approximately 138 kB compressed; Vite reports a warning for its uncompressed size above 500 kB.
- The saved presentation backup is copied into dist after each build and its HTTP route was checked.

Browser and end-to-end checks performed locally on 15 November 2026:

- A real 24 h panel-power search returned three candidates from 304 screened grid points and 32 evaluated alternative site/time combinations. Mandatory known ground support kept qualification at zero.
- All four ranking priorities completed through the HTTP API. Candidate order matched each lexicographic key, exclusions and NASA thresholds remained enforced, and every returned scenario passed the assessed requirements. Power and communication priorities produced different coordinate orders from the default.
- Desktop 1280 × 900, tablet 714 × 844, and mobile 390 × 844 were inspected. No document-level horizontal overflow remained after correcting the hidden legend. Header navigation spacing was also corrected.
- WebGL terrain rendered, surface Sun/Earth views worked, and selecting R1/R2 synchronized coordinates and the horizon. Sun, Earth, permanent-shadow and LOLA map layers remained available.
- Explorer cursor End advanced to +24 h with matching UTC, horizon and lower battery readouts. Play/pause advanced and stopped the cursor. Candidate ranking criteria and exclusion reasons expanded correctly.
- Editing settings clears the previous computed sky guides and labels and returns a Sun/Earth camera to orbit mode. This reset behavior was corrected and verified in the final build.
- In-app reference checks reported 25 Sun and 25 Earth comparisons passing. Maximum azimuth/elevation differences were 0.000002680/0.000008131° for Sun and 0.000003787/0.000006894° for Earth, below the declared 0.0001° tolerance.
- A downloaded browser study JSON contained real-v4.0, the power priority, three candidates, zero qualifying options, rejection reasons and all 22 source checksums.
- The presentation backup route returned HTTP 200. The user's deployment files and saved report were unchanged. No browser console errors or warnings were reported during the inspected flow.

These are implementation checks with the archived regional data, not mission or landing-safety certification. Core numerical limits in MATHEMATICS.md continue to apply.
