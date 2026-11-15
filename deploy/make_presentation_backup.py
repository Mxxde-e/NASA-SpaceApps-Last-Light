"""Save an offline presentation report from a real completed cached search."""
import html,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def render(v):
    if isinstance(v,dict):
        return '<dl>'+''.join('<dt>'+html.escape(str(k))+'</dt><dd>'+render(x)+'</dd>' for k,x in v.items() if k not in {'samples','timeline','horizon','horizons','traces'})+'</dl>'
    if isinstance(v,list):
        if len(v)>12: return str(len(v))+' samples (full series in the live study export)'
        return ''.join('<section>'+render(x)+'</section>' for x in v)
    return html.escape(str(v))
if __name__=='__main__':
    paths=list((ROOT/'data/cache').glob('result-*.json'))
    if not paths: raise SystemExit('Complete a real search first.')
    d=json.loads(max(paths,key=lambda p:p.stat().st_mtime).read_text())
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Last Light saved study</title><style>body{background:#091522;color:#f4efdf;font:16px system-ui;max-width:1100px;margin:auto;padding:36px}h1,h2{color:#ffcc71}section{border:1px solid #345;padding:18px;margin:18px 0;border-radius:12px}dt{color:#78ddd1;font-weight:bold;margin-top:12px}dd{overflow-wrap:anywhere}dl dl{border-left:1px solid #345;padding-left:12px}@media print{body{background:white;color:black}h1,h2,dt{color:black}}</style><h1>LAST LIGHT</h1><h2>Saved real-data presentation example</h2><p>Offline snapshot of an actual computed study. Inputs cannot be changed here. Ground support, descent safety, radio links and flight reachability remain unassessed.</p>'
    for k in ['computedUTC','elapsedSeconds','request','qualifyingCount','screenedGridPoints','nasaRejectedGridPoints','geometryLocations','evaluatedScenarios','original','candidates','notes','geometry','screening']:
        if k in d: page+='<section><h2>'+html.escape(k)+'</h2>'+render(d[k])+'</section>'
    page+='</html>'
    for p in [ROOT/'docs/presentation-backup.html',ROOT/'dist/presentation-backup.html']:
        p.parent.mkdir(parents=True,exist_ok=True);p.write_text(page,encoding='utf-8')
    print('Saved real study',d.get('computedUTC'))
