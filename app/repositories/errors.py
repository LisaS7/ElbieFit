class RepoError(Exception):
    """Base class for repository-level errors."""

    pass


class WorkoutRepoError(RepoError):
    """Generic workout repository error."""

    pass


class WorkoutNotFoundError(WorkoutRepoError):
    """Raised when a workout cannot be found for the given key."""

    pass
