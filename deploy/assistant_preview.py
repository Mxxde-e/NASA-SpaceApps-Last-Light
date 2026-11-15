"""Local/CI guide-only test app; no science engine or model credentials required."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.chat import router
app=FastAPI()
app.include_router(router)
app.mount('/',StaticFiles(directory='dist',html=True),name='preview')
