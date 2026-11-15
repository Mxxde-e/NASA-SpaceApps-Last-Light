"""SPICE surface-observer geometry in the terrain's MOON_ME_DE421 frame."""
from datetime import datetime,timezone
from functools import lru_cache
import threading
import numpy as np
import spiceypy as spice
from .terrain import DATA, FRAME
from .numerics import surface_position, az_el

SPICE_LOCK=threading.RLock()

def parse_utc(value):
    if isinstance(value,datetime): result=value
    else: result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None: raise ValueError('Provide an explicit UTC offset or Z suffix.')
    return result.astimezone(timezone.utc)

def iso_utc(timestamp):
    return datetime.fromtimestamp(timestamp,timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')

class Geometry:
    def __init__(self):
        names=['naif0012.tls','pck00011.tpc','de421.bsp','moon_pa_de421_1900-2050.bpc','moon_080317.tf']
        with SPICE_LOCK:
            for name in names: spice.furnsh(str(DATA/'kernels'/name))
            coverage=spice.pckcov(str(DATA/'kernels'/'moon_pa_de421_1900-2050.bpc'),31006)
            start,stop=spice.wnfetd(coverage,0)
            # Restrict the supported pilot interval to avoid boundary/correction extrapolation.
            self.support_start=max(start,spice.str2et('2000-01-01T00:00:00'))
            self.support_end=min(stop,spice.str2et('2049-12-31T23:59:59'))
            self.start_utc=spice.et2utc(self.support_start,'ISOC',0)+'Z'
            self.end_utc=spice.et2utc(self.support_end,'ISOC',0)+'Z'
            spice.pxform(FRAME,'J2000',spice.str2et('2026-11-15T00:00:00'))

    def validate_date(self,timestamp):
        with SPICE_LOCK: et=spice.str2et(iso_utc(timestamp))
        if not self.support_start<=et<=self.support_end: raise ValueError(f'Date is outside supported kernel coverage {self.start_utc} through {self.end_utc}.')

    @lru_cache(maxsize=200_000)
    def at(self,lon,lat,elevation_m,height_m,timestamp):
        observer=surface_position(lon,lat,elevation_m,height_m)/1000.0
        utc=datetime.fromtimestamp(timestamp,timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
        with SPICE_LOCK:
            et=spice.str2et(utc)
            if not self.support_start<=et<=self.support_end: raise ValueError('Missing SPICE time coverage.')
            result={}
            for target,key in [('SUN','sun'),('EARTH','earth')]:
                state,_=spice.spkcpo(target,et,FRAME,'OBSERVER','CN+S',observer,'MOON',FRAME)
                azimuth,elevation=az_el(np.asarray(state[:3]),lon,lat)
                result[key+'Az']=azimuth; result[key+'El']=elevation
                distance=float(np.linalg.norm(state[:3]))
                result[key+'DistanceKm']=distance
                radius=695700.0 if key=='sun' else 6378.137
                result[key+'AngularRadiusDeg']=float(np.degrees(np.arcsin(radius/distance)))
        return result

    def point_at(self,point,height_m,timestamp):
        return self.at(point['longitude'],point['latitude'],point['elevationM'],height_m,float(timestamp))

    def metadata(self):
        return {'startUTC':self.start_utc,'endUTC':self.end_utc,'frame':FRAME,'ephemeris':'DE421',
                'correction':'CN+S: converged light time and stellar aberration; no atmospheric refraction',
                'observer':'Actual surface position including DEM elevation and entered instrument height',
                'visibility':'Mission bands use the body centre unless Earth any-disc is selected. Panel power estimates a uniform solar-disc fraction above a locally straight horizon. Radio-link budgets and eclipses are not modeled.'}
