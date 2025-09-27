"""
Baseline Fitness Assessment Module

This module provides functions to analyze Strava data and establish current fitness levels
across multiple dimensions: aerobic capacity, training stress tolerance, strength baseline,
and recovery capacity.
"""

import os
import math
from typing import List, Dict, Any
from datetime import datetime, timedelta
from statistics import mean
from strava_client import get_recent_activities, strava_api


def calculate_vo2_max_estimation(running_activities: List[Dict]) -> Dict[str, Any]:
    """
    Estimate VO2 max from recent running activities using multiple methods.
    
    Uses Jack Daniels' formula and pace-based estimation for running activities
    with heart rate data when available.
    
    Args:
        running_activities: List of running activity data with pace and HR info
        
    Returns:
        Dict containing VO2 max estimations and supporting data
    """
    if not running_activities:
        return {
            "vo2_max_ml_kg_min": None,
            "method": "insufficient_data",
            "confidence": "low",
            "activities_analyzed": 0
        }
    
    vo2_estimates = []
    
    for activity in running_activities:
        # Skip if essential data is missing
        if not activity.get('distance') or not activity.get('moving_time'):
            continue
            
        distance_km = activity['distance'] / 1000  # Convert m to km
        time_hours = activity['moving_time'] / 3600  # Convert seconds to hours
        
        # Skip very short runs (< 1km) or very slow runs
        if distance_km < 1.0 or time_hours > 2.0:
            continue
            
        # Calculate pace in minutes per km
        pace_min_per_km = (time_hours * 60) / distance_km
        
        # Jack Daniels' VO2 max estimation from pace
        # VO2 = 15.3 × (distance in meters / time in minutes)
        time_minutes = activity['moving_time'] / 60
        vo2_pace = 15.3 * (activity['distance'] / time_minutes)
        
        # Alternative method using running velocity
        # VO2 = 0.2 × velocity(m/min) + 3.5 (for submaximal running)
        velocity_m_per_min = activity['distance'] / time_minutes
        vo2_velocity = 0.2 * velocity_m_per_min + 3.5
        
        # Weight the estimates based on run duration and intensity
        duration_weight = min(time_hours / 0.5, 1.0)  # Longer runs get more weight up to 30 min
        
        # Use the higher of the two estimates for conservative approach
        estimated_vo2 = max(vo2_pace, vo2_velocity) * duration_weight
        
        # Cap unrealistic values
        if 20 <= estimated_vo2 <= 80:
            vo2_estimates.append({
                'vo2_estimate': estimated_vo2,
                'distance_km': distance_km,
                'pace_min_per_km': pace_min_per_km,
                'activity_date': activity.get('start_date'),
                'method': 'pace_based'
            })
    
    if not vo2_estimates:
        return {
            "vo2_max_ml_kg_min": None,
            "method": "insufficient_quality_data",
            "confidence": "low",
            "activities_analyzed": len(running_activities)
        }
    
    # Calculate final VO2 max estimate
    recent_estimates = sorted(vo2_estimates, 
                            key=lambda x: x.get('activity_date', ''), 
                            reverse=True)[:5]  # Use 5 most recent
    
    vo2_values = [est['vo2_estimate'] for est in recent_estimates]
    final_vo2_max = mean(vo2_values)
    
    # Determine confidence based on data quality
    confidence = "high" if len(vo2_estimates) >= 5 else "medium" if len(vo2_estimates) >= 3 else "low"
    
    return {
        "vo2_max_ml_kg_min": round(final_vo2_max, 1),
        "method": "multi_run_pace_analysis",
        "confidence": confidence,
        "activities_analyzed": len(running_activities),
        "estimates_used": len(recent_estimates),
        "estimate_range": {
            "min": round(min(vo2_values), 1),
            "max": round(max(vo2_values), 1),
            "std_dev": round(math.sqrt(sum((x - final_vo2_max) ** 2 for x in vo2_values) / len(vo2_values)), 1)
        },
        "supporting_data": recent_estimates[:3]  # Include top 3 for reference
    }


