import React,{lazy,Suspense,useId,useState} from 'react';
import SourceMap from './NasaScreening.jsx';
import {HelpTip,StudioIcon} from './components/StudioUI.jsx';
const TerrainView=lazy(()=>import('./TerrainView.jsx'));
const f=(v,d=1)=>Number.isFinite(v)?v.toLocaleString('en-GB',{maximumFractionDigits:d,minimumFractionDigits:d}):'—';
const range=(a,unit='')=>a?`${f(a[0])}${Math.abs(a[1]-a[0])>.05?`–${f(a[1])}`:''}${unit}`:'—';
const utc=s=>new Date(s).toISOString().slice(0,16).replace('T',' ')+' UTC';

export function StudioRail(){
  const [active,setActive]=useState('explore');
  return <nav className="studio-rail" aria-label="Study navigation">{[['explore','Explore'],['compare','Compare'],['evidence','Evidence']].map(([id,label])=><a key={id} href={`#${id}`} aria-current={active===id?'page':undefined} onClick={()=>setActive(id)}><StudioIcon name={id} size={23}/><span>{label}</span></a>)}<div className="rail-end"><span>5 × 5 km</span><HelpTip label="Study footprint">One Connecting Ridge study region near the lunar south pole. The app does not search the whole Moon.</HelpTip></div></nav>;
}

export function SelectedInspector({scenario,point,request}){
  const location=scenario?.point||point;
  const rows=scenario?[
    ['Landing',utc(scenario.landingUTC),'The selected scenario’s actual landing UTC. Original and alternative landing times can differ.'],
    ['Sun-centre-visible time',range(scenario.metrics.sunVisibleH,' h'),'Time the Sun centre clears terrain in the selected mission. The range reflects terrain sensitivity.'],
    ['Earth-visible time',range(scenario.metrics.earthVisibleH,' h'),'Time Earth clears terrain under the selected centre or any-disc definition. A visible Earth does not guarantee a radio link.'],
    ['Minimum battery',range(scenario.metrics.batteryMinimumPercent,'%'),'Lowest modeled battery charge, including landing charge. The range gives lower and upper sensitivity cases.'],
    ['Relocation',`${f(location.relocationM,0)} m`,'Surface distance from the original point. It is not a trajectory or fuel calculation.']
  ]:[
    ['NASA sunlight frequency',`${f(location.nasa?.solarPct)}%`,'Archived, long-term any-disc sunlight frequency at the nearest 60 m NASA pixel. Not mission-specific hours.'],
    ['NASA Earth frequency',`${f(location.nasa?.earthPct)}%`,'Archived, long-term any-disc Earth visibility. Not the selected mission’s radio availability.'],
    ['50 m plane slope',`${f(location.slopeDeg,2)}°`,'Regional tilt fitted from the 5 m elevation source. Rock clearance and footpad support remain unknown.']
  ];
  return <section className="studio-inspector" aria-label="Selected candidate details"><div className="inspector-title"><span className="studio-id">{scenario?.id||'O'}</span><h2>{scenario?(scenario.id==='O'?'Original scenario':'Selected candidate'):'Original study point'}</h2></div><p className="inspector-coordinates">{f(location.latitude,5)}°, {f(location.longitude,5)}° E</p><dl>{rows.map(([label,value,help])=><div key={label}><dt>{label}<HelpTip label={label}>{help}</HelpTip></dt><dd>{value}</dd></div>)}</dl>
    {scenario?<><div className={`inspector-status ${scenario.selectedLimitsPass?'limits-pass':'limits-review'}`}>{scenario.selectedLimitsPass?'✓ Meets assessed limits':scenario.violations.length?'△ Assessed limit exceeded':'◌ Assessed limits uncertain'}</div><p className="inspector-ground">Ground support unassessed <HelpTip label="Ground support">Bearing strength, regolith depth and footpad sinkage have not been measured by this study. Passing assessed limits does not establish landing safety.</HelpTip></p>{request.requireKnownGround&&<p className="studio-warning">Does not qualify: known ground support is required.</p>}<a className="studio-compare-action" href="#assistant-comparison"><StudioIcon name="compare" size={16}/>Compare candidate</a></>:<p className="inspector-empty">Run a study to compare mission sunlight, Earth visibility and battery energy.</p>}
    <p className="studio-data-note">Archived NASA data · SPICE geometry<br/>Investigation only · landing safety unassessed</p>
  </section>;
}

