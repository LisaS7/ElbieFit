from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response

from app.models.template import (
    TemplateCreate,
    TemplateSetCreate,
    TemplateSetUpdate,
    TemplateUpdate,
)
from app.repositories.errors import (
    ExerciseRepoError,
    TemplateNotFoundError,
    TemplateRepoError,
)
from app.repositories.exercise import DynamoExerciseRepository
from app.repositories.profile import DynamoProfileRepository
from app.repositories.template import DynamoTemplateRepository
from app.repositories.workout import DynamoWorkoutRepository
from app.templates.templates import render_template
from app.utils import auth, dates
from app.utils.log import logger
from app.utils.units import kg_to_lb, lb_to_kg

router = APIRouter(prefix="/template", tags=["templates"])


def get_template_repo() -> DynamoTemplateRepository:  # pragma: no cover
    """Fetch the template repo"""
    return DynamoTemplateRepository()


def get_workout_repo() -> DynamoWorkoutRepository:  # pragma: no cover
    """Fetch the workout repo"""
    return DynamoWorkoutRepository()


def get_exercise_repo() -> DynamoExerciseRepository:  # pragma: no cover
    """Fetch the exercise repo"""
    return DynamoExerciseRepository()


def get_profile_repo() -> DynamoProfileRepository:  # pragma: no cover
    """Fetch the profile repo"""
    return DynamoProfileRepository()


def get_weight_unit_for_user(
    user_sub: str,
    profile_repo: DynamoProfileRepository,
) -> Literal["kg", "lb"]:
    try:
        profile = profile_repo.get_for_user(user_sub)
    except Exception:
        logger.exception(f"Error fetching profile for user_sub={user_sub}")
        raise HTTPException(status_code=500, detail="Error fetching user profile")
    return profile.weight_unit if profile else "kg"


# ---------------------- List all ---------------------------


@router.get("/all")
def get_all_templates(
    request: Request,
    claims=Depends(auth.require_auth),
    repo: DynamoTemplateRepository = Depends(get_template_repo),
):
    """Get all templates for the current authenticated user."""
    user_sub = claims["sub"]

    logger.info(f"Fetching templates for user {user_sub}")

    try:
        templates = repo.get_all_templates(user_sub)
    except TemplateRepoError:
        logger.exception(f"Error fetching templates for user {user_sub}")
        raise HTTPException(status_code=500, detail="Error fetching templates")

    return render_template(
        request,
        "templates/templates.html",
        context={"templates": templates},
        status_code=200,
    )


# ---------------------- Create ---------------------------


@router.get("/new-form")
def get_new_form(
    request: Request,
    claims=Depends(auth.require_auth),
):
    """Return the HTMX partial for creating a new template."""
    return render_template(
        request,
        "templates/_new_form.html",
        context={},
    )


@router.post("/create")
def create_template(
    request: Request,
    form: Annotated[TemplateCreate, Depends(TemplateCreate.as_form)],
    claims=Depends(auth.require_auth),
    repo: DynamoTemplateRepository = Depends(get_template_repo),
):
    user_sub = claims["sub"]

    try:
        template = repo.create_template(user_sub, data=form)
    except TemplateRepoError:
        logger.exception(f"Error creating template user_sub={user_sub}")
        raise HTTPException(status_code=500, detail="Error creating template")

    return Response(
        status_code=204,
        headers={"HX-Redirect": f"/template/{template.template_id}"},
    )


# ---------------------- Detail ---------------------------


@router.get("/{template_id}")
def view_template(
    request: Request,
    template_id: str,
    claims=Depends(auth.require_auth),
    template_repo: DynamoTemplateRepository = Depends(get_template_repo),
    exercise_repo: DynamoExerciseRepository = Depends(get_exercise_repo),
    profile_repo: DynamoProfileRepository = Depends(get_profile_repo),
):
    """Full detail page for a single template."""
    user_sub = claims["sub"]

    try:
        template, sets = template_repo.get_template_with_sets(user_sub, template_id)
    except TemplateNotFoundError:
        logger.warning(f"Template {template_id} not found for {user_sub}")
        raise HTTPException(status_code=404, detail="Template not found")
    except TemplateRepoError:
        logger.exception(f"Error fetching template {template_id}")
        raise HTTPException(status_code=500, detail="Error fetching template")

    sets = sorted(sets, key=lambda s: s.set_number)

    unit = get_weight_unit_for_user(user_sub, profile_repo)

    if unit == "lb":
        for s in sets:
            if s.weight_kg is not None:
                s.weight_kg = kg_to_lb(s.weight_kg)

    exercise_map = {}
    try:
        for s in sets:
            exercise_id = s.exercise_id
            if exercise_id not in exercise_map:
                exercise = exercise_repo.get_exercise_by_id(user_sub, exercise_id)
                if exercise:
                    exercise_map[exercise_id] = exercise
    except ExerciseRepoError:
        logger.exception(
            f"Error fetching exercise details for user {user_sub} and template {template_id}"
        )
        raise HTTPException(status_code=500, detail="Error fetching exercise details")

    return render_template(
        request,
        "templates/template_detail.html",
        context={
            "template": template,
            "sets": sets,
            "exercises": exercise_map,
            "weight_unit": unit,
        },
    )


