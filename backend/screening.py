"""NASA's archived, precomputed polar maps; never a mission-time series."""
import io
import numpy as np
from PIL import Image
from .terrain import DATA,FRAME,PATCH_BOUNDS,pds_number

PRODUCT_URL='https://pgda.gsfc.nasa.gov/products/69'

class Screening:
    def __init__(self,terrain):
        self.terrain=terrain
        self.grids={}; self.labels={}; self.pngs={}
        for key in ['solar','earth','shadow']:
            text=(DATA/'screening'/f'{key}.lbl').read_text()
            if 'MEAN EARTH/POLAR AXIS OF DE421' not in text or 'LSB_INTEGER' not in text:
                raise ValueError('Precomputed map frame/encoding mismatch.')
            info={k:pds_number(text,k) for k in ['LINES','LINE_SAMPLES','SCALING_FACTOR','OFFSET','MAP_SCALE','LINE_PROJECTION_OFFSET','SAMPLE_PROJECTION_OFFSET']}
            if info['MAP_SCALE']!=60 or pds_number(text,'CENTER_LATITUDE')!=-90 or pds_number(text,'A_AXIS_RADIUS')!=1737.4:
                raise ValueError('Unexpected precomputed-map projection.')
            if pds_number(text,'SAMPLE_BITS')!=16: raise ValueError('Unexpected precomputed encoding.')
            shape=(int(info['LINES']),int(info['LINE_SAMPLES']))
            path=DATA/'screening'/f'{key}.img'
            if path.stat().st_size!=np.prod(shape)*2: raise ValueError('Truncated precomputed map.')
            expected=(.000025,.5) if key=='shadow' else (.00004,0)
            if (info['SCALING_FACTOR'],info['OFFSET'])!=expected: raise ValueError('Unexpected NASA scale/offset.')
            self.grids[key]=np.memmap(path,dtype='<i2',mode='r',shape=shape)
            self.labels[key]=info

    def values(self,x,y,key):
        """Nearest source pixel. Do not interpolate a categorical shadow flag."""
        info=self.labels[key]
        x,y=np.broadcast_arrays(np.asarray(x,dtype=float),np.asarray(y,dtype=float))
        row=np.floor(info['LINE_PROJECTION_OFFSET']-y/60+.5).astype(int)
        col=np.floor(info['SAMPLE_PROJECTION_OFFSET']+x/60+.5).astype(int)
        valid=(row>=0)&(col>=0)&(row<self.grids[key].shape[0])&(col<self.grids[key].shape[1])
        raw=np.asarray(self.grids[key][np.clip(row,0,self.grids[key].shape[0]-1),np.clip(col,0,self.grids[key].shape[1]-1)],dtype=float)
        valid &= np.isin(raw,[-20000,20000]) if key=='shadow' else (raw>=0)&(raw<=25000)
        values=raw*info['SCALING_FACTOR']+info['OFFSET']
        return np.where(valid,values,np.nan),row,col,raw

    def point(self,point):
        result={'pixelM':60,'sourceURL':PRODUCT_URL,'definition':'Long-term frequency of any part of the disc visible; not mission-specific hours.'}
        for key,field in [('solar','solarPct'),('earth','earthPct'),('shadow','permanentShadow')]:
            value,row,col,raw=self.values(point['x'],point['y'],key)
            result[field]=None if not np.isfinite(value) else bool(value>=.5) if key=='shadow' else float(value*100)
            result[key+'Pixel']={'row':int(row),'column':int(col),'rawDN':int(raw)}
        result['available']=all(result[k] is not None for k in ['solarPct','earthPct','permanentShadow'])
        return result

    def map_png(self,layer):
        if layer not in ('solar','earth','shadow'): raise ValueError('Choose solar, earth, or shadow.')
        if layer in self.pngs: return self.pngs[layer]
        xmin,ymin,xmax,ymax=PATCH_BOUNDS
        x=xmin+(np.arange(500)+.5)*(xmax-xmin)/500
        y=ymax-(np.arange(500)+.5)*(ymax-ymin)/500
        xx,yy=np.meshgrid(x,y)
        values,*_=self.values(xx,yy,layer)
        palettes={'solar':([14,24,39],[244,182,75]),'earth':([14,24,39],[91,223,201]),'shadow':([78,95,102],[173,133,222])}
        dark,bright=[np.array(c) for c in palettes[layer]]
        colour=dark+(bright-dark)*values[...,None]
        terrain=np.asarray(Image.open(io.BytesIO(self.terrain.png)),dtype=float)
        colour=.83*colour+.17*terrain
        colour[~np.isfinite(values)]=[100,105,110]
        data=io.BytesIO(); Image.fromarray(np.clip(colour,0,255).astype('uint8')).save(data,format='PNG')
        self.pngs[layer]=data.getvalue()
        return self.pngs[layer]

    def metadata(self):
        return {'sourceURL':PRODUCT_URL,'pixelM':60,'frame':FRAME,'productVersion':'V1.05 / 201608',
                'productDate':'2016-09-15','terrainObservationPeriod':'2009-07-13 through 2013-07-18',
                'averagingPeriod':'18.6-year modeled cycle; exact start/end epochs are not specified in these labels.',
                'solarDefinition':'Fraction of modeled timesteps with any part of the solar disc visible, not average electrical output.',
                'earthDefinition':'Fraction of modeled timesteps with any part of Earth visible; does not establish DSN or radio-link availability.',
                'shadowDefinition':'Permanent-shadow classification in the source model; no classification of local ground support.',
                'surface':'Source surface/terrain model; changing instrument height does not modify the NASA averages.',
                'sampling':'Nearest 60 m source pixel; no fabricated 5 m detail.',
                'citation':'Mazarico et al. (2011), Icarus 211, 1066–1081, doi:10.1016/j.icarus.2010.10.030',
                'limitations':'Archived modeled screening products, including possible DEM artifacts. EXTRAs are not supported by PDS or the LOLA Science Team.'}
