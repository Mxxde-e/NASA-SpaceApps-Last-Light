# NASA screening and panel-power update

Implemented in the existing local project, algorithm **real-v3.1**. The existing hosted simulated demonstration has not been deployed or changed by this update.

## What changed

1. **NASA datasets first.** The map now switches among actual precomputed solar visibility, Earth visibility, permanent shadow, and regional LOLA hillshade. Candidate screening applies user thresholds to NASA source pixels before detailed candidate terrain and geometry. Defaults of 20% Sun/Earth frequency are illustrative user requirements, not NASA recommendations.
2. **Separate time scales and definitions.** NASA percentages are archived, long-term any-disc visibility frequencies at 60 m resolution. Mission results use the selected dates and instrument height. Sun bands track the centre; Earth centre/any-disc is selectable. NASA percentages remain separate from mission-visible hours, electrical generation, and radio-link availability.
3. **Panel power.** The default interface model now uses area, efficiency, electrical losses, fixed tilt/azimuth or ideal Sun tracking, inverse-square irradiance, and an approximate visible solar-disc fraction. Available watts/Wh, battery curves, comparison rows, and the timeline use these calculations. A labeled constant-generation comparison option remains available.
4. **Mission timing guidance.** The interface explains launch window → translunar injection → transfer/lunar approach → landing UTC and links NASA/CSA introductory material. Landing UTC remains an explicit mission-plan input; launch delays are not converted into equal arrival delays.
5. **Usable map selection.** Original/candidate focus buttons remain accessible when dates share coordinates or markers are close. Shared coordinates use one graphic marker. On mobile, NASA maps appear before the long setup form.
6. **Provenance and exports.** The manifest now contains 22 checksum-verified source files, including seven new NASA screening assets. Study JSON includes NASA pixels, model settings, calculated power/energy, mission visibility definitions, and source checksums.

## Sources and interpretation

The primary PDS IMG/LBL products are `AVGVISIB_85S_060M_201608`, `AVGVISIB_85S_060M_201608_EARTH`, and `LPSR_85S_060M_201608`, version V1.05, produced 2016-09-15. All use 60 m source pixels and the compatible lunar DE421 mean-Earth projection. Their labels describe underlying terrain observations from 2009–2013; these are not the averaging epochs. NASA describes an 18.6-year modeled cycle, while exact averaging epochs are not specified in these labels.

At the project's reference point, the source pixel has **38.544% solar visibility frequency**, **33.852% Earth visibility**, and is **not classified as permanent shadow**. Those percentages do not predict continuous sunlight over a specific mission or prove firm ground. The map preserves source-pixel resolution rather than fabricating 5 m screening values. The higher-resolution regional terrain remains a separate calculation source.

Source scales are verified explicitly: visibility fraction = DN × 0.00004; permanent-shadow flag = DN × 0.000025 + 0.5. Thus shadow DN −20,000 maps to 0, and +20,000 to 1. Missing or unexpected values are unassessed. NASA's EXTRAs README notes possible DEM artifacts and that these products are not supported by PDS or the LOLA Science Team.

Sources: [NASA Lunar Polar Illumination](https://pgda.gsfc.nasa.gov/products/69), [PDS product directory](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/extras/illumination/img/), [source README](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/extras/illumination/readme_illumination_2016.txt), [NASA irradiance reference](https://earth.gsfc.nasa.gov/climate/projects/solar-irradiance/science). Citation: Mazarico et al. (2011), Icarus 211, 1066–1081, doi:10.1016/j.icarus.2010.10.030.

## Mathematical checks actually performed

**67 Python tests and 20 original Node tests passed.** The production build passed. The Python suite includes the earlier independent Horizons/frame checks and adds analytic panel-normal incidence, inverse-square flux, area/efficiency/loss scaling, disc-segment symmetry and limits, partial solar visibility with a hidden centre, variable interval generation, Earth centre versus any-disc, invalid inputs, missing power data, and NASA screening gates. Actual-data tests independently verify the new PDS registration and scale using GDAL, inspect reference pixel values and a positive PSR pixel, and verify NASA rejection before candidate terrain/geometry.

A real 24-hour power calculation at longitude −137.5733594631768°, latitude −89.4806345655543°, starting 2026-11-15 12:00 UTC, was repeated with 60 s and 30 s sampling:

| Quantity | Maximum difference |
|---|---:|
| Available solar energy, lower/upper cases | 0.0001975 Wh |
| Minimum battery energy, lower/upper cases | 0.0001240 Wh |

This demonstrates quadrature convergence at that point and time. It does not bound errors elsewhere or remove the larger terrain, pointing, and physical-model uncertainties. [Detailed convergence record](validation/mentor-power-convergence.json).

In a separate actual six-hour reference mission, a 1 m² panel at 25% efficiency and 15% losses produced **1,777.09 Wh** of available energy with ideal tracking versus **41.84 Wh** for a horizontal fixed panel. This illustrates the calculated low-Sun incidence effect under those assumptions, not a claim about real lander hardware.

## End-to-end checks actually performed

- All four distinct PNG map layers and the 22-source metadata manifest loaded through the local API.
- Invalid map layers, zero panel area, and invalid Earth-visibility definitions were rejected.
- The real candidate search satisfied the selected NASA thresholds and excluded PSR pixels. Requiring known ground support kept qualification at zero.
- A 100% NASA sunlight threshold excluded all 316 searched points and produced an honest empty result. Restoring the threshold returned three investigation candidates; 125 points were excluded by NASA screening in the tested browser configuration.
- Original/R2 focus changed the active NASA source values and horizon. At shared coordinates, focus controls avoid overlaid-marker ambiguity.
- Fixed-panel and tracking controls changed watts and available Wh; time scrubbing updated the instantaneous power readout. Playback, pause, and rewind worked.
- At 390 × 844, the NASA map was square, appeared before setup, and the document had no horizontal overflow. Desktop was also inspected.
- The updated study JSON download succeeded and was retained with the validation artifacts. Browser console inspection reported no warnings/errors.

The recorded API candidate search took **5.90 s**, and its repeat cache request **0.15 s**, with terrain caches available. The tested browser search took **12.6 s**. These are local observations, not timing guarantees. [API checks](validation/mentor-http-checks.json), [actual full result](validation/mentor-http-study.json), [browser export](validation/mentor-browser-export.json).

## Remaining limits

This remains a regional investigation navigator. The solar-disc model assumes uniform brightness and a locally straight terrain horizon; it does not model horizon variation across the disc, limb darkening, or eclipses. Reference irradiance and hardware parameters are entered assumptions; tracking mechanics, detailed thermal/electrical behavior, and dust degradation remain unmodeled. Ground bearing strength, regolith depth, footpad sinkage, obstacle clearance, trajectories, and landing safety remain unassessed. See [MATHEMATICS.md](MATHEMATICS.md) for equations and sampling details and [README.md](README.md) for running the project.
