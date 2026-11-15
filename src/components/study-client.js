export function selectionRequest(request,scenario){
  return {...request,originalLat:scenario.point.latitude,originalLon:scenario.point.longitude,landingUTC:scenario.landingUTC,earliestUTC:scenario.landingUTC,latestUTC:scenario.landingUTC,changeType:'time',excludeOriginal:false};
}
export async function requestJSON(path,body,signal){
  const response=await fetch(path,{signal,...(body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{})});
  const data=await response.json();
  if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Check the mission settings and try again.');
  return data;
}
export async function runStudy(plan,{signal,onProgress}){
  const job=await requestJSON('/api/search',plan,signal);
  for(;;){
    const status=await requestJSON(`/api/jobs/${encodeURIComponent(job.jobId)}`,null,signal);
    if(status.status==='complete')return status.result;
    if(status.status==='failed')throw new Error(status.error||'The calculation failed.');
    onProgress(status.progress||'Calculating real geometry…');
    await new Promise((resolve,reject)=>{
      const abort=()=>{clearTimeout(timer);reject(new DOMException('Stopped waiting','AbortError'));};
      const timer=setTimeout(()=>{signal.removeEventListener('abort',abort);resolve();},1000);
      signal.addEventListener('abort',abort,{once:true});if(signal.aborted)abort();
    });
  }
}
