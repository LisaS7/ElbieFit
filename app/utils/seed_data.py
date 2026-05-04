import uuid
from datetime import date, timedelta
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


def build_exercise_ids() -> dict[str, str]:
    """
    Deterministic exercise IDs
    """
    base = uuid.UUID("00000000-0000-0000-0000-000000000000")
    return {
        # Bodyweight
        "BW_SQUAT": str(uuid.uuid5(base, "BW_SQUAT")),
        "BW_KNEE_PUSHUP": str(uuid.uuid5(base, "BW_KNEE_PUSHUP")),
        # Barbell
        "BB_SQUAT": str(uuid.uuid5(base, "BB_SQUAT")),
        "BB_DEADLIFT": str(uuid.uuid5(base, "BB_DEADLIFT")),
        # Kettlebell
        "KB_SQUAT": str(uuid.uuid5(base, "KB_SQUAT")),
        "KB_LUNGE": str(uuid.uuid5(base, "KB_LUNGE")),
        "KB_SINGLE_LEG_DEADLIFT": str(uuid.uuid5(base, "KB_SINGLE_LEG_DEADLIFT")),
        # Dumbbell
        "DB_OVERHEAD_PRESS": str(uuid.uuid5(base, "DB_OVERHEAD_PRESS")),
        "DB_BENCH_PRESS": str(uuid.uuid5(base, "DB_BENCH_PRESS")),
        "DB_BICEP_CURL": str(uuid.uuid5(base, "DB_BICEP_CURL")),
        "DB_BENT_OVER_ROW": str(uuid.uuid5(base, "DB_BENT_OVER_ROW")),
        "DB_SINGLE_LEG_DEADLIFT": str(uuid.uuid5(base, "DB_SINGLE_LEG_DEADLIFT")),
        # Machine
        "MACHINE_LAT_PULLDOWN": str(uuid.uuid5(base, "MACHINE_LAT_PULLDOWN")),
        "MACHINE_TRICEP_EXTENSION": str(uuid.uuid5(base, "MACHINE_TRICEP_EXTENSION")),
    }


def build_exercises(pk: str) -> List[Exercise]:
    """
    Build all exercises used by the seed workouts.
    """
    ts = now()
    exercise_ids = build_exercise_ids()

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
            equipment="dumbbells",
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
            equipment="dumbbells",
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
            equipment="dumbbells",
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
            equipment="dumbbells",
            category="pull",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK=f"EXERCISE#{exercise_ids['DB_SINGLE_LEG_DEADLIFT']}",
            type="exercise",
            name="Single-Leg Deadlift",
            muscles=["glutes", "hamstrings", "core"],
            equipment="dumbbells",
            category="legs",
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


