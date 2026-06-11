from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class GoalEnum(str, Enum):
    weight_loss = "weight_loss"
    muscle_gain = "muscle_gain"
    endurance = "endurance"
    flexibility = "flexibility"
    maintenance = "maintenance"

class LevelEnum(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"

class ActivityLevelEnum(str, Enum):
    sedentary = "sedentary"
    lightly_active = "lightly_active"
    moderately_active = "moderately_active"
    very_active = "very_active"
    extra_active = "extra_active"

class ExercicesRequest(BaseModel):
    user_id: int
    goal: GoalEnum
    level: LevelEnum
    equipment: List[str]
    sessions_per_week: int
    session_duration_minutes: int
    limitations: Optional[List[str]] = []
    preferred_activities: Optional[List[str]] = []

class FeedbackRequest(BaseModel):
    rating: int
    comment: Optional[str] = None