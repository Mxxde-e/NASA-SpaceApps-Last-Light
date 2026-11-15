# Real-data mathematics

Implementation: `backend/numerics.py`, `terrain.py`, `geometry.py`, and `analysis.py`. The original simulated model is separate. Units are metres, explicitly named degrees/radians, watts, watt-hours, and UTC/elapsed hours.

The v4 dashboard adds a display-only mesh and explicit ranking priorities. See [IMPROVEMENTS.md](IMPROVEMENTS.md) for their coordinate transforms, ranking equations, and verification. The existing terrain, ephemeris, visibility, solar-power, and battery mathematics remain the analysis engine.

## Terrain and reference frame

NASA PGDA LOLA **Site01** supplies five co-registered 5 m GeoTIFFs: elevation, height RMS, slope, slope RMS, and return count. Elevation is height above a **1,737,400 m lunar sphere**, not radius. Dimensions, affine transforms, CRS, masks, and checksums are verified. Missing heights never become zero terrain.

The source uses spherical south-polar stereographic projection, central longitude 0°, latitude −90°, **MOON_ME_DE421**. Longitude is east-positive, displayed in [−180°,180°). The study bounds are X [−13,500,−8,500], Y [−14,500,−9,500] m, wholly inside the 16 km source. IAU_MOON and principal-axis coordinates are not substituted for the terrain frame.

For a unit lunar vector u=(ux,uy,uz), the exact projection is:

```text
X = 2R uy / (1 − uz)
Y = 2R ux / (1 − uz)
latitude = −π/2 + 2 atan(hypot(X,Y)/(2R))
longitude = atan2(X,Y)
```

The analytic projection is checked against pyproj. Raster-aligned 50 m patches use projected pixel lengths/areas; the small near-pole projection-scale variation is not removed. Raster alignment can offset the patch center by up to one pixel from entered coordinates. No footpad-scale precision is implied.

Fit 100 pixels to `z=aX+bY+c` by least squares:

```text
plane slope = atan(sqrt(a²+b²))
relief = max(z) − min(z)
roughness = RMS(z − fitted_plane)
```

Plane sensitivity is ±2 times the median published pixel-slope RMS, a screening proxy rather than an estimated plane covariance. Relief sensitivity is ±4 times maximum patch height RMS, from the difference between two pointwise ±2×RMS envelopes. Spatial covariance is not modeled; these are not formal confidence intervals.

Four-connected source-slope regions use `slope+2RMS` and `max(0,slope−2RMS)`. Area is count × 25 m², clipped to the study patch. Connected area does not prove usable landing footprint or rock clearance. Requests below 2,500 m² are rejected.

## Precomputed NASA screening

The three archived PDS products are `AVGVISIB_85S_060M_201608`, its `_EARTH` counterpart, and `LPSR_85S_060M_201608`, version V1.05, produced 2016-09-15. All have 5,058 × 5,058 signed little-endian int16 pixels at 60 m, in the compatible DE421 mean-Earth south-polar projection. Labels describe terrain inputs acquired 2009–2013. NASA describes the averages over an 18.6-year modeled cycle; exact averaging epochs and a configurable observation height are not specified in these labels. Do not mistake terrain acquisition dates for averaging epochs.

Visibility fraction = DN × 0.00004. Percent = fraction × 100. The label defines frequency of timesteps with any portion of the Sun/Earth disc visible, not mean electrical power. Permanent-shadow flag = DN × 0.000025 + 0.5: −20,000 means not classified as PSR; +20,000 means PSR. Other values are missing, not a pass. The loader validates scales, offsets, shape, source hashes, frame, and projection; GDAL independently checks pixel registration. Sampling uses the nearest source pixel, without invented 5 m screening detail or interpolation of the categorical shadow flag.

The candidate finder applies these user-entered screening limits before detailed candidate terrain and geometry. Values refer to the nearest source pixel at the study point, not a guaranteed classification of its whole landing footprint. NASA averages remain fixed when landing date, panel pointing, or instrument height changes. NASA's EXTRAs README warns about possible DEM artifacts and states these products are not supported by PDS or the LOLA Science Team.

## Terrain horizon on a curved Moon

For observer radius `ro=R+elevation+instrument_height`, terrain radius `rt=R+terrain_height`, and `δ=great_circle_distance/R`:

```text
α = atan2(rt cos δ − ro, rt sin δ)
horizon(A) = max α along azimuth A
```

Rays follow spherical great circles. Azimuth is clockwise from true local north, spaced 0.25°. Radial sampling starts at 5 m: 5 m steps to 20 km, 20 m to 220 km, and 500 m to 300 km. Bilinear sampling uses the finest supported raster. Maximum tangent reduction before atan is algebraically equivalent here because the horizontal denominator is positive. Lunar curvature is included.

Outside the regional source, use PDS **LDEM_85S_40M**, then **LDEM_16** (16 pixels/degree, about 1,895 m north–south pixels). PDS DN is signed little-endian int16. **Height=0.5×DN**. OFFSET=1,737,400 is added only for radius. Polar line/sample offsets and cylindrical registration are checked using GDAL's independent PDS reader.

