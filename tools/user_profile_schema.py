
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import date, datetime
from enum import Enum


class DayOfWeek(str, Enum):
    """Enum for days of the week"""
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


class WorkoutType(str, Enum):
    """Enum for workout types"""
    STRENGTH = "Strength"
    RUNNING = "Running"
    CARDIO = "Cardio"
    REST = "Rest"
    MIXED = "Mixed"


class Workout(BaseModel):
    """Individual workout session model"""
    workout_date: date = Field(description="Date of the workout")
    day_of_week: DayOfWeek = Field(description="Day of the week for the workout")
    workout_type: WorkoutType = Field(description="Type of workout")
    workout_description: str = Field(min_length=1, description="Detailed description of the workout")
    success_criteria: str = Field(min_length=1, description="Criteria to measure workout success")
    completed: bool = Field(default=False, description="Whether the workout was completed")
    notes: Optional[str] = Field(default=None, description="Additional notes about the workout")
    
    @field_validator('day_of_week')
    @classmethod
    def validate_day_matches_date(cls, v, info):
        """Ensure the day_of_week matches the actual date"""
        if info.data and 'workout_date' in info.data:
            actual_day = info.data['workout_date'].strftime('%A')
            if v != actual_day:
                # Auto-correct the day based on the date
                return actual_day
        return v
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class UserProfile(BaseModel):
    """User profile and workout plan model"""
    username: str = Field(min_length=1, description="Unique username identifier")
    
    # Weekly workout preferences
    days_per_week: int = Field(ge=1, le=7, description="Total number of workout days per week")
    runs_per_week: int = Field(ge=0, le=7, description="Number of running sessions per week")
    strength_workouts_per_week: int = Field(ge=0, le=7, description="Number of strength training sessions per week")
    
    # Goals
    strength_goals: str = Field(min_length=1, description="Strength training objectives and goals")
    running_goals: str = Field(min_length=1, description="Running objectives and goals")
    
    # Training plan
    training_plan: List[Workout] = Field(default_factory=list, description="List of planned workouts")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="When the profile was created")
    updated_at: datetime = Field(default_factory=datetime.now, description="When the profile was last updated")
    
    @field_validator('runs_per_week', 'strength_workouts_per_week')
    @classmethod
    def validate_workout_distribution(cls, v, info):
        """Ensure the sum of specific workouts doesn't exceed total days"""
        if info.data and 'days_per_week' in info.data:
            # Get the field name being validated
            field_name = info.field_name
            other_field = 'strength_workouts_per_week' if field_name == 'runs_per_week' else 'runs_per_week'
            
            # Calculate total specific workouts
            total_specific = v
            if other_field in info.data:
                total_specific += info.data[other_field]
            
            if total_specific > info.data['days_per_week']:
                raise ValueError(f"Total specific workouts ({total_specific}) cannot exceed total workout days ({info.data['days_per_week']})")
        return v
    
    def add_workout(self, workout: Workout) -> None:
        """Add a workout to the training plan"""
        self.training_plan.append(workout)
        self.updated_at = datetime.now()
    
    def get_workouts_by_date_range(self, start_date: date, end_date: date) -> List[Workout]:
        """Get workouts within a specific date range"""
        return [
            workout for workout in self.training_plan
            if start_date <= workout.workout_date <= end_date
        ]
    
    def get_workouts_by_type(self, workout_type: WorkoutType) -> List[Workout]:
        """Get all workouts of a specific type"""
        return [
            workout for workout in self.training_plan
            if workout.workout_type == workout_type
        ]
    
    def mark_workout_completed(self, workout_date: date, notes: Optional[str] = None) -> bool:
        """Mark a workout as completed by date"""
        for workout in self.training_plan:
            if workout.workout_date == workout_date:
                workout.completed = True
                if notes:
                    workout.notes = notes
                self.updated_at = datetime.now()
                return True
        return False