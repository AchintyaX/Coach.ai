#!/usr/bin/env python3
"""
Workout Database MCP Server

A FastMCP server that provides comprehensive workout and user profile management
capabilities through the Model Context Protocol. This server wraps the WorkoutDatabase
class to provide structured, validated access to fitness coaching data.

The server exposes tools for:
- Creating and managing user profiles
- Adding and tracking workouts
- Querying workout data by date ranges and types
- Marking workouts as completed
- Database backup and maintenance

All tools include detailed JSON schemas for robust input validation and
clear descriptions to help LLM agents understand their capabilities.
"""

import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pathlib import Path

# Add the project root to the Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastmcp import FastMCP, Context
from tools.workout_db_tools import WorkoutDatabase
from tools.user_profile_schema import UserProfile, Workout, WorkoutType, DayOfWeek

# Initialize FastMCP server
mcp = FastMCP("workout-database-server")

# Initialize database with a default path
DEFAULT_DB_PATH = os.path.join(project_root, "data", "workout_database.json")
db = WorkoutDatabase(DEFAULT_DB_PATH)

# ============================================================================
# USER PROFILE MANAGEMENT TOOLS
# ============================================================================

@mcp.tool
def create_user_profile(
    username: str,
    days_per_week: int,
    runs_per_week: int,
    strength_workouts_per_week: int,
    strength_goals: str,
    running_goals: str
) -> Dict[str, Any]:
    """
    Create a new user profile in the fitness coaching database.
    
    This tool creates a comprehensive user profile that includes workout preferences,
    training frequency, and fitness goals. The profile serves as the foundation
    for personalized workout planning and progress tracking.
    
    Args:
        username: Unique identifier for the user (3-50 characters, alphanumeric and underscores only)
        days_per_week: Total number of workout days per week (1-7, must be >= runs_per_week + strength_workouts_per_week)
        runs_per_week: Number of running/cardio sessions per week (0-7, cannot exceed days_per_week)
        strength_workouts_per_week: Number of strength training sessions per week (0-7, cannot exceed days_per_week)
        strength_goals: Detailed description of strength training objectives (e.g., "Increase bench press to 200lbs, improve overall functional strength")
        running_goals: Detailed description of running/cardio objectives (e.g., "Complete 10K in under 45 minutes, build endurance for half marathon")
    
    Returns:
        Dict containing:
        - success: Boolean indicating if profile was created
        - message: Descriptive message about the operation result
        - profile_data: Created profile information (if successful)
        - validation_errors: List of validation issues (if any)
    
    Examples:
        - Create profile for beginner runner: username="john_doe", days_per_week=4, runs_per_week=2, strength_workouts_per_week=2
        - Create profile for strength focused athlete: username="jane_smith", days_per_week=5, runs_per_week=1, strength_workouts_per_week=4
    """
    try:
        # Create UserProfile object with validation
        user_profile = UserProfile(
            username=username,
            days_per_week=days_per_week,
            runs_per_week=runs_per_week,
            strength_workouts_per_week=strength_workouts_per_week,
            strength_goals=strength_goals,
            running_goals=running_goals
        )
        
        # Attempt to create in database
        success = db.create_user_profile(user_profile)
        
        if success:
            return {
                "success": True,
                "message": f"Successfully created profile for user '{username}'",
                "profile_data": {
                    "username": username,
                    "total_days_per_week": days_per_week,
                    "running_sessions": runs_per_week,
                    "strength_sessions": strength_workouts_per_week,
                    "created_at": user_profile.created_at.isoformat()
                },
                "validation_errors": []
            }
        else:
            return {
                "success": False,
                "message": f"User '{username}' already exists in the database",
                "profile_data": None,
                "validation_errors": ["Username already taken"]
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to create user profile: {str(e)}",
            "profile_data": None,
            "validation_errors": [str(e)]
        }

