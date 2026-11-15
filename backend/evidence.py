"""Run the included, independently captured Horizons fixture comparisons."""
from datetime import datetime,timezone
from pathlib import Path
import re
from functools import lru_cache


@lru_cache(maxsize=1)
def geometry_evidence(geometry):
    checks=[]
    for body in ('sun','earth'):
        text=(Path(__file__).parent/'tests'/f'horizons-{body}.txt').read_text(encoding='utf-8')
        block=text.split('$$SOE')[1].split('$$EOE')[0]
        rows=re.findall(r'(2026-\w+-\d+\s+\d+:\d+)\s+\S*\s+([-\d.]+)\s+([-\d.]+)',block)
        if len(rows)!=25: raise ValueError('The included Horizons reference fixture is incomplete.')
        az_errors=[]; el_errors=[]
        for date,az,el in rows:
            t=datetime.strptime(date,'%Y-%b-%d %H:%M').replace(tzinfo=timezone.utc).timestamp()
            value=geometry.at(-137.50198,-89.46316,1944.761474609375,2,t)
            az_errors.append(abs((value[body+'Az']-float(az)+180)%360-180))
            el_errors.append(abs(value[body+'El']-float(el)))
        checks.append({'body':body,'comparisons':len(rows),'maxAzimuthDifferenceDeg':max(az_errors),
                       'maxElevationDifferenceDeg':max(el_errors),'toleranceDeg':.0001,
                       'passed':max(az_errors+el_errors)<.0001})
    return {'checkedUTC':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'checks':checks,
            'reference':'Included JPL Horizons DE441 outputs; 2026-11-15 06:00 through 2026-11-16 06:00 UTC, hourly.',
            'observer':'Longitude −137.50198°, latitude −89.46316°, altitude 1.946761474609375 km including 2 m height.',
            'scope':'Direction checks at one observer and 25 times per body. This is not validation of terrain occlusion, a radio link, all sites or landing safety. Horizons and the DE421 engine differ in ephemeris/frame details.'}
