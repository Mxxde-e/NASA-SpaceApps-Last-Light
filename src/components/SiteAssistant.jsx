import React,{useEffect,useRef,useState} from 'react';
import guide from '../../backend/site_guide.json';
import './SiteAssistant.css';

const welcome={role:'assistant',content:'Need a hand? I can explain Last Light and help you find the right controls. I cannot run searches or choose a landing site.'};
const targets={setup:['assistant-setup','mission'],terrain:['assistant-terrain'],comparison:['assistant-comparison','comparison'],sources:['assistant-sources','method']};
export default function SiteAssistant({mode}){
  const [open,setOpen]=useState(false),[messages,setMessages]=useState([welcome]),[question,setQuestion]=useState(''),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
  const input=useRef(null),toggle=useRef(null),end=useRef(null),controller=useRef(null);
  useEffect(()=>{controller.current?.abort();controller.current=null;setMessages([welcome]);setBusy(false);setNotice('');},[mode]);
  useEffect(()=>{if(open)input.current?.focus();},[open]);
  useEffect(()=>{end.current?.scrollIntoView({block:'nearest'});},[messages,busy]);
  useEffect(()=>()=>controller.current?.abort(),[]);
  function close(){setOpen(false);toggle.current?.focus();}
  function navigate(section){
    const el=(targets[section]||[]).map(id=>document.getElementById(id)).find(Boolean);
    if(!el){setNotice('Run a study first to reveal its comparisons, or switch to Real-data study.');return;}
    if(el.tagName==='DETAILS')el.open=true;
    el.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
    el.focus({preventScroll:true});close();
  }
  async function ask(text){
    text=text.trim();if(!text||busy||text.length>1200)return;
    const history=messages.slice(1).slice(-6).map(({role,content})=>({role,content:content.slice(0,1200)}));
    setMessages(m=>[...m.slice(-19),{role:'user',content:text}]);setQuestion('');setNotice('');setBusy(true);
    const abort=new AbortController();controller.current=abort;
    const timer=setTimeout(()=>abort.abort(),22000);
    try{
      const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,history,mode}),signal:abort.signal});
      if(!response.ok)throw new Error('Chat unavailable');
      const data=await response.json();
      if(typeof data.answer!=='string'||!['guide','ai'].includes(data.mode))throw new Error('Invalid answer');
      if(controller.current!==abort)return;
      setMessages(m=>[...m,{role:'assistant',content:data.answer.slice(0,2400),section:targets[data.section]?data.section:null,label:data.mode==='ai'?'AI answer · verify against the site':'Verified site guide'}]);
      setNotice(data.notice||'');
    }catch{
      if(controller.current!==abort)return;
      const words=new Set(text.toLowerCase().replaceAll('?','').split(/\s+/));
      const entry=[...guide].sort((a,b)=>b.keywords.filter(w=>words.has(w)).length-a.keywords.filter(w=>words.has(w)).length)[0];
      setMessages(m=>[...m,{role:'assistant',content:entry.answer,section:entry.section,label:'Verified site guide'}]);
      setNotice('AI connection unavailable. Site help still works.');
    }finally{clearTimeout(timer);if(controller.current===abort)setBusy(false);}
  }
  return <aside className="site-assistant" aria-label="Last Light help">
    {open&&<section id="site-assistant-panel" role="dialog" aria-modal="false" aria-labelledby="site-assistant-title" className="site-assistant-panel" onKeyDown={e=>{if(e.key==='Escape')close();}}>
      <header><div><strong id="site-assistant-title">Ask Last Light</strong><small>Site help · {mode==='real'?'Real-data study':'Simulated demo'}</small></div><button type="button" aria-label="Close site help" onClick={close}>×</button></header>
      <p className="site-assistant-privacy">Questions may be sent to an AI provider when enabled. Do not enter personal information or API keys.</p>
      <div className="site-assistant-messages" role="log" aria-live="polite" aria-relevant="additions" tabIndex="0">
        {messages.map((m,i)=><article key={i} className={`site-assistant-message ${m.role}`}><small>{m.role==='user'?'You':m.label||'Last Light guide'}</small><p>{m.content}</p>{m.section&&<button type="button" onClick={()=>navigate(m.section)}>Go to {m.section==='setup'?'mission setup':m.section==='sources'?'method & sources':m.section} →</button>}</article>)}
        {busy&&<p role="status">Looking up site help…</p>}<div ref={end}/>
      </div>
      <div className="site-assistant-suggestions">{guide.slice(0,4).map(g=><button type="button" key={g.id} disabled={busy} onClick={()=>ask(g.title)}>{g.title}</button>)}</div>
      {notice&&<p role="status" className="site-assistant-notice">{notice}</p>}
      <form onSubmit={e=>{e.preventDefault();ask(question);}}><label htmlFor="site-assistant-question">Ask about this website</label><div><input ref={input} id="site-assistant-question" value={question} maxLength={1200} onChange={e=>setQuestion(e.target.value)} placeholder="How do I compare landing dates?" autoComplete="off"/><button type="submit" disabled={busy||!question.trim()}>Send</button></div></form>
      <footer><span>Help, not flight advice.</span><button type="button" disabled={busy} onClick={()=>{setMessages([welcome]);setNotice('');}}>Clear chat</button></footer>
    </section>}
    <button ref={toggle} type="button" className="site-assistant-toggle" aria-label={open?'Close site help panel':'Ask Last Light'} aria-expanded={open} aria-controls="site-assistant-panel" onClick={()=>open?close():setOpen(true)}><span aria-hidden="true">✦ </span>{open?'Close help':'Ask Last Light'}</button>
  </aside>;
}
