import test from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULTS, SITES, TERRAIN, HOUR, STEP, COVERAGE_END, parseUTC, inputUTC, geometry, horizonAt, simulate, findAlternatives, validate, hiddenRuns, explain, energyAt, assessTerrain, requiredGroundPressure } from '../src/model.js';
const base = () => ({ ...DEFAULTS });
const run = (c, id=c.altSite, landing=parseUTC(c.altDate), options={})=>simulate(id,landing,Number(c.duration),c,options);

test('opening demonstration is deterministic and derived from the intervals',()=>{
  const c=base(), o=run(c,'A',parseUTC(c.originalDate),{enforceWindow:false}), a=run(c);
  assert.deepEqual(a,run(c));
  assert.equal(o.metrics.sunHours,51); assert.equal(a.metrics.sunHours,27);
  assert.equal(o.metrics.minEnergy,3120); assert.equal(a.metrics.minEnergy,1200);
  assert.equal(o.meets,true); assert.equal(a.meets,false); assert.ok(a.reserveCrossing>0);
  assert.equal(a.metrics.sunHours,a.intervals.filter(p=>p.sunVisible).length*STEP);
  assert.equal(a.metrics.earthHours,a.intervals.filter(p=>p.earthVisible).length*STEP);
  assert.match(explain(o,a),/24 h/); assert.match(explain(o,a),/40\.0 percentage points/);
});
test('site and time changes recalculate geometry and metrics',()=>{
  const c=base(), a=run(c), b=run(c,'B'), earlier=run(c,'A',parseUTC(c.originalDate));
  assert.notDeepEqual(a.metrics,b.metrics); assert.notDeepEqual(a.metrics,earlier.metrics);
  assert.equal(a.intervals.length,72/STEP);
});
test('horizon visibility and timeline share the same geometry for every sample',()=>{
  for(const site of SITES){const c=base(),s=run(c,site.id);for(const p of s.intervals){assert.deepEqual({...geometry(site,p.timestamp)},Object.fromEntries(Object.entries(p).filter(([k])=>!['hour','timestamp'].includes(k)))); assert.equal(p.sunVisible,p.sunEl>horizonAt(site,p.sunAz));assert.equal(p.earthVisible,p.earthEl>horizonAt(site,p.earthAz));}}
});
test('battery follows the entered generation and load; changing settings can make delay pass',()=>{
  const c=base(),a=run(c),relaxed=run({...c,reserve:20});
  assert.equal(a.meets,false);assert.equal(relaxed.meets,true);
  const stronger=run({...c,capacity:12000});assert.ok(stronger.metrics.minCharge>a.metrics.minCharge);
  const s=run({...c,load:17,generation:50,capacity:100000});
  for(let i=0;i<s.intervals.length;i++){assert.ok(Math.abs(s.energy[i+1].value-Math.min(100000,s.energy[i].value+((s.intervals[i].sunVisible?50:0)-17)*STEP))<1e-7);}
});
test('no generation when Sun hidden; zero load and full charge remain bounded',()=>{
  const c={...base(),generation:0,load:0,initial:100},s=run(c);assert.equal(s.metrics.minEnergy,c.capacity);assert.ok(s.energy.every(p=>p.value===c.capacity));
});
test('depletion stops modeled operation and energy does not restart in later light',()=>{
  const c={...base(),capacity:100,load:80,generation:0},s=run(c);
  assert.equal(s.depletion,1.125);assert.equal(s.metrics.minEnergy,0);assert.equal(s.meets,false);
  assert.equal(energyAt(s,2),null);assert.equal(energyAt(s,1.125),0);
  assert.ok(s.energy.filter(p=>p.hour>s.depletion).every(p=>p.value===null));
  assert.match(s.violations.join(' '),/operation stops/);
});
test('empty initial battery is stopped at landing, including in sunlight',()=>{
  const s=run({...base(),initial:0,generation:1000});assert.equal(s.depletion,0);assert.equal(energyAt(s,0),0);assert.equal(energyAt(s,.25),null);
});
test('boundary intervals are explicitly marked truncated',()=>{
  const runs=hiddenRuns([{v:false},{v:false},{v:true},{v:false}],'v');assert.deepEqual(runs,[{start:0,end:.5,hours:.5,truncated:true},{start:.75,end:1,hours:.25,truncated:true}]);
  assert.equal(run(base()).metrics.dark.truncated,true);
});
test('finder filters mandatory violations before sorting and respects delayed arrival',()=>{
  const c=base(),result=findAlternatives(c);assert.equal(result.options.length,3);
  for(const s of result.options){assert.equal(s.meets,true);assert.equal(s.siteId,c.originalSite);assert.ok(s.landing>=parseUTC(c.altDate));assert.ok(s.landing>=parseUTC(c.earliest));assert.ok(s.landing<=parseUTC(c.latest));}
  const shifts=result.options.map(s=>Math.abs(s.landing-parseUTC(c.originalDate)));assert.deepEqual(shifts,[...shifts].sort((a,b)=>a-b));
});
test('original exclusion holds at every later time and in every change mode',()=>{
  for(const mode of ['time','site','both']){const c={...base(),reason:'excluded',mode,altSite:'B',altDate:DEFAULTS.originalDate,reserve:0,maxEarthHidden:168};for(const s of findAlternatives(c).options)assert.notEqual(s.siteId,c.originalSite);}
  const s=run({...base(),reason:'excluded'});assert.equal(s.meets,false);assert.match(s.violations.join(' '),/excluded/);
});
test('site-only search retains original landing time; both changes site and time',()=>{
  const c={...base(),reason:'power',mode:'site',altSite:'B',altDate:DEFAULTS.originalDate,reserve:0,maxEarthHidden:168};const r=findAlternatives(c);assert.ok(r.options.length>0);for(const s of r.options){assert.equal(s.landing,parseUTC(c.originalDate));assert.notEqual(s.siteId,c.originalSite);}
  for(const s of findAlternatives({...c,mode:'both'}).options){assert.notEqual(s.siteId,c.originalSite);assert.notEqual(s.landing,parseUTC(c.originalDate));}
});
test('honest empty results under impossible requirements',()=>{
  const c={...base(),generation:0,load:5000,initial:0,reserve:100,maxEarthHidden:0};const r=findAlternatives(c);assert.ok(r.searched>0);assert.deepEqual(r.options,[]);
});
test('missing or out-of-coverage data is never passing',()=>{
  for(const s of [simulate('A',COVERAGE_END-5*HOUR,72,base()),simulate('X',parseUTC(DEFAULTS.altDate),72,base()),run({...base(),capacity:''}),run({...base(),load:-1})]){assert.equal(s.assessed,false);assert.equal(s.status,'Not assessed');assert.equal(s.metrics,undefined);}
  assert.deepEqual(findAlternatives({...base(),altDate:'2026-12-03T00:00'}).options,[]);
});
test('validation handles date range, 15-minute boundaries, duration and missing values',()=>{
  assert.deepEqual(validate(base()),[]);
  for(const patch of [{earliest:'2026-11-30T00:00',latest:'2026-11-18T00:00'},{altDate:'2026-11-19T06:02'},{altDate:'2026-11-30T00:00'},{reserve:101},{capacity:0},{duration:2.1},{load:''},{altDate:''}])assert.ok(validate({...base(),...patch}).length>0);
  assert.equal(inputUTC(NaN),''); // Changing modes with an empty original date cannot throw.
});

