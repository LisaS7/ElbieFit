import uuid
from datetime import date
from decimal import Decimal
from typing import List, Tuple

from app.models import Exercise, UserProfile, Workout, WorkoutSet
from app.utils.dates import now


def _build_base_profile(pk: str, display_name: str, email: str) -> UserProfile:
    ts = now()
    return UserProfile(
        PK=pk,
        SK="PROFILE",
        display_name=display_name,
        email=email,
        created_at=ts,
        updated_at=ts,
        timezone="Europe/London",
    )


def build_profile(
    pk: str, display_name: str = "Lisa Test", email: str = "lisa@example.com"
) -> UserProfile:
    """
    Build the test user profile.
    """
    return _build_base_profile(pk=pk, display_name=display_name, email=email)


def build_demo_profile(pk: str) -> UserProfile:
    return _build_base_profile(
        pk=pk, display_name="Demo User", email="demo@elbiefit.co.uk"
    )


def build_exercise_ids(dataset: str) -> dict[str, str]:
    """
    Deterministic exercise IDs per dataset (demo/test).
    """
    base = uuid.UUID("00000000-0000-0000-0000-000000000000")
    return {
        "PUSHUP": str(uuid.uuid5(base, f"{dataset}-PUSHUP")),
        "ROW": str(uuid.uuid5(base, f"{dataset}-ROW")),
        "SQUAT": str(uuid.uuid5(base, f"{dataset}-SQUAT")),
        "DEADLIFT": str(uuid.uuid5(base, f"{dataset}-DEADLIFT")),
        "PLANK": str(uuid.uuid5(base, f"{dataset}-PLANK")),
        "BURPEE": str(uuid.uuid5(base, f"{dataset}-BURPEE")),
        "KETTLEBELL_SWING": str(uuid.uuid5(base, f"{dataset}-KETTLEBELL_SWING")),
        "LUNGE": str(uuid.uuid5(base, f"{dataset}-LUNGE")),
        "BENCH_PRESS": str(uuid.uuid5(base, f"{dataset}-BENCH_PRESS")),
        "SHOULDER_PRESS": str(uuid.uuid5(base, f"{dataset}-SHOULDER_PRESS")),
    }


def build_exercises(pk: str, dataset: str) -> List[Exercise]:
    """
    Build all exercises used by the seed workouts.
    """
    ts = now()
    exercise_ids = build_exercise_ids(dataset)

    return [
        Exercise(
            PK=pk,
            SK=f"EXERCISE#{exercise_ids['PUSHUP']}",
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
            SK=f"EXERCISE#{exercise_ids['ROW']}",
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
            SK=f"EXERCISE#{exercise_ids['SQUAT']}",
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
            SK=f"EXERCISE#{exercise_ids['DEADLIFT']}",
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
            SK=f"EXERCISE#{exercise_ids['PLANK']}",
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
            SK=f"EXERCISE#{exercise_ids['BURPEE']}",
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
            SK=f"EXERCISE#{exercise_ids['KETTLEBELL_SWING']}",
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
            SK=f"EXERCISE#{exercise_ids['LUNGE']}",
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
            SK=f"EXERCISE#{exercise_ids['BENCH_PRESS']}",
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
            SK=f"EXERCISE#{exercise_ids['SHOULDER_PRESS']}",
            type="exercise",
            name="Shoulder Press",
            muscles=["shoulders", "triceps"],
            equipment="dumbbells",
            category="push",
            created_at=ts,
            updated_at=ts,
        ),
    ]


def build_workouts(pk: str, dataset: str) -> List[Tuple[Workout, List[WorkoutSet]]]:
    """
    Build all workouts and their sets.
    Returns a list of (Workout, [WorkoutSet, ...]) tuples.
    """
    ts = now()
    exercise_ids = build_exercise_ids(dataset)
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
            exercise_id=exercise_ids["PUSHUP"],
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
            exercise_id=exercise_ids["ROW"],
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
            exercise_id=exercise_ids["SQUAT"],
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
            exercise_id=exercise_ids["DEADLIFT"],
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
            exercise_id=exercise_ids["PLANK"],
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
            exercise_id=exercise_ids["BURPEE"],
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
            exercise_id=exercise_ids["KETTLEBELL_SWING"],
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
            exercise_id=exercise_ids["LUNGE"],
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
            exercise_id=exercise_ids["BENCH_PRESS"],
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
            exercise_id=exercise_ids["SHOULDER_PRESS"],
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