@mcp.tool
def get_user_profile(username: str) -> Dict[str, Any]:
    """
    Retrieve a complete user profile from the database.
    
    This tool fetches all user information including personal preferences,
    workout frequency settings, fitness goals, and current training plan.
    Essential for understanding a user's fitness context before providing advice.
    
    Args:
        username: Unique identifier of the user to retrieve
        
    Returns:
        Dict containing:
        - success: Boolean indicating if profile was found
        - message: Descriptive message about the operation result
        - profile_data: Complete user profile information including:
          - Basic info (username, created/updated dates)
          - Workout preferences (days per week, workout distribution)
          - Goals (strength and running objectives)
          - Training plan (list of scheduled workouts)
          - Statistics (total workouts, completed count)
        - user_found: Boolean indicating if user exists in database
    
    Examples:
        - Retrieve existing user: get_user_profile("john_doe")
        - Check if user exists: get_user_profile("potential_new_user")
    """
    try:
        user_profile = db.get_user_profile(username)
        
        if user_profile is None:
            return {
                "success": False,
                "message": f"User '{username}' not found in database",
                "profile_data": None,
                "user_found": False
            }
        
        # Calculate training plan statistics
        total_workouts = len(user_profile.training_plan)
        completed_workouts = sum(1 for workout in user_profile.training_plan if workout.completed)
        
        return {
            "success": True,
            "message": f"Successfully retrieved profile for user '{username}'",
            "profile_data": {
                "username": user_profile.username,
                "workout_schedule": {
                    "total_days_per_week": user_profile.days_per_week,
                    "runs_per_week": user_profile.runs_per_week,
                    "strength_workouts_per_week": user_profile.strength_workouts_per_week
                },
                "goals": {
                    "strength_goals": user_profile.strength_goals,
                    "running_goals": user_profile.running_goals
                },
                "training_statistics": {
                    "total_planned_workouts": total_workouts,
                    "completed_workouts": completed_workouts,
                    "completion_rate": round((completed_workouts / total_workouts * 100) if total_workouts > 0 else 0, 1)
                },
                "dates": {
                    "profile_created": user_profile.created_at.isoformat(),
                    "last_updated": user_profile.updated_at.isoformat()
                },
                "has_training_plan": total_workouts > 0
            },
            "user_found": True
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving user profile: {str(e)}",
            "profile_data": None,
            "user_found": False
        }