def calculate_training_stress_capacity(activities: List[Dict], athlete_zones: Dict = None) -> Dict[str, Any]:
    """
    Calculate Training Stress Score (TSS) capacity based on recent training patterns.
    
    TSS estimates training load considering intensity and duration.
    For running: TSS = (duration_hours × normalized_graded_pace × intensity_factor^2) × 100
    For cycling: TSS = (duration_hours × normalized_power / FTP)^2 × 100
    
    Args:
        activities: List of recent activities with power/pace data
        athlete_zones: Heart rate and power zones for intensity calculation
        
    Returns:
        Dict containing TSS capacity metrics
    """
    if not activities:
        return {
            "weekly_tss_capacity": None,
            "chronic_training_load": None,
            "acute_training_load": None,
            "training_stress_balance": None,
            "method": "insufficient_data"
        }
    
    # Calculate TSS for each activity
    activity_tss = []
    
    for activity in activities:
        if not activity.get('moving_time'):
            continue
            
        duration_hours = activity['moving_time'] / 3600
        activity_type = activity.get('type', '').lower()
        tss = 0
        
        if activity_type in ['run', 'workout']:
            # Running TSS estimation
            if activity.get('average_heartrate') and athlete_zones:
                hr_zones = athlete_zones.get('heart_rate', {}).get('zones', [])
                if hr_zones:
                    # Calculate intensity factor from heart rate
                    avg_hr = activity['average_heartrate']
                    lthr = hr_zones[3]['min'] if len(hr_zones) > 3 else avg_hr * 0.9  # Estimate LTHR
                    intensity_factor = avg_hr / lthr
                    
                    # Running TSS = duration × IF^2 × 100
                    tss = duration_hours * (intensity_factor ** 2) * 100
            else:
                # Fallback: estimate based on pace if distance available
                if activity.get('distance'):
                    distance_km = activity['distance'] / 1000
                    pace_min_per_km = (duration_hours * 60) / distance_km
                    
                    # Rough intensity estimation from pace (4:00/km = high intensity)
                    intensity_factor = max(0.5, min(1.2, 5.0 / pace_min_per_km))
                    tss = duration_hours * (intensity_factor ** 2) * 100
                    
        elif activity_type in ['ride', 'cycling']:
            # Cycling TSS estimation
            if activity.get('average_watts') and athlete_zones:
                power_zones = athlete_zones.get('power', {}).get('zones', [])
                if power_zones and len(power_zones) > 3:
                    ftp = power_zones[3]['min']  # Zone 4 threshold as FTP estimate
                    avg_power = activity['average_watts']
                    normalized_power = avg_power * 1.05  # Rough NP estimation
                    
                    intensity_factor = normalized_power / ftp
                    tss = duration_hours * (intensity_factor ** 2) * 100
            else:
                # Fallback: estimate based on duration and assumed moderate intensity
                tss = duration_hours * 60  # Rough estimate for moderate effort
                
        else:
            # Other activities (swimming, strength training, etc.)
            # Use duration-based estimation with lower intensity factor
            tss = duration_hours * 40  # Conservative estimate
        
        if tss > 0:
            activity_tss.append({
                'date': activity.get('start_date'),
                'tss': round(tss, 1),
                'type': activity_type,
                'duration_hours': round(duration_hours, 2)
            })
    
    if not activity_tss:
        return {
            "weekly_tss_capacity": None,
            "chronic_training_load": None,
            "acute_training_load": None,
            "training_stress_balance": None,
            "method": "insufficient_quality_data"
        }
    
    # Sort by date for time-series analysis
    activity_tss.sort(key=lambda x: x.get('date', ''))
    
    # Calculate Chronic Training Load (CTL) - 42-day exponential average
    # Calculate Acute Training Load (ATL) - 7-day exponential average
    now = datetime.now()
    daily_tss = {}
    
    # Group TSS by day
    for activity in activity_tss:
        date_str = activity['date'][:10] if activity.get('date') else now.strftime('%Y-%m-%d')
        if date_str not in daily_tss:
            daily_tss[date_str] = 0
        daily_tss[date_str] += activity['tss']
    
    # Calculate CTL and ATL
    ctl_sum = sum(daily_tss.values())
    atl_sum = sum(tss for date, tss in daily_tss.items() 
                  if (now - datetime.strptime(date, '%Y-%m-%d')).days <= 7)
    
    # Rough CTL/ATL calculation (simplified)
    ctl = ctl_sum / min(42, len(daily_tss)) if daily_tss else 0
    atl = atl_sum / min(7, len([d for d in daily_tss.keys() 
                               if (now - datetime.strptime(d, '%Y-%m-%d')).days <= 7]))
    
    # Training Stress Balance (TSB) = CTL - ATL
    tsb = ctl - atl
    
    # Weekly TSS capacity estimation
    weekly_tss = sum(daily_tss.values()) * (7 / len(daily_tss)) if daily_tss else 0
    
    return {
        "weekly_tss_capacity": round(weekly_tss, 1),
        "chronic_training_load": round(ctl, 1),
        "acute_training_load": round(atl, 1),
        "training_stress_balance": round(tsb, 1),
        "total_activities_analyzed": len(activity_tss),
        "training_days": len(daily_tss),
        "average_daily_tss": round(mean(daily_tss.values()), 1) if daily_tss else 0,
        "method": "tss_estimation"
    }


