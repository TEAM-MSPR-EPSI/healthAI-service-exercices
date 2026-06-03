import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

GOALS_FR = {
    "weight_loss": "Perte de poids",
    "muscle_gain": "Prise de masse",
    "endurance": "Endurance",
    "flexibility": "Flexibilité",
    "maintenance": "Maintien"
}

LEVELS_FR = {
    "beginner": "Débutant",
    "intermediate": "Intermédiaire",
    "advanced": "Avancé"
}

async def generer_plan_exercices(profile: dict, exercices: list) -> str:
    noms_exercices = [ex["name"] for ex in exercices]
    goal_fr = GOALS_FR.get(profile["goal"], profile["goal"])
    level_fr = LEVELS_FR.get(profile["level"], profile["level"])

    prompt = f"""
Tu es un coach sportif expert. Génère un programme d'entraînement structuré sur 1 semaine.

Profil utilisateur :
- Objectif : {goal_fr}
- Niveau : {level_fr}
- Séances par semaine : {profile['sessions_per_week']}
- Durée par séance : {profile['session_duration_minutes']} minutes
- Limitations physiques : {', '.join(profile.get('limitations', [])) or 'Aucune'}

Exercices sélectionnés : {', '.join(noms_exercices)}

Génère un plan semaine clair avec pour chaque séance : exercices, séries, répétitions et temps de repos.
Sois concis et pratique.
"""

    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    response = model.generate_content(prompt)
    return response.text