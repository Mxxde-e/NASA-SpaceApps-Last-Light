import test from 'node:test';
import assert from 'node:assert/strict';
import {createDictation} from '../src/components/dictation.js';
import {runStudy,selectionRequest} from '../src/components/study-client.js';

test('autofill pins the chosen site and time while preserving engineering requirements',()=>{
  const request={durationH:72,loadW:80,requireKnownGround:true,excludeOriginal:true,changeType:'both'};
  const selected={point:{latitude:-89.5,longitude:-140},landingUTC:'2026-11-18T12:00:00Z'};
  const actual=selectionRequest(request,selected);
  assert.equal(actual.originalLat,selected.point.latitude);assert.equal(actual.originalLon,selected.point.longitude);
  assert.equal(actual.landingUTC,selected.landingUTC);assert.equal(actual.earliestUTC,actual.latestUTC);assert.equal(actual.changeType,'time');assert.equal(actual.excludeOriginal,false);
  assert.equal(actual.durationH,72);assert.equal(actual.loadW,80);assert.equal(actual.requireKnownGround,true);assert.equal(request.excludeOriginal,true);
});

test('dictation appends editable text, never submits, and stops updating after disposal',()=>{
  let recognition,text='',states=[];
  class FakeRecognition{constructor(){recognition=this;}start(){this.onstart();}stop(){this.onend();}abort(){this.aborted=true;}}
  const voice=createDictation(FakeRecognition,{onText:v=>text=v,onState:v=>states.push(v),onError:()=>{}});
  voice.start('Find');recognition.onresult({results:[[{transcript:'a site on November 18'}]]});assert.equal(text,'Find a site on November 18');
  voice.stop();assert.equal(states.at(-1),false);voice.dispose();assert.equal(recognition.onresult,null);assert.equal(recognition.aborted,true);
});
test('permission denial and recognition start errors leave typed input available',()=>{
  let recognition,error,state;
  class FakeRecognition{constructor(){recognition=this;}start(){throw new Error('device');}abort(){}}
  const voice=createDictation(FakeRecognition,{onText:()=>assert.fail('must not alter draft'),onState:v=>state=v,onError:v=>error=v});
  voice.start();assert.equal(state,false);assert.match(error,/Type/);
  recognition.onerror({error:'not-allowed'});assert.match(error,/denied/);voice.dispose();
});
test('study client uses backend result and reports failures rather than invented candidates',async()=>{
  const original=globalThis.fetch,calls=[];
  try{
    const expected={candidates:[{id:'actual'}]};
    globalThis.fetch=async(path,options)=>{calls.push({path,options});return {ok:true,json:async()=>path==='/api/search'?{jobId:'verified'}:{status:'complete',result:expected}};};
    assert.deepEqual(await runStudy({durationH:24},{signal:new AbortController().signal,onProgress:()=>{}}),expected);
    assert.equal(calls[0].path,'/api/search');assert.equal(JSON.parse(calls[0].options.body).durationH,24);assert.equal(calls[1].path,'/api/jobs/verified');
    globalThis.fetch=async path=>({ok:true,json:async()=>path==='/api/search'?{jobId:'failure'}:{status:'failed',error:'Unsupported coordinates'}});
    await assert.rejects(()=>runStudy({},{signal:new AbortController().signal,onProgress:()=>{}}),/Unsupported coordinates/);
  }finally{globalThis.fetch=original;}
});
