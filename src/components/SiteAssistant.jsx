import React,{useEffect,useRef,useState} from 'react';
import guide from '../../backend/site_guide.json';
import './SiteAssistant.css';
import {StudioIcon} from './StudioUI.jsx';
import {PlanReview,ResultOptions} from './MissionPlanner.jsx';
import {createDictation} from './dictation.js';
import {requestJSON,runStudy} from './study-client.js';

const welcome={role:'assistant',content:'I can explain Last Light or help plan a real-data study. Ask for a landing date and requirements, then review settings before calculating. Results cover Connecting Ridge; ground safety remains unassessed.'};
const targets={setup:['assistant-setup','mission'],terrain:['assistant-terrain'],comparison:['assistant-comparison','comparison'],sources:['assistant-sources','method']};
const wantsPlan=text=>/\b(best|find|recommend|calculate|plan)\b/i.test(text)&&/\b(land|landing|site|sites|study)\b/i.test(text)&&!/^how (do|does)\b/i.test(text);
export default function SiteAssistant({mode,missionContext,onApply}){
  const [open,setOpen]=useState(false),[messages,setMessages]=useState([welcome]),[question,setQuestion]=useState(''),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
  const [planner,setPlanner]=useState(null),[result,setResult]=useState(null),[progress,setProgress]=useState(''),[listening,setListening]=useState(false),[voiceSupported,setVoiceSupported]=useState(false);
  const input=useRef(null),toggle=useRef(null),end=useRef(null),controller=useRef(null),dictation=useRef(null),resultsStart=useRef(null);
  const stopVoice=()=>{dictation.current?.dispose();dictation.current=null;setListening(false);};
  useEffect(()=>{setVoiceSupported(!!(window.SpeechRecognition||window.webkitSpeechRecognition));},[]);
  useEffect(()=>{controller.current?.abort();controller.current=null;stopVoice();setMessages([welcome]);setPlanner(null);setResult(null);setBusy(false);setProgress('');setNotice('');},[mode]);
  useEffect(()=>{if(open)input.current?.focus();},[open]);
  useEffect(()=>{end.current?.scrollIntoView({block:'nearest'});},[messages,busy,planner,result]);
  useEffect(()=>{if(result)resultsStart.current?.scrollIntoView({block:'start'});},[result]);
  useEffect(()=>()=>{controller.current?.abort();dictation.current?.dispose();},[]);
  function close(){stopVoice();setOpen(false);toggle.current?.focus();}
  function navigate(section){
    const el=(targets[section]||[]).map(id=>document.getElementById(id)).find(Boolean);
    if(!el){setNotice('Run a study first to reveal its comparisons, or switch to Real-data study.');return;}
    if(el.tagName==='DETAILS')el.open=true;
    el.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});el.focus({preventScroll:true});close();
  }
  async function prepare(text='',draft=planner?.draft||{}){
    if(busy)return;
    if(mode!=='real'){setNotice('Switch to Real-data study to calculate real landing options.');return;}
    if(!missionContext?.form){setNotice('Wait for the real-data workspace to load, then try again.');return;}
    stopVoice();setBusy(true);setNotice('');setResult(null);
    const abort=new AbortController();controller.current=abort;const timer=setTimeout(()=>abort.abort(),22000);
    try{
      const data=await requestJSON('/api/chat/prepare',{message:text,draft,context:missionContext.form},abort.signal);
      if(controller.current!==abort)return;
      if(data.mode!=='planner'||typeof data.answer!=='string')throw new Error('Invalid planner response.');
      setPlanner(data);setMessages(m=>[...m.slice(-19),...(text?[{role:'user',content:text}]:[]),{role:'assistant',content:data.answer,label:'Mission settings · review required'}]);
    }catch(error){if(controller.current===abort)setNotice(error.name==='AbortError'?'The planner timed out. No study was started.':error.message||'Planner unavailable. Use the mission form.');}
    finally{clearTimeout(timer);if(controller.current===abort)setBusy(false);}
  }
  async function calculate(plan){
    if(busy||missionContext?.busy)return;
    setBusy(true);setNotice('');setResult(null);setProgress('Starting real NASA/SPICE calculation…');
    const abort=new AbortController();controller.current=abort;
    try{
      const data=await runStudy(plan,{signal:abort.signal,onProgress:setProgress});if(controller.current!==abort)return;
      setResult(data);setMessages(m=>[...m.slice(-19),{role:'assistant',content:'Calculation complete. These options come from the real-data engine under the reviewed settings.',label:'Computed results'}]);
    }catch(error){if(controller.current===abort)setNotice(error.name==='AbortError'?'Stopped waiting. A submitted backend calculation continues; wait before starting another study.':error.message);}
    finally{if(controller.current===abort){setBusy(false);setProgress('');}}
  }
  async function ask(text){
    text=text.trim();if(!text||busy||listening||text.length>1200)return;setQuestion('');
    if(planner||wantsPlan(text)){await prepare(text);return;}
    const history=messages.slice(1).slice(-6).map(({role,content})=>({role,content:content.slice(0,1200)}));
    setMessages(m=>[...m.slice(-19),{role:'user',content:text}]);setNotice('');setBusy(true);
    const abort=new AbortController();controller.current=abort;const timer=setTimeout(()=>abort.abort(),22000);
    try{
      const data=await requestJSON('/api/chat',{message:text,history,mode},abort.signal);
      if(typeof data.answer!=='string'||!['guide','ai'].includes(data.mode))throw new Error('Invalid answer');if(controller.current!==abort)return;
      setMessages(m=>[...m,{role:'assistant',content:data.answer.slice(0,2400),section:targets[data.section]?data.section:null,label:data.mode==='ai'?'AI answer · verify against the site':'Verified site guide'}]);setNotice(data.notice||'');
    }catch{
      if(controller.current!==abort)return;
      const words=new Set(text.toLowerCase().replaceAll('?','').split(/\s+/));const entry=[...guide].sort((a,b)=>b.keywords.filter(w=>words.has(w)).length-a.keywords.filter(w=>words.has(w)).length)[0];
      setMessages(m=>[...m,{role:'assistant',content:entry.answer,section:entry.section,label:'Verified site guide'}]);setNotice('AI connection unavailable. Site help still works.');
    }finally{clearTimeout(timer);if(controller.current===abort)setBusy(false);}
  }
  function voice(){
    if(listening){dictation.current?.stop();return;}stopVoice();setNotice('');
    const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;if(!Recognition){setNotice('Voice input unavailable. You can still type.');return;}
    try{dictation.current=createDictation(Recognition,{onText:setQuestion,onState:setListening,onError:setNotice});dictation.current.start(question);}catch{setListening(false);setNotice('Voice input is unavailable. Type your question instead.');}
  }
  const clear=()=>{stopVoice();setMessages([welcome]);setPlanner(null);setResult(null);setQuestion('');setNotice('');};
  return <aside className="site-assistant" aria-label="Last Light help">
    {open&&<section id="site-assistant-panel" role="dialog" aria-modal="false" aria-labelledby="site-assistant-title" className="site-assistant-panel" onKeyDown={e=>{if(e.key==='Escape')close();}}>
      <header><div><strong id="site-assistant-title">Ask Last Light</strong><small>{planner?'Mission planner':'Site help'} · {mode==='real'?'Real-data study':'Simulated demo'}</small></div><button type="button" aria-label="Close site help" onClick={close}>×</button></header>
      <p className="site-assistant-privacy">Questions may be sent to an AI provider when enabled. Voice uses your browser’s recognition service and may send audio online. Review dictated text before Send. Do not enter personal information or keys.</p>
      <div className="site-assistant-messages" role="log" aria-live="polite" aria-relevant="additions" tabIndex="0">
        {messages.map((m,i)=><article key={i} className={`site-assistant-message ${m.role}`}><small>{m.role==='user'?'You':m.label||'Last Light guide'}</small><p>{m.content}</p>{m.section&&<button type="button" onClick={()=>navigate(m.section)}>Go to {m.section==='setup'?'mission setup':m.section==='sources'?'method & sources':m.section} →</button>}</article>)}
        {planner&&!result&&<PlanReview key={JSON.stringify(planner.draft)} {...planner} busy={busy||missionContext?.busy} onReview={draft=>prepare('',draft)} onCalculate={calculate}/>}
        {result&&<div ref={resultsStart}><ResultOptions result={result} disabled={busy||missionContext?.busy||mode!=='real'} onApply={selection=>{onApply(selection);close();}}/></div>}
        {busy&&<p role="status">{progress||'Looking up site help…'}</p>}<div ref={end}/>
      </div>
      <div className="site-assistant-suggestions">{planner?<button type="button" disabled={busy} onClick={()=>{setPlanner(null);setResult(null);setNotice('');}}>Exit planner</button>:<><button type="button" disabled={busy||mode!=='real'} onClick={()=>prepare()}>Plan a real study</button>{guide.slice(0,4).map(g=><button type="button" key={g.id} disabled={busy} onClick={()=>ask(g.title)}>{g.title}</button>)}</>}{progress&&<button type="button" onClick={()=>controller.current?.abort()}>Stop waiting</button>}</div>
      {notice&&<p role="status" className="site-assistant-notice">{notice}</p>}
      <form onSubmit={e=>{e.preventDefault();ask(question);}}><label htmlFor="site-assistant-question">Ask about this website or a mission</label><div><input ref={input} id="site-assistant-question" value={question} maxLength={1200} onChange={e=>setQuestion(e.target.value)} placeholder="Best site on 2026-11-18?" autoComplete="off" disabled={listening}/><button type="button" className="chat-mic" aria-label={listening?'Stop dictation':'Start voice input'} aria-pressed={listening} disabled={!voiceSupported||busy} onClick={voice}>{listening?'Stop':'Mic'}</button><button type="submit" disabled={busy||listening||!question.trim()}>Send</button></div><small role="status">{listening?'Listening… Stop to review your text.':!voiceSupported?'Voice input unavailable in this browser; typing is available.':'Voice fills this field; it never sends automatically.'}</small></form>
      <footer><span>Investigation, not flight advice.</span><button type="button" disabled={busy} onClick={clear}>Clear chat</button></footer>
    </section>}
    <button ref={toggle} type="button" className="site-assistant-toggle" aria-label={open?'Close site help panel':'Ask Last Light'} aria-expanded={open} aria-controls="site-assistant-panel" onClick={()=>open?close():setOpen(true)}><StudioIcon name="chat" size={17}/>{open?'Close help':'Ask Last Light'}</button>
  </aside>;
}
