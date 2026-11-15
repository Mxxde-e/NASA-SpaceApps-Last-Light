"""Local-only HTTP service. Run from the project root with python -m backend.server."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import json
import threading
import time
import uuid
import traceback
from fastapi import FastAPI,HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from .analysis import Engine,StudyRequest,ALGORITHM_VERSION
from .terrain import ROOT,DATA
from .chat import router as chat_router

executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='lunar-analysis')
engine_future=None
jobs={}
jobs_lock=threading.Lock()

@asynccontextmanager
async def lifespan(app):
    global engine_future
    engine_future=executor.submit(Engine)
    yield
    executor.shutdown(wait=False,cancel_futures=True)

app=FastAPI(title='Last Light real-data regional study',version='4.0.0',lifespan=lifespan)

app.include_router(chat_router)

def engine():
    if engine_future is None or not engine_future.done(): raise HTTPException(503,'Loading real terrain and SPICE kernels. Please wait.')
    try: return engine_future.result()
    except Exception as error: raise HTTPException(503,f'Real data unavailable: {error}. Run python -m backend.acquire first.')

@app.get('/api/study')
def study():
    service=engine()
    terrain=service.terrain.metadata()
    terrain['defaultPoint']=service.point(terrain['defaultPoint']['longitude'],terrain['defaultPoint']['latitude'])
    return {'terrain':terrain,'screening':service.screening.metadata(),'geometry':service.geometry.metadata(),'nowUTC':datetime.now(timezone.utc).isoformat().replace('+00:00','Z')}

@app.get('/api/map.png')
def map_image(layer:str='terrain'):
    service=engine()
    try: png=service.terrain.png if layer=='terrain' else service.screening.map_png(layer)
    except ValueError as error: raise HTTPException(422,str(error))
    return Response(png,media_type='image/png',headers={'Cache-Control':'public,max-age=3600'})

@app.get('/api/point')
def point(lon:float,lat:float):
    try: return engine().point(lon,lat)
    except ValueError as error: raise HTTPException(422,str(error))

@app.get('/api/terrain-mesh')
def terrain_mesh():
    return engine().terrain.display_mesh()

@app.get('/api/evidence')
def evidence():
    from .evidence import geometry_evidence
    return geometry_evidence(engine().geometry)

def run_job(identifier,request):
    try:
        service=engine()
        manifest=service.terrain.manifest['assets']
        fingerprint=ALGORITHM_VERSION+'|'+json.dumps(request.model_dump(),sort_keys=True)+'|'+'|'.join(e['sha256'] for _,e in sorted(manifest.items()))
        key=hashlib.sha256(fingerprint.encode()).hexdigest()
        path=DATA/'cache'/f'result-{key}.json'
        def progress(value): jobs[identifier]['progress']=value
        if path.exists():
            progress('Loading a checksum-matched cached result')
            result=json.loads(path.read_text()); result['cached']=True
        else:
            result=service.search(request,progress); result['cached']=False
            temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(result,allow_nan=False));temporary.replace(path)
        jobs[identifier].update(status='complete',result=result,progress='Calculation complete')
    except Exception as error:
        traceback.print_exc()
        jobs[identifier].update(status='failed',error=str(error),progress='Calculation failed; no results are treated as passing.')

@app.post('/api/search')
def start_search(request:StudyRequest):
    engine()
    with jobs_lock:
        if any(j['status']=='running' for j in jobs.values()): raise HTTPException(429,'A calculation is already running. Wait for it to finish.')
        if len(jobs)>12:
            for key in list(jobs)[:-6]: jobs.pop(key)
        identifier=uuid.uuid4().hex
        jobs[identifier]={'status':'running','progress':'Queued real-data analysis','started':time.time()}
        executor.submit(run_job,identifier,request)
    return {'jobId':identifier,'status':'running'}

@app.get('/api/jobs/{identifier}')
def get_job(identifier:str):
    if identifier not in jobs: raise HTTPException(404,'Calculation not found. Start a new search.')
    job=jobs[identifier]
    return {k:v for k,v in job.items() if k!='started'}|{'elapsedSeconds':time.time()-job['started']}

if (ROOT/'dist').exists(): app.mount('/',StaticFiles(directory=ROOT/'dist',html=True),name='frontend')

if __name__=='__main__':
    import uvicorn
    uvicorn.run('backend.server:app',host='127.0.0.1',port=8000,workers=1)
