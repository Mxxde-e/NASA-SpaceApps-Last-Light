import React from 'react';
const n=(v,d=1)=>Number.isFinite(v)?v.toFixed(d):'—';
const range=(a,b,d=1)=>`${n(a,d)}${Math.abs(a-b)>10**-d/2?`–${n(b,d)}`:''}`;

export function PowerInputs({control,Control,form,change}){
  return <><h3 className="settings-heading">Panel power & communications</h3><label className="real-control"><span>Generation model</span><select aria-label="Generation model" value={form.powerModel} onChange={e=>change('powerModel',e.target.value)}><option value="panel">Panel area, pointing & solar geometry</option><option value="constant">Constant Sun-centre-visible watts</option></select></label>
    <div className="real-fields power-common">{control('capacityWh','Usable battery','Wh',1,100000,100)}{control('initialPercent','Landing charge','%',0,100,1)}{control('loadW','Constant load','W',0,5000,1)}{control('reservePercent','Minimum reserve','%',0,100,1)}{control('maxEarthHiddenH','Maximum Earth-hidden interval','h',0,168,.25)}</div>
    <label className="real-control power-select"><span>Mission Earth-visibility definition</span><select aria-label="Mission Earth visibility definition" value={form.earthVisibilityMode} onChange={e=>change('earthVisibilityMode',e.target.value)}><option value="centre">Earth centre clears terrain</option><option value="any">Any portion of Earth disc clears terrain</option></select></label><p className="real-form-help">NASA screening uses any-disc visibility. Neither definition establishes a usable ground-station radio link.</p>
    {form.powerModel==='panel'?<div className="panel-inputs"><div className="real-fields">{control('panelAreaM2','Solar-panel area','m²',.01,100,.01)}{control('panelEfficiencyPercent','Conversion efficiency','%',0,100,1)}{control('panelLossPercent','Combined electrical losses','%',0,100,1)}{control('irradianceAt1AU','Reference irradiance at 1 AU','W/m²',0,2000,1)}</div>
      <label className="real-control power-select"><span>Panel pointing</span><select aria-label="Panel pointing" value={form.panelTracking} onChange={e=>change('panelTracking',e.target.value)}><option value="sun">Ideal two-axis Sun tracking</option><option value="fixed">Fixed tilt and azimuth</option></select></label>
      {form.panelTracking==='fixed'&&<div className="real-fields">{control('panelTiltDeg','Panel tilt from horizontal','°',0,90,.5)}{control('panelAzimuthDeg','Panel-facing azimuth','°',0,360,1)}</div>}
      <p className="real-form-help">Area, efficiency, losses and pointing are hardware assumptions. Fixed azimuth is clockwise from local north. Ideal tracking faces the Sun whenever available; tracking limits and motor loads are unmodeled. Panel orientation is independent of the terrain plane.</p>
    </div>:<div className="real-fields">{control('generationW','Sun-centre-visible generation','W',0,10000,1)}</div>}
  </>;
}

export function SolarReadout({sample,request}){
  if(request.powerModel!=='panel')return <div className="solar-readout"><span>Entered constant generation<strong>{n(request.generationW,0)} W when Sun centre is visible</strong></span></div>;
  return <div className="solar-readout" aria-live="polite"><span>Available panel output<strong>{range(sample.generationLowW,sample.generationHighW)} W</strong></span><span>Incidence angle<strong>{n(sample.incidenceDeg)}°</strong></span><span>Visible solar disc<strong>{range(sample.solarDiscLow*100,sample.solarDiscHigh*100)}%</strong></span><small>{n(sample.solarIrradianceWm2,1)} W/m² incident solar flux · {n(sample.sunDistanceAU,4)} AU · lower–upper terrain sensitivity</small></div>;
}

export function SolarPowerChart({original,selected,index,request}){
  if(request.powerModel!=='panel')return null;
  const cases=[[original,'Original','#e9dfc6'],...(selected?[[selected,'Alternative','#e9b769']]:[])];
  const max=Math.max(1,...cases.flatMap(([s])=>s.samples.map(p=>p.generationHighW)))*1.1;
  const x=h=>50+h/request.durationH*900,y=w=>160-w/max*130;
  const path=(s,key)=>s.samples.map((p,i)=>`${i?'L':'M'}${x(p.hour)},${y(p[key])}`).join(' ');
  const active=selected||original, hour=active.samples[Math.min(index,active.samples.length-1)].hour;
  return <section className="panel solar-chart"><div className="section-head"><h2>Available solar power</h2><span className="quiet-tag">AREA × IRRADIANCE × EFFICIENCY × INCIDENCE × VISIBILITY × LOSSES</span></div><svg viewBox="0 0 1000 195" role="img" aria-label="Available panel power in watts, original and alternative lower and upper sensitivity curves">
    {[0,.5,1].map(f=><g key={f}><line x1="50" x2="950" y1={y(f*max)} y2={y(f*max)} stroke="#536774" strokeOpacity=".35"/><text x="42" y={y(f*max)+4} textAnchor="end">{n(f*max,0)} W</text></g>)}
    {cases.map(([s,label,color])=><g key={label}><path d={path(s,'generationHighW')} fill="none" stroke={color} strokeWidth="1.5" strokeDasharray="5 4" opacity=".6"/><path d={path(s,'generationLowW')} fill="none" stroke={color} strokeWidth="2"/></g>)}
    <line x1={x(hour)} x2={x(hour)} y1="25" y2="165" stroke="#ece2cd"/>{[0,.25,.5,.75,1].map(f=><text key={f} x={x(f*request.durationH)} y="183" textAnchor="middle">{n(f*request.durationH,1)} h</text>)}
  </svg><div className="solar-energy-summary">{cases.map(([s,label])=><span key={label}>{label} · available solar energy<strong>{range(...s.solarEnergyWh,0)} Wh</strong></span>)}</div><p className="panel-footnote">Solid curves: lower case; dashed: upper case. Graph cursor samples are five minutes apart. Energy uses one-minute midpoint power samples and refined visibility boundaries. Available energy includes potential generation after battery saturation or mission-operation depletion; it is not all stored or used.</p></section>;
}
