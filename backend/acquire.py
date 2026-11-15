"""Download the documented public study data; record bytes and SHA-256 provenance."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
KERNEL_BASE = 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/'
ILLUM_BASE = 'https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/extras/illumination/'
ASSETS = {
    'terrain/elevation.tif': 'https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_surf.tif',
    'terrain/elevation_rms.tif': 'https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_toterr.tif',
    'terrain/slope.tif': 'https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_slp.tif',
    'terrain/slope_rms.tif': 'https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_slperr.tif',
    'terrain/return_count.tif': 'https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_ldec.tif',
    'terrain/README.txt': 'https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/README',
    'kernels/de421.bsp': KERNEL_BASE + 'spk/planets/a_old_versions/de421.bsp',
    'kernels/moon_pa_de421_1900-2050.bpc': KERNEL_BASE + 'pck/moon_pa_de421_1900-2050.bpc',
    'kernels/moon_080317.tf': KERNEL_BASE + 'fk/satellites/moon_080317.tf',
    'kernels/naif0012.tls': KERNEL_BASE + 'lsk/naif0012.tls',
    'kernels/pck00011.tpc': KERNEL_BASE + 'pck/pck00011.tpc',
    'terrain/surrounding.img': 'https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldem_85s_40m.img',
    'terrain/surrounding.lbl': 'https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldem_85s_40m.lbl',
    'terrain/global.img': 'https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_16.img',
    'terrain/global.lbl': 'https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_16.lbl',
    'screening/solar.img': ILLUM_BASE+'img/avgvisib_85s_060m_201608.img',
    'screening/solar.lbl': ILLUM_BASE+'img/avgvisib_85s_060m_201608.lbl',
    'screening/earth.img': ILLUM_BASE+'img/avgvisib_85s_060m_201608_earth.img',
    'screening/earth.lbl': ILLUM_BASE+'img/avgvisib_85s_060m_201608_earth.lbl',
    'screening/shadow.img': ILLUM_BASE+'img/lpsr_85s_060m_201608.img',
    'screening/shadow.lbl': ILLUM_BASE+'img/lpsr_85s_060m_201608.lbl',
    'screening/README.txt': ILLUM_BASE+'readme_illumination_2016.txt',
}

def acquire(assets=ASSETS):
    DATA.mkdir(exist_ok=True)
    manifest_path = DATA / 'sources.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'assets': {}}
    for relative, url in assets.items():
        path = DATA / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = manifest['assets'].get(relative, {})
        if path.exists() and entry.get('sha256') == hashlib.sha256(path.read_bytes()).hexdigest():
            print('Verified cached', relative, flush=True)
            continue
        print('Downloading', relative, flush=True)
        temporary = path.with_suffix(path.suffix + '.partial')
        request = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(request, timeout=45) as response:
            headers = dict(response.headers)
            expected = int(response.headers.get('Content-Length', '0'))
        with temporary.open('wb') as output:
            if expected > 4 * 1024 * 1024 and headers.get('Accept-Ranges','').lower() == 'bytes':
                for start in range(0, expected, 2 * 1024 * 1024):
                    end = min(expected-1, start + 2 * 1024 * 1024-1)
                    req = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}'})
                    with urllib.request.urlopen(req, timeout=90) as response:
                        if response.status != 206 or not response.headers.get('Content-Range','').startswith(f'bytes {start}-'):
                            raise RuntimeError(f'Invalid range response for {relative}: {start}')
                        block = response.read()
                        if len(block) != end-start+1: raise RuntimeError('Truncated range')
                        output.write(block)
                    if start % (10*1024*1024) == 0: print(relative, round((end+1)/expected*100), '%', flush=True)
            else:
                with urllib.request.urlopen(url, timeout=90) as response:
                    while chunk := response.read(1024*1024): output.write(chunk)
        if expected and expected != temporary.stat().st_size: raise RuntimeError(f'Incomplete asset: {relative}')
        temporary.replace(path)
        manifest['assets'][relative] = {
            'url': url, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'bytes': path.stat().st_size, 'retrievedUTC': datetime.now(timezone.utc).isoformat(),
            'lastModified': headers.get('Last-Modified'),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2))
        print('Saved', relative, path.stat().st_size, 'bytes', flush=True)
    return manifest

if __name__ == '__main__':
    acquire()
