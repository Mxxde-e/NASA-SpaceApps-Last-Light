"""Bounded real-coordinate search, event refinement and physical energy integration."""
from datetime import datetime,timezone
import time
import math
import numpy as np
from pydantic import BaseModel,Field,model_validator
from .terrain import Terrain,PATCH_BOUNDS
from .geometry import Geometry,parse_utc,iso_utc
from .numerics import circular_interpolate,visibility,integrate_battery,longest_interval,great_circle_m,refine_zero
from .screening import Screening
from .solar import panel_power

ALGORITHM_VERSION='real-v3.1'

class StudyRequest(BaseModel):
    originalLat:float=Field(default=-89.46316,ge=-90,le=90)
    originalLon:float=Field(default=-137.50198,ge=-180,le=360)
    landingUTC:str
    earliestUTC:str
    latestUTC:str
    durationH:float=Field(default=72,ge=1,le=168)
    changeType:str='both'
    excludeOriginal:bool=False
    exclusionRadiusM:float=Field(default=100,ge=0,le=1000)
    radiusM:float=Field(default=2500,ge=0,le=5000)
    maxSlopeDeg:float=Field(default=12,ge=0,le=30)
    maxReliefM:float=Field(default=15,ge=0,le=100)
    minAreaM2:float=Field(default=2500,ge=2500,le=1000000)
    maxHeightRmsM:float=Field(default=2,ge=.05,le=20)
    observerHeightM:float=Field(default=2,ge=.5,le=10)
    capacityWh:float=Field(default=12000,ge=1,le=100000)
    initialPercent:float=Field(default=90,ge=0,le=100)
    loadW:float=Field(default=50,ge=0,le=5000)
    generationW:float=Field(default=200,ge=0,le=10000)
    reservePercent:float=Field(default=20,ge=0,le=100)
    maxEarthHiddenH:float=Field(default=72,ge=0,le=168)
    requireKnownGround:bool=False
    minAverageSolarPercent:float=Field(default=0,ge=0,le=100)
    minAverageEarthPercent:float=Field(default=0,ge=0,le=100)
    excludePermanentShadow:bool=True
    earthVisibilityMode:str='centre'
    powerModel:str='constant' # Backwards-compatible API; the interface defaults to panel.
    panelAreaM2:float=Field(default=1,gt=0,le=100)
    panelEfficiencyPercent:float=Field(default=25,ge=0,le=100)
    panelLossPercent:float=Field(default=15,ge=0,le=100)
    panelTiltDeg:float=Field(default=90,ge=0,le=90)
    panelAzimuthDeg:float=Field(default=0,ge=0,le=360)
    panelTracking:str='sun'
    irradianceAt1AU:float=Field(default=1361,ge=0,le=2000)

    @model_validator(mode='after')
    def date_and_mode_validation(self):
        a,b,c=[parse_utc(v).timestamp() for v in [self.landingUTC,self.earliestUTC,self.latestUTC]]
        if b>c: raise ValueError('Earliest landing must precede latest landing.')
        if c-b>72*3600: raise ValueError('Pilot landing search spans at most 72 hours.')
        if self.changeType not in ('time','site','both'): raise ValueError('Choose time, site or both.')
        if self.powerModel not in ('constant','panel'): raise ValueError('Choose constant or panel power.')
        if self.panelTracking not in ('sun','fixed'): raise ValueError('Choose fixed pointing or ideal Sun tracking.')
        if self.earthVisibilityMode not in ('centre','any'): raise ValueError('Choose Earth centre or any-disc visibility.')
        if self.excludeOriginal and self.changeType=='time': raise ValueError('An excluded original location requires a site change.')
        for t in [a,b,c]:
            if abs(t/60-round(t/60))>1e-6: raise ValueError('Use whole-minute UTC landing times.')
        return self

