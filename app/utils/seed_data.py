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
        # Bodyweight
        "BW_SQUAT": str(uuid.uuid5(base, f"{dataset}-BW_SQUAT")),
        "BW_KNEE_PUSHUP": str(uuid.uuid5(base, f"{dataset}-BW_KNEE_PUSHUP")),
        # Barbell
        "BB_SQUAT": str(uuid.uuid5(base, f"{dataset}-BB_SQUAT")),
        "BB_DEADLIFT": str(uuid.uuid5(base, f"{dataset}-BB_DEADLIFT")),
        # Kettlebell
        "KB_SQUAT": str(uuid.uuid5(base, f"{dataset}-KB_SQUAT")),
        "KB_LUNGE": str(uuid.uuid5(base, f"{dataset}-KB_LUNGE")),
        "KB_SINGLE_LEG_DEADLIFT": str(
            uuid.uuid5(base, f"{dataset}-KB_SINGLE_LEG_DEADLIFT")
        ),
        # Dumbbell
        "DB_OVERHEAD_PRESS": str(uuid.uuid5(base, f"{dataset}-DB_OVERHEAD_PRESS")),
        "DB_BENCH_PRESS": str(uuid.uuid5(base, f"{dataset}-DB_BENCH_PRESS")),
        "DB_BICEP_CURL": str(uuid.uuid5(base, f"{dataset}-DB_BICEP_CURL")),
        "DB_BENT_OVER_ROW": str(uuid.uuid5(base, f"{dataset}-DB_BENT_OVER_ROW")),
        # Machine
        "MACHINE_LAT_PULLDOWN": str(
            uuid.uuid5(base, f"{dataset}-MACHINE_LAT_PULLDOWN")
        ),
        "MACHINE_TRICEP_EXTENSION": str(
            uuid.uuid5(base, f"{dataset}-MACHINE_TRICEP_EXTENSION")
        ),
    }


def build_exercises(pk: str, dataset: str) -> List[Exercise]:
    """
    Build all exercises used by the seed workouts.
    """
    ts = now()
    exercise_ids = build_exercise_ids(dataset)

    return [
        # ──────────────── Bodyweight ────────────────
        Exercise(
            PK=pk,
            SK=f"EXERCISE#{exercise_ids['BW_SQUAT']}",
            type="exercise",
            name="Squat",
            muscles=["quads", "glutes", "hamstrings"],
            equipment="bodyweight",
            category="legs",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK=f"EXERCISE#{exercise_ids['BW_KNEE_PUSHUP']}",
            type="exercise",
            name="Knee Push-up",
            muscles=["chest", "triceps", "shoulders"],
            equipment="bodyweight",
            category="push",
            created_at=ts,
            updated_at=ts,
        ),
        # ──────────────── Barbell ────────────────
        Exercise(
            PK=pk,
            SK=f"EXERCISE#{exercise_ids['BB_SQUAT']}",
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
            SK=f"EXERCISE#{exercise_ids['BB_DEADLIFT']}",
            type="exercise",
            name="Deadlift",
            muscles=["glutes", "hamstrings", "lower_back"],
            equipment="barbell",
            category="legs",
            created_at=ts,
            updated_at=ts,
        ),
        # ──────────────── Kettlebell ────────────────
        Exercise(
            PK=pk,
            SK=f"EXERCISE#{exercise_ids['KB_SQUAT']}",
            type="exercise",
            name="Goblet Squat",
            muscles=["quads", "glutes", "hamstrings", "core"],
            equipment="kettlebell",
            category="legs",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK=f"EXERCISE#{exercise_ids['KB_LUNGE']}",
            type="exercise",
            name="Lunge",
            muscles=["quads", "glutes", "hamstrings"],
            equipment="kettlebell",
            category="legs",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK=f"EXERCISE#{exercise_ids['KB_SINGLE_LEG_DEADLIFT']}",
            type="exercise",
            name="Single-Leg Deadlift",
            muscles=["glutes", "hamstrings", "core"],
            equipment="kettlebell",
            category="legs",
            created_at=ts,
            updated_at=ts,
        ),
        # ──────────────── Dumbbell ────────────────
        Exercise(
            PK=pk,
            SK=f"EXERCISE#{exercise_ids['DB_OVERHEAD_PRESS']}",
            type="exercise",
            name="Overhead Press",
            muscles=["shoulders", "triceps"],
            equipment="dumbbell",
            category="push",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK=f"EXERCISE#{exercise_ids['DB_BENCH_PRESS']}",
            type="exercise",
            name="Bench Press",
            muscles=["chest", "triceps", "shoulders"],
            equipment="dumbbell",
            category="push",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK=f"EXERCISE#{exercise_ids['DB_BICEP_CURL']}",
            type="exercise",
            name="Bicep Curl",
            muscles=["biceps"],
            equipment="dumbbell",
            category="pull",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK=f"EXERCISE#{exercise_ids['DB_BENT_OVER_ROW']}",
            type="exercise",
            name="Bent Over Row",
            muscles=["lats", "upper_back", "biceps"],
            equipment="dumbbell",
            category="pull",
            created_at=ts,
            updated_at=ts,
        ),
        # ──────────────── Machine ────────────────
        Exercise(
            PK=pk,
            SK=f"EXERCISE#{exercise_ids['MACHINE_LAT_PULLDOWN']}",
            type="exercise",
            name="Lat Pulldown",
            muscles=["lats", "upper_back", "biceps"],
            equipment="machine",
            category="pull",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK=f"EXERCISE#{exercise_ids['MACHINE_TRICEP_EXTENSION']}",
            type="exercise",
            name="Tricep Extension",
            muscles=["triceps"],
            equipment="machine",
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

    # Workout 1: Push/Pull
    w1 = Workout(
        PK=pk,
        SK="WORKOUT#2025-11-04#W1",
        type="workout",
        date=date(2025, 11, 4),
        name="Upper Body",
        tags=["push", "pull"],
        notes="Pressy/pully.",
        created_at=ts,
        updated_at=ts,
    )
    s1 = [
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-04#W1#SET#001",
            type="set",
            exercise_id=exercise_ids["DB_BENCH_PRESS"],
            set_number=1,
            reps=8,
            weight_kg=Decimal(12.0),
            rpe=7,
            created_at=ts,
            updated_at=ts,
        ),
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-04#W1#SET#002",
            type="set",
            exercise_id=exercise_ids["MACHINE_LAT_PULLDOWN"],
            set_number=2,
            reps=10,
            weight_kg=Decimal(30.0),
            rpe=8,
            created_at=ts,
            updated_at=ts,
        ),
    ]
    workouts.append((w1, s1))

    # Workout 2: Legs
    w2 = Workout(
        PK=pk,
        SK="WORKOUT#2025-11-06#W2",
        type="workout",
        date=date(2025, 11, 6),
        name="Legs",
        tags=["legs"],
        notes="Lower body day.",
        created_at=ts,
        updated_at=ts,
    )
    s2 = [
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-06#W2#SET#001",
            type="set",
            exercise_id=exercise_ids["BB_SQUAT"],
            set_number=1,
            reps=6,
            weight_kg=Decimal(40.0),
            rpe=7,
            created_at=ts,
            updated_at=ts,
        ),
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-06#W2#SET#002",
            type="set",
            exercise_id=exercise_ids["BB_DEADLIFT"],
            set_number=2,
            reps=5,
            weight_kg=Decimal(60.0),
            rpe=8,
            created_at=ts,
            updated_at=ts,
        ),
    ]
    workouts.append((w2, s2))

    # Workout 3: Accessories
    w3 = Workout(
        PK=pk,
        SK="WORKOUT#2025-11-08#W3",
        type="workout",
        date=date(2025, 11, 8),
        name="Accessories",
        tags=["push", "pull", "legs"],
        notes="Bits and bobs.",
        created_at=ts,
        updated_at=ts,
    )
    s3 = [
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-08#W3#SET#001",
            type="set",
            exercise_id=exercise_ids["KB_LUNGE"],
            set_number=1,
            reps=10,
            weight_kg=Decimal(12.0),
            rpe=7,
            created_at=ts,
            updated_at=ts,
        ),
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-08#W3#SET#002",
            type="set",
            exercise_id=exercise_ids["DB_BICEP_CURL"],
            set_number=2,
            reps=12,
            weight_kg=Decimal(8.0),
            rpe=8,
            created_at=ts,
            updated_at=ts,
        ),
    ]
    workouts.append((w3, s3))

    return workouts
