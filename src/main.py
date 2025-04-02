from fastapi import FastAPI
from database import close_mongo_connection

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Événement de démarrage de l'application"""
    pass

@app.on_event("shutdown")
async def shutdown_event():
    """Événement d'arrêt de l'application"""
    await close_mongo_connection()

@app.get("/")
def read_root():
    return {"message": "Hello World"}
