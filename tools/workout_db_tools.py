"""
WorkoutDatabase - TinyDB-based database for managing UserProfile objects

This module provides a WorkoutDatabase class that handles CRUD operations
for UserProfile objects using TinyDB as the storage backend.
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pathlib import Path

from tinydb import TinyDB, Query
from tinydb.operations import set as db_set

from .user_profile_schema import UserProfile, Workout


class WorkoutDatabase:
    """
    Database class for managing UserProfile objects with TinyDB backend.
    
    Uses username as the primary key for CRUD operations.
    """
    
    def __init__(self, db_path: str = "workout_data.json"):
        """
        Initialize the WorkoutDatabase.
        
        Args:
            db_path: Path to the TinyDB JSON file (default: "workout_data.json")
        """
        # Ensure the directory exists
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.db = TinyDB(db_path)
        self.User = Query()
    
    def _serialize_userprofile(self, user_profile: UserProfile) -> Dict[str, Any]:
        """
        Convert UserProfile object to dictionary for TinyDB storage.
        
        Args:
            user_profile: UserProfile object to serialize
            
        Returns:
            Dictionary representation suitable for TinyDB
        """
        # Convert to dict using Pydantic's model_dump method
        data = user_profile.model_dump()
        
        # Convert date objects to ISO format strings
        for workout in data.get('training_plan', []):
            if isinstance(workout.get('workout_date'), date):
                workout['workout_date'] = workout['workout_date'].isoformat()
        
        # Convert datetime objects to ISO format strings
        for field in ['created_at', 'updated_at']:
            if field in data and isinstance(data[field], datetime):
                data[field] = data[field].isoformat()
                
        return data
    
    def _deserialize_userprofile(self, data: Dict[str, Any]) -> UserProfile:
        """
        Convert dictionary from TinyDB to UserProfile object.
        
        Args:
            data: Dictionary from TinyDB storage
            
        Returns:
            UserProfile object
        """
        # Convert ISO format strings back to date objects
        for workout in data.get('training_plan', []):
            if isinstance(workout.get('workout_date'), str):
                workout['workout_date'] = date.fromisoformat(workout['workout_date'])
        
        # Convert ISO format strings back to datetime objects
        for field in ['created_at', 'updated_at']:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])
        
        return UserProfile(**data)
    
    def create_user_profile(self, user_profile: UserProfile) -> bool:
        """
        Create a new user profile in the database.
        
        Args:
            user_profile: UserProfile object to store
            
        Returns:
            True if created successfully, False if username already exists
        """
        # Check if user already exists
        if self.db.contains(self.User.username == user_profile.username):
            return False
        
        # Serialize and insert
        data = self._serialize_userprofile(user_profile)
        self.db.insert(data)
        return True
    
    def get_user_profile(self, username: str) -> Optional[UserProfile]:
        """
        Retrieve a user profile by username.
        
        Args:
            username: Username to search for
            
        Returns:
            UserProfile object if found, None otherwise
        """
        result = self.db.get(self.User.username == username)
        if result is None:
            return None
        
        return self._deserialize_userprofile(result)
    
    def update_user_profile(self, username: str, user_profile: UserProfile) -> bool:
        """
        Update an existing user profile.
        
        Args:
            username: Username of the profile to update
            user_profile: Updated UserProfile object
            
        Returns:
            True if updated successfully, False if user not found
        """
        # Check if user exists
        if not self.db.contains(self.User.username == username):
            return False
        
        # Update the updated_at timestamp
        user_profile.updated_at = datetime.now()
        
        # Serialize and update
        data = self._serialize_userprofile(user_profile)
        self.db.update(data, self.User.username == username)
        return True
    
    def delete_user_profile(self, username: str) -> bool:
        """
        Delete a user profile by username.
        
        Args:
            username: Username of the profile to delete
            
        Returns:
            True if deleted successfully, False if user not found
        """
        if not self.db.contains(self.User.username == username):
            return False
        
        self.db.remove(self.User.username == username)
        return True
    
    def list_all_users(self) -> List[str]:
        """
        Get a list of all usernames in the database.
        
        Returns:
            List of usernames
        """
        all_profiles = self.db.all()
        return [profile['username'] for profile in all_profiles]
    
    def get_all_user_profiles(self) -> List[UserProfile]:
        """
        Retrieve all user profiles from the database.
        
        Returns:
            List of UserProfile objects
        """
        all_data = self.db.all()
        return [self._deserialize_userprofile(data) for data in all_data]
    
    def add_workout_to_user(self, username: str, workout: Workout) -> bool:
        """
        Add a workout to a specific user's training plan.
        
        Args:
            username: Username of the user
            workout: Workout object to add
            
        Returns:
            True if added successfully, False if user not found
        """
        user_profile = self.get_user_profile(username)
        if user_profile is None:
            return False
        
        user_profile.add_workout(workout)
        return self.update_user_profile(username, user_profile)
    
    def mark_workout_completed(self, username: str, workout_date: date, notes: Optional[str] = None) -> bool:
        """
        Mark a workout as completed for a specific user.
        
        Args:
            username: Username of the user
            workout_date: Date of the workout to mark as completed
            notes: Optional notes about the completed workout
            
        Returns:
            True if marked successfully, False if user or workout not found
        """
        user_profile = self.get_user_profile(username)
        if user_profile is None:
            return False
        
        success = user_profile.mark_workout_completed(workout_date, notes)
        if success:
            return self.update_user_profile(username, user_profile)
        return False
    
    def get_user_workouts_by_date_range(self, username: str, start_date: date, end_date: date) -> Optional[List[Workout]]:
        """
        Get workouts for a user within a specific date range.
        
        Args:
            username: Username of the user
            start_date: Start date of the range
            end_date: End date of the range
            
        Returns:
            List of Workout objects if user found, None otherwise
        """
        user_profile = self.get_user_profile(username)
        if user_profile is None:
            return None
        
        return user_profile.get_workouts_by_date_range(start_date, end_date)
    
    def backup_database(self, backup_path: str) -> bool:
        """
        Create a backup of the database.
        
        Args:
            backup_path: Path where the backup should be saved
            
        Returns:
            True if backup created successfully, False otherwise
        """
        try:
            import shutil
            shutil.copy2(self.db.storage.path, backup_path)
            return True
        except Exception:
            return False
    
    def clear_all_data(self) -> None:
        """
        Remove all data from the database.
        
        Warning: This operation cannot be undone!
        """
        self.db.truncate()
    
    def close(self) -> None:
        """
        Close the database connection.
        """
        self.db.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()