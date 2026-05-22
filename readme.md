# Documentation — healthAI-service-exercices

## 1. Présentation du service

`healthAI-service-exercices` est un micro-service indépendant du projet HealthAI Coach. Il constitue le **moteur de recommandation d'activités physiques** de la plateforme.

Son rôle est de générer des programmes d'entraînement personnalisés en combinant deux approches complémentaires :

- Un **modèle de machine learning** qui prédit les exercices les plus adaptés au profil de l'utilisateur
- Un **modèle de langage** (Google Gemini) qui génère un plan d'entraînement structuré et lisible à partir des exercices sélectionnés

Le service est développé en **Python / FastAPI**, connecté à **PostgreSQL** (source de données utilisateurs et exercices) et à **MongoDB** (stockage des recommandations générées).

## 2. Architecture

```
                        ┌─────────────────────────────────┐
                        │     healthAI-service-exercices   │
                        │                                  │
                        │  FastAPI (port 8002)             │
                        │                                  │
                        │  1. Lecture profil user          │
                        │     └─▶ PostgreSQL               │
                        │                                  │
                        │  2. Prédiction ML                │
                        │     └─▶ RandomForestClassifier   │
                        │                                  │
                        │  3. Génération plan textuel      │
                        │     └─▶ Google Gemini API        │
                        │                                  │
                        │  4. Stockage recommandation      │
                        │     └─▶ MongoDB                  │
                        └─────────────────────────────────┘
```

## 3. Prérequis

- Docker et Docker Compose installés
- Une clé API Google Gemini (gratuite) — voir section 4
- BDD PostgreSQL alimentée avec des données via l'ETL (tables `sport_exercise` et `sport_equipment` non vides)
- MongoDB configuré dans le Docker Compose

## 4. Installation et démarrage

### 4.1 Obtenir une clé API Gemini

1. Aller sur https://aistudio.google.com
2. Se connecter avec un compte Google
3. Cliquer sur **"Get API key"** → **"Create API key"**
4. Copier la clé générée (commence par `AIza...`)

Le modèle utilisé est `gemini-1.5-flash` : **gratuit**, limité à 15 requêtes/minute et 1500 requêtes/jour.

### 4.2 Lancer le projet

```bash
docker compose up --build -d
```

Vérifier les logs du service :

```bash
docker logs exercices_service
```

Les logs doivent afficher dans l'ordre :
1. Connexion MongoDB réussie
2. Entraînement du modèle ML avec le `classification_report`
3. `Uvicorn running on http://0.0.0.0:8002`

## 5. Structure du projet

```
healthAI-service-exercices/
├── app.py                    # Point d'entrée FastAPI, initialisation au démarrage
├── state.py                   # Cache partagé (exercices, équipements)
├── routers/
│   └── exercices.py           # Définition des routes de l'API
├── services/
│   ├── modele.py              # Modèle ML + scoring
│   ├── llm.py                 # Appel API Gemini
│   └── user_profile.py        # Requêtes PostgreSQL
├── models/
│   └── schemas.py             # Schémas Pydantic (validation des données)
├── db/
│   ├── mongo.py               # Connexion MongoDB (Motor)
│   └── postgres.py            # Connexion PostgreSQL (SQLAlchemy async)
├── Dockerfile
├── requirements.txt
└── .env
```

## 6. Fonctionnement détaillé

### 6.1 Initialisation au démarrage

Au lancement du conteneur, `app.py` exécute dans l'ordre :

1. **Connexion MongoDB** via Motor (client async)
2. **Chargement des exercices** disponible depuis PostgreSQL (`sport_exercise`)
3. **Chargement de l'équipement** disponible depuis PostgreSQL (`sport_equipment`)
4. **Entraînement ou chargement du modèle ML** — si `modele_exercices.joblib` existe déjà sur le volume, il est chargé directement ; sinon il est entraîné et sauvegardé

Les exercices et équipements sont stockés dans `state.py` (cache en mémoire) pour ne pas interroger PostgreSQL à chaque requête.

### 6.2 Traitement d'une requête de recommandation

Quand `POST /exercices/recommander` est appelé, voici le pipeline complet :

