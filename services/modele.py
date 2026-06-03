import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# objective_enum
GOALS = {
    "weight_loss": 0,
    "muscle_gain": 1,
    "endurance": 2,
    "flexibility": 3,
    "maintenance": 4
}

# difficulty_enum
LEVELS = {
    "beginner": 0,
    "intermediate": 1,
    "advanced": 2
}

# muscle_group_enum
MUSCLE_GROUPS = [
    "chest", "back", "shoulders", "biceps", "triceps",
    "forearms", "abs", "glutes", "quadriceps", "hamstrings",
    "calves", "full_body"
]

MODEL_PATH = "modele_exercices.joblib"

def encoder_profil(profile: dict, equipment_list: list) -> np.ndarray:
    goal = GOALS.get(profile["goal"], 0)
    level = LEVELS.get(profile["level"], 0)
    sessions = profile["sessions_per_week"]
    duree = profile["session_duration_minutes"]
    equipment_vec = [1 if eq in profile.get("equipment", []) else 0 for eq in equipment_list]
    return np.array([goal, level, sessions, duree] + equipment_vec).reshape(1, -1)

def generer_donnees_entrainement(exercices: list, equipment_list: list):
    donnees = []
    labels = []

    for _ in range(500):
        goal_key = np.random.choice(list(GOALS.keys()))
        goal = GOALS[goal_key]
        level_key = np.random.choice(list(LEVELS.keys()))
        level = LEVELS[level_key]
        sessions = np.random.randint(2, 6)
        duree = np.random.choice([30, 45, 60])
        equipment = np.random.choice(equipment_list, size=np.random.randint(1, 4), replace=False).tolist()
        equipment_vec = [1 if eq in equipment else 0 for eq in equipment_list]
        profil_vec = [goal, level, sessions, duree] + equipment_vec

        meilleur = None
        meilleur_score = -1
        for i, ex in enumerate(exercices):
            score = 0
            if ex["objective"] == goal_key:
                score += 3
            if ex["difficulty"] == level_key:
                score += 2
            if any(eq in equipment for eq in ex["equipment"]):
                score += 2
            if score > meilleur_score:
                meilleur_score = score
                meilleur = i

        if meilleur is not None:
            donnees.append(profil_vec)
            labels.append(meilleur)

    return np.array(donnees), np.array(labels)

def entrainer_modele(exercices: list, equipment_list: list):
    print("Entraînement du modèle en cours...")
    X, y = generer_donnees_entrainement(exercices, equipment_list)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    modele = RandomForestClassifier(n_estimators=100, random_state=42)
    modele.fit(X_train, y_train)

    y_pred = modele.predict(X_test)
    # Obtenir les classes uniques présentes dans y_test
    classes_uniques = sorted(np.unique(y_test))
    noms = [exercices[i]["name"] if i < len(exercices) else f"Exercise_{i}" for i in classes_uniques]
    print(classification_report(y_test, y_pred, labels=classes_uniques, target_names=noms, zero_division=0))

    joblib.dump(modele, MODEL_PATH)
    print(f"Modèle sauvegardé : {MODEL_PATH}")
    return modele

def charger_modele(exercices: list, equipment_list: list):
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return entrainer_modele(exercices, equipment_list)

def predire_exercices(profile: dict, exercices: list, equipment_list: list) -> list:
    modele = charger_modele(exercices, equipment_list)
    X = encoder_profil(profile, equipment_list)
    probas = modele.predict_proba(X)[0]

    exercices_avec_score = list(zip(exercices, probas))
    exercices_avec_score.sort(key=lambda x: x[1], reverse=True)

    resultats = []
    for ex, score in exercices_avec_score:
        if any(lim in ex.get("limitations_incompatible", []) for lim in profile.get("limitations", [])):
            continue
        if not any(eq in profile.get("equipment", []) for eq in ex.get("equipment", [])):
            continue
        resultats.append({**ex, "score": round(float(score), 4)})

    return resultats[:8]