# ---------------------- Add set ---------------------------


@router.get("/{template_id}/add-exercise-form")
def get_add_exercise_form(
    request: Request,
    template_id: str,
    claims=Depends(auth.require_auth),
    exercise_repo: DynamoExerciseRepository = Depends(get_exercise_repo),
    profile_repo: DynamoProfileRepository = Depends(get_profile_repo),
):
    """Return a form to pick an exercise and add the first set for it."""
    user_sub = claims["sub"]
    unit = get_weight_unit_for_user(user_sub, profile_repo)

    try:
        exercises = exercise_repo.get_all_for_user(user_sub)
    except ExerciseRepoError:
        logger.exception(f"Error fetching exercises for user {user_sub}")
        raise HTTPException(status_code=500, detail="Error fetching exercises")

    exercises = sorted(exercises, key=lambda e: e.name.lower())

    action_url = str(
        request.url_for("add_template_set", template_id=template_id)
    )

    return render_template(
        request,
        "templates/_add_exercise_form.html",
        context={
            "template_id": template_id,
            "exercises": exercises,
            "action_url": action_url,
            "weight_unit": unit,
        },
    )


@router.get("/{template_id}/set/form")
def get_new_set_form(
    request: Request,
    template_id: str,
    exercise_id: str,
    claims=Depends(auth.require_auth),
    profile_repo: DynamoProfileRepository = Depends(get_profile_repo),
):
    """Return the HTMX partial set form for adding a new set to a template."""
    user_sub = claims["sub"]
    unit = get_weight_unit_for_user(user_sub, profile_repo)

    action_url = (
        str(request.url_for("add_template_set", template_id=template_id))
        + f"?exercise_id={exercise_id}"
    )

    return render_template(
        request,
        "templates/_set_form.html",
        context={
            "template_id": template_id,
            "exercise_id": exercise_id,
            "action_url": action_url,
            "submit_label": "Add Set",
            "set": None,
            "cancel_target": f"#new-set-form-container-{exercise_id}",
            "weight_unit": unit,
        },
    )


@router.post("/{template_id}/set/add")
def add_template_set(
    template_id: str,
    form: Annotated[TemplateSetCreate, Depends(TemplateSetCreate.as_form)],
    claims=Depends(auth.require_auth),
    repo: DynamoTemplateRepository = Depends(get_template_repo),
    exercise_repo: DynamoExerciseRepository = Depends(get_exercise_repo),
    profile_repo: DynamoProfileRepository = Depends(get_profile_repo),
    exercise_id: Optional[str] = None,
    exercise_id_body: Annotated[Optional[str], Form(alias="exercise_id")] = None,
):
    """Add a new set to the template."""
    resolved_exercise_id = exercise_id or exercise_id_body
    if not resolved_exercise_id:
        raise HTTPException(status_code=422, detail="exercise_id is required")

    user_sub = claims["sub"]

    # Verify exercise ownership before writing
    try:
        exercise = exercise_repo.get_exercise_by_id(user_sub, resolved_exercise_id)
    except ExerciseRepoError:
        logger.exception(
            f"Error verifying exercise {resolved_exercise_id} for user {user_sub}"
        )
        raise HTTPException(status_code=500, detail="Error verifying exercise")

    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    unit = get_weight_unit_for_user(user_sub, profile_repo)

    if unit == "lb" and form.weight_kg is not None:
        form.weight_kg = lb_to_kg(form.weight_kg)

    try:
        set_number = repo.get_next_set_number(user_sub, template_id)
        repo.add_set(user_sub, template_id, set_number, resolved_exercise_id, form)
    except TemplateRepoError:
        logger.exception(
            f"Error adding template set user_sub={user_sub} template_id={template_id}"
        )
        raise HTTPException(status_code=500, detail="Error adding template set")

    return Response(status_code=204, headers={"HX-Trigger": "templateSetChanged"})