def build_workouts(pk: str) -> List[Tuple[Workout, List[WorkoutSet]]]:
    """
    Build all workouts and their sets.
    Returns a list of (Workout, [WorkoutSet, ...]) tuples.

    Includes 3 historical workouts (> 12 weeks ago) plus ~33 recent workouts
    spread across the last 12 weeks with progressive overload on key lifts,
    so the frequency and exercise-progress charts have meaningful data.
    """
    ts = now()
    ex = build_exercise_ids()
    today = date.today()
    workouts: List[Tuple[Workout, List[WorkoutSet]]] = []

    def mk_workout(wid, days_back, name, tags, notes=None):
        dt = today - timedelta(days=days_back)
        return Workout(
            PK=pk,
            SK=f"WORKOUT#{dt.isoformat()}#{wid}",
            type="workout",
            date=dt,
            name=name,
            tags=tags,
            notes=notes,
            created_at=ts,
            updated_at=ts,
        )

    def mk_set(w, num, exercise_key, reps, weight, rpe):
        return WorkoutSet(
            PK=pk,
            SK=f"{w.SK}#SET#{num:03d}",
            type="set",
            set_number=num,
            exercise_id=ex[exercise_key],
            reps=reps,
            weight_kg=Decimal(str(weight)),
            rpe=rpe,
            created_at=ts,
            updated_at=ts,
        )

    # ── Historical workouts (> 12 weeks ago, won't appear in frequency chart) ──

    w1 = mk_workout("W1", 148, "Upper Body", ["push", "pull"], "Pressy/pully.")
    workouts.append((w1, [
        mk_set(w1, 1, "DB_BENCH_PRESS", 8, 12.0, 7),
        mk_set(w1, 2, "MACHINE_LAT_PULLDOWN", 10, 30.0, 8),
    ]))

    w2 = mk_workout("W2", 146, "Legs", ["legs"], "Lower body day.")
    workouts.append((w2, [
        mk_set(w2, 1, "BB_SQUAT", 6, 40.0, 7),
        mk_set(w2, 2, "BB_DEADLIFT", 5, 60.0, 8),
    ]))

    w3 = mk_workout("W3", 144, "Accessories", ["push", "pull", "legs"], "Bits and bobs.")
    workouts.append((w3, [
        mk_set(w3, 1, "KB_LUNGE", 10, 12.0, 7),
        mk_set(w3, 2, "DB_BICEP_CURL", 12, 8.0, 8),
    ]))

    # ── Recent workouts (last 12 weeks, relative to today) ────────────────────
    #
    # Schedule: ~3 sessions/week, rotating Push / Pull / Legs.
    # Weight arrays indexed by session number (0-based) to show progressive
    # overload on the main lifts — the exercise-progress chart will show a
    # clear upward trend.

    # fmt: off
    SQUAT_KG   = [40,   42.5, 42.5, 45,   45,   47.5, 47.5, 50,   50,   52.5, 52.5, 55  ]
    DEAD_KG    = [60,   62.5, 65,   65,   67.5, 70,   70,   72.5, 75,   75,   77.5, 80  ]
    BENCH_KG   = [14,   14,   15,   15,   16,   16,   17,   17,   18,   18,   19,   20  ]
    OHP_KG     = [8,    8,    9,    9,    10,   10,   10,   11,   11,   12,   12,   12  ]
    LAT_KG     = [30,   32,   32,   35,   36,   38,   40,   42,   44               ]
    ROW_KG     = [12,   12,   14,   14,   16,   16,   18,   18,   20               ]
    CURL_KG    = [8,    8,    9,    9,    10,   10,   10,   11,   12               ]
    GOBLET_KG  = [16,   16,   18,   18,   20,   20,   20,   22,   22,   24,   24,   24  ]
    TRICEP_KG  = [25,   25,   28,   28,   30,   30,   32,   32,   34,   34,   36,   38  ]
    # fmt: on

    # (days_back, wid, session_type, name, notes)
    schedule = [
        # Week 12 (~83 days ago) — 3 sessions
        (83, "W04", "push", "Push Day",   "Back to it after a break."),
        (81, "W05", "pull", "Pull Day",   None),
        (79, "W06", "legs", "Leg Day",    None),
        # Week 11 (~76 days) — 2 sessions
        (76, "W07", "push", "Push Day",   None),
        (74, "W08", "legs", "Legs",       None),
        # Week 10 (~69 days) — 3 sessions
        (69, "W09", "push", "Push Day",   None),
        (67, "W10", "pull", "Pull Day",   None),
        (65, "W11", "legs", "Leg Day",    None),
        # Week 9 (~62 days) — 2 sessions
        (62, "W12", "push", "Upper Body", None),
        (60, "W13", "legs", "Legs",       None),
        # Week 8 (~55 days) — 3 sessions
        (55, "W14", "push", "Push Day",   "Felt strong today."),
        (53, "W15", "pull", "Pull Day",   None),
        (51, "W16", "legs", "Leg Day",    None),
        # Week 7 (~48 days) — 3 sessions
        (48, "W17", "push", "Push Day",   None),
        (46, "W18", "legs", "Legs",       None),
        (44, "W19", "pull", "Pull Day",   None),
        # Week 6 (~41 days) — 3 sessions
        (41, "W20", "push", "Push Day",   None),
        (39, "W21", "legs", "Leg Day",    None),
        (37, "W22", "pull", "Pull Day",   None),
        # Week 5 (~34 days) — 2 sessions (lighter week)
        (34, "W23", "push", "Push Day",   None),
        (32, "W24", "legs", "Legs",       None),
        # Week 4 (~27 days) — 3 sessions
        (27, "W25", "push", "Push Day",   None),
        (25, "W26", "pull", "Pull Day",   None),
        (23, "W27", "legs", "Leg Day",    "Increased squat weight."),
        # Week 3 (~20 days) — 3 sessions
        (20, "W28", "push", "Push Day",   None),
        (18, "W29", "legs", "Legs",       None),
        (16, "W30", "pull", "Pull Day",   None),
        # Week 2 (~13 days) — 3 sessions
        (13, "W31", "push", "Push Day",   None),
        (11, "W32", "legs", "Leg Day",    None),
        (9,  "W33", "pull", "Pull Day",   None),
        # Week 1 (last 6 days) — 3 sessions
        (6,  "W34", "push", "Push Day",   "PB on bench press!"),
        (4,  "W35", "legs", "Legs",       None),
        (1,  "W36", "pull", "Pull Day",   None),
    ]

    push_n = pull_n = legs_n = 0

    for days_back, wid, session_type, name, notes in schedule:
        if session_type == "push":
            i = push_n
            tags = ["push"]
            w = mk_workout(wid, days_back, name, tags, notes)
            sets = [
                mk_set(w, 1, "DB_BENCH_PRESS",         8,  BENCH_KG[i],  7),
                mk_set(w, 2, "DB_BENCH_PRESS",         8,  BENCH_KG[i],  7),
                mk_set(w, 3, "DB_BENCH_PRESS",         6,  BENCH_KG[i],  8),
                mk_set(w, 4, "DB_OVERHEAD_PRESS",      10, OHP_KG[i],    7),
                mk_set(w, 5, "DB_OVERHEAD_PRESS",      10, OHP_KG[i],    7),
                mk_set(w, 6, "MACHINE_TRICEP_EXTENSION", 12, TRICEP_KG[i], 7),
                mk_set(w, 7, "MACHINE_TRICEP_EXTENSION", 12, TRICEP_KG[i], 8),
            ]
            push_n += 1

        elif session_type == "pull":
            i = pull_n
            tags = ["pull"]
            w = mk_workout(wid, days_back, name, tags, notes)
            sets = [
                mk_set(w, 1, "MACHINE_LAT_PULLDOWN", 10, LAT_KG[i],  7),
                mk_set(w, 2, "MACHINE_LAT_PULLDOWN", 10, LAT_KG[i],  8),
                mk_set(w, 3, "MACHINE_LAT_PULLDOWN", 8,  LAT_KG[i],  8),
                mk_set(w, 4, "DB_BENT_OVER_ROW",     10, ROW_KG[i],  7),
                mk_set(w, 5, "DB_BENT_OVER_ROW",     10, ROW_KG[i],  7),
                mk_set(w, 6, "DB_BICEP_CURL",         12, CURL_KG[i], 7),
                mk_set(w, 7, "DB_BICEP_CURL",         12, CURL_KG[i], 8),
            ]
            pull_n += 1

        else:  # legs
            i = legs_n
            tags = ["legs"]
            w = mk_workout(wid, days_back, name, tags, notes)
            sets = [
                mk_set(w, 1, "BB_SQUAT",   5, SQUAT_KG[i],  7),
                mk_set(w, 2, "BB_SQUAT",   5, SQUAT_KG[i],  8),
                mk_set(w, 3, "BB_SQUAT",   5, SQUAT_KG[i],  8),
                mk_set(w, 4, "BB_DEADLIFT", 4, DEAD_KG[i],   7),
                mk_set(w, 5, "BB_DEADLIFT", 4, DEAD_KG[i],   8),
                mk_set(w, 6, "KB_SQUAT",   12, GOBLET_KG[i], 7),
                mk_set(w, 7, "KB_SQUAT",   12, GOBLET_KG[i], 8),
            ]
            legs_n += 1

        workouts.append((w, sets))

    return workouts