def calculate_strength_baseline(activities: List[Dict]) -> Dict[str, Any]:
    """
    Calculate strength baseline from gym sessions and strength training activities.
    
    Analyzes frequency, duration, and patterns of strength training to establish
    a baseline fitness level for resistance training.
    
    Args:
        activities: List of activities including strength/gym sessions
        
    Returns:
        Dict containing strength training baseline metrics
    """
    strength_activities = [
        activity for activity in activities
        if activity.get('type', '').lower() in ['workout', 'weighttraining', 'crossfit', 'bodyweight']
        or 'gym' in activity.get('name', '').lower()
        or 'strength' in activity.get('name', '').lower()
        or 'weights' in activity.get('name', '').lower()
    ]
    
    if not strength_activities:
        return {
            "weekly_strength_frequency": 0,
            "average_session_duration": None,
            "strength_consistency": "none",
            "estimated_strength_level": "beginner",
            "method": "no_strength_data"
        }
    
    # Analyze frequency patterns
    now = datetime.now()
    recent_sessions = []
    
    for activity in strength_activities:
        if activity.get('start_date'):
            try:
                activity_date = datetime.fromisoformat(activity['start_date'].replace('Z', '+00:00'))
                days_ago = (now - activity_date).days
                
                if days_ago <= 90:  # Last 3 months
                    duration_minutes = activity.get('moving_time', 0) / 60
                    recent_sessions.append({
                        'date': activity_date,
                        'duration_minutes': duration_minutes,
                        'name': activity.get('name', ''),
                        'days_ago': days_ago
                    })
            except:
                continue
    
    if not recent_sessions:
        return {
            "weekly_strength_frequency": 0,
            "average_session_duration": None,
            "strength_consistency": "none",
            "estimated_strength_level": "beginner",
            "method": "no_recent_strength_data"
        }
    
    # Calculate frequency metrics
    weeks_of_data = max(1, max(session['days_ago'] for session in recent_sessions) / 7)
    weekly_frequency = len(recent_sessions) / weeks_of_data
    
    # Calculate average session duration
    valid_durations = [s['duration_minutes'] for s in recent_sessions if s['duration_minutes'] > 0]
    avg_duration = mean(valid_durations) if valid_durations else None
    
    # Assess consistency (coefficient of variation in weekly frequency)
    weekly_counts = {}
    for session in recent_sessions:
        week = session['date'].isocalendar()[1]
        year = session['date'].year
        week_key = f"{year}-W{week}"
        weekly_counts[week_key] = weekly_counts.get(week_key, 0) + 1
    
    if len(weekly_counts) > 1:
        weekly_values = list(weekly_counts.values())
        consistency_cv = (math.sqrt(sum((x - mean(weekly_values)) ** 2 for x in weekly_values) / len(weekly_values)) / mean(weekly_values))
        
        if consistency_cv < 0.3:
            consistency = "high"
        elif consistency_cv < 0.6:
            consistency = "moderate"
        else:
            consistency = "low"
    else:
        consistency = "insufficient_data"
    
    # Estimate strength level based on frequency and duration
    if weekly_frequency >= 4 and avg_duration and avg_duration >= 60:
        strength_level = "advanced"
    elif weekly_frequency >= 3 and avg_duration and avg_duration >= 45:
        strength_level = "intermediate"
    elif weekly_frequency >= 2:
        strength_level = "beginner_plus"
    elif weekly_frequency >= 1:
        strength_level = "beginner"
    else:
        strength_level = "sedentary"
    
    return {
        "weekly_strength_frequency": round(weekly_frequency, 1),
        "average_session_duration": round(avg_duration, 1) if avg_duration else None,
        "strength_consistency": consistency,
        "estimated_strength_level": strength_level,
        "total_sessions_analyzed": len(recent_sessions),
        "weeks_of_data": round(weeks_of_data, 1),
        "session_duration_range": {
            "min": round(min(valid_durations), 1) if valid_durations else None,
            "max": round(max(valid_durations), 1) if valid_durations else None
        },
        "method": "frequency_duration_analysis"
    }


