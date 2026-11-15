"""Physical and numerical primitives. SI units except explicitly named degrees/hours."""
import math
import numpy as np

MOON_RADIUS_M = 1_737_400.0

def basis(lon_deg, lat_deg):
    lon, lat = np.radians([lon_deg, lat_deg])
    up = np.array([np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)])
    east = np.array([-np.sin(lon), np.cos(lon), 0.0])
    north = np.cross(up, east)
    return east, north, up

def surface_position(lon_deg, lat_deg, elevation_m=0.0, height_m=0.0):
    return basis(lon_deg, lat_deg)[2] * (MOON_RADIUS_M + elevation_m + height_m)

def az_el(vector, lon_deg, lat_deg):
    east, north, up = basis(lon_deg, lat_deg)
    e, n, u = np.dot(vector,east), np.dot(vector,north), np.dot(vector,up)
    azimuth=float(np.degrees(np.arctan2(e,n)) % 360)
    if azimuth>=360: azimuth=0.0 # roundoff at the north wrap
    return azimuth, float(np.degrees(np.arctan2(u,np.hypot(e,n))))

def great_circle_m(lon1, lat1, lon2, lat2):
    l1,p1,l2,p2 = np.radians([lon1,lat1,lon2,lat2])
    h = np.sin((p2-p1)/2)**2 + np.cos(p1)*np.cos(p2)*np.sin((l2-l1)/2)**2
    return float(2*MOON_RADIUS_M*np.arcsin(np.sqrt(np.clip(h,0,1))))

def plane_fit(z, spacing_m):
    if not np.all(np.isfinite(z)): raise ValueError('Patch contains no-data pixels.')
    row, col = np.indices(z.shape, dtype=float)
    dx = (col-col.mean())*spacing_m
    dy = -(row-row.mean())*spacing_m
    design = np.column_stack([dx.ravel(),dy.ravel(),np.ones(z.size)])
    coefficients = np.linalg.lstsq(design,z.ravel(),rcond=None)[0]
    residual = z.ravel()-design@coefficients
    return {
        'slopeDeg': float(np.degrees(np.arctan(np.hypot(*coefficients[:2])))),
        'reliefM': float(np.ptp(z)), 'roughnessRmsM': float(np.sqrt(np.mean(residual**2))),
        'gradientGridX':float(coefficients[0]), 'gradientGridY':float(coefficients[1]),
    }

def circular_interpolate(azimuth, azimuths, values):
    return float(np.interp(azimuth % 360, np.r_[azimuths,360.0],np.r_[values,values[0]]))

def elevation_from_radii(radius_terrain, radius_observer, angular_distance):
    return np.degrees(np.arctan2(radius_terrain*np.cos(angular_distance)-radius_observer,
                                radius_terrain*np.sin(angular_distance)))

def visibility(elevation, horizon_low, horizon_high):
    if not np.all(np.isfinite([elevation,horizon_low,horizon_high])): return 'unknown'
    if elevation > horizon_high: return 'visible'
    if elevation < horizon_low: return 'hidden'
    return 'uncertain'

def longest_interval(intervals, predicate, mission_h):
    longest = {'hours':0.0,'startH':0.0,'endH':0.0,'truncated':False}
    start = None
    for item in intervals:
        if predicate(item):
            if start is None: start=item['startH']
        elif start is not None:
            end=item['startH']
            if end-start>longest['hours']:
                longest={'hours':end-start,'startH':start,'endH':end,'truncated':start==0}
            start=None
    if start is not None and mission_h-start>longest['hours']:
        longest={'hours':mission_h-start,'startH':start,'endH':mission_h,'truncated':True}
    return longest

def integrate_battery(intervals, capacity_wh, initial_percent, load_w, generation_w, reserve_percent, optimistic=False):
    energy=capacity_wh*initial_percent/100
    reserve=capacity_wh*reserve_percent/100
    minimum=energy
    depletion=0.0 if energy==0 else None
    crossing=0.0 if energy<reserve else None
    points=[{'hour':0.0,'value':float(energy)}]
    for item in intervals:
        end=item['endH']; start=item['startH']
        if depletion is not None:
            points.append({'hour':end,'value':None}); continue
        lit=item['sunState']=='visible' or (optimistic and item['sunState'] in ('uncertain','unknown'))
        key='generationHighW' if optimistic else 'generationLowW'
        generation=item[key] if key in item else (generation_w if lit else 0)
        rate=generation-load_w
        nxt=min(capacity_wh,energy+rate*(end-start))
        if rate>0 and energy<capacity_wh and energy+rate*(end-start)>capacity_wh:
            points.append({'hour':start+(capacity_wh-energy)/rate,'value':float(capacity_wh)})
        if crossing is None and nxt<reserve and rate<0: crossing=start+(energy-reserve)/(-rate)
        if nxt<=0:
            depletion=start+energy/(-rate) if rate<0 else start
            minimum=0.0
            points.append({'hour':depletion,'value':0.0})
            if end>depletion+1e-12: points.append({'hour':end,'value':None})
            energy=0.0
        else:
            energy=nxt; minimum=min(minimum,energy)
            points.append({'hour':end,'value':float(energy)})
    return {'points':points,'minimumWh':float(minimum),'minimumPercent':float(minimum/capacity_wh*100),
            'reserveCrossingH':crossing,'depletionH':depletion}

def refine_zero(fn, a, b, tolerance_seconds=1.0):
    fa,fb=fn(a),fn(b)
    if not math.isfinite(fa+fb) or fa*fb>0: raise ValueError('Root is not bracketed.')
    if fa==0: return a
    if fb==0: return b
    while (b-a)*3600>tolerance_seconds:
        mid=(a+b)/2; fm=fn(mid)
        if fa*fm<=0: b=mid
        else: a=mid; fa=fm
    return (a+b)/2
