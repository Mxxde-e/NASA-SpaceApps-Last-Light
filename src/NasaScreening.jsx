import React,{useState} from 'react';
import './screening.css';

const pct=v=>v==null?'Unassessed':`${v.toFixed(2)}%`;
const layers={solar:'NASA sunlight',earth:'NASA Earth visibility',shadow:'NASA permanent shadow',terrain:'LOLA terrain'};

export function NasaFilters({control,form,change}){
  return <><legend>1 / Screen with NASA datasets</legend><div className="real-fields">
    {control('minAverageSolarPercent','Minimum NASA sunlight frequency','%',0,100,.01)}
    {control('minAverageEarthPercent','Minimum NASA Earth visibility','%',0,100,.01)}
  </div><label className="real-check"><input type="checkbox" checked={form.excludePermanentShadow} onChange={e=>change('excludePermanentShadow',e.target.checked)}/>Exclude NASA permanent-shadow pixels</label>
  <p className="real-form-help">Your screening thresholds apply to archived 60 m, long-term any-disc visibility frequencies. These are separate from the selected mission's hours and power.</p></>;
}

export default function NasaScreening({info,point,candidates,onPick,onSelect,selected,busy}){
  const [layer,setLayer]=useState('solar');
  const bounds=info.terrain.boundsXY;
  const markers=[...(point?[{id:'O',point}]:[]),...candidates];
  const active=markers.find(m=>m.id===selected)||markers[0];
  const samePoint=(a,b)=>Math.hypot(a.point.x-b.point.x,a.point.y-b.point.y)<.01;
  const mapped=markers.filter((m,i)=>markers.findIndex(n=>samePoint(m,n))===i).map(m=>active&&samePoint(active,m)?active:m);
  const data=active?.point.nasa;
  const xy=p=>[100*(p.x-bounds[0])/(bounds[2]-bounds[0]),100*(bounds[3]-p.y)/(bounds[3]-bounds[1])];
  return <section id="assistant-terrain" tabIndex="-1" className="panel real-map-panel nasa-panel"><div className="section-head"><h2>Start with NASA's maps</h2><span className="quiet-tag">5 × 5 KM STUDY FOOTPRINT</span></div>
    <div className="nasa-layer-picker" role="group" aria-label="Map layer">{Object.entries(layers).map(([id,label])=><button key={id} aria-pressed={layer===id} onClick={()=>setLayer(id)}>{label}</button>)}</div>
    <div className={`real-map ${busy?'busy':''}`} onClick={e=>{if(busy)return;const r=e.currentTarget.getBoundingClientRect();onPick(bounds[0]+(e.clientX-r.left)/r.width*(bounds[2]-bounds[0]),bounds[3]-(e.clientY-r.top)/r.height*(bounds[3]-bounds[1]));}} role="group" aria-label="NASA screening map; click to choose original point, or use latitude and longitude fields">
      <img src={`/api/map.png?layer=${layer}&v=3`} alt={layer==='terrain'?'Hillshade from actual 5 m NASA LOLA elevations':`${layers[layer]}: actual archived 60 m source pixels with illustrative hillshade`}/>
      <div className="real-map-top"><span>CONNECTING RIDGE</span><span>{layer==='terrain'?'5 M ELEVATION':'60 M NASA SOURCE PIXELS'}</span></div>
      {mapped.map(m=>{const [x,y]=xy(m.point);return <button key={m.id} className={`real-marker ${m.id==='O'?'origin':''} ${m.id===selected?'selected':''}`} style={{left:`${x}%`,top:`${y}%`}} aria-label={m.id==='O'?'Original study point':`Inspect candidate ${m.id}`} onClick={e=>{e.stopPropagation();onSelect(m.id);}}><span>{m.id}</span><small>{m.id==='O'?'Original':m.id}</small></button>;})}
      <div className="real-map-bottom"><span>{layer==='terrain'?'Computed hillshade · not current sunlight':'Archived model · not mission-date conditions'}</span><span>5 km width</span></div>
    </div>
    <div className="nasa-focus" role="group" aria-label="Focus a mapped scenario">{markers.map(m=><button key={m.id} disabled={busy} aria-label={m.id==='O'?'Focus original point':`Focus ${m.id}`} aria-pressed={m.id===selected} onClick={()=>onSelect(m.id)}>{m.id==='O'?'Original':m.id}</button>)}<small>Times at the same coordinates share one map marker.</small></div>
    {layer!=='terrain'&&<div className={`nasa-scale ${layer}`}><span>{layer==='shadow'?'Not classified as PSR':'0%'}</span><i/><span>{layer==='shadow'?'Permanent shadow':'100%'}</span></div>}
    <div className="nasa-values" aria-live="polite"><span className="nasa-active">{active?.id||'O'} · NEAREST 60 M NASA PIXEL</span><div><span>Sunlight frequency<strong>{pct(data?.solarPct)}</strong></span><span>Earth visibility<strong>{pct(data?.earthPct)}</strong></span><span>Permanent shadow<strong>{data?.permanentShadow==null?'Unassessed':data.permanentShadow?'Classified PSR':'Not classified'}</strong></span></div></div>
    <div className="real-map-note"><p>{info.terrain.name}</p><span>NASA averages cover an 18.6-year modeled cycle. They measure time with any portion of the disc visible, not electrical output. Pixel boundaries remain at 60 m; no 5 m screening detail is implied. Click to move the original point.</span></div>
  </section>;
}

export function LaunchContext(){
  return <details className="panel launch-context"><summary>Use landing times from your mission plan <span>⌄</span></summary><div>
    <div className="launch-stages"><span>Launch window</span><b>→</b><span>Translunar injection</span><b>→</b><span>Transfer / lunar approach</span><b>→</b><span>Landing UTC</span></div>
    <p>A changed launch window can require a revised trajectory and arrival time. Enter the updated <strong>landing UTC</strong> below, then reassess the surface conditions. This navigator does not convert a launch delay into an equal landing delay or calculate a transfer trajectory.</p>
    <p><a href="https://www.nasa.gov/specials/artemis-i-press-kit/" target="_blank" rel="noreferrer">NASA Artemis I mission architecture ↗</a><span> · </span><a href="https://www.csa-asc.gc.ca/eng/news/articles/2026/2026-01-09-artemis-ii-launch-opportunities-announced.asp" target="_blank" rel="noreferrer">CSA explanation of launch windows ↗</a></p><small>Artemis I illustrates translunar flight; it did not land on the Moon.</small>
  </div></details>;
}

export function NasaMethod({info}){
  return <div className="nasa-method"><h3>NASA screening and mission calculations</h3><p><a href={info.screening.sourceURL} target="_blank" rel="noreferrer">NASA Lunar Polar Illumination ↗</a> · {info.screening.productVersion} · product {info.screening.productDate}. Terrain observations: {info.screening.terrainObservationPeriod}. {info.screening.averagingPeriod}</p>
    <p>NASA's sunlight and Earth maps report long-term any-disc visibility frequencies. Mission Sun bands use the Sun's centre; the Earth definition is selectable. Different resolutions, observer heights, and time spans prevent treating these percentages as a direct accuracy check on the mission timeline.</p>
    <p>{info.screening.surface} {info.screening.sampling} {info.screening.limitations}</p>
    <p>Source citation: {info.screening.citation}.</p>
  </div>;
}

