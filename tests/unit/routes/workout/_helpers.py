from dataclasses import dataclass
from datetime import date as DateType


@dataclass(frozen=True)
class WorkoutPath:
    workout_date: DateType
    workout_id: str

    @property
    def base(self) -> str:
        return f"/workout/{self.workout_date.isoformat()}/{self.workout_id}"

    def set_add(self, exercise_id: str) -> str:
        return f"{self.base}/set/add?exercise_id={exercise_id}"

    def set_edit(self, set_number: int) -> str:
        return f"{self.base}/set/{set_number}"

    def set_edit_form(self, set_number: int) -> str:
        return f"{self.base}/set/{set_number}/edit"

    def set_form(self, exercise_id: str) -> str:
        return f"{self.base}/set/form?exercise_id={exercise_id}"

    @property
    def meta(self) -> str:
        return f"{self.base}/meta"

    @property
    def edit_meta(self) -> str:
        return f"{self.base}/edit-meta"


def assert_html(response) -> None:
    assert response.status_code == 200
    assert "<html" in response.text


def post_set(client, path: WorkoutPath, exercise_id: str = "EX-1", **overrides):
    data = {"reps": "8", "weight_kg": "60.5", "rpe": "9"}
    data.update(overrides)
    return client.post(path.set_add(exercise_id), data=data, follow_redirects=False)


def post_edit_set(client, path: WorkoutPath, set_number: int = 1, **overrides):
    data = {"reps": "10", "weight_kg": "70.5", "rpe": "8"}
    data.update(overrides)
    return client.post(path.set_edit(set_number), data=data, follow_redirects=False)


def post_meta(client, path: WorkoutPath, **overrides):
    data = {
        "name": "Edit Me",
        "date": path.workout_date.isoformat(),
        "tags": "",
        "notes": "",
    }
    data.update(overrides)
    return client.post(path.meta, data=data)