def geometry_sample(geometry,point,height,horizon,timestamp,request=None):
    value=dict(geometry.point_at(point,height,timestamp))
    for body in ['sun','earth']:
        az=value[body+'Az']
        low=circular_interpolate(az,horizon['azimuth'],horizon['low'])
        high=circular_interpolate(az,horizon['azimuth'],horizon['high'])
        nominal=circular_interpolate(az,horizon['azimuth'],horizon['nominal'])
        centre=visibility(value[body+'El'],low,high)
        any_disc=visibility(value[body+'El']+value.get(body+'AngularRadiusDeg',0),low,high)
        value[body+'CentreState']=centre; value[body+'AnyState']=any_disc
        value[body+'State']=any_disc if body=='earth' and request and request.earthVisibilityMode=='any' else centre
        value[body+'HorizonLow']=low; value[body+'HorizonHigh']=high
        value[body+'Horizon']=nominal
    if request and request.powerModel=='panel': value.update(panel_power(value,request))
    return value

def build_series(geometry,point,height,horizon,start,end,step_s=300,request=None):
    if request and request.powerModel=='panel': step_s=min(step_s,60)
    base=np.unique(np.r_[np.arange(start,end,step_s),end])
    samples={float(t):geometry_sample(geometry,point,height,horizon,float(t),request) for t in base}
    added=[]
    for a,b in zip(base[:-1],base[1:]):
        for body in ['sun','earth']:
            for boundary in ['Low','High']:
                key=body+'Horizon'+boundary
                def margin(value):
                    radius=value.get('earthAngularRadiusDeg',0) if body=='earth' and request and request.earthVisibilityMode=='any' else 0
                    return value[body+'El']+radius-value[key]
                fa=margin(samples[float(a)]); fb=margin(samples[float(b)])
                if fa*fb<0:
                    def fn(hour):
                        t=start+hour*3600
                        value=geometry_sample(geometry,point,height,horizon,t,request)
                        return margin(value)
                    root=start+refine_zero(fn,(a-start)/3600,(b-start)/3600)*3600
                    added.append(root)
    times=np.unique(np.r_[base,added])
    # Classify each interval at its midpoint after inserting all bracketed sensitivity transitions.
    midpoints=[geometry_sample(geometry,point,height,horizon,float((a+b)/2),request) for a,b in zip(times[:-1],times[1:])]
    return {'times':times,'states':midpoints,'start':start,'end':end,'transitionCount':len(added),'stepSeconds':step_s}

def interval_slice(series,landing,duration):
    stop=landing+duration*3600
    result=[]
    for i,(a,b) in enumerate(zip(series['times'][:-1],series['times'][1:])):
        left=max(a,landing); right=min(b,stop)
        if right<=left: continue
        result.append({'startH':float((left-landing)/3600),'endH':float((right-landing)/3600),
                       'sunState':series['states'][i]['sunState'],'earthState':series['states'][i]['earthState'],
                       **{k:series['states'][i][k] for k in ['generationLowW','generationHighW'] if k in series['states'][i]}})
    if not result or abs(sum(p['endH']-p['startH'] for p in result)-duration)>1e-7: raise ValueError('Incomplete mission geometry coverage.')
    return result

