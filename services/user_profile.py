from sqlalchemy import text
from db.postgres import AsyncSessionLocal

async def get_user_profile(user_id: int) -> dict:
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT
                u.user_id,
                u.user_size,
                u.user_weight,
                uhp.user_health_profile_objective AS goal,
                uhp.user_health_profile_activity AS activity_level,
                u.user_gender
            FROM user_ u
            LEFT JOIN user_health_profile uhp ON u.user_id = uhp.user_id
            WHERE u.user_id = :user_id
        """), {"user_id": user_id})
        row = result.mappings().first()
        if not row:
            return None
        return dict(row)

async def get_user_equipment(user_id: int) -> list:
    """
    Récupère l'équipement disponible via le programme sportif de l'utilisateur.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT DISTINCT se.sport_equipment_name
            FROM user_ u
            JOIN sport_program sp ON u.sport_program_id = sp.sport_program_id
            JOIN program_sport_session pss ON sp.sport_program_id = pss.sport_program_id
            JOIN sport_session_exercise sse ON pss.sport_session_id = sse.sport_session_id
            JOIN sport_exercise_equipment see ON sse.sport_exercise_id = see.sport_exercise_id
            JOIN sport_equipment se ON see.sport_equipment_id = se.sport_equipment_id
            WHERE u.user_id = :user_id
        """), {"user_id": user_id})
        rows = result.fetchall()
        return [r[0] for r in rows]

async def get_all_exercises() -> list:
    """
    Récupère tous les exercices depuis sport_exercise avec leur équipement associé.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT
                se.sport_exercise_id,
                se.sport_exercise_name AS name,
                se.sport_exercise_objective AS objective,
                se.sport_exercise_difficulty AS difficulty,
                se.sport_exercise_muscle_group AS muscle_group,
                se.sport_exercise_instruction AS instruction,
                se.sport_exercise_cal_burned AS cal_burned,
                COALESCE(
                    array_agg(eq.sport_equipment_name) FILTER (WHERE eq.sport_equipment_name IS NOT NULL),
                    ARRAY[]::varchar[]
                ) AS equipment
            FROM sport_exercise se
            LEFT JOIN sport_exercise_equipment see ON se.sport_exercise_id = see.sport_exercise_id
            LEFT JOIN sport_equipment eq ON see.sport_equipment_id = eq.sport_equipment_id
            GROUP BY se.sport_exercise_id
        """))
        rows = result.mappings().all()
        return [dict(r) for r in rows]

async def get_all_equipment() -> list:
    """
    Récupère tous les équipements disponibles.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT sport_equipment_name FROM sport_equipment
        """))
        return [r[0] for r in result.fetchall()]