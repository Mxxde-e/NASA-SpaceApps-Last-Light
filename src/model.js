// Fictional geometry, sampled and held constant for each 15-minute interval.
// These accelerated cycles are illustrative. They are not lunar ephemerides.
export const HOUR = 3_600_000;
export const STEP = 0.25;
export const COVERAGE_START = Date.parse('2026-11-15T00:00:00Z');
export const COVERAGE_END = Date.parse('2026-12-01T00:00:00Z');
export const SITES = [
  { id: 'A', name: 'Aster Ridge', description: 'An exposed ridge with a raised western horizon. A later arrival can extend the modeled dark interval.', slope: 5.2, elevation: 1420, x: 38, y: 40, phase: 0, sunBias: 2, sunAmp: 7, horizon: 2.3, earthBias: 3.8, earthPhase: 0.7 },
  { id: 'B', name: 'Selene Shelf', description: 'A broad shelf with a lower synthetic horizon. More modeled sunlight comes with longer Earth-hidden intervals.', slope: 3.8, elevation: 980, x: 67, y: 65, phase: 17, sunBias: 4.3, sunAmp: 6, horizon: 1.7, earthBias: 1.3, earthPhase: 1.9 },
  { id: 'C', name: 'Lumen Basin', description: 'A shallow basin with an open modeled Earth view. Its surrounding rim can reduce Sun-visible time.', slope: 7.1, elevation: -640, x: 72, y: 27, phase: -24, sunBias: 3, sunAmp: 6.2, horizon: 2, earthBias: 5.1, earthPhase: -0.4 },
];
// Invented patch properties, independent of the illustrative map mesh.
// Bearing capacity is an assumption, never inferred from slope or dust depth.
export const TERRAIN = {
  A: { surface: 'Thin loose regolith over a rocky substrate', relief: 0.22, rockCover: 4, looseLayerCm: 8, bearingKPa: 24 },
  B: { surface: 'Compact regolith plain with sparse exposed rocks', relief: 0.12, rockCover: 1, looseLayerCm: 3, bearingKPa: 32 },
  C: { surface: 'Uneven patch with loose regolith and scattered rocks', relief: 0.44, rockCover: 9, looseLayerCm: 18, bearingKPa: null },
};
export const TERRAIN_LIMITS = {
  maxSlope: [0, 45, 'Maximum patch slope'], maxRelief: [0, 10, 'Maximum patch relief'],
  maxRockCover: [0, 100, 'Maximum rock coverage'], maxLooseLayerCm: [0, 1000, 'Maximum loose-layer depth'],
  landerMass: [1, 100000, 'Landed mass'], footpadArea: [0.01, 100, 'Total footpad contact area'],
  loadMultiplier: [1, 10, 'Load multiplier'],
};
export const DEFAULTS = {
  originalSite: 'A', originalDate: '2026-11-18T06:00',
  altSite: 'A', altDate: '2026-11-19T06:00', duration: 72,
  reason: 'delay', mode: 'time',
  earliest: '2026-11-18T06:00', latest: '2026-11-25T06:00',
  maxEarthHidden: 32, capacity: 4800, initial: 90, load: 80, generation: 190, reserve: 30,
  maxSlope: 6, maxRelief: 0.3, maxRockCover: 5, maxLooseLayerCm: 15,
  landerMass: 1000, footpadArea: 0.2, loadMultiplier: 2,
};
export const parseUTC = value => Date.parse(`${value}Z`);
export const inputUTC = ms => Number.isFinite(ms) ? new Date(ms).toISOString().slice(0, 16) : '';
export const utc = ms => Number.isFinite(ms) ? new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(ms).replace(',', '') + ' UTC' : 'Invalid date';
export const fmt = (n, digits = 1) => Number.isFinite(n) ? n.toLocaleString('en-GB', { maximumFractionDigits: digits, minimumFractionDigits: digits }) : '—';
export const siteById = id => SITES.find(s => s.id === id);
export const requiredGroundPressure = config => Number(config.landerMass) * 1.62 * Number(config.loadMultiplier) / (Number(config.footpadArea) * 1000);
export function assessTerrain(site, config, properties = TERRAIN[site?.id]) {
  const violations = [], unknowns = [];
  const valid = Object.entries(TERRAIN_LIMITS).every(([key,[min,max]])=>config[key] !== '' && Number.isFinite(Number(config[key])) && Number(config[key]) >= min && Number(config[key]) <= max);
  if (!site || !valid) return { assessed: false, meets: false, violations, unknowns: ['Valid terrain requirements and lander assumptions are required.'], requiredKPa: null, bearingMargin: null };
  const requiredKPa = requiredGroundPressure(config);
  for (const [key, value, label, unit] of [
    ['maxSlope',site.slope,'Patch slope','°'], ['maxRelief',properties?.relief,'Patch relief','m'],
    ['maxRockCover',properties?.rockCover,'Rock coverage','%'], ['maxLooseLayerCm',properties?.looseLayerCm,'Loose-layer depth','cm'],
  ]) {
    if (!Number.isFinite(value) || value < 0) unknowns.push(`${label} is unknown for this sample patch.`);
    else if (value > Number(config[key])) violations.push(`${label} ${fmt(value)} ${unit} exceeds the entered limit of ${fmt(Number(config[key]))} ${unit}.`);
  }
  const knownBearing = Number.isFinite(properties?.bearingKPa) && properties.bearingKPa >= 0;
  const bearingMargin = knownBearing ? properties.bearingKPa - requiredKPa : null;
  if (!knownBearing) unknowns.push('Ground support not assessed: assumed bearing capacity is unknown.');
  else if (bearingMargin < -1e-9) violations.push(`Screening ground pressure ${fmt(requiredKPa)} kPa exceeds assumed ground capacity ${fmt(properties.bearingKPa)} kPa.`);
  return { assessed: unknowns.length === 0, meets: unknowns.length === 0 && violations.length === 0, properties, requiredKPa, bearingMargin, violations, unknowns };
}
const rad = degrees => degrees * Math.PI / 180;
export function horizonAt(site, azimuth) {
  return site.horizon + 1.15 * Math.sin(rad(azimuth * 2 + site.phase * 3)) + 0.45 * Math.cos(rad(azimuth * 5));
}
export function geometry(site, timestamp) {
  const t = (timestamp - COVERAGE_START) / HOUR;
  const sunAz = ((90 + t * 2.1 + site.phase * 2) % 360 + 360) % 360;
  const earthAz = 183 + 24 * Math.sin(t * Math.PI / 96 + site.earthPhase);
  const sunEl = site.sunBias + site.sunAmp * Math.sin((t - 48 + site.phase) * Math.PI * 2 / 168);
  const earthEl = site.earthBias + 4.2 * Math.sin(t * Math.PI * 2 / 60 + site.earthPhase);
  return { sunAz, earthAz, sunEl, earthEl, sunVisible: sunEl > horizonAt(site, sunAz), earthVisible: earthEl > horizonAt(site, earthAz) };
}
export function validate(config) {
  const errors = [];
  for (const key of ['originalSite', 'altSite']) if (!siteById(config[key])) errors.push('Choose one of the three sample study points.');
  const dates = ['originalDate', 'altDate', 'earliest', 'latest'];
  for (const key of dates) {
    const value = parseUTC(config[key]);
    if (!Number.isFinite(value)) errors.push('Enter all dates and times in UTC.');
    else if (value < COVERAGE_START || value > COVERAGE_END) errors.push('Dates must be inside 15 Nov–01 Dec 2026 sample coverage.');
    else if (value % (STEP * HOUR) !== 0) errors.push('Use times on a 15-minute boundary (00, 15, 30, or 45).');
  }
  const ranges = { duration: [1, 168], maxEarthHidden: [0, 168], capacity: [1, 100000], initial: [0, 100], load: [0, 5000], generation: [0, 10000], reserve: [0, 100] };
  for (const [key, [min, max]] of Object.entries(ranges)) {
    if (config[key] === '' || !Number.isFinite(Number(config[key])) || Number(config[key]) < min || Number(config[key]) > max) errors.push(`${({ duration:'Mission duration', maxEarthHidden:'Earth-hidden limit', capacity:'Battery capacity', initial:'Initial charge', load:'Average load', generation:'Sun-visible generation', reserve:'Battery reserve' })[key]} must be ${min}–${max}.`);
  }
  if (Number(config.duration) % STEP !== 0) errors.push('Mission duration must use 0.25-hour increments.');
  for (const [key,[min,max,label]] of Object.entries(TERRAIN_LIMITS)) if (config[key] === '' || !Number.isFinite(Number(config[key])) || Number(config[key]) < min || Number(config[key]) > max) errors.push(`${label} must be ${min}–${max}.`);
  if (parseUTC(config.earliest) > parseUTC(config.latest)) errors.push('Earliest alternative must precede the latest alternative.');
  for (const key of ['originalDate', 'altDate']) if (parseUTC(config[key]) + Number(config.duration) * HOUR > COVERAGE_END) errors.push('The full mission must end by 01 Dec 2026 00:00 UTC.');
  return [...new Set(errors)];
}
export function hiddenRuns(intervals, key) {
  const runs = [];
  let start = null;
  for (let i = 0; i <= intervals.length; i++) {
    if (i < intervals.length && !intervals[i][key]) { if (start === null) start = i; }
    else if (start !== null) { runs.push({ start: start * STEP, end: i * STEP, hours: (i - start) * STEP, truncated: start === 0 || i === intervals.length }); start = null; }
  }
  return runs;
}
export function simulate(siteId, landing, duration, requirements, { enforceWindow = true } = {}) {
  const site = siteById(siteId);
  const ranges = {capacity:[1,100000],initial:[0,100],load:[0,5000],generation:[0,10000],reserve:[0,100],maxEarthHidden:[0,168]};
  const hardwareValid = Object.entries(ranges).every(([k,[min,max]]) => requirements[k] !== '' && Number.isFinite(Number(requirements[k])) && Number(requirements[k]) >= min && Number(requirements[k]) <= max) && (!enforceWindow || (Number.isFinite(parseUTC(requirements.earliest)) && Number.isFinite(parseUTC(requirements.latest))));
  if (!site || !Number.isFinite(landing) || !Number.isFinite(Number(duration)) || duration < 1 || duration > 168 || duration % STEP || landing % (STEP * HOUR) || landing < COVERAGE_START || landing + duration * HOUR > COVERAGE_END || !hardwareValid || requirements.capacity <= 0) return { assessed: false, status: 'Not assessed', siteId, landing, intervals: [], energy: [], violations: ['Complete supported coverage and valid inputs are required.'] };
  const n = Math.round(duration / STEP);
  const intervals = Array.from({ length: n }, (_, i) => ({ hour: i * STEP, timestamp: landing + i * STEP * HOUR, ...geometry(site, landing + i * STEP * HOUR) }));
  const capacity = Number(requirements.capacity), reserveWh = capacity * Number(requirements.reserve) / 100;
  let energyNow = capacity * Number(requirements.initial) / 100;
  let minEnergy = energyNow, depletion = energyNow === 0 ? 0 : null;
  let reserveCrossing = energyNow < reserveWh ? 0 : null;
  const energy = [{ hour: 0, value: energyNow }];
  for (let i = 0; i < n; i++) {
    if (depletion !== null) { energy.push({ hour: (i + 1) * STEP, value: null }); continue; }
    const rate = (intervals[i].sunVisible ? Number(requirements.generation) : 0) - Number(requirements.load);
    const next = Math.min(capacity, energyNow + rate * STEP);
    if (reserveCrossing === null && next < reserveWh) reserveCrossing = i * STEP + (rate < 0 ? (energyNow - reserveWh) / -rate : 0);
    if (next <= 0) {
      depletion = i * STEP + (rate < 0 ? energyNow / -rate : 0);
      energy.push({ hour: depletion, value: 0 });
      if (depletion < (i + 1) * STEP) energy.push({ hour: (i + 1) * STEP, value: null });
      energyNow = 0;
    } else { energyNow = next; energy.push({ hour: (i + 1) * STEP, value: energyNow }); }
    minEnergy = Math.min(minEnergy, energyNow);
  }
  const sunRuns = hiddenRuns(intervals, 'sunVisible'), earthRuns = hiddenRuns(intervals, 'earthVisible');
  const longest = runs => runs.reduce((a, b) => b.hours > a.hours ? b : a, { hours: 0, truncated: false });
  const metrics = { sunHours: intervals.filter(p => p.sunVisible).length * STEP, earthHours: intervals.filter(p => p.earthVisible).length * STEP, dark: longest(sunRuns), earthHidden: longest(earthRuns), minEnergy, minCharge: minEnergy / capacity * 100 };
  const terrain = assessTerrain(site, requirements);
  const violations = [...terrain.violations];
  if (enforceWindow && (landing < parseUTC(requirements.earliest) || landing > parseUTC(requirements.latest))) violations.push('Landing is outside the allowed alternative date range.');
  if (requirements.reason === 'excluded' && enforceWindow && siteId === requirements.originalSite) violations.push('The original study point is excluded.');
  if (requirements.reason === 'delay' && enforceWindow && landing <= parseUTC(requirements.originalDate)) violations.push('A delayed landing must be later than the original landing time.');
  if (metrics.earthHidden.hours > Number(requirements.maxEarthHidden)) violations.push(`Earth-hidden interval exceeds your limit by ${fmt(metrics.earthHidden.hours - Number(requirements.maxEarthHidden))} h.`);
  if (minEnergy < reserveWh) violations.push(`Battery falls ${fmt(reserveWh - minEnergy, 0)} Wh below the entered reserve.`);
  if (depletion !== null) violations.push(`Battery depletes at +${fmt(depletion)} h; operation stops.`);
  const meets = violations.length === 0 && terrain.assessed;
  return { assessed: true, siteId, site, landing, duration, intervals, energy, metrics, terrain, unknowns: terrain.unknowns, depletion, reserveCrossing, reserveWh, violations, meets, status: violations.length ? 'Violates a requirement' : terrain.assessed ? 'Meets modeled requirements' : 'Not assessed' };
}
export function findAlternatives(config) {
  if (validate(config).length) return { options: [], searched: 0 };
  const origin = parseUTC(config.originalDate), earliest = parseUTC(config.earliest), latest = parseUTC(config.latest);
  const points = config.mode === 'time' ? [config.originalSite] : SITES.map(s => s.id).filter(id => id !== config.originalSite);
  const times = config.mode === 'site' ? [origin] : Array.from({ length: Math.floor((latest - earliest) / (6 * HOUR)) + 1 }, (_, i) => earliest + i * 6 * HOUR);
  // Include range endpoint and exact entered alternative; no stochastic searching.
  if (config.mode !== 'site') times.push(latest, parseUTC(config.altDate));
  let searched = 0;
  const qualified = [];
  for (const siteId of points) for (const landing of [...new Set(times)]) {
    if (landing < earliest || landing > latest || (siteId === config.originalSite && landing === origin) || (config.mode === 'both' && landing === origin) || (config.reason === 'delay' && (landing <= origin || landing < parseUTC(config.altDate))) || (config.reason === 'excluded' && siteId === config.originalSite)) continue;
    searched++;
    const scenario = simulate(siteId, landing, Number(config.duration), config);
    if (scenario.assessed && scenario.meets) qualified.push(scenario);
  }
  qualified.sort((a, b) => Math.abs(a.landing - origin) - Math.abs(b.landing - origin) || b.metrics.minCharge - a.metrics.minCharge || a.siteId.localeCompare(b.siteId));
  return { options: qualified.slice(0, 3), searched };
}
export function explain(original, alternative) {
  if (!original.assessed || !alternative.assessed) return 'Complete the inputs within sample coverage to compare the scenarios.';
  const delta = (alternative.landing - original.landing) / HOUR;
  const darkDelta = alternative.metrics.dark.hours - original.metrics.dark.hours;
  const chargeDelta = alternative.metrics.minCharge - original.metrics.minCharge;
  const lead = original.siteId === alternative.siteId ? `Moving the landing ${delta >= 0 ? 'later' : 'earlier'} by ${fmt(Math.abs(delta), 0)} h` : `Moving from sample ${original.siteId} to sample ${alternative.siteId}${delta ? ` and shifting the date by ${fmt(delta, 0)} h` : ' at the same time'}`;
  const terrainNote = !alternative.terrain.assessed ? ' Ground support remains not assessed; this option cannot qualify.' : alternative.terrain.violations.length ? ` Terrain screening: ${alternative.terrain.violations.join(' ')}` : ` Terrain assumptions meet the entered limits, with ${fmt(alternative.terrain.bearingMargin)} kPa of ground-capacity margin. This is not a sinkage prediction.`;
  return `${lead} ${darkDelta === 0 ? 'leaves the longest Sun-hidden interval unchanged' : `${darkDelta > 0 ? 'extends' : 'shortens'} the longest Sun-hidden interval by ${fmt(Math.abs(darkDelta))} h`}. Minimum estimated charge ${chargeDelta >= 0 ? 'increases' : 'decreases'} by ${fmt(Math.abs(chargeDelta))} percentage points. ${alternative.depletion !== null ? `Under your power assumptions, operation stops at +${fmt(alternative.depletion)} h.` : alternative.reserveCrossing !== null ? `Under your power assumptions, the alternative crosses the battery reserve at +${fmt(alternative.reserveCrossing)} h.` : 'Under your power assumptions, the alternative stays at or above the battery reserve.'}${terrainNote}`;
}
export function energyAt(scenario, hour) {
  if (!scenario.assessed || (scenario.depletion !== null && hour > scenario.depletion)) return null;
  const points = scenario.energy.filter(p => p.value !== null);
  let left = points[0], right = points.at(-1);
  for (const p of points) { if (p.hour <= hour) left = p; if (p.hour >= hour) { right = p; break; } }
  return left.hour === right.hour ? left.value : left.value + (right.value - left.value) * (hour - left.hour) / (right.hour - left.hour);
}
