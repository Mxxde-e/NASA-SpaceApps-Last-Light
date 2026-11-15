# Simulated demo: earlier verification

This file records the earlier simulated prototype. Real-data pilot verification is in [VALIDATION.md](VALIDATION.md).

## Terrain update

All 20 calculation tests passed, including six new cases: ground-pressure scaling with mass/area/multiplier; independent slope/relief/rock/loose-layer filtering; unknown ground capacity remaining Not assessed while charts work; terrain violations filtering otherwise viable candidates; bearing strength independent of dust/appearance and landing time; and validation of the new controls. The production build passed.

New browser checks performed against the updated local app:

- Default screening pressure displayed 16.2 kPa.
- Maximum rock coverage of 1% produced the computed 4% rock violation and an empty same-site search.
- Increasing landed mass to 2,000 kg changed pressure to 32.4 kPa and triggered the 24 kPa assumed-capacity violation. Changing total contact area to 0.4 m² reduced pressure to 16.2 kPa and removed that violation.
- With other limits relaxed, sample C displayed Unknown capacity and an overall Not assessed status while geometry remained available. Its search returned only B options.
- Zero footpad area produced a validation error.
- The new controls were visually checked on desktop and at 390 × 844; the mobile page did not overflow horizontally. No browser console errors were reported when checked.
- A screenshot of the new controls was saved as `last-light-terrain-preview.jpg` beside the source folder.

Actual sinkage, site-specific soil strength, landing dynamics, and landing safety have not been validated. Ground properties and limits are simulated assumptions.

## Original release checks

14 Node test cases passed, covering deterministic opening results, site/time recalculation, horizon/band agreement at every sample for all three sites, battery integration, settings that change a delayed scenario from fail to pass, zero generation/load, depletion and no restart, empty initial charge, boundary-truncated intervals, filter-before-rank search, excluded original points, allowed change modes, empty results, missing coverage, and input validation.

Production build passed with Vite 7.2.2. Final console output and asset sizes are reported by the build command; no runtime API credentials are needed.

Browser checks actually performed against the local Vite app:

- Original and delayed opening values matched calculation tests.
- Lowering reserve from 30% to 20% changed the alternative to Meets modeled requirements.
- Explore alternatives returned three qualifying options. Compare this option updated the selected alternative's date and comparison.
- Selecting sample B updated the description, active candidate, and comparison.
- Excluding the original point returned only B and C in a same-time search.
- Zero initial charge produced an honest empty search and explicit operation-stopped battery events.
- Changing the alternative landing to 20 Nov recalculated sunlight to 3 hours and battery to depletion. A 30 Nov landing produced the full-coverage validation message and disabled search. A date input-event issue found during this check was fixed and the date check repeated successfully.
- Playback exposed Pause; pausing, Home, and ArrowRight moved the cursor to +0.25 h with matching absolute UTC timestamps.
- Setting the slider to +48 h updated both the timeline readout and horizon timestamp. A slider input-event issue was corrected and scrubbing repeated successfully.
- Mobile layout and charts were visually inspected at 390 × 844. Tablet width around 714 px and desktop width 1280 px were checked for page overflow; neither overflowed after a tablet hero-layout repair. Desktop layout was also visually inspected in the normal browser viewport.
- The browser reported no console error entries when checked.

The implementation includes focus outlines, labels, keyboard controls, and reduced-motion CSS. No screen-reader audit or full accessibility certification was performed.

No scientific validation, live NASA API integration, trajectory validation, landing-safety assessment, or real radio-link modeling was performed. All results use fictional deterministic samples and entered assumptions.
