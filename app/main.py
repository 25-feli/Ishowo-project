from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router
from app.database.config import engine
from app.database.init_db import init_database
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(
    title="ISHOWO - Prospect Intelligence",
    version="1.0.0",
    description="API de prospection intelligente"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.mount("/static", StaticFiles(directory="frontend-react"), name="static")


# Routes
app.include_router(router, prefix="/api", tags=["ISHOWO"])

@app.on_event("startup")
def startup():
    """Initialisation au démarrage"""
    print("Démarrage de ISHOWO API...")
    init_database(engine)
    print(" API ISHOWO prête")
    print("Lien de l'interface http://localhost:8000/docs")

@app.get("/")
async def root():
    return {
        "service": "ISHOWO - Prospection intelligente",
        "version": "1.0.0",
        "docs": "/docs",
        "api": "/api"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
