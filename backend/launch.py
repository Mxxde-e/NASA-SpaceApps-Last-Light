"""User-facing local launcher; the console owns the service until Ctrl+C."""
import threading
import time
import urllib.request
import webbrowser
import uvicorn

URL='http://127.0.0.1:8000'

def open_when_ready():
    for _ in range(120):
        try:
            with urllib.request.urlopen(URL+'/api/study',timeout=2) as response:
                if response.status==200:
                    webbrowser.open(URL)
                    return
        except Exception: time.sleep(.5)

if __name__=='__main__':
    threading.Thread(target=open_when_ready,daemon=True).start()
    print('Last Light local pilot: '+URL+' — close this console or press Ctrl+C to stop.',flush=True)
    uvicorn.run('backend.server:app',host='127.0.0.1',port=8000,workers=1)