@mcp.tool
def update_user_goals(
    username: str,
    strength_goals: Optional[str] = None,
    running_goals: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update fitness goals for an existing user profile.
    
    This tool allows modification of user fitness objectives without affecting
    their workout schedule or existing training plan. Useful for goal progression
    or when user priorities change.
    
    Args:
        username: Unique identifier of the user to update
        strength_goals: New strength training objectives (optional, keeps existing if not provided)
        running_goals: New running/cardio objectives (optional, keeps existing if not provided)
        
    Returns:
        Dict containing:
        - success: Boolean indicating if update was successful
        - message: Descriptive message about the operation result
        - updated_fields: List of fields that were modified
        - current_goals: Updated goal information
    
    Examples:
        - Update both goals: update_user_goals("john_doe", "Deadlift 300lbs", "Run 5K in 20 minutes")
        - Update only strength: update_user_goals("jane_smith", strength_goals="Focus on Olympic lifts")
        - Update only running: update_user_goals("mike_runner", running_goals="Train for Boston Marathon")
    """
    try:
        user_profile = db.get_user_profile(username)
        
        if user_profile is None:
            return {
                "success": False,
                "message": f"User '{username}' not found in database",
                "updated_fields": [],
                "current_goals": None
            }
        
        updated_fields = []
        
        # Update goals if provided
        if strength_goals is not None:
            user_profile.strength_goals = strength_goals
            updated_fields.append("strength_goals")
            
        if running_goals is not None:
            user_profile.running_goals = running_goals
            updated_fields.append("running_goals")
        
        if not updated_fields:
            return {
                "success": False,
                "message": "No goals provided for update",
                "updated_fields": [],
                "current_goals": {
                    "strength_goals": user_profile.strength_goals,
                    "running_goals": user_profile.running_goals
                }
            }
        
        # Save updates to database
        success = db.update_user_profile(username, user_profile)
        
        if success:
            return {
                "success": True,
                "message": f"Successfully updated {', '.join(updated_fields)} for user '{username}'",
                "updated_fields": updated_fields,
                "current_goals": {
                    "strength_goals": user_profile.strength_goals,
                    "running_goals": user_profile.running_goals
                }
            }
        else:
            return {
                "success": False,
                "message": "Failed to save goal updates to database",
                "updated_fields": [],
                "current_goals": None
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Error updating user goals: {str(e)}",
            "updated_fields": [],
            "current_goals": None
        }

# ============================================================================
# WORKOUT MANAGEMENT TOOLS
# ============================================================================

@mcp.tool
def add_workout(
    username: str,
    workout_date: str,
    workout_type: str,
    workout_description: str,
    success_criteria: str,
    day_of_week: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a new workout to a user's training plan.
    
    This tool creates a structured workout entry with clear success criteria
    and automatically handles day-of-week validation. Essential for building
    comprehensive training plans and tracking workout progression.
    
    Args:
        username: User to add the workout for
        workout_date: Date of the workout in YYYY-MM-DD format (e.g., "2024-03-15")
        workout_type: Type of workout - must be one of: "Strength", "Running", "Cardio", "Rest", "Mixed"
        workout_description: Detailed description of the workout activities (e.g., "5x5 squats, 3x8 bench press, 20min core work")
        success_criteria: Specific, measurable criteria for workout completion (e.g., "Complete all sets with proper form, heart rate 150-170 bpm during cardio")
        day_of_week: Day of the week (optional, will be auto-calculated from date if not provided)
        
    Returns:
        Dict containing:
        - success: Boolean indicating if workout was added
        - message: Descriptive message about the operation result
        - workout_data: Added workout information
        - validation_errors: List of any validation issues
    
    Examples:
        - Strength workout: add_workout("john_doe", "2024-03-15", "Strength", "Upper body: bench press 5x5, rows 4x8", "Complete all sets with good form")
        - Running workout: add_workout("jane_runner", "2024-03-16", "Running", "5K tempo run", "Maintain 7:30/mile pace for entire distance")
        - Mixed workout: add_workout("mike_athlete", "2024-03-17", "Mixed", "30min strength + 20min cardio", "Complete strength circuit, maintain 150+ bpm during cardio")
    """
    try:
        # Validate workout_type
        valid_types = ["Strength", "Running", "Cardio", "Rest", "Mixed"]
        if workout_type not in valid_types:
            return {
                "success": False,
                "message": f"Invalid workout_type '{workout_type}'. Must be one of: {', '.join(valid_types)}",
                "workout_data": None,
                "validation_errors": [f"workout_type must be one of: {', '.join(valid_types)}"]
            }
        
        # Parse and validate date
        try:
            parsed_date = date.fromisoformat(workout_date)
        except ValueError:
            return {
                "success": False,
                "message": f"Invalid date format '{workout_date}'. Use YYYY-MM-DD format",
                "workout_data": None,
                "validation_errors": ["Date must be in YYYY-MM-DD format"]
            }
        
        # Auto-calculate day of week if not provided
        if day_of_week is None:
            day_of_week = parsed_date.strftime('%A')
        
        # Validate day_of_week
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        if day_of_week not in valid_days:
            return {
                "success": False,
                "message": f"Invalid day_of_week '{day_of_week}'. Must be one of: {', '.join(valid_days)}",
                "workout_data": None,
                "validation_errors": [f"day_of_week must be one of: {', '.join(valid_days)}"]
            }
        
        # Create workout object
        workout = Workout(
            workout_date=parsed_date,
            day_of_week=DayOfWeek(day_of_week),
            workout_type=WorkoutType(workout_type),
            workout_description=workout_description,
            success_criteria=success_criteria
        )
        
        # Add to user's training plan
        success = db.add_workout_to_user(username, workout)
        
        if success:
            return {
                "success": True,
                "message": f"Successfully added {workout_type.lower()} workout for {username} on {workout_date}",
                "workout_data": {
                    "date": workout_date,
                    "day": day_of_week,
                    "type": workout_type,
                    "description": workout_description,
                    "success_criteria": success_criteria,
                    "completed": False
                },
                "validation_errors": []
            }
        else:
            return {
                "success": False,
                "message": f"Failed to add workout - user '{username}' not found",
                "workout_data": None,
                "validation_errors": ["User not found in database"]
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Error adding workout: {str(e)}",
            "workout_data": None,
            "validation_errors": [str(e)]
        }

@mcp.tool
def mark_workout_completed(
    username: str,
    workout_date: str,
    completion_notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mark a scheduled workout as completed with optional notes.
    
    This tool updates workout status and allows recording of performance notes,
    modifications, or observations. Critical for tracking progress and adherence
    to training plans.
    
    Args:
        username: User who completed the workout
        workout_date: Date of the completed workout in YYYY-MM-DD format
        completion_notes: Optional notes about the workout performance (e.g., "Felt strong, increased weight on squats", "Cut short due to fatigue")
        
    Returns:
        Dict containing:
        - success: Boolean indicating if workout was marked completed
        - message: Descriptive message about the operation result
        - workout_info: Information about the completed workout
        - previous_status: Whether workout was already completed
    
    Examples:
        - Basic completion: mark_workout_completed("john_doe", "2024-03-15")
        - With performance notes: mark_workout_completed("jane_runner", "2024-03-16", "PR on 5K time - 22:45!")
        - With modifications: mark_workout_completed("mike_athlete", "2024-03-17", "Skipped last set due to shoulder discomfort")
    """
    try:
        # Validate and parse date
        try:
            parsed_date = date.fromisoformat(workout_date)
        except ValueError:
            return {
                "success": False,
                "message": f"Invalid date format '{workout_date}'. Use YYYY-MM-DD format",
                "workout_info": None,
                "previous_status": None
            }
        
        # Check if user exists and get current workout status
        user_profile = db.get_user_profile(username)
        if user_profile is None:
            return {
                "success": False,
                "message": f"User '{username}' not found in database",
                "workout_info": None,
                "previous_status": None
            }
        
        # Find the workout to check current status
        target_workout = None
        for workout in user_profile.training_plan:
            if workout.workout_date == parsed_date:
                target_workout = workout
                break
        
        if target_workout is None:
            return {
                "success": False,
                "message": f"No workout scheduled for {username} on {workout_date}",
                "workout_info": None,
                "previous_status": None
            }
        
        previous_status = target_workout.completed
        
        # Mark workout as completed
        success = db.mark_workout_completed(username, parsed_date, completion_notes)
        
        if success:
            return {
                "success": True,
                "message": f"{'Workout already completed, updated notes' if previous_status else 'Successfully marked workout as completed'} for {username} on {workout_date}",
                "workout_info": {
                    "date": workout_date,
                    "type": target_workout.workout_type.value,
                    "description": target_workout.workout_description,
                    "completion_notes": completion_notes,
                    "was_already_completed": previous_status
                },
                "previous_status": previous_status
            }
        else:
            return {
                "success": False,
                "message": f"Failed to mark workout as completed - technical error",
                "workout_info": None,
                "previous_status": previous_status
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Error marking workout completed: {str(e)}",
            "workout_info": None,
            "previous_status": None
        }

@mcp.tool
def get_user_workouts_by_date_range(
    username: str,
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """
    Retrieve all workouts for a user within a specified date range.
    
    This tool provides comprehensive workout history and upcoming schedule
    within any date range. Essential for progress analysis, weekly planning,
    and identifying workout patterns.
    
    Args:
        username: User whose workouts to retrieve
        start_date: Start of date range in YYYY-MM-DD format (inclusive)
        end_date: End of date range in YYYY-MM-DD format (inclusive)
        
    Returns:
        Dict containing:
        - success: Boolean indicating if query was successful
        - message: Descriptive message about the operation result
        - workouts: List of workouts in the date range with detailed information
        - summary: Statistical summary of the workout data
        - date_range: Confirmed date range of the query
    
    Examples:
        - Current week: get_user_workouts_by_date_range("john_doe", "2024-03-11", "2024-03-17")
        - Full month: get_user_workouts_by_date_range("jane_runner", "2024-03-01", "2024-03-31")
        - Specific period: get_user_workouts_by_date_range("mike_athlete", "2024-02-15", "2024-03-15")
    """
    try:
        # Validate and parse dates
        try:
            start_parsed = date.fromisoformat(start_date)
            end_parsed = date.fromisoformat(end_date)
        except ValueError as e:
            return {
                "success": False,
                "message": f"Invalid date format. Use YYYY-MM-DD format. Error: {str(e)}",
                "workouts": [],
                "summary": None,
                "date_range": None
            }
        
        if start_parsed > end_parsed:
            return {
                "success": False,
                "message": "Start date must be before or equal to end date",
                "workouts": [],
                "summary": None,
                "date_range": None
            }
        
        # Get workouts in date range
        workouts = db.get_user_workouts_by_date_range(username, start_parsed, end_parsed)
        
        if workouts is None:
            return {
                "success": False,
                "message": f"User '{username}' not found in database",
                "workouts": [],
                "summary": None,
                "date_range": None
            }
        
        # Convert workouts to detailed dictionaries
        workout_list = []
        completed_count = 0
        workout_type_counts = {}
        
        for workout in workouts:
            workout_dict = {
                "date": workout.workout_date.isoformat(),
                "day_of_week": workout.day_of_week.value,
                "type": workout.workout_type.value,
                "description": workout.workout_description,
                "success_criteria": workout.success_criteria,
                "completed": workout.completed,
                "notes": workout.notes
            }
            workout_list.append(workout_dict)
            
            if workout.completed:
                completed_count += 1
            
            # Count workout types
            workout_type = workout.workout_type.value
            workout_type_counts[workout_type] = workout_type_counts.get(workout_type, 0) + 1
        
        # Calculate summary statistics
        total_workouts = len(workout_list)
        completion_rate = round((completed_count / total_workouts * 100) if total_workouts > 0 else 0, 1)
        
        return {
            "success": True,
            "message": f"Retrieved {total_workouts} workout(s) for {username} from {start_date} to {end_date}",
            "workouts": workout_list,
            "summary": {
                "total_workouts": total_workouts,
                "completed_workouts": completed_count,
                "pending_workouts": total_workouts - completed_count,
                "completion_rate_percent": completion_rate,
                "workout_type_breakdown": workout_type_counts,
                "date_span_days": (end_parsed - start_parsed).days + 1
            },
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving workouts: {str(e)}",
            "workouts": [],
            "summary": None,
            "date_range": None
        }

# ============================================================================
# DATABASE MANAGEMENT TOOLS
# ============================================================================

@mcp.tool
def list_all_users() -> Dict[str, Any]:
    """
    Get a list of all users currently registered in the fitness database.
    
    This tool provides an overview of all users in the system, useful for
    administrative purposes, user management, and system statistics.
    
    Returns:
        Dict containing:
        - success: Boolean indicating if query was successful
        - message: Descriptive message about the operation result
        - users: List of all usernames in the database
        - user_count: Total number of registered users
        - database_status: Information about database state
    
    Examples:
        - System overview: list_all_users()
        - User existence check: Use to see if a username exists before operations
    """
    try:
        users = db.list_all_users()
        
        return {
            "success": True,
            "message": f"Retrieved {len(users)} user(s) from database",
            "users": sorted(users),  # Sort alphabetically for consistency
            "user_count": len(users),
            "database_status": {
                "has_users": len(users) > 0,
                "database_path": DEFAULT_DB_PATH
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving user list: {str(e)}",
            "users": [],
            "user_count": 0,
            "database_status": {
                "has_users": False,
                "database_path": DEFAULT_DB_PATH
            }
        }

@mcp.tool
def get_database_statistics() -> Dict[str, Any]:
    """
    Get comprehensive statistics about the fitness coaching database.
    
    This tool provides insights into database usage, user activity levels,
    workout distribution, and system health metrics. Valuable for understanding
    coaching effectiveness and user engagement patterns.
    
    Returns:
        Dict containing:
        - success: Boolean indicating if analysis was successful
        - message: Descriptive message about the operation result
        - statistics: Comprehensive database metrics including:
          - User statistics (total users, active users)
          - Workout statistics (total workouts, completion rates)
          - Type distribution (workout type breakdown)
          - Activity trends (recent activity patterns)
        - analysis_date: When these statistics were generated
    
    Examples:
        - System health check: get_database_statistics()
        - Progress reporting: Use for generating coaching effectiveness reports
    """
    try:
        all_profiles = db.get_all_user_profiles()
        
        if not all_profiles:
            return {
                "success": True,
                "message": "Database is empty - no users registered",
                "statistics": {
                    "user_stats": {"total_users": 0},
                    "workout_stats": {"total_workouts": 0},
                    "type_distribution": {},
                    "activity_trends": {}
                },
                "analysis_date": datetime.now().isoformat()
            }
        
        # Calculate comprehensive statistics
        total_users = len(all_profiles)
        total_workouts = 0
        completed_workouts = 0
        workout_type_counts = {}
        users_with_workouts = 0
        recent_activity_count = 0
        
        # Recent activity threshold (last 30 days)
        thirty_days_ago = date.today().replace(day=1)  # Simplified: start of current month
        
        for profile in all_profiles:
            profile_workout_count = len(profile.training_plan)
            if profile_workout_count > 0:
                users_with_workouts += 1
            
            for workout in profile.training_plan:
                total_workouts += 1
                
                if workout.completed:
                    completed_workouts += 1
                
                # Count workout types
                workout_type = workout.workout_type.value
                workout_type_counts[workout_type] = workout_type_counts.get(workout_type, 0) + 1
                
                # Check for recent activity
                if workout.workout_date >= thirty_days_ago:
                    recent_activity_count += 1
        
        # Calculate rates and percentages
        completion_rate = round((completed_workouts / total_workouts * 100) if total_workouts > 0 else 0, 1)
        active_user_rate = round((users_with_workouts / total_users * 100) if total_users > 0 else 0, 1)
        avg_workouts_per_user = round(total_workouts / total_users, 1) if total_users > 0 else 0
        
        return {
            "success": True,
            "message": f"Generated statistics for {total_users} users and {total_workouts} workouts",
            "statistics": {
                "user_stats": {
                    "total_users": total_users,
                    "users_with_workouts": users_with_workouts,
                    "active_user_percentage": active_user_rate,
                    "average_workouts_per_user": avg_workouts_per_user
                },
                "workout_stats": {
                    "total_workouts": total_workouts,
                    "completed_workouts": completed_workouts,
                    "pending_workouts": total_workouts - completed_workouts,
                    "overall_completion_rate": completion_rate
                },
                "type_distribution": workout_type_counts,
                "activity_trends": {
                    "recent_workouts_this_month": recent_activity_count,
                    "database_utilization": "High" if total_workouts > 50 else "Medium" if total_workouts > 10 else "Low"
                }
            },
            "analysis_date": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error generating database statistics: {str(e)}",
            "statistics": {
                "user_stats": {},
                "workout_stats": {},
                "type_distribution": {},
                "activity_trends": {}
            },
            "analysis_date": datetime.now().isoformat()
        }

# ============================================================================
# SERVER STARTUP AND CONFIGURATION
# ============================================================================

def main():
    """
    Main entry point for the Workout Database MCP Server.
    
    Initializes the FastMCP server with STDIO transport for seamless
    integration with LlamaIndex agents and other MCP clients.
    """
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DEFAULT_DB_PATH), exist_ok=True)
    
    # Run server with STDIO transport (default)
    mcp.run()

if __name__ == "__main__":
    main()