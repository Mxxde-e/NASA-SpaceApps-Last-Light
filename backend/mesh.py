"""A reduced display mesh from real elevation pixels; never used for analysis."""
import numpy as np
from .numerics import basis,MOON_RADIUS_M


def build_terrain_mesh(terrain):
    # Every tenth 5 m source pixel: a 50 m display grid, no invented detail.
    rows=np.arange(terrain.r0+4,terrain.r1,10)
    cols=np.arange(terrain.c0+4,terrain.c1,10)
    cc,rr=np.meshgrid(cols,rows)
    x=terrain.transform.c+(cc+.5)*terrain.pixel
    y=terrain.transform.f-(rr+.5)*terrain.pixel
    lon,lat=terrain.to_lonlat.transform(x,y)
    z=terrain.datasets['z'][rr,cc].astype(float)
    xmin,ymin,xmax,ymax=terrain.metadata_bounds
    ref_lon,ref_lat=terrain.lonlat((xmin+xmax)/2,(ymin+ymax)/2)
    ref_z=float(terrain.pixel_sample((xmin+xmax)/2,(ymin+ymax)/2))
    if not np.isfinite(ref_z): raise ValueError('Missing elevation at mesh reference.')
    east,north,up=basis(ref_lon,ref_lat)
    lon,lat=np.radians(lon),np.radians(lat)
    unit=np.stack([np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)],axis=-1)
    world=(MOON_RADIUS_M+z)[...,None]*unit
    reference=(MOON_RADIUS_M+ref_z)*up
    enu=(world-reference)@np.stack([east,north,up]).T
    valid=np.all(np.isfinite(enu),axis=-1)
    indices=[]; width=len(cols)
    for r in range(len(rows)-1):
        for c in range(width-1):
            a=r*width+c; b=a+1; d=a+width; e=d+1
            for triangle in [(a,d,b),(b,d,e)]:
                if all(valid.ravel()[i] for i in triangle): indices.extend(triangle)
    # Invalid vertices are unreferenced, not filled terrain.
    enu[~valid]=0
    return {'reference':{'longitude':ref_lon,'latitude':ref_lat,'elevationM':ref_z,'radiusM':MOON_RADIUS_M},
            'verticesENU':np.round(enu.reshape(-1,3),3).ravel().tolist(),'indices':indices,
            'sourcePixelM':terrain.pixel,'displaySpacingM':terrain.pixel*10,'verticalScale':1,
            'missingVertices':int(np.sum(~valid)),'frame':'MOON_ME_DE421',
            'description':'Curved-Moon elevation mesh, 50 m display grid sampled from 5 m LOLA source. Missing triangles omitted. Illustrative lighting; analysis uses the full source data.'}