def evaluate_series(point,horizon,series,landing,request,terrain_violations,terrain_uncertain,original_landing):
    duration=request.durationH
    intervals=interval_slice(series,landing,duration)
    hours=lambda body,state:float(sum(p['endH']-p['startH'] for p in intervals if p[body+'State']==state))
    low=integrate_battery(intervals,request.capacityWh,request.initialPercent,request.loadW,request.generationW,request.reservePercent)
    high=integrate_battery(intervals,request.capacityWh,request.initialPercent,request.loadW,request.generationW,request.reservePercent,True)
    dark_lo=longest_interval(intervals,lambda p:p['sunState']=='hidden',duration)
    dark_hi=longest_interval(intervals,lambda p:p['sunState']!='visible',duration)
    earth_lo=longest_interval(intervals,lambda p:p['earthState']=='hidden',duration)
    earth_hi=longest_interval(intervals,lambda p:p['earthState']!='visible',duration)
    violations=list(terrain_violations); uncertain=list(terrain_uncertain)
    if any(p[body+'State']=='unknown' for p in intervals for body in ('sun','earth')):
        uncertain.append('Missing visibility data: selected requirements are not fully assessed.')
    if request.powerModel=='panel' and any('generationLowW' not in p or 'generationHighW' not in p for p in intervals):
        uncertain.append('Missing panel-generation data: power is not assessed.')
    if high['minimumPercent']<request.reservePercent or high['depletionH'] is not None: violations.append('Even the optimistic sensitivity case violates battery reserve or depletes.')
    elif low['minimumPercent']<request.reservePercent or low['depletionH'] is not None: uncertain.append('Power requirement depends on terrain/visibility uncertainty.')
    if earth_lo['hours']>request.maxEarthHiddenH: violations.append('Earth-hidden interval exceeds the entered limit even in the favorable case.')
    elif earth_hi['hours']>request.maxEarthHiddenH: uncertain.append('Earth-hidden limit depends on the horizon sensitivity case.')
    selected_pass=not violations and not uncertain
    return {'point':point,'landingUTC':iso_utc(landing),'landingTimestamp':landing,'durationH':duration,
            'scheduleShiftH':(landing-original_landing)/3600,'intervals':intervals,
            'metrics':{'sunVisibleH':[hours('sun','visible'),hours('sun','visible')+hours('sun','uncertain')],
                       'earthVisibleH':[hours('earth','visible'),hours('earth','visible')+hours('earth','uncertain')],
                       'sunUncertainH':hours('sun','uncertain'),'earthUncertainH':hours('earth','uncertain'),
                       'longestDarkH':[dark_lo['hours'],dark_hi['hours']],'longestEarthHiddenH':[earth_lo['hours'],earth_hi['hours']],
                       'darkTruncated':dark_lo['truncated'] or dark_hi['truncated'],'earthTruncated':earth_lo['truncated'] or earth_hi['truncated'],
                       'batteryMinimumWh':[low['minimumWh'],high['minimumWh']],'batteryMinimumPercent':[low['minimumPercent'],high['minimumPercent']]},
            'solarEnergyWh':[float(sum((p['endH']-p['startH'])*(p.get(key,request.generationW if p['sunState']=='visible' or optimistic and p['sunState']=='uncertain' else 0)) for p in intervals)) for key,optimistic in [('generationLowW',False),('generationHighW',True)]],
            'powerModel':request.powerModel,'powerStepSeconds':series.get('stepSeconds',300),
            'batteryLow':low,'batteryHigh':high,'violations':violations,'uncertainRequirements':uncertain,
            'selectedLimitsPass':selected_pass,'qualifies':selected_pass and not request.requireKnownGround,
            'overallStatus':'Violates an assessed requirement' if violations else 'Uncertain assessed requirements' if uncertain else 'Meets assessed limits · ground review required',
            'unknowns':['Rock/obstacle clearance','Regolith depth','Ground bearing strength','Footpad sinkage','Trajectory reachability'],
            'fullyAssessed':False}

