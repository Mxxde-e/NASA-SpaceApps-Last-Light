import React,{useEffect,useId,useLayoutEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';

export function StudioIcon({name,size=20,...props}){
  const paths={moon:<path d="M20.8 13.2A8.8 8.8 0 0 1 10.8 3a9 9 0 1 0 10 10.2Z"/>,sun:<><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></>,explore:<><circle cx="12" cy="12" r="9"/><path d="m16 8-2 6-6 2 2-6 6-2Z"/></>,compare:<><rect x="3" y="3" width="12" height="12" rx="2"/><path d="M9 18v1a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-1"/></>,evidence:<><path d="M5 20V10m7 10V4m7 16v-7"/></>,play:<path d="m8 5 11 7-11 7V5Z"/>,export:<><path d="M12 16V3m-4 4 4-4 4 4M4 15v5h16v-5"/></>,chat:<path d="M20 11a8 8 0 0 1-8 8H7l-4 3v-7a8 8 0 1 1 17-4Z"/>};
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name]||paths.explore}</svg>;
}

export function HelpTip({label,children}){
  const id=useId(),trigger=useRef(null),tooltip=useRef(null),timer=useRef(null);
  const [open,setOpen]=useState(false),[position,setPosition]=useState({left:12,top:12});
  const close=()=>{clearTimeout(timer.current);setOpen(false);};
  const show=()=>{clearTimeout(timer.current);setOpen(true);};
  const leave=()=>{timer.current=setTimeout(()=>setOpen(false),130);};
  useLayoutEffect(()=>{
    if(!open)return;
    const place=()=>{
      const viewport=document.documentElement.clientWidth,r=trigger.current.getBoundingClientRect(),height=tooltip.current?.offsetHeight||90,width=Math.min(280,viewport-24);
      setPosition({left:Math.max(12,Math.min(r.left-12,viewport-width-12)),top:r.bottom+height+12<window.innerHeight?r.bottom+8:Math.max(12,r.top-height-8)});
    };
    place();window.addEventListener('resize',place);window.addEventListener('scroll',close,true);
    const escape=e=>{if(e.key==='Escape'){e.stopPropagation();close();trigger.current?.focus();}};
    document.addEventListener('keydown',escape);
    return()=>{window.removeEventListener('resize',place);window.removeEventListener('scroll',close,true);document.removeEventListener('keydown',escape);};
  },[open]);
  useEffect(()=>()=>clearTimeout(timer.current),[]);
  return <><button ref={trigger} type="button" className="help-tip" aria-label={`About ${label}`} aria-describedby={open?id:undefined} aria-expanded={open} onMouseEnter={show} onMouseLeave={leave} onFocus={show} onBlur={close} onClick={e=>{e.preventDefault();e.stopPropagation();show();}}>?</button>{open&&createPortal(<div ref={tooltip} id={id} role="tooltip" className="studio-tooltip" style={position} onMouseEnter={show} onMouseLeave={leave}>{children}</div>,document.body)}</>;
}

export function SelectField({label,hint,value,onChange,children,disabled}){
  const id=useId();
  return <div className="real-control"><div className="field-heading"><label htmlFor={id}>{label}</label>{hint&&<HelpTip label={label}>{hint}</HelpTip>}</div><select id={id} aria-label={label} value={value} onChange={onChange} disabled={disabled}>{children}</select></div>;
}

export function ThemeToggle(){
  const [theme,setTheme]=useState(()=>{try{return localStorage.getItem('last-light-theme')==='dark'?'dark':'light';}catch{return 'light';}});
  useEffect(()=>{document.documentElement.dataset.theme=theme;document.documentElement.style.colorScheme=theme;document.querySelector('meta[name="theme-color"]')?.setAttribute('content',theme==='dark'?'#161b1c':'#ffffff');try{localStorage.setItem('last-light-theme',theme);}catch{}},[theme]);
  return <button className="studio-theme-toggle" type="button" aria-label={`Switch to ${theme==='light'?'dark':'light'} mode`} aria-pressed={theme==='dark'} onClick={()=>setTheme(t=>t==='light'?'dark':'light')}><StudioIcon name={theme==='light'?'moon':'sun'} size={17}/><span>{theme==='light'?'Dark':'Light'}</span></button>;
}

export function ReadabilityToggle(){
  const [large,setLarge]=useState(()=>{try{return localStorage.getItem('last-light-readable')==='true';}catch{return false;}});
  useEffect(()=>{document.documentElement.dataset.readable=String(large);try{localStorage.setItem('last-light-readable',String(large));}catch{}},[large]);
  return <button type="button" className="studio-theme-toggle" aria-label="Larger text and controls" aria-pressed={large} onClick={()=>setLarge(v=>!v)}>Aa<span>{large?'Standard size':'Larger text'}</span></button>;
}

export const fieldHelp={
  originalLat:'Latitude of the original study point. Negative values are south of the lunar equator.',
  originalLon:'East-positive longitude of the original point. The point must fit inside the mapped study footprint.',
  landingUTC:'Landing time of the original plan, in UTC. This is separate from the allowed alternative landing window.',
  earliestUTC:'Earliest allowed landing time for an alternative. Enter the mission-plan arrival time in UTC, not the launch time.',
  latestUTC:'Latest allowed alternative landing time, in UTC. The search window can span up to 72 hours.',
  durationH:'Time to analyze on the lunar surface after each landing. The current study supports 1 to 168 hours.',
  radiusM:'Maximum surface distance from the original location to search. This does not establish flight reachability.',
  exclusionRadiusM:'Radius around the original location excluded when the original-location exclusion is enabled.',
  maxSlopeDeg:'Maximum regional slope over a 50 m fitted patch. This does not resolve footpad-scale tilt or rocks.',
  maxReliefM:'Largest allowed height difference across the 50 m patch.',
  minAreaM2:'Minimum connected mapped area meeting the slope limit. Connected area does not prove a clear landing footprint.',
  maxHeightRmsM:'Maximum published elevation RMS allowed for data-quality screening. Lower values mean less reported height uncertainty.',
  observerHeightM:'Height above the elevation model used for the Sun, Earth and terrain-horizon calculations.',
  capacityWh:'Usable energy the battery can store, in watt-hours.',initialPercent:'Battery charge at landing, as a percentage of usable capacity.',
  loadW:'Assumed constant electrical demand during modeled surface operation, in watts.',
  generationW:'Entered constant output while the Sun centre is visible. This comparison mode omits panel-incidence calculations.',
  reservePercent:'Minimum battery charge required during the modeled mission. Falling below it fails the power requirement.',
  maxEarthHiddenH:'Longest allowed continuous interval with Earth hidden by terrain. Visible Earth alone does not verify a radio link.',
  minAverageSolarPercent:'Minimum archived NASA long-term any-disc sunlight frequency. This is not the selected mission’s sunlight duration.',
  minAverageEarthPercent:'Minimum archived NASA long-term any-disc Earth visibility. This is not verified ground-station availability.',
  panelAreaM2:'Total active solar-panel collecting area in square metres.',
  panelEfficiencyPercent:'Fraction of incident panel energy converted to electricity before the entered electrical losses.',
  panelLossPercent:'Combined electrical losses after conversion, expressed as a percentage.',
  panelTiltDeg:'Angle of a fixed panel above the local horizontal: 0° is horizontal and 90° is vertical.',
  panelAzimuthDeg:'Direction a fixed panel faces, clockwise from local north.',
  irradianceAt1AU:'Reference solar flux at one astronomical unit. Sun-distance scaling is calculated separately; this is an entered assumption.'
};
