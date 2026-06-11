import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

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

def obtenir_modele_gratuit_actif() -> str:
    """Interroge OpenRouter en direct pour lister et utiliser un modèle gratuit en ligne."""
    modele_fallback = "meta-llama/llama-3.1-8b-instruct:free"
    try:
        url_models = "https://openrouter.ai/api/v1/models".strip()
        reponse = requests.get(url_models, timeout=10)
        if reponse.status_code == 200:
            data = reponse.json().get("data", [])
            modeles_gratuits = [m["id"] for m in data if str(m.get("id", "")).endswith(":free")]
            if modeles_gratuits:
                print(f"--- [INFO OPENROUTER] Modèles gratuits opérationnels détectés : {modeles_gratuits} ---")
                return modeles_gratuits[0]
    except Exception as e:
        print(f"--- [ATTENTION] Impossible de lister les modèles, utilisation du fallback : {str(e)} ---")
    return modele_fallback

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

CONSIGNES DE FORMATAGE CRUCIALES :
1. N'utilise ABSOLUMENT AUCUN formatage Markdown. 
2. Interdiction totale d'utiliser des astérisques (*), des dièses (#), ou des tirets du bas (_).
3. Rédige uniquement en TEXTE BRUT (Plain Text).
4. Pour structurer ton texte, utilise uniquement des sauts de ligne simples ou doubles (Touches Entrée).
5. Écris les titres des jours ou des séances en MAJUSCULES pour les faire ressortir.

Génère un plan semaine clair avec pour chaque séance : exercices, séries, répétitions et temps de repos.
Sois concis et pratique.
"""

    if not api_key:
        return "Clé API OpenRouter manquante dans le fichier .env."

    url_api = "https://openrouter.ai/api/v1/chat/completions".strip()
    modele_choisi = obtenir_modele_gratuit_actif()
    print(f"--- [DEBUG IA] Modèle sélectionné pour la génération : {modele_choisi} ---")

    try:
        response = requests.post(
            url=url_api,
            headers={
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json"
            },
            json={
                "model": modele_choisi,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=30
        )
        
        response.raise_for_status()
        res_json = response.json()
        
        if "choices" in res_json and len(res_json["choices"]) > 0:
            return res_json["choices"][0]["message"]["content"]
            
        return "L'IA n'a pas pu formater de réponse textuelle."

    except Exception as e:
        print(f"--- ERREUR GENERATION IA DANS LLM.PY (OPENROUTER) --- : {str(e)}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"-> Réponse brute du serveur d'API : {response.text}")
        return "Plan d'entraînement indisponible (Erreur de communication avec l'IA)."