"""LOLA regional terrain with documented PDS scale, masks and lunar coordinates."""
from pathlib import Path
import hashlib
import io
import json
import re
import threading
import numpy as np
import rasterio
from pyproj import Transformer, CRS
from scipy.ndimage import map_coordinates, label
from PIL import Image
from .numerics import MOON_RADIUS_M, basis, plane_fit, elevation_from_radii

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
FRAME='MOON_ME_DE421'
PATCH_BOUNDS=(-13500.0,-14500.0,-8500.0,-9500.0)

def pds_number(text,key):
    match=re.search(r'^\s*'+re.escape(key)+r'\s*=\s*([-+0-9.Ee]+)',text,re.M)
    if not match: raise ValueError(f'Missing PDS field {key}')
    return float(match.group(1))

class Terrain:
    def __init__(self):
        self.manifest=json.loads((DATA/'sources.json').read_text())
        # Check the actual bytes before trusting provenance or checksum-keyed caches.
        from .acquire import ASSETS
        for name in ASSETS:
            entry=self.manifest['assets'][name]
            with (DATA/name).open('rb') as source:
                digest=hashlib.file_digest(source,'sha256').hexdigest()
            if digest!=entry['sha256']: raise ValueError(f'Source checksum mismatch: {name}. Re-run backend.acquire.')
        self.datasets={}
        for key,filename in [('z','elevation.tif'),('z_rms','elevation_rms.tif'),('slope','slope.tif'),('slope_rms','slope_rms.tif'),('returns','return_count.tif')]:
            with rasterio.open(DATA/'terrain'/filename) as ds:
                if key=='z':
                    self.transform=ds.transform; self.crs=CRS(ds.crs); self.shape=(ds.height,ds.width)
                    self.full_bounds=list(ds.bounds)
                    self.pixel=float(ds.res[0])
                elif ds.transform!=self.transform or (ds.height,ds.width)!=self.shape or CRS(ds.crs)!=self.crs: raise ValueError('Regional grids are not co-registered.')
                self.datasets[key]=ds.read(1,masked=True).astype('float32').filled(np.nan)
                if key in ('z_rms','slope','slope_rms','returns'):
                    self.datasets[key][self.datasets[key]<0]=np.nan
        if abs(self.crs.ellipsoid.semi_major_metre-MOON_RADIUS_M)>1e-6: raise ValueError('Wrong lunar reference sphere.')
        if self.transform.b!=0 or self.transform.d!=0 or self.transform.a!=5 or self.transform.e!=-5: raise ValueError('Unexpected regional grid axes.')
        self.to_lonlat=Transformer.from_crs(self.crs,self.crs.geodetic_crs,always_xy=True)
        self.from_lonlat=Transformer.from_crs(self.crs.geodetic_crs,self.crs,always_xy=True)
        self.background,self.background_info=self._pds('surrounding',polar=True)
        self.global_dem,self.global_info=self._pds('global',polar=False)
        self.global_max=float(np.max(self.global_dem))*self.global_info['scale']
        self.horizon_lock=threading.Lock()
        self.cache=DATA/'cache'; self.cache.mkdir(exist_ok=True)
        self.r0,self.c0=self.index(PATCH_BOUNDS[0],PATCH_BOUNDS[3])
        self.r1,self.c1=self.index(PATCH_BOUNDS[2],PATCH_BOUNDS[1])
        self.roi_z=self.datasets['z'][self.r0:self.r1,self.c0:self.c1]
        if self.roi_z.shape!=(1000,1000): raise ValueError('Unexpected study-patch dimensions.')
        self.png=self._hillshade()

    def _pds(self,name,polar):
        text=(DATA/'terrain'/f'{name}.lbl').read_text()
        if 'MEAN EARTH/POLAR AXIS OF DE421' not in text: raise ValueError('PDS lunar frame mismatch.')
        if 'LSB_INTEGER' not in text or pds_number(text,'SAMPLE_BITS')!=16: raise ValueError('Unexpected PDS encoding.')
        rows,cols=int(pds_number(text,'LINES')),int(pds_number(text,'LINE_SAMPLES'))
        if (DATA/'terrain'/f'{name}.img').stat().st_size!=rows*cols*2: raise ValueError('Truncated PDS image.')
        info={'rows':rows,'cols':cols,'scale':pds_number(text,'SCALING_FACTOR'),'radius':pds_number(text,'OFFSET')}
        if info['radius']!=MOON_RADIUS_M: raise ValueError('PDS radius mismatch.')
        if polar:
            info.update(pixel=pds_number(text,'MAP_SCALE'),lineOffset=pds_number(text,'LINE_PROJECTION_OFFSET'),sampleOffset=pds_number(text,'SAMPLE_PROJECTION_OFFSET'))
        else: info['ppd']=pds_number(text,'MAP_RESOLUTION')
        return np.memmap(DATA/'terrain'/f'{name}.img',dtype='<i2',mode='r',shape=(rows,cols)),info

    def index(self,x,y):
        col,row=(~self.transform)@(x,y)
        return int(np.floor(row+1e-9)),int(np.floor(col+1e-9))

    def pixel_sample(self,x,y,key='z'):
        col,row=(~self.transform)@(x,y)
        result=map_coordinates(self.datasets[key],[np.atleast_1d(row)-.5,np.atleast_1d(col)-.5],order=1,mode='constant',cval=np.nan,prefilter=False)
        return result[0] if np.ndim(row)==0 else result

    def lonlat(self,x,y):
        lon,lat=self.to_lonlat.transform(x,y)
        return float(lon),float(lat)

    def point(self,lon,lat,width=50):
        x,y=self.from_lonlat.transform(lon,lat)
        xmin,ymin,xmax,ymax=PATCH_BOUNDS
        if not (xmin+width/2<=x<=xmax-width/2 and ymin+width/2<=y<=ymax-width/2): raise ValueError('Point/50 m patch falls outside the verified study footprint.')
        r,c=self.index(x,y); half=int(round(width/self.pixel/2))
        sl=np.s_[r-half:r+half,c-half:c+half]
        z=self.datasets['z'][sl]
        fit=plane_fit(z,self.pixel)
        sr=self.datasets['slope_rms'][sl]; zr=self.datasets['z_rms'][sl]
        if not np.all(np.isfinite(sr)) or not np.all(np.isfinite(zr)): raise ValueError('Missing uncertainty data in candidate patch.')
        return {'x':float(x),'y':float(y),'longitude':float((lon+180)%360-180),'latitude':float(lat),
                'elevationM':float(self.pixel_sample(x,y)),'heightRmsM':float(np.max(zr)),
                'slopeRmsDeg':float(np.median(sr)), 'sourceSlopeDeg':float(np.median(self.datasets['slope'][sl])),
                'directReturnFraction':float(np.mean(self.datasets['returns'][sl]>0)),
                'patchWidthM':width,**fit}

    def component_maps(self,max_slope):
        sl=np.s_[self.r0:self.r1,self.c0:self.c1]
        s=self.datasets['slope'][sl]; e=self.datasets['slope_rms'][sl]
        valid=np.isfinite(self.roi_z)&np.isfinite(s)&np.isfinite(e)&(e>=0)
        result=[]
        for values in [s+2*e,np.maximum(0,s-2*e)]:
            regions,_=label(valid&(values<=max_slope)) # four-connected; no diagonal-only links
            area=np.bincount(regions.ravel())*self.pixel**2
            area[0]=0
            result.append((regions,area))
        return result

    def area_at(self,point,components):
        r,c=self.index(point['x'],point['y']); r-=self.r0; c-=self.c0
        return [float(areas[regions[r,c]]) for regions,areas in components]

    def sample_world(self,unit):
        """Use the finest supported raster at each location; never fill no-data with zero."""
        # Exact spherical south-polar stereographic; avoid millions of repeated
        # longitude/latitude/projection conversions while constructing horizons.
        factor=2*MOON_RADIUS_M/(1-unit[...,2])
        x=factor*unit[...,1]; y=factor*unit[...,0]
        bg=self.background_info
        br=bg['lineOffset']-np.asarray(y)/bg['pixel']
        bc=bg['sampleOffset']+np.asarray(x)/bg['pixel']
        h=map_coordinates(self.background,[br,bc],order=1,mode='constant',cval=np.nan,prefilter=False,output=np.float64)*bg['scale']
        sigma=np.full(h.shape,20.0) # explicit sensitivity allowance, not a published RMS map
        res=np.full(h.shape,40.0)
        missing=~np.isfinite(h)
        if np.any(missing):
            far=unit[missing]
            lon=np.degrees(np.arctan2(far[...,1],far[...,0]))
            lat=np.degrees(np.arctan2(far[...,2],np.hypot(far[...,0],far[...,1])))
            gl=self.global_info
            gr=np.clip((90-lat)*gl['ppd']-.5,0,gl['rows']-1)
            gc=(lon%360)*gl['ppd']-.5
            # wrap longitude, clamp latitude; this study's rays never reach a pole row discontinuity
            h[missing]=map_coordinates(self.global_dem,[gr,gc],order=1,mode='grid-wrap',prefilter=False,output=np.float64)*gl['scale']
            sigma[missing]=250.0; res[missing]=1895.21
        col=(x-self.transform.c)/self.pixel-.5
        row=(self.transform.f-y)/self.pixel-.5
        inside=(row>=0)&(col>=0)&(row<=self.shape[0]-1)&(col<=self.shape[1]-1)
        coords=[row[inside],col[inside]]
        near=map_coordinates(self.datasets['z'],coords,order=1,mode='constant',cval=np.nan,prefilter=False)
        rms=map_coordinates(self.datasets['z_rms'],coords,order=1,mode='constant',cval=np.nan,prefilter=False)
        valid=np.isfinite(near)&np.isfinite(rms)&(rms>=0)
        height_inside=h[inside]; sigma_inside=sigma[inside]; res_inside=res[inside]
        height_inside[valid]=near[valid]; sigma_inside[valid]=rms[valid]; res_inside[valid]=5.0
        h[inside]=height_inside; sigma[inside]=sigma_inside; res[inside]=res_inside
        return h,sigma,res

    def horizon(self,point,height_m,az_step=.25,radial_scale=1.0):
        signature='v4|'+('|'.join(v['sha256'] for k,v in sorted(self.manifest['assets'].items()) if k.startswith('terrain/')))+f'|{point["longitude"]:.8f}|{point["latitude"]:.8f}|{height_m}|{az_step}|{radial_scale}'
        key=hashlib.sha256(signature.encode()).hexdigest()
        path=self.cache/f'horizon-{key}.npz'
        with self.horizon_lock:
            if path.exists():
                with np.load(path) as a: return {k:a[k] for k in a.files}
            az=np.arange(0,360,az_step)
            # Resolve the source grid along each ray: 5 m near the regional DEM,
            # half a 40 m background pixel beyond it, then <=1/3 global pixels.
            distance=np.unique(np.r_[np.arange(5,20000,5*radial_scale),np.arange(20000,220000,20*radial_scale),np.arange(220000,300001,500*radial_scale),300000])
            delta=distance/MOON_RADIUS_M
            cosine=np.cos(delta); sine=np.sin(delta)
            def highest_angle(rt,observer_radius):
                # All rays are shorter than pi*R and have a positive horizontal
                # denominator. atan is monotone: reduce the tangent first, then
                # evaluate one transcendental function per azimuth, not per pixel.
                tangent=(cosine-observer_radius/rt)/sine
                return np.degrees(np.arctan(np.max(tangent,axis=1)))
            east,north,up=basis(point['longitude'],point['latitude'])
            ro=MOON_RADIUS_M+point['elevationM']+height_m
            # Observer interpolation RMS at the actual point, not max RMS over the whole patch.
            observer_sigma=float(self.pixel_sample(point['x'],point['y'],'z_rms'))
            nominal=[]; low=[]; high=[]; resolutions=[]
            for start in range(0,len(az),40):
                radians=np.radians(az[start:start+40])
                horizontal=np.sin(radians)[:,None]*east+np.cos(radians)[:,None]*north
                unit=np.cos(delta)[None,:,None]*up+np.sin(delta)[None,:,None]*horizontal[:,None,:]
                z,sigma,res=self.sample_world(unit)
                if not np.all(np.isfinite(z)): raise ValueError('Horizon has missing surrounding terrain.')
                rt=MOON_RADIUS_M+z
                nominal.extend(highest_angle(rt,ro))
                low.extend(highest_angle(rt-2*sigma,ro+2*observer_sigma))
                high.extend(highest_angle(rt+2*sigma,ro-2*observer_sigma))
                resolutions.extend(np.max(res,axis=1))
            # Bound terrain beyond the sampled domain within the piecewise-interpolated global DEM model.
            # 2*250 m is the disclosed coarse-terrain sensitivity allowance, not a geological guarantee.
            outer=float(elevation_from_radii(MOON_RADIUS_M+self.global_max+500,ro-2*observer_sigma,delta[-1]))
            result={'azimuth':az,'nominal':np.asarray(nominal),'low':np.asarray(low),'high':np.maximum(high,outer),
                    'outerModelBoundDeg':np.asarray(outer),'maxRangeM':np.asarray(distance[-1]),'coarsestM':np.asarray(max(resolutions))}
            temporary=path.with_suffix('.tmp.npz'); np.savez_compressed(temporary,**result); temporary.replace(path)
            return result

    def _hillshade(self):
        z=self.roi_z[::2,::2]
        dy,dx=np.gradient(z,10,10)
        normal=np.stack([-dx,dy,np.ones(z.shape)],axis=-1)
        normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
        light=np.array([-.4,-.5,.77]); light/=np.linalg.norm(light)
        shade=np.clip(np.sum(normal*light,axis=-1)*.65+.25,0,1)
        image=np.stack([shade*108+18,shade*116+26,shade*120+34],axis=-1)
        image[~np.isfinite(z)]=[10,20,30]
        data=io.BytesIO(); Image.fromarray(image.astype('uint8')).save(data,format='PNG')
        return data.getvalue()

    def metadata(self):
        lon,lat=self.lonlat(-11000,-12000)
        point=self.point(lon,lat)
        return {'name':'Shackleton–de Gerlache Connecting Ridge','frame':FRAME,'referenceRadiusM':MOON_RADIUS_M,
                'boundsXY':PATCH_BOUNDS,'pixelM':self.pixel,'patchWidthM':50,'defaultPoint':point,
                'regionSizeM':5000,'imageUrl':'/api/map.png','sources':self.manifest['assets'],
                'terrainProductURL':'https://pgda.gsfc.nasa.gov/products/78',
                'unknowns':['Rock/obstacle clearance','Loose-layer depth','Actual bearing strength','Footpad sinkage','Trajectory reachability'],
                'sensitivity':{'regional':'±2 × supplied height/slope RMS; not a certified confidence interval',
                               'surrounding40m':'±40 m height sensitivity (entered model allowance)',
                               'global1895m':'±500 m height sensitivity (entered model allowance)'},
                'sourcePeriod':'Regional product: Barker et al. 2021; files last modified 2020. Surrounding observations: 2009–2017; global: 2009–2016.',
                'mapDescription':'Computed hillshade from numerical LOLA elevations; shading is illustrative and is not a sunlight calculation.'}