The envelope raises/lowers regional terrain and observer by twice their supplied height RMS. Coarse allowances are assumptions: ±40 m for 40 m terrain and ±500 m for global terrain, not published RMS. Beyond 300 km, the upper model also considers the global raster maximum +500 m at the domain boundary. This bounds the interpolated model, not unresolved terrain or obstacles. Angular/radial aliasing and terrain inside the first 5 m remain limitations.

## Sun and Earth

SPICE kernels: `de421.bsp`, `moon_pa_de421_1900-2050.bpc`, `moon_080317.tf`, `pck00011.tpc`, and `naif0012.tls`. The frame kernel supplies the PA-to-ME rotation. Supported dates are deliberately restricted to 2000–2049; complete missions are coverage-checked. The original mission and candidate date window are sampled separately, avoiding years of intermediate samples for a distant reference date.

`spkcpo` uses the actual elevated fixed surface position, output reference location OBSERVER, and **CN+S** correction: converged light time plus stellar aberration. There is no atmospheric refraction. Project apparent vector v onto local east/north/up:

```text
azimuth = atan2(v·east, v·north) mod 2π
elevation = atan2(v·up, hypot(v·east,v·north))
```

The Sun-centre band compares centre elevation with the upper/lower horizons. Earth visibility can use the centre or any-disc criterion: elevation plus apparent angular radius clears the horizon. The Earth radius is approximated by 6,378.137 km; the Sun radius by 695,700 km; angular radius is asin(radius / SPICE distance). Centre, any-disc, and panel-disc-fraction definitions are kept separate. Eclipses, relativistic light bending, and radio-link budgets are absent. Horizons includes additional effects and newer DE441 dynamics; reference checks validate agreement within a stated tolerance, not identity.

## Time and energy

Panel mode uses a one-minute grid; legacy constant generation uses five minutes. The grid brackets sign changes against both envelope boundaries. Bisection refines those transitions to one second, and refined intervals are classified at their midpoints. Events wholly within a base interval can be missed. One-second root precision is not a physical accuracy claim. The five-minute display samples use the same geometry and horizon.

Panel generation is calculated from actual Sun distance and orientation:

```text
S = S0 × (AU / Sun_distance)²
cos(incidence) = sin(Sun_elevation) cos(tilt)
              + cos(Sun_elevation) sin(tilt) cos(Sun_azimuth − panel_azimuth)
P = S × area × efficiency × max(0,cos(incidence)) × visible_disc_fraction × (1−losses)
```

Tilt is measured from horizontal; panel azimuth is clockwise from local north. The panel normal is independent of the fitted terrain plane. Ideal two-axis tracking sets incidence to zero as an explicit hardware assumption. Tracking limits, motor consumption, thermal efficiency, and plume/dust degradation are not simulated. Efficiency and loss percentages are divided by 100. The default editable S0=1,361 W/m² is a reference assumption, not a live irradiance measurement; AU=149,597,870.7 km.

For a uniform-brightness solar disc and a locally straight horizon, let u=(Sun centre elevation − horizon elevation)/angular radius, clipped to [−1,1]. Visible area fraction is `(acos(−u) + u sqrt(1−u²))/pi`. The high horizon produces lower power; the low horizon produces upper power. This first-order disc model ignores changes in horizon elevation across the Sun's azimuthal width, solar limb darkening, and eclipses. A partially visible Sun can supply power while its centre is hidden. NASA's long-term any-disc frequency is never substituted into this instantaneous equation.

Panel output is held at each interval's midpoint value on a one-minute grid, including refined visibility boundaries. This is midpoint quadrature; battery integration is exact for those piecewise-constant rates. Five-minute display samples show instantaneous power and do not set integrated energy. In legacy constant-generation mode, generation is entered watts while the Sun centre is visible, zero when hidden, and lower/upper cases bracket uncertain visibility.

With interval rate `q=generation−load`:

```text
E_next = min(capacity, E + q × Δhours)
time_to_capacity = (capacity−E)/q   [q>0]
time_to_reserve = (E−reserve)/−q    [q<0]
time_to_depletion = E/−q           [q<0]
```

Available solar energy sums P×Δhours over the entire modeled mission, including potential output after battery saturation or operation depletion; it is distinct from energy actually stored or used. Curves contain exact saturation and depletion kinks. They stop at depletion, without restart. The minimum includes landing energy. Visible totals and longest hidden durations use the same refined intervals; boundary-touching hidden durations cover only the mission portion.

Requirements overlapping sensitivity cases do not pass. Known violations are filtered before ranking. Ground/rock/trajectory unknowns stay separate; mandatory known ground support gives zero qualifying options. “Meets assessed limits” applies only to the calculated subset; no result is fully assessed or certified safe.

Sources: [NASA precomputed polar maps](https://pgda.gsfc.nasa.gov/products/69), [NASA solar irradiance reference](https://earth.gsfc.nasa.gov/climate/projects/solar-irradiance/science), [NASA LOLA regional products](https://pgda.gsfc.nasa.gov/products/78), [PDS LOLA](https://pds-geosciences.wustl.edu/missions/lro/lola.htm), [NAIF kernels](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/), [SPICE spkcpo](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkcpo_c.html), [Horizons manual](https://ssd.jpl.nasa.gov/horizons/manual.html). The application embeds no Horizons API or relay.