def calculate_recovery_capacity(activities: List[Dict]) -> Dict[str, Any]:
    """
    Analyze recovery capacity from training frequency patterns and rest days.
    
    Examines training patterns to assess how well an athlete recovers between sessions
    and their capacity for training load.
    
    Args:
        activities: List of recent activities
        
    Returns:
        Dict containing recovery capacity metrics
    """
    if not activities:
        return {
            "recovery_score": None,
            "average_rest_between_sessions": None,
            "training_stress_tolerance": "unknown",
            "recommended_rest_days": None,
            "method": "insufficient_data"
        }
    
    # Sort activities by date
    dated_activities = []
    for activity in activities:
        if activity.get('start_date'):
            try:
                activity_date = datetime.fromisoformat(activity['start_date'].replace('Z', '+00:00'))
                dated_activities.append({
                    'date': activity_date,
                    'duration': activity.get('moving_time', 0) / 3600,  # hours
                    'type': activity.get('type', '').lower(),
                    'intensity': activity.get('average_heartrate', 0) / 180 if activity.get('average_heartrate') else 0.5  # Rough intensity estimate
                })
            except:
                continue
    
    if len(dated_activities) < 3:
        return {
            "recovery_score": None,
            "average_rest_between_sessions": None,
            "training_stress_tolerance": "unknown",
            "recommended_rest_days": None,
            "method": "insufficient_activity_data"
        }
    
    # Sort by date
    dated_activities.sort(key=lambda x: x['date'])
    
    # Calculate rest periods between activities
    rest_periods = []
    intensity_after_rest = []
    
    for i in range(1, len(dated_activities)):
        prev_activity = dated_activities[i-1]
        curr_activity = dated_activities[i]
        
        rest_hours = (curr_activity['date'] - prev_activity['date']).total_seconds() / 3600
        rest_periods.append(rest_hours)
        
        # Track if performance/intensity maintained after rest
        intensity_after_rest.append({
            'rest_hours': rest_hours,
            'prev_intensity': prev_activity['intensity'],
            'curr_intensity': curr_activity['intensity'],
            'intensity_maintained': curr_activity['intensity'] >= prev_activity['intensity'] * 0.9
        })
    
    # Calculate recovery metrics
    avg_rest_hours = mean(rest_periods) if rest_periods else 0
    
    # Recovery score based on ability to maintain intensity after different rest periods
    recovery_patterns = {
        'short_rest': [r for r in intensity_after_rest if r['rest_hours'] < 24],
        'medium_rest': [r for r in intensity_after_rest if 24 <= r['rest_hours'] < 48],
        'long_rest': [r for r in intensity_after_rest if r['rest_hours'] >= 48]
    }
    
    recovery_scores = {}
    for period, data in recovery_patterns.items():
        if data:
            maintained_percentage = sum(1 for d in data if d['intensity_maintained']) / len(data)
            recovery_scores[period] = maintained_percentage
    
    # Overall recovery score (weighted average)
    if recovery_scores:
        overall_recovery = (
            recovery_scores.get('short_rest', 0.5) * 0.2 +
            recovery_scores.get('medium_rest', 0.7) * 0.5 +
            recovery_scores.get('long_rest', 0.9) * 0.3
        )
    else:
        overall_recovery = 0.5  # Default moderate
    
    # Assess training stress tolerance
    training_days_per_week = len([a for a in dated_activities 
                                 if (datetime.now() - a['date']).days <= 7])
    
    if training_days_per_week >= 6 and overall_recovery > 0.7:
        stress_tolerance = "high"
        recommended_rest = 1
    elif training_days_per_week >= 4 and overall_recovery > 0.6:
        stress_tolerance = "moderate"
        recommended_rest = 2
    elif training_days_per_week >= 2:
        stress_tolerance = "low_moderate"
        recommended_rest = 2
    else:
        stress_tolerance = "low"
        recommended_rest = 3
    
    # Adjust recommendations based on recovery score
    if overall_recovery < 0.5:
        recommended_rest += 1
    
    return {
        "recovery_score": round(overall_recovery * 100, 1),  # Convert to percentage
        "average_rest_between_sessions": round(avg_rest_hours, 1),
        "training_stress_tolerance": stress_tolerance,
        "recommended_rest_days": recommended_rest,
        "training_frequency_per_week": training_days_per_week,
        "recovery_patterns": {
            "short_rest_recovery": round(recovery_scores.get('short_rest', 0) * 100, 1),
            "medium_rest_recovery": round(recovery_scores.get('medium_rest', 0) * 100, 1),
            "long_rest_recovery": round(recovery_scores.get('long_rest', 0) * 100, 1)
        },
        "activities_analyzed": len(dated_activities),
        "method": "activity_frequency_analysis"
    }


