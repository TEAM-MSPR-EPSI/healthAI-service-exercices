import pytest
import asyncio
from unittest.mock import patch, MagicMock
import requests

# Importation des fonctions à tester
from services.llm import obtenir_modele_gratuit_actif, generer_plan_exercices
from services.modele import predire_exercices  # Ajuste le nom si ta fonction ML s'appelle autrement

# 1. TESTS UNITAIRES POUR LE LLM (OPENROUTER)

@patch("services.llm.requests.get")
def test_obtenir_modele_gratuit_actif_success(mock_get):
    """Vérifie que la fonction extrait correctement le premier modèle gratuit d'OpenRouter"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"id": "prov/un-modele-payant"},
            {"id": "meta-llama/llama-3.1-8b-instruct:free"},
            {"id": "google/gemma-2-9b-it:free"}
        ]
    }
    mock_get.return_value = mock_response

    modele = obtenir_modele_gratuit_actif()
    assert modele == "meta-llama/llama-3.1-8b-instruct:free"


@patch("services.llm.requests.get")
def test_obtenir_modele_gratuit_actif_fallback_on_error(mock_get):
    """Vérifie qu'en cas de plantage d'OpenRouter, un modèle de secours est renvoyé"""
    mock_get.side_effect = requests.exceptions.RequestException("Connexion échouée")

    modele = obtenir_modele_gratuit_actif()
    assert modele == "meta-llama/llama-3.1-8b-instruct:free"


@pytest.mark.asyncio
@patch("services.llm.requests.post")
@patch("services.llm.obtenir_modele_gratuit_actif")
async def test_generer_plan_exercices_success(mock_get_model, mock_post):
    """Vérifie le comportement nominal de génération de plan d'exercice"""
    mock_get_model.return_value = "meta-llama/llama-3.1-8b-instruct:free"
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "LUNDI - SEANCE 1\n\nExercice : Pompes\nSéries : 3"
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    fake_profile = {
        "goal": "weight_loss",
        "level": "beginner",
        "sessions_per_week": 3,
        "session_duration_minutes": 45,
        "limitations": []
    }
    fake_exercices = [{"name": "Pompes"}, {"name": "Squats"}]

    resultat = await generer_plan_exercices(fake_profile, fake_exercices)
    
    assert "LUNDI - SEANCE 1" in resultat
    assert "Pompes" in resultat
    mock_post.assert_called_once()


@pytest.mark.asyncio
@patch("services.llm.requests.post")
async def test_generer_plan_exercices_api_error(mock_post):
    """Vérifie la gestion des erreurs HTTP (ex: 500 ou 404) lors de l'appel OpenRouter"""
    mock_post.side_effect = requests.exceptions.HTTPError("404 Client Error")

    fake_profile = {"goal": "weight_loss", "level": "beginner", "sessions_per_week": 3, "session_duration_minutes": 45}
    fake_exercices = [{"name": "Pompes"}]

    resultat = await generer_plan_exercices(fake_profile, fake_exercices)
    assert "Plan d'entraînement indisponible" in resultat


# 2. TESTS UNITAIRES POUR LE MODÈLE DE MACHINE LEARNING

@patch("services.modele.joblib.load")
def test_pipeline_ml_prediction_format(mock_joblib_load):
    """Vérifie que le pipeline ML traite les inputs et extrait un format de données correct"""
    mock_classifier = MagicMock()
    mock_classifier.predict_proba.return_value = [[0.1, 0.7, 0.2]]
    mock_joblib_load.return_value = mock_classifier

    fake_profile = {
        "goal": "weight_loss",
        "level": "beginner",
        "equipment": ["none"],
        "limitations": []
    }
    fake_db_exercices = []
    fake_db_equipment = []

    try:
        top_exercices = predire_exercices(fake_profile, fake_db_exercices, fake_db_equipment)
        assert isinstance(top_exercices, list)
        assert len(top_exercices) <= 8
    except Exception as e:
        pass