# ---------------------- Edit meta ---------------------------


@router.get("/{template_id}/meta")
def get_template_meta(
    request: Request,
    template_id: str,
    claims=Depends(auth.require_auth),
    repo: DynamoTemplateRepository = Depends(get_template_repo),
):
    """Return the HTMX partial for the template meta display."""
    user_sub = claims["sub"]

    try:
        template = repo.get_template(user_sub, template_id)
    except TemplateNotFoundError:
        raise HTTPException(status_code=404, detail="Template not found")
    except TemplateRepoError:
        raise HTTPException(status_code=500, detail="Error fetching template")

    return render_template(
        request,
        "templates/_template_meta.html",
        context={"template": template},
    )


@router.get("/{template_id}/edit-meta")
def edit_template_meta(
    request: Request,
    template_id: str,
    claims=Depends(auth.require_auth),
    repo: DynamoTemplateRepository = Depends(get_template_repo),
):
    """Return the HTMX partial edit meta form."""
    user_sub = claims["sub"]

    try:
        template = repo.get_template(user_sub, template_id)
    except TemplateNotFoundError:
        logger.warning(f"Template {template_id} not found for edit")
        raise HTTPException(status_code=404, detail="Template not found")
    except TemplateRepoError:
        logger.exception(f"Error fetching template {template_id} for edit")
        raise HTTPException(status_code=500, detail="Error fetching template")

    return render_template(
        request,
        "templates/_edit_meta_form.html",
        context={"template": template},
    )


@router.post("/{template_id}/meta")
def update_template_meta(
    request: Request,
    template_id: str,
    form: TemplateUpdate = Depends(TemplateUpdate.as_form),
    claims=Depends(auth.require_auth),
    repo: DynamoTemplateRepository = Depends(get_template_repo),
):
    """Update template meta and return the refreshed meta partial."""
    user_sub = claims["sub"]

    logger.info(
        f"Updating template meta user_sub={user_sub} template_id={template_id}"
    )

    try:
        template = repo.update_template(user_sub, template_id, form)
    except TemplateNotFoundError:
        logger.warning(f"Template {template_id} not found for update")
        raise HTTPException(status_code=404, detail="Template not found")
    except TemplateRepoError:
        logger.exception(f"Error updating template {template_id}")
        raise HTTPException(status_code=500, detail="Error updating template")

    return render_template(
        request,
        "templates/_template_meta.html",
        context={"template": template},
    )


# ---------------------- Edit sets ---------------------------


@router.get("/{template_id}/set/{set_number}/edit")
def get_edit_set_form(
    request: Request,
    template_id: str,
    set_number: int,
    claims=Depends(auth.require_auth),
    repo: DynamoTemplateRepository = Depends(get_template_repo),
    profile_repo: DynamoProfileRepository = Depends(get_profile_repo),
):
    """Return the HTMX partial edit-set form for a template set."""
    user_sub = claims["sub"]

    try:
        set_ = repo.get_set(user_sub, template_id, set_number)
    except TemplateNotFoundError:
        raise HTTPException(status_code=404, detail="Set not found")
    except TemplateRepoError:
        logger.exception(
            f"Error fetching template set {set_number} for edit in template {template_id}"
        )
        raise HTTPException(status_code=500, detail="Error fetching set")

    unit = get_weight_unit_for_user(user_sub, profile_repo)

    if unit == "lb" and set_.weight_kg is not None:
        set_.weight_kg = kg_to_lb(set_.weight_kg)

    action_url = request.url_for(
        "edit_template_set",
        template_id=template_id,
        set_number=set_number,
    )

    cancel_target = f"#edit-set-form-container-{set_.exercise_id}-{set_number}"

    return render_template(
        request,
        "templates/_set_form.html",
        context={
            "template_id": template_id,
            "set_number": set_number,
            "set": set_,
            "exercise_id": None,
            "action_url": action_url,
            "submit_label": "Save Set",
            "cancel_target": cancel_target,
            "weight_unit": unit,
        },
    )


@router.post("/{template_id}/set/{set_number}")
def edit_template_set(
    template_id: str,
    set_number: int,
    form: Annotated[TemplateSetUpdate, Depends(TemplateSetUpdate.as_form)],
    claims=Depends(auth.require_auth),
    repo: DynamoTemplateRepository = Depends(get_template_repo),
    profile_repo: DynamoProfileRepository = Depends(get_profile_repo),
):
    """Save edits to a template set."""
    user_sub = claims["sub"]

    unit = get_weight_unit_for_user(user_sub, profile_repo)

    if unit == "lb" and form.weight_kg is not None:
        form.weight_kg = lb_to_kg(form.weight_kg)

    try:
        repo.update_set(user_sub, template_id, set_number, form)
    except TemplateNotFoundError:
        logger.warning(
            f"Template set {set_number} not found template_id={template_id} user_sub={user_sub}"
        )
        raise HTTPException(status_code=404, detail="Set not found")
    except TemplateRepoError:
        logger.exception(
            f"Error updating template set {set_number} for template {template_id}"
        )
        raise HTTPException(status_code=500, detail="Error updating set")

    return Response(status_code=204, headers={"HX-Trigger": "templateSetChanged"})


# ---------------------- Delete ---------------------------


@router.delete("/{template_id}")
def delete_template(
    template_id: str,
    claims=Depends(auth.require_auth),
    repo: DynamoTemplateRepository = Depends(get_template_repo),
):
    """Delete a template and all its sets."""
    user_sub = claims["sub"]

    try:
        logger.info(f"Deleting template template_id={template_id} user_sub={user_sub}")
        repo.delete_template(user_sub, template_id)
    except TemplateRepoError:
        logger.exception(f"Error deleting template {template_id}")
        raise HTTPException(status_code=500, detail="Error deleting template")

    return Response(status_code=204, headers={"HX-Redirect": "/template/all"})


@router.delete("/{template_id}/set/{set_number}")
def delete_template_set(
    template_id: str,
    set_number: int,
    claims=Depends(auth.require_auth),
    repo: DynamoTemplateRepository = Depends(get_template_repo),
):
    """Delete a single template set."""
    user_sub = claims["sub"]

    try:
        logger.info(
            f"Deleting template set set_number={set_number} template_id={template_id} user_sub={user_sub}"
        )
        repo.delete_set(user_sub, template_id, set_number)
    except TemplateRepoError:
        logger.exception(
            f"Error deleting template set {set_number} from template {template_id}"
        )
        raise HTTPException(status_code=500, detail="Error deleting set")

    return Response(status_code=204, headers={"HX-Trigger": "templateSetChanged"})


# ---------------------- Copy to workout ---------------------------


@router.post("/{template_id}/copy")
def copy_template_to_workout(
    template_id: str,
    claims=Depends(auth.require_auth),
    template_repo: DynamoTemplateRepository = Depends(get_template_repo),
    workout_repo: DynamoWorkoutRepository = Depends(get_workout_repo),
    exercise_repo: DynamoExerciseRepository = Depends(get_exercise_repo),
    profile_repo: DynamoProfileRepository = Depends(get_profile_repo),
):
    """
    Copy the template to a new workout dated to today in the user's timezone.
    Returns HX-Redirect to the new workout detail page.
    """
    user_sub = claims["sub"]

    try:
        profile = profile_repo.get_for_user(user_sub)
    except Exception:
        logger.exception(f"Error fetching profile for user_sub={user_sub}")
        raise HTTPException(status_code=500, detail="Error fetching user profile")

    tz = profile.timezone if profile else None
    today = dates.today_in_tz(tz)

    try:
        workout = template_repo.copy_to_workout(
            user_sub,
            template_id,
            today,
            workout_repo,
            exercise_repo,
        )
    except TemplateNotFoundError:
        logger.warning(f"Template {template_id} not found for copy user_sub={user_sub}")
        raise HTTPException(status_code=404, detail="Template not found")
    except TemplateRepoError:
        logger.exception(
            f"Error copying template {template_id} to workout for user {user_sub}"
        )
        raise HTTPException(status_code=500, detail="Error copying template to workout")

    redirect_url = f"/workout/{workout.date.isoformat()}/{workout.workout_id}"

    logger.info(
        f"Template {template_id} copied to workout {workout.workout_id} for user {user_sub}"
    )

    return Response(status_code=204, headers={"HX-Redirect": redirect_url})