```
Requête entrante (user_id + profil)
        │
        ▼
Lecture profil utilisateur dans PostgreSQL
(objectif, niveau d'activité depuis user_health_profile)
        │
        ▼
Fusion avec les données envoyées par le front
(le front peut surcharger l'objectif ou l'équipement)
        │
        ▼
Prédiction ML (modèle)
→ calcule la probabilité d'adéquation pour chaque exercice
→ filtre les exercices incompatibles (limitations, équipement manquant)
→ retourne le top 8
        │
        ▼
Génération du plan textuel (Google Gemini)
→ reçoit le profil + les 8 exercices sélectionnés
→ génère un programme semaine structuré en français
        │
        ▼
Stockage dans MongoDB (collection recommandations_exercices)
        │
        ▼
Réponse JSON (recommandation_id + exercices_scores + plan_genere)
```

### 6.3 Tables PostgreSQL utilisées

| Table | Usage |
|---|---|
| `user_` | Données de base de l'utilisateur |
| `user_health_profile` | Objectif santé, niveau d'activité |
| `sport_exercise` | Liste des exercices disponibles |
| `sport_equipment` | Liste des équipements disponibles |
| `sport_exercise_equipment` | Association exercice ↔ équipement |
| `sport_program` | Programme sportif de l'utilisateur |
| `program_sport_session` | Sessions du programme |
| `sport_session_exercise` | Exercices des sessions |

## 7. API — Routes disponibles

La documentation interactive complète est disponible sur **http://localhost:8002/docs** après démarrage.

### `GET /health`

Vérifie que le service est opérationnel.

**Réponse :**
```json
{
  "status": "ok",
  "service": "exercices_service"
}
```

### `POST /exercices/recommander`

Génère un programme d'entraînement personnalisé.

**Body :**
```json
{
  "user_id": 1,
  "goal": "weight_loss",
  "level": "beginner",
  "equipment": ["none", "mat"],
  "sessions_per_week": 3,
  "session_duration_minutes": 45,
  "limitations": ["knee"],
  "preferred_activities": []
}
```

**Valeurs acceptées :**

| Champ | Valeurs possibles |
|---|---|
| `goal` | `weight_loss`, `muscle_gain`, `endurance`, `flexibility`, `maintenance` |
| `level` | `beginner`, `intermediate`, `advanced` |
| `limitations` | `lower_back`, `knee`, `shoulder` |

**Réponse :**
```json
{
  "recommandation_id": "664f1a2b3c4d5e6f7a8b9c0d",
  "exercices_scores": [
    {
      "name": "Pompes",
      "score": 0.42,
      "equipment": ["none", "mat"],
      "limitations_incompatible": ["shoulder"]
    }
  ],
  "plan_genere": "Semaine 1 :\n\nLundi - Séance 1 (45 min)..."
}
```

### `GET /exercices/historique/{user_id}`

Retourne les 10 dernières recommandations d'un utilisateur.

**Exemple :** `GET /exercices/historique/1`

**Réponse :**
```json
[
  {
    "_id": "664f1a2b3c4d5e6f7a8b9c0d",
    "created_at": "2025-05-18T10:00:00Z",
    "input_profile": { ... },
    "plan_genere": "Semaine 1 : ..."
  }
]
```

### `POST /exercices/{recommandation_id}/feedback`

Enregistre le feedback de l'utilisateur sur une recommandation.

**Exemple :** `POST /exercices/664f1a2b3c4d5e6f7a8b9c0d/feedback`

**Body :**
```json
{
  "rating": 4,
  "comment": "Très bon programme, bien adapté à mon niveau"
}
```

**Réponse :**
```json
{
  "status": "feedback enregistré"
}
```

### `GET /exercices/liste`

Retourne la liste complète des exercices disponibles (depuis le cache PostgreSQL).

## 8. Modèle de données MongoDB

### Collection `recommandations_exercices`

Chaque document correspond à une recommandation générée :

