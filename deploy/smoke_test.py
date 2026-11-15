"""Bounded deployment checks. Run against the gateway, not Uvicorn directly."""
import sys,requests
base=(sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8080').rstrip('/')
s=requests.Session()
r=s.get(base+'/',timeout=30);assert r.status_code==200,r.status_code
assert r.headers.get('X-Content-Type-Options')=='nosniff'
assert r.headers.get('X-Frame-Options')=='DENY'
for p in ['/.env','/.git/config','/backend/server.py']:
    assert s.get(base+p,timeout=10).status_code==404,p
assert s.get(base+'/api/study',timeout=30).status_code==200
assert s.post(base+'/api/search',data='x'*17000,timeout=10).status_code==413
codes=[s.post(base+'/api/search',json={},headers={'X-Forwarded-For':f'192.0.2.{i}'},timeout=10).status_code for i in range(8)]
assert 422 in codes and 429 in codes,codes
assert s.get(base+'/presentation-backup.html',timeout=10).status_code==200
print('PASS: homepage, study API, security headers, private-file 404s, oversized-body 413, shared search limit 429, offline report. Search responses:',codes)