def get_comprehensive_fitness_baseline(days_lookback: int = 90) -> Dict[str, Any]:
    """
    Get a comprehensive fitness baseline assessment for an athlete.
    
    Combines VO2 max estimation, TSS capacity, strength baseline, and recovery
    capacity into a complete fitness profile.
    
    Args:
        days_lookback: Number of days to look back for activity analysis
        
    Returns:
        Dict containing comprehensive fitness baseline
    """
    token = os.getenv("STRAVA_ACCESS_TOKEN")
    if not token:
        return {"error": "Missing STRAVA_ACCESS_TOKEN environment variable"}
    
    try:
        # Fetch recent activities
        activities_data = get_recent_activities(token, per_page=200)
        activities = [
            {
                'id': activity.id,
                'name': activity.name,
                'distance': activity.distance,
                'start_date': activity.start_date.isoformat() if activity.start_date else None,
                'type': getattr(activity, 'type', 'Unknown'),
                'moving_time': getattr(activity, 'moving_time', 0),
                'average_heartrate': getattr(activity, 'average_heartrate', None),
                'average_watts': getattr(activity, 'average_watts', None)
            }
            for activity in activities_data
        ]
        
        # Filter recent activities
        cutoff_date = datetime.now() - timedelta(days=days_lookback)
        recent_activities = [
            activity for activity in activities
            if activity.get('start_date') and 
            datetime.fromisoformat(activity['start_date'].replace('Z', '+00:00')) > cutoff_date
        ]
        
        # Get athlete zones for TSS calculation
        try:
            zones_response = strava_api.get("athlete/zones", headers={"Authorization": f"Bearer {token}"})
            athlete_zones = zones_response
        except:
            athlete_zones = None
        
        # Get running activities for VO2 max
        running_activities = [
            activity for activity in recent_activities
            if activity.get('type', '').lower() in ['run', 'trail_run', 'treadmill']
        ]
        
        # Calculate all fitness metrics
        vo2_max_results = calculate_vo2_max_estimation(running_activities)
        tss_capacity_results = calculate_training_stress_capacity(recent_activities, athlete_zones)
        strength_baseline_results = calculate_strength_baseline(recent_activities)
        recovery_capacity_results = calculate_recovery_capacity(recent_activities)
        
        # Calculate overall fitness score (0-100)
        fitness_components = []
        
        # VO2 max contribution (0-25 points)
        if vo2_max_results.get('vo2_max_ml_kg_min'):
            vo2_score = min(25, max(0, (vo2_max_results['vo2_max_ml_kg_min'] - 30) * 0.8))
            fitness_components.append(vo2_score)
        
        # TSS capacity contribution (0-25 points)
        if tss_capacity_results.get('weekly_tss_capacity'):
            tss_score = min(25, tss_capacity_results['weekly_tss_capacity'] / 20)
            fitness_components.append(tss_score)
        
        # Strength contribution (0-25 points)
        strength_levels = {'sedentary': 0, 'beginner': 5, 'beginner_plus': 10, 'intermediate': 18, 'advanced': 25}
        strength_score = strength_levels.get(strength_baseline_results.get('estimated_strength_level', 'beginner'), 5)
        fitness_components.append(strength_score)
        
        # Recovery contribution (0-25 points)
        if recovery_capacity_results.get('recovery_score'):
            recovery_score = recovery_capacity_results['recovery_score'] / 4  # Convert to 0-25 scale
            fitness_components.append(recovery_score)
        
        overall_fitness_score = sum(fitness_components) if fitness_components else None
        
        return {
            "overall_fitness_score": round(overall_fitness_score, 1) if overall_fitness_score else None,
            "assessment_date": datetime.now().isoformat(),
            "data_period_days": days_lookback,
            "activities_analyzed": len(recent_activities),
            "vo2_max_assessment": vo2_max_results,
            "training_stress_capacity": tss_capacity_results,
            "strength_baseline": strength_baseline_results,
            "recovery_capacity": recovery_capacity_results,
            "fitness_level_interpretation": {
                "overall": "excellent" if overall_fitness_score and overall_fitness_score >= 80 else
                         "good" if overall_fitness_score and overall_fitness_score >= 60 else
                         "moderate" if overall_fitness_score and overall_fitness_score >= 40 else
                         "developing" if overall_fitness_score else "insufficient_data",
                "strengths": [],
                "areas_for_improvement": []
            }
        }
        
    except Exception as e:
        return {"error": f"Failed to calculate fitness baseline: {str(e)}"}