test('ground pressure responds to lunar weight, area, and entered load multiplier',()=>{
  const c=base();assert.ok(Math.abs(requiredGroundPressure(c)-16.2)<1e-10);
  assert.ok(Math.abs(requiredGroundPressure({...c,landerMass:2000})-32.4)<1e-10);
  assert.ok(Math.abs(requiredGroundPressure({...c,footpadArea:.4})-8.1)<1e-10);
  assert.ok(Math.abs(requiredGroundPressure({...c,loadMultiplier:1})-8.1)<1e-10);
  assert.equal(assessTerrain(SITES[0],c).meets,true);
  assert.equal(assessTerrain(SITES[0],{...c,landerMass:2000}).meets,false);
});
test('slope, relief, rock coverage and loose layer each disqualify independently',()=>{
  for(const patch of [{maxSlope:5},{maxRelief:.2},{maxRockCover:3},{maxLooseLayerCm:7}]){
    const result=assessTerrain(SITES[0],{...base(),...patch});assert.equal(result.assessed,true);assert.equal(result.meets,false);assert.equal(result.violations.length,1);
  }
  assert.equal(assessTerrain(SITES[0],{...base(),maxSlope:5.2,maxRelief:.22,maxRockCover:4,maxLooseLayerCm:8}).meets,true);
});
test('unknown ground capacity stays not assessed with working geometry and never qualifies',()=>{
  const c={...base(),reason:'power',mode:'both',altSite:'C',load:0,generation:0,reserve:0,maxEarthHidden:168,maxSlope:45,maxRelief:10,maxRockCover:100,maxLooseLayerCm:1000};
  const s=run(c);assert.equal(s.assessed,true);assert.equal(s.terrain.assessed,false);assert.equal(s.status,'Not assessed');assert.equal(s.meets,false);assert.equal(s.intervals.length,288);assert.equal(s.terrain.bearingMargin,null);
  assert.ok(findAlternatives(c).options.every(option=>option.siteId!=='C'));
});
test('terrain failures filter options even when power and communications pass',()=>{
  const c={...base(),load:0,generation:0,reserve:0,maxEarthHidden:168,maxRockCover:0};
  const result=findAlternatives(c);assert.ok(result.searched>0);assert.deepEqual(result.options,[]);
  assert.equal(run(c).status,'Violates a requirement');assert.match(run(c).violations.join(' '),/Rock coverage/);
});
test('ground strength is independent from dust depth and surface appearance',()=>{
  const low=assessTerrain(SITES[1],base(),{...TERRAIN.B,looseLayerCm:0,bearingKPa:1});assert.equal(low.meets,false);assert.match(low.violations.join(' '),/ground pressure/);
  const missing=assessTerrain(SITES[1],base(),{...TERRAIN.B,looseLayerCm:0,bearingKPa:null});assert.equal(missing.assessed,false);
  const a=run(base()),b=run({...base(),altDate:'2026-11-23T06:00'});assert.deepEqual(a.terrain,b.terrain);
});
test('invalid terrain and lander controls are rejected',()=>{
  for(const patch of [{maxSlope:''},{maxRelief:-1},{maxRockCover:101},{maxLooseLayerCm:-1},{footpadArea:0},{landerMass:0},{loadMultiplier:.5}])assert.ok(validate({...base(),...patch}).length>0);
});
