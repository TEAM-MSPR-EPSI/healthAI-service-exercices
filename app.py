from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import traceback
from contextlib import asynccontextmanager
from routers import exercices
from db.mongo import connect, disconnect
from services.user_profile import get_all_exercises, get_all_equipment
from services.modele import charger_modele
from dotenv import load_dotenv
import state

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect()
    state.exercices_cache = await get_all_exercises()
    state.equipment_cache = await get_all_equipment()

    if state.exercices_cache:
        charger_modele(state.exercices_cache, state.equipment_cache)
    else:
        print("Base vide au démarrage — appelez POST /exercices/entrainer après avoir alimenté la base")

    yield
    await disconnect()

app = FastAPI(
    title="HealthAI - Service de Recommandation d'Exercices",
    version="1.0.0",
    description="Moteur de recommandation d'activités physiques personnalisées",
    lifespan=lifespan
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": traceback.format_exc()}
    )

app.include_router(exercices.router, prefix="/exercices", tags=["exercices"])

@app.get("/health")
async def health():
    return {"status": "ok", "service": "exercices_service"}