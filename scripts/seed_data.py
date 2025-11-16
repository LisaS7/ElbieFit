# scripts/seed_data.py
from datetime import date
from decimal import Decimal
from typing import List, Tuple

from app.models import Exercise, UserProfile, Workout, WorkoutSet
from app.utils.dates import now


def build_profile(pk: str) -> UserProfile:
    """
    Build the test user profile.
    """
    ts = now()
    return UserProfile(
        PK=pk,
        SK="PROFILE",
        display_name="Lisa Test",
        email="lisa@example.com",
        created_at=ts,
        updated_at=ts,
        timezone="Europe/London",
    )


def build_exercises(pk: str) -> List[Exercise]:
    """
    Build all exercises used by the seed workouts.
    """
    ts = now()
    return [
        Exercise(
            PK=pk,
            SK="EXERCISE#PUSHUP",
            type="exercise",
            name="Push-up",
            muscles=["chest", "triceps", "shoulders"],
            equipment="bodyweight",
            category="push",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK="EXERCISE#ROW",
            type="exercise",
            name="Dumbbell Row",
            muscles=["lats", "upper_back", "biceps"],
            equipment="dumbbells",
            category="pull",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK="EXERCISE#SQUAT",
            type="exercise",
            name="Back Squat",
            muscles=["quads", "glutes", "hamstrings"],
            equipment="barbell",
            category="legs",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK="EXERCISE#DEADLIFT",
            type="exercise",
            name="Deadlift",
            muscles=["hamstrings", "glutes", "back"],
            equipment="barbell",
            category="hinge",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK="EXERCISE#PLANK",
            type="exercise",
            name="Plank",
            muscles=["core"],
            equipment="bodyweight",
            category="core",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK="EXERCISE#BURPEE",
            type="exercise",
            name="Burpee",
            muscles=["full_body"],
            equipment="bodyweight",
            category="conditioning",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK="EXERCISE#KETTLEBELL_SWING",
            type="exercise",
            name="Kettlebell Swing",
            muscles=["glutes", "hamstrings", "back"],
            equipment="kettlebell",
            category="hinge",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK="EXERCISE#LUNGE",
            type="exercise",
            name="Lunge",
            muscles=["quads", "glutes", "hamstrings"],
            equipment="dumbbells",
            category="legs",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK="EXERCISE#BENCH_PRESS",
            type="exercise",
            name="Bench Press",
            muscles=["chest", "triceps", "shoulders"],
            equipment="barbell",
            category="push",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK="EXERCISE#SHOULDER_PRESS",
            type="exercise",
            name="Shoulder Press",
            muscles=["shoulders", "triceps"],
            equipment="dumbbells",
            category="push",
            created_at=ts,
            updated_at=ts,
        ),
    ]


def build_workouts(pk: str) -> List[Tuple[Workout, List[WorkoutSet]]]:
    """
    Build all workouts and their sets.
    Returns a list of (Workout, [WorkoutSet, ...]) tuples.
    """
    ts = now()
    workouts: List[Tuple[Workout, List[WorkoutSet]]] = []

    # Workout 1: Push/Pull B
    w1 = Workout(
        PK=pk,
        SK="WORKOUT#2025-11-04#W1",
        type="workout",
        date=date(2025, 11, 4),
        name="Workout B",
        tags=["push", "pull", "upper_body"],
        notes="Push/pull day",
        created_at=ts,
        updated_at=ts,
    )
    s1 = [
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-04#W1#SET#001",
            type="set",
            exercise_id="PUSHUP",
            set_number=1,
            reps=12,
            weight_kg=Decimal(0.0),
            rpe=7,
            created_at=ts,
            updated_at=ts,
        ),
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-04#W1#SET#002",
            type="set",
            exercise_id="ROW",
            set_number=2,
            reps=10,
            weight_kg=Decimal(20.0),
            rpe=8,
            created_at=ts,
            updated_at=ts,
        ),
    ]
    workouts.append((w1, s1))

    # Workout 2: Lower Body Strength
    w2 = Workout(
        PK=pk,
        SK="WORKOUT#2025-11-06#W2",
        type="workout",
        date=date(2025, 11, 6),
        name="Lower Body Strength",
        tags=["legs", "strength"],
        notes="Focused on legs today. Knees screamed in ancient tongues.",
        created_at=ts,
        updated_at=ts,
    )
    s2 = [
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-06#W2#SET#001",
            type="set",
            exercise_id="SQUAT",
            set_number=1,
            reps=8,
            weight_kg=Decimal(40.0),
            rpe=7,
            created_at=ts,
            updated_at=ts,
        ),
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-06#W2#SET#002",
            type="set",
            exercise_id="DEADLIFT",
            set_number=2,
            reps=5,
            weight_kg=Decimal(60.0),
            rpe=8,
            created_at=ts,
            updated_at=ts,
        ),
    ]
    workouts.append((w2, s2))

    # Workout 3: Cardio & Core
    w3 = Workout(
        PK=pk,
        SK="WORKOUT#2025-11-08#W3",
        type="workout",
        date=date(2025, 11, 8),
        name="Cardio & Core",
        tags=["cardio", "core"],
        notes="Felt like my soul was escaping through my sweat glands.",
        created_at=ts,
        updated_at=ts,
    )
    s3 = [
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-08#W3#SET#001",
            type="set",
            exercise_id="PLANK",
            set_number=1,
            reps=1,
            weight_kg=Decimal(0.0),
            rpe=6,
            created_at=ts,
            updated_at=ts,
        ),
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-08#W3#SET#002",
            type="set",
            exercise_id="BURPEE",
            set_number=2,
            reps=10,
            weight_kg=Decimal(0.0),
            rpe=9,
            created_at=ts,
            updated_at=ts,
        ),
    ]
    workouts.append((w3, s3))

    # Workout 4: Full Body Flow
    w4 = Workout(
        PK=pk,
        SK="WORKOUT#2025-11-10#W4",
        type="workout",
        date=date(2025, 11, 10),
        name="Full Body Flow",
        tags=["full_body", "conditioning"],
        notes="Everything popped but in a friendly way.",
        created_at=ts,
        updated_at=ts,
    )
    s4 = [
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-10#W4#SET#001",
            type="set",
            exercise_id="KETTLEBELL_SWING",
            set_number=1,
            reps=15,
            weight_kg=Decimal(12.0),
            rpe=7,
            created_at=ts,
            updated_at=ts,
        ),
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-10#W4#SET#002",
            type="set",
            exercise_id="LUNGE",
            set_number=2,
            reps=12,
            weight_kg=Decimal(10.0),
            rpe=8,
            created_at=ts,
            updated_at=ts,
        ),
    ]
    workouts.append((w4, s4))

    # Workout 5: Push Day A
    w5 = Workout(
        PK=pk,
        SK="WORKOUT#2025-11-12#W5",
        type="workout",
        date=date(2025, 11, 12),
        name="Push Day A",
        tags=["push", "upper_body"],
        notes="Chest and triceps howled like a drowned cult choir.",
        created_at=ts,
        updated_at=ts,
    )
    s5 = [
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-12#W5#SET#001",
            type="set",
            exercise_id="BENCH_PRESS",
            set_number=1,
            reps=6,
            weight_kg=Decimal(35.0),
            rpe=7,
            created_at=ts,
            updated_at=ts,
        ),
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-12#W5#SET#002",
            type="set",
            exercise_id="SHOULDER_PRESS",
            set_number=2,
            reps=8,
            weight_kg=Decimal(15.0),
            rpe=8,
            created_at=ts,
            updated_at=ts,
        ),
    ]
    workouts.append((w5, s5))

    return workouts