```json
{
  "_id": "ObjectId",
  "user_id": 1,
  "created_at": "2025-05-18T10:00:00Z",
  "input_profile": {
    "user_id": 1,
    "goal": "weight_loss",
    "level": "beginner",
    "equipment": ["none", "mat"],
    "sessions_per_week": 3,
    "session_duration_minutes": 45,
    "limitations": [],
    "preferred_activities": []
  },
  "exercices_scores": [
    {
      "name": "Pompes",
      "score": 0.42,
      "objective": "weight_loss",
      "difficulty": "beginner",
      "equipment": ["none", "mat"],
      "limitations_incompatible": ["shoulder"]
    }
  ],
  "plan_genere": "Semaine 1 :\n\nLundi - Séance cardio (45 min)...",
  "llm_provider": "gemini-1.5-flash",
  "feedback": {
    "rating": 4,
    "comment": "Très bon programme"
  }
}
```

| Champ | Type | Description |
|---|---|---|
| `user_id` | int | Identifiant de l'utilisateur |
| `created_at` | datetime | Date et heure de génération |
| `input_profile` | object | Profil utilisateur utilisé pour la recommandation |
| `exercices_scores` | array | Exercices sélectionnés avec leur score de pertinence |
| `plan_genere` | string | Plan d'entraînement généré par Gemini |
| `llm_provider` | string | Modèle LLM utilisé (traçabilité) |
| `feedback` | object \| null | Feedback de l'utilisateur (null si absent) |

## 9. Modèle ML

### Choix du modèle

Le modèle utilisé est un **RandomForestClassifier** (scikit-learn). Ce choix est justifié par :

- Sa robustesse sur des données tabulaires de petite taille
- Sa capacité à gérer des features hétérogènes (catégorielles encodées + numériques)
- L'absence de besoin de normalisation des données
- La lisibilité des résultats via `predict_proba` (probabilités par classe)

### Données d'entraînement

Le modèle est entraîné sur **500 profils synthétiques** générés automatiquement au démarrage. Chaque profil est composé de :

| Feature | Description |
|---|---|
| `goal` | Objectif encodé en entier (0-4) |
| `level` | Niveau encodé en entier (0-2) |
| `sessions_per_week` | Nombre de séances par semaine (2-5) |
| `session_duration_minutes` | Durée par séance (30, 45 ou 60 min) |
| `equipment_vec` | Vecteur binaire de présence de chaque équipement |

Le label (variable cible) est **l'exercice le plus adapté** selon des règles métier définies dans `REGLES`.

### Pipeline de prédiction

1. Le profil utilisateur est encodé en vecteur numérique
2. Le modèle calcule la **probabilité d'adéquation** pour chaque exercice
3. Les exercices sont triés par probabilité décroissante
4. Les exercices **incompatibles** (limitations physiques ou équipement manquant) sont filtrés
5. Le **top 8** est retourné

### Persistance du modèle

Le modèle entraîné est sauvegardé dans `modele_exercices.joblib` via `joblib`. Au prochain démarrage du conteneur, il est rechargé directement sans réentraînement, grâce au volume Docker.

### Métriques

Les métriques de performance (précision, rappel, F1-score) sont affichées dans les logs du conteneur au moment de l'entraînement via `classification_report` de scikit-learn.

## 10. Intégration Gemini

### Rôle de Gemini

Gemini intervient **après** la sélection des exercices par le modèle ML. Son rôle est uniquement de **générer le plan textuel** à partir des exercices déjà sélectionnés. Il ne choisit pas les exercices — cela évite les hallucinations.

### Prompt utilisé

```
Tu es un coach sportif expert. Génère un programme d'entraînement structuré sur 1 semaine.

Profil utilisateur :
- Objectif : {goal_fr}
- Niveau : {level_fr}
- Séances par semaine : {sessions_per_week}
- Durée par séance : {session_duration_minutes} minutes
- Limitations physiques : {limitations}

Exercices sélectionnés : {noms_exercices}

Génère un plan semaine clair avec pour chaque séance : exercices, séries, répétitions et temps de repos.
Sois concis et pratique.
```

### Limites du tier gratuit

| Limite | Valeur |
|---|---|
| Requêtes par minute | 15 |
| Requêtes par jour | 1 500 |
| Coût | 0 € |