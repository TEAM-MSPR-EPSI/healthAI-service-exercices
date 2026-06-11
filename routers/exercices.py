from fastapi import APIRouter, HTTPException
from models.schemas import ExercicesRequest, FeedbackRequest
from services.modele import predire_exercices, entrainer_modele, MODEL_PATH
from services.llm import generer_plan_exercices
from services.user_profile import get_user_profile, get_user_equipment, get_all_exercises, get_all_equipment
from db.mongo import get_db
from datetime import datetime, timezone
from bson import ObjectId
import state
import os

router = APIRouter()

@router.post("/entrainer")
async def entrainer_modele_route():
    exercices = await get_all_exercises()
    equipment_list = await get_all_equipment()

    if not exercices:
        raise HTTPException(status_code=400, detail="Aucun exercice en base de données")

    if os.path.exists(MODEL_PATH):
        os.remove(MODEL_PATH)

    entrainer_modele(exercices, equipment_list)
    state.exercices_cache = exercices
    state.equipment_cache = equipment_list

    return {
        "status": "Modèle entraîné avec succès",
        "nb_exercices": len(exercices),
        "nb_equipements": len(equipment_list)
    }

@router.post("/recommander")
async def recommander_exercices(request: ExercicesRequest):
    if not state.exercices_cache:
        raise HTTPException(status_code=503, detail="Modèle non entraîné — appelez POST /exercices/entrainer d'abord")

    user_profile = await get_user_profile(request.user_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    profile = request.model_dump()
    if not profile.get("equipment"):
        profile["equipment"] = await get_user_equipment(request.user_id)

    scored = predire_exercices(profile, state.exercices_cache, state.equipment_cache)

    if not scored:
        raise HTTPException(status_code=400, detail="Aucun exercice compatible avec ce profil")

    try:
        plan = await generer_plan_exercices(profile, scored)
    except Exception as e:
        print(f"--- ERREUR CRITIQUE GEMINI --- : {str(e)}")
        raise HTTPException(
            status_code=502, 
            detail="Le service d'IA est indisponible ou vos quotas Google AI Studio sont épuisés. Veuillez réessayer ultérieurement."
        )

    doc = {
        "user_id": request.user_id,
        "created_at": datetime.now(timezone.utc),
        "input_profile": profile,
        "exercices_scores": scored,
        "plan_genere": plan,
        "llm_provider": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        "feedback": None
    }

    db = get_db()
    result = await db.recommandations_exercices.insert_one(doc)

    return {
        "recommandation_id": str(result.inserted_id),
        "exercices_scores": scored,
        "plan_genere": plan
    }

@router.get("/historique/{user_id}")
async def get_historique(user_id: int):
    db = get_db()
    cursor = db.recommandations_exercices.find(
        {"user_id": user_id},
        {"_id": 1, "created_at": 1, "input_profile": 1, "plan_genere": 1}
    ).sort("created_at", -1).limit(10)
    historique = await cursor.to_list(length=10)
    for doc in historique:
        doc["_id"] = str(doc["_id"])
    return historique

@router.post("/{recommandation_id}/feedback")
async def ajouter_feedback(recommandation_id: str, feedback: FeedbackRequest):
    db = get_db()
    result = await db.recommandations_exercices.update_one(
        {"_id": ObjectId(recommandation_id)},
        {"$set": {"feedback": feedback.model_dump()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Recommandation introuvable")
    return {"status": "feedback enregistré"}

@router.get("/liste")
async def liste_exercices():
    return state.exercices_cache