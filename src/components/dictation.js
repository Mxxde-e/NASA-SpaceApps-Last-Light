// Browser speech recognition is opt-in and only fills an editable draft.
export function createDictation(Recognition,{onText,onState,onError}){
  const recognition=new Recognition();let active=false,disposed=false,base='';
  recognition.lang='en-US';recognition.continuous=false;recognition.interimResults=true;
  recognition.onstart=()=>{if(!disposed){active=true;onState(true);}};
  recognition.onresult=event=>{
    if(disposed)return;
    const text=Array.from(event.results,result=>result[0]?.transcript||'').join(' ');
    onText(`${base}${base&&text?' ':''}${text}`.slice(0,1200));
  };
  recognition.onerror=event=>{if(!disposed){onError(event.error==='not-allowed'?'Microphone permission was denied. You can still type your question.':event.error==='no-speech'?'No speech detected. Try again or type your question.':'Voice input could not finish. You can still type your question.');}};
  recognition.onend=()=>{active=false;if(!disposed)onState(false);};
  return {
    start(text=''){if(disposed||active)return; base=text;active=true;onState(true);try{recognition.start();}catch{active=false;onState(false);onError('Voice input is unavailable. Type your question instead.');}},
    stop(){if(active)recognition.stop();},
    dispose(){disposed=true;active=false;recognition.onresult=null;recognition.onerror=null;recognition.onend=null;recognition.onstart=null;recognition.abort();}
  };
}