class Engine:
    def __init__(self):
        self.terrain=Terrain(); self.screening=Screening(self.terrain); self.geometry=Geometry()

    def point(self,lon,lat):
        point=self.terrain.point(lon,lat)
        point['nasa']=self.screening.point(point)
        return point

    def nasa_requirements(self,point,request):
        data=point['nasa']; violations=[]; uncertain=[]
        if not data['available']: uncertain.append('NASA precomputed screening coverage is missing.')
        else:
            if data['solarPct']<request.minAverageSolarPercent: violations.append('NASA long-term sunlight frequency is below the screening minimum.')
            if data['earthPct']<request.minAverageEarthPercent: violations.append('NASA long-term Earth visibility is below the screening minimum.')
            if request.excludePermanentShadow and data['permanentShadow']: violations.append('The source NASA pixel is classified as permanent shadow.')
        return violations,uncertain

    def terrain_requirements(self,point,request,components):
        violations=[]; uncertain=[]
        point=dict(point)
        if 'nasa' not in point: point['nasa']=self.screening.point(point)
        nv,nu=self.nasa_requirements(point,request); violations.extend(nv); uncertain.extend(nu)
        a_low,a_high=self.terrain.area_at(point,components)
        point['connectedAreaM2']=[a_low,a_high]
        s=point['slopeDeg']; e=2*point['slopeRmsDeg']
        point['slopeSensitivityDeg']=[max(0,s-e),s+e]
        if max(0,s-e)>request.maxSlopeDeg: violations.append('Patch plane slope exceeds the limit in both sensitivity cases.')
        elif s+e>request.maxSlopeDeg: uncertain.append('Slope requirement overlaps the ±2×RMS sensitivity interval.')
        relief=point['reliefM']; re=4*point['heightRmsM']
        point['reliefSensitivityM']=[max(0,relief-re),relief+re]
        if max(0,relief-re)>request.maxReliefM: violations.append('50 m patch relief exceeds the entered limit in both sensitivity cases.')
        elif relief+re>request.maxReliefM: uncertain.append('Relief requirement overlaps the pointwise height sensitivity envelope.')
        if point['heightRmsM']>request.maxHeightRmsM: violations.append('Published height RMS exceeds the entered data-quality limit.')
        if a_high<request.minAreaM2: violations.append('Connected area is too small in both source-slope sensitivity cases.')
        elif a_low<request.minAreaM2: uncertain.append('Connected-area requirement depends on slope uncertainty.')
        return point,violations,uncertain

    def decorate(self,scenario,horizon,request,identifier):
        point=scenario['point']; landing=scenario['landingTimestamp']; duration=request.durationH
        cursor=[]
        for hour in np.unique(np.r_[np.arange(0,duration,1/12),duration]):
            sample=geometry_sample(self.geometry,point,request.observerHeightM,horizon,landing+float(hour)*3600,request)
            cursor.append({'hour':float(hour),'utc':iso_utc(landing+float(hour)*3600),**sample})
        scenario.update(id=identifier,samples=cursor,horizon={k:horizon[k].tolist() for k in ['azimuth','nominal','low','high']})
        scenario['sourceURL']='https://pgda.gsfc.nasa.gov/products/78'
        scenario['inspectionURL']='https://quickmap.lroc.im-ldi.com/'
        return scenario

    def search(self,request:StudyRequest,progress=lambda message:None):
        began=time.perf_counter()
        origin_time=parse_utc(request.landingUTC).timestamp(); first=parse_utc(request.earliestUTC).timestamp(); last=parse_utc(request.latestUTC).timestamp()
        if request.changeType=='site' and not first<=origin_time<=last: raise ValueError('A site-only search must include the original landing time in its allowed range.')
        for t in [origin_time,origin_time+request.durationH*3600,first,last+request.durationH*3600]: self.geometry.validate_date(t)
        origin=self.point(request.originalLon,request.originalLat)
        origin['relocationM']=0.0
        progress('Screening NASA long-term maps, then regional LOLA terrain')
        components=self.terrain.component_maps(request.maxSlopeDeg)
        origin,ov,ou=self.terrain_requirements(origin,request,components)
        start=first; end=last+request.durationH*3600
        progress('Computing original-site terrain horizon and SPICE geometry')
        origin_horizon=self.terrain.horizon(origin,request.observerHeightM)
        origin_series=build_series(self.geometry,origin,request.observerHeightM,origin_horizon,origin_time,origin_time+request.durationH*3600,request=request)
        original=evaluate_series(origin,origin_horizon,origin_series,origin_time,request,ov,ou,origin_time)
        original=self.decorate(original,origin_horizon,request,'O')
        points=[]; screened=0; nasa_rejected=0
        if request.changeType=='time': points=[(origin,ov,ou)]
        else:
            xmin,ymin,xmax,ymax=PATCH_BOUNDS
            for y in np.arange(ymax-125,ymin,-250):
                for x in np.arange(xmin+125,xmax,250):
                    lon,lat=self.terrain.lonlat(x,y)
                    dist=great_circle_m(origin['longitude'],origin['latitude'],lon,lat)
                    if dist>request.radiusM or dist<max(100,request.exclusionRadiusM if request.excludeOriginal else 100): continue
                    screened+=1
                    # NASA averages are a screening gate before expensive terrain/geometry.
                    nasa=self.screening.point({'x':float(x),'y':float(y)})
                    nv,nu=self.nasa_requirements({'nasa':nasa},request)
                    if nv or nu: nasa_rejected+=1; continue
                    try: point=self.point(lon,lat)
                    except ValueError: continue
                    point['relocationM']=dist
                    point,v,u=self.terrain_requirements(point,request,components)
                    if v or u: continue # filter mandatory available-data limitations before shortlisting
                    points.append((point,v,u))
            points.sort(key=lambda p:p[0]['relocationM'])
            # Distinct areas and a bounded analysis budget; this is not an exhaustive optimizer.
            chosen=[]
            for item in points:
                if all(great_circle_m(item[0]['longitude'],item[0]['latitude'],s[0]['longitude'],s[0]['latitude'])>=500 for s in chosen): chosen.append(item)
                if len(chosen)>=8: break
            points=chosen
        times=[origin_time] if request.changeType=='site' else sorted(set([float(x) for x in np.arange(first,last+1,6*3600)]+[last]))
        candidates=[]; evaluated=0
        for idx,(point,pv,pu) in enumerate(points):
            progress(f'Analyzing location {idx+1} of {len(points)} with real geometry')
            same=point['relocationM']==0
            horizon=origin_horizon if same else self.terrain.horizon(point,request.observerHeightM)
            series=build_series(self.geometry,point,request.observerHeightM,horizon,start,end,request=request)
            for landing in times:
                if same and (landing==origin_time or request.excludeOriginal): continue
                if request.changeType=='both' and landing==origin_time: continue
                if not first<=landing<=last: continue
                evaluated+=1
                result=evaluate_series(point,horizon,series,landing,request,pv,pu,origin_time)
                if result['selectedLimitsPass']: candidates.append((result,horizon))
        candidates.sort(key=lambda pair:(abs(pair[0]['scheduleShiftH']),pair[0]['point']['relocationM'],-pair[0]['metrics']['batteryMinimumPercent'][0]))
        distinct=[]
        for item in candidates:
            p=item[0]['point']
            if request.changeType!='time' and any(great_circle_m(p['longitude'],p['latitude'],q[0]['point']['longitude'],q[0]['point']['latitude'])<500 for q in distinct): continue
            distinct.append(item)
            if len(distinct)==3: break
        options=[self.decorate(s,h,request,f'R{i+1}') for i,(s,h) in enumerate(distinct)]
        now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        return {'algorithmVersion':ALGORITHM_VERSION,'computedUTC':now,'elapsedSeconds':time.perf_counter()-began,'request':request.model_dump(),
                'original':original,'candidates':options,'qualifyingCount':0 if request.requireKnownGround else len(options),
                'screenedGridPoints':screened,'nasaRejectedGridPoints':nasa_rejected,'geometryLocations':len(points)+(0 if request.changeType=='time' else 1),'evaluatedScenarios':evaluated,
                'notes':['Candidates are real coordinates, not certified landing locations.',
                         'NASA 60 m averages describe long-term any-disc visibility; they are not the selected mission timeline or average electrical output.',
                         'Panel power uses Sun distance, area, efficiency, losses, pointing and a uniform-disc fraction above a locally straight horizon. One-minute midpoint power sampling; eclipses and thermal effects unmodeled.',
                         'Mission Earth bands use '+('any portion of the Earth disc' if request.earthVisibilityMode=='any' else 'the Earth centre')+'; Earth visibility does not establish a radio link.',
                         'Landing dates are explicit mission inputs. Launch-to-landing timing, transfer trajectory and flight reachability are not inferred.',
                         'Sensitivity cases are ±2× published RMS with disclosed coarse-terrain allowances; they are not strict bounds on reality.',
                         'Source-slope connected areas are measured only inside the 5 km mapped study patch.',
                         'Horizon rays use 0.25° azimuth spacing and 5/20/500 m radial steps to 300 km. Angular/radial aliasing remains possible.',
                         'Up to eight spatially separated terrain-screened locations are analyzed; the search is bounded, not exhaustive.',
                         'Visibility roots bracketed on the time grid are refined to one second. Panel mode uses one-minute sampling; constant power uses five minutes. Events wholly inside an interval may be missed.',
                         'All candidates require independent ground/obstacle and trajectory assessment.'],
                'geometry':self.geometry.metadata(),'screening':self.screening.metadata()}
