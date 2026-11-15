"""Local/CI guide-only test app; no science engine or model credentials required."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.chat import router
from backend.mission_chat import router as planner_router
app=FastAPI()
app.include_router(router)
app.include_router(planner_router)
app.mount('/',StaticFiles(directory='dist',html=True),name='preview')