export function StudioExplorer({info,point,candidates,current,index,request,active,onPick,onSelect,busy,onExport}){
  const [mode,setMode]=useState('terrain');
  return <section className="studio-explorer" id="explore" aria-label="Study area explorer"><div className="studio-canvas-heading"><div><h1>Connecting Ridge</h1><p>5 × 5 km study area <HelpTip label="Terrain view">The 3D display uses actual LOLA elevation data. Its lighting is illustrative, not a photograph or a live sunlight calculation.</HelpTip></p></div><div className="studio-explorer-actions"><div className="studio-segmented" role="group" aria-label="Explorer view"><button aria-pressed={mode==='terrain'} onClick={()=>setMode('terrain')}>3D terrain</button><button aria-pressed={mode==='maps'} onClick={()=>setMode('maps')}>NASA maps</button></div>{onExport&&<button className="studio-export" aria-label="Export study JSON" onClick={onExport}><StudioIcon name="export" size={17}/><span>Export</span></button>}</div></div>
    {mode==='terrain'?<div id="assistant-terrain" tabIndex="-1"><div className="studio-scenario-picker" role="group" aria-label="Select terrain scenario">{[{id:'O',point},...candidates].map(m=><button key={m.id} disabled={busy} aria-label={`Select terrain ${m.id==='O'?'original':m.id}`} aria-pressed={active===m.id} onClick={()=>onSelect(m.id)}>{m.id==='O'?'O · Original':m.id}</button>)}<span>{current?`${current.id} · ${utc(current.samples[Math.min(index,current.samples.length-1)].utc)}`:'Select a point on NASA maps or in advanced settings'}</span></div><Suspense fallback={<p className="terrain-fallback">Loading NASA elevation terrain…</p>}><TerrainView point={point} candidates={candidates} scenario={current} index={index} request={request} onSelect={onSelect} onMaps={()=>setMode('maps')}/></Suspense></div>:<SourceMap info={info} point={point} candidates={candidates} onPick={onPick} onSelect={onSelect} selected={active} busy={busy}/>}
  </section>;
}

export function StudioTimeline({scenario,request,index,setIndex,playing,setPlaying}){
  const pattern=useId().replaceAll(':','');
  if(!scenario)return <section className="studio-timeline studio-timeline-empty"><div><StudioIcon name="play"/><h2>Mission timeline</h2></div><p>Run a study to explore sunlight, Earth visibility and battery charge over time.</p></section>;
  const sample=scenario.samples[Math.min(index,scenario.samples.length-1)],hour=sample.hour,duration=scenario.durationH;
  const x=t=>t/duration*1000;
  const path=scenario.batteryLow.points.filter(p=>p.value!==null).map((p,i)=>`${i?'L':'M'}${x(p.hour)},${66-p.value/request.capacityWh*56}`).join(' ');
  return <section className="studio-timeline" aria-label="Shared mission timeline"><div className="studio-timeline-heading"><h2>{scenario.id} · Mission timeline</h2><div><button aria-label={playing?'Pause explorer playback':'Play explorer playback'} onClick={()=>{if(index===scenario.samples.length-1)setIndex(0);setPlaying(!playing);}}><span aria-hidden="true">{playing?'Ⅱ':'▶'}</span></button><button aria-label="Rewind explorer playback" onClick={()=>{setIndex(0);setPlaying(false);}}>↶</button></div><span className="timeline-time">+{f(hour,2)} h <small>{utc(sample.utc)}</small></span><HelpTip label="Mission timeline">One elapsed-time cursor updates the terrain, horizon and charts. Absolute UTC stays specific to each landing. Arrow keys move the cursor by one sample.</HelpTip></div>
    <div className="studio-timeline-plot"><div className="timeline-scrub-label">Elapsed time</div><div className="timeline-scrub"><input type="range" aria-label="Explorer mission time" min="0" max={scenario.samples.length-1} step="1" value={Math.min(index,scenario.samples.length-1)} onInput={e=>{setIndex(Number(e.target.value));setPlaying(false);}}/><div className="studio-hour-ticks">{Array.from({length:7},(_,i)=><span key={i}>{f(duration*i/6,0)} h</span>)}</div></div>
    {['sun','earth'].map(body=><React.Fragment key={body}><div className="timeline-row-label">{body==='sun'?'Sun visibility':'Earth visibility'}</div><svg className="studio-visibility-track" viewBox="0 0 1000 15" preserveAspectRatio="none" role="img" aria-label={`${scenario.id} ${body} visibility; solid visible, hatched uncertain, dim hidden`}><defs><pattern id={`${pattern}-${body}`} patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(35)"><rect width="6" height="6" fill="var(--studio-soft)"/><line x1="0" x2="0" y2="6" stroke={body==='sun'?'var(--studio-sun)':'var(--studio-earth)'} strokeWidth="2"/></pattern></defs>{scenario.intervals.map((s,i)=><rect key={i} x={x(s.startH)} width={x(s.endH-s.startH)+.12} height="15" fill={s[body+'State']==='visible'?(body==='sun'?'var(--studio-sun)':'var(--studio-earth)'):s[body+'State']==='hidden'?'var(--studio-band-hidden)':`url(#${pattern}-${body})`}/>)}<line x1={x(hour)} x2={x(hour)} y2="15" stroke="var(--studio-text)" strokeWidth="2"/></svg></React.Fragment>)}
    <div className="timeline-row-label">Battery<small>Lower case</small></div><svg className="studio-battery-track" viewBox="0 0 1000 78" preserveAspectRatio="none" role="img" aria-label="Lower sensitivity battery charge; curve stops at depletion"><line x2="1000" y1={66-request.reservePercent*.56} y2={66-request.reservePercent*.56} stroke="var(--studio-danger)" strokeDasharray="5 4"/><path d={path} fill="none" stroke="var(--studio-earth)" strokeWidth="2" vectorEffect="non-scaling-stroke"/><line x1={x(hour)} x2={x(hour)} y2="78" stroke="var(--studio-text)" strokeOpacity=".5"/></svg></div>
    <div className="studio-timeline-legend"><span>Solid: visible · Hatched: uncertain</span><span>Dashed: {request.reservePercent}% reserve · Battery stops at depletion</span></div>
  </section>;
}
