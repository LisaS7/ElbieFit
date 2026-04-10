import uuid
from datetime import date as DateType
from typing import List

from boto3.dynamodb.conditions import Key

from app.models.template import (
    Template,
    TemplateCreate,
    TemplateSet,
    TemplateSetCreate,
    TemplateSetUpdate,
    TemplateUpdate,
)
from app.models.workout import WorkoutCreate, WorkoutSetCreate
from app.repositories.base import DynamoRepository
from app.repositories.errors import RepoError, TemplateNotFoundError, TemplateRepoError
from app.utils import dates, db
from app.utils.log import logger


class DynamoTemplateRepository(DynamoRepository[Template]):
    """
    DynamoDB implementation for workout template data access.
    """

    def _to_model(self, item: dict):
        item_type = item.get("type")

        try:
            if item_type == "template":
                return Template(**item)
            elif item_type == "template_set":
                return TemplateSet(**item)
        except Exception as e:
            logger.error(f"_to_model failed: {e}")
            raise TemplateRepoError("Failed to create template model from item") from e

        raise TemplateRepoError(f"Unknown item type: {item_type}")

    # ----------------------- Get -----------------------------

    def get_all_templates(self, user_sub: str) -> List[Template]:
        """
        Return all template items for the user, sorted by name.
        """
        pk = db.build_user_pk(user_sub)

        try:
            items = self._safe_query(
                KeyConditionExpression=Key("PK").eq(pk)
                & Key("SK").begins_with("TEMPLATE#")
            )
        except RepoError as e:
            logger.error(f"Repo error fetching templates: {e}")
            raise TemplateRepoError("Failed to fetch templates from database") from e

        try:
            models = [self._to_model(item) for item in items]
            templates = [m for m in models if isinstance(m, Template)]
            templates.sort(key=lambda t: t.name.lower())
            return templates
        except TemplateRepoError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing templates: {e}")
            raise TemplateRepoError(
                "Failed to parse templates from database response"
            ) from e

    def get_template(self, user_sub: str, template_id: str) -> Template:
        """
        Fetch a single template item by id.
        """
        pk = db.build_user_pk(user_sub)
        sk = db.build_template_sk(template_id)

        try:
            raw_item = self._safe_get(Key={"PK": pk, "SK": sk})
        except RepoError as e:
            logger.error(f"Failed to load template {template_id}: {e}")
            raise TemplateRepoError("Failed to load template from database") from e

        if not raw_item:
            logger.warning(f"Template not found: {template_id}")
            raise TemplateNotFoundError(
                f"Template {template_id} not found for user {user_sub}"
            )

        try:
            return Template(**raw_item)
        except Exception as e:
            logger.error(f"Failed to parse template {template_id}: {e}")
            raise TemplateRepoError("Failed to parse template from database") from e

    def get_template_with_sets(
        self, user_sub: str, template_id: str
    ) -> tuple[Template, List[TemplateSet]]:
        """
        Fetch a template and all its sets in a single query using begins_with.
        """
        pk = db.build_user_pk(user_sub)
        # begins_with "TEMPLATE#<id>" matches both the template item
        # (SK = "TEMPLATE#<id>") and set items (SK = "TEMPLATE#<id>#SET#...")
        sk_prefix = db.build_template_sk(template_id)

        try:
            items = self._safe_query(
                KeyConditionExpression=Key("PK").eq(pk)
                & Key("SK").begins_with(sk_prefix)
            )
        except RepoError as e:
            logger.error(f"Repo error querying template+sets for {template_id}: {e}")
            raise TemplateRepoError(
                "Failed to query template and sets from database"
            ) from e

        try:
            models = [self._to_model(item) for item in items]
        except TemplateRepoError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing template and sets: {e}")
            raise TemplateRepoError(
                "Failed to parse template and sets from response"
            ) from e

        template_items = [m for m in models if isinstance(m, Template)]
        sets = [m for m in models if isinstance(m, TemplateSet)]

        if not template_items:
            logger.warning(f"Template not found: {template_id}")
            raise TemplateNotFoundError(
                f"Template {template_id} not found for user {user_sub}"
            )

        return template_items[0], sets

    def get_next_set_number(self, user_sub: str, template_id: str) -> int:
        """
        Determine the next set number for a template by counting existing sets.
        """
        pk = db.build_user_pk(user_sub)
        sk_prefix = db.build_template_set_prefix(template_id)

        try:
            items = self._safe_query(
                KeyConditionExpression=Key("PK").eq(pk)
                & Key("SK").begins_with(sk_prefix)
            )
            if not items:
                return 1

            set_numbers = []
            for item in items:
                parts = item["SK"].split("#")
                if len(parts) >= 4:
                    try:
                        set_number = int(parts[-1])
                        set_numbers.append(set_number)
                    except ValueError:
                        logger.warning(f"Invalid set number in SK: {item['SK']}")

            if not set_numbers:
                logger.warning("No valid set numbers found, defaulting to 1")
                return 1

            return max(set_numbers) + 1
        except RepoError as e:
            logger.error(f"Error determining next template set number: {e}")
            raise TemplateRepoError("Failed to determine next set number") from e

    def get_set(
        self, user_sub: str, template_id: str, set_number: int
    ) -> TemplateSet:
        """
        Fetch a single template set by set_number.
        """
        pk = db.build_user_pk(user_sub)
        sk = db.build_template_set_sk(template_id, set_number)

        try:
            raw_item = self._safe_get(Key={"PK": pk, "SK": sk})
        except RepoError as e:
            logger.error(
                f"Failed to load template set {set_number} for template {template_id}"
            )
            raise TemplateRepoError("Failed to load template set from database") from e

        if not raw_item:
            logger.warning(
                f"Template set {set_number} not found for template {template_id}"
            )
            raise TemplateNotFoundError(f"Template set {set_number} not found")

        try:
            return TemplateSet(**raw_item)
        except Exception as e:
            logger.error(
                f"Failed to parse template set {set_number} for template {template_id}: {e}"
            )
            raise TemplateRepoError("Failed to parse template set from database") from e

    # ----------------------- Create -----------------------------

    def create_template(self, user_sub: str, data: TemplateCreate) -> Template:
        """
        Persist a new template item to DynamoDB.
        """
        new_id = str(uuid.uuid4())
        now = dates.now()

        template = Template(
            PK=db.build_user_pk(user_sub),
            SK=db.build_template_sk(new_id),
            type="template",
            name=data.name,
            created_at=now,
            updated_at=now,
        )

        try:
            self._safe_put(template.to_ddb_item())
        except RepoError as e:
            logger.error(f"Failed to put template: {e}")
            raise TemplateRepoError("Failed to create template in database") from e

        return template

    def add_set(
        self,
        user_sub: str,
        template_id: str,
        set_number: int,
        exercise_id: str,
        data: TemplateSetCreate,
    ) -> TemplateSet:
        """
        Add a new set to the existing template.
        """
        now = dates.now()

        new_set = TemplateSet(
            PK=db.build_user_pk(user_sub),
            SK=db.build_template_set_sk(template_id, set_number),
            type="template_set",
            set_number=set_number,
            exercise_id=exercise_id,
            reps=data.reps,
            weight_kg=data.weight_kg,
            rpe=data.rpe,
            created_at=now,
            updated_at=now,
        )

        try:
            self._safe_put(new_set.to_ddb_item())
        except RepoError as e:
            logger.error(f"Failed to add template set: {e}")
            raise TemplateRepoError("Failed to add template set to database") from e

        return new_set

    # ----------------------- Update -----------------------------

    def update_template(
        self, user_sub: str, template_id: str, data: TemplateUpdate
    ) -> Template:
        """
        Fetch, update, and re-persist a template item.
        """
        template = self.get_template(user_sub, template_id)

        updated = template.model_copy(
            update={
                "name": data.name,
                "tags": data.tags,
                "notes": data.notes or None,
                "updated_at": dates.now(),
            }
        )

        try:
            self._safe_put(updated.to_ddb_item())
        except RepoError as e:
            logger.error(f"Failed to update template {template_id}: {e}")
            raise TemplateRepoError("Failed to update template in database") from e

        return updated

    def update_set(
        self,
        user_sub: str,
        template_id: str,
        set_number: int,
        data: TemplateSetUpdate,
    ) -> TemplateSet:
        """
        Fetch, update, and re-persist a template set.
        """
        existing = self.get_set(user_sub, template_id, set_number)

        updated_set = existing.model_copy(
            update={
                "reps": data.reps,
                "weight_kg": data.weight_kg,
                "rpe": data.rpe,
                "updated_at": dates.now(),
            }
        )

        try:
            self._safe_put(updated_set.to_ddb_item())
        except RepoError as e:
            logger.error(
                f"Failed to update template set {set_number} for template {template_id}: {e}"
            )
            raise TemplateRepoError("Failed to update template set") from e

        return updated_set

    # ----------------------- Delete -----------------------------

    def delete_template(self, user_sub: str, template_id: str) -> None:
        """
        Delete a template and all its sets in a single batch operation.
        """
        pk = db.build_user_pk(user_sub)
        sk_prefix = db.build_template_sk(template_id)

        try:
            items = self._safe_query(
                KeyConditionExpression=Key("PK").eq(pk)
                & Key("SK").begins_with(sk_prefix)
            )
        except RepoError as e:
            logger.error(f"Failed loading template items for deletion: {e}")
            raise TemplateRepoError(
                "Failed to load template and sets for deletion"
            ) from e

        if not items:
            return

        try:
            with self._table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
        except Exception as e:
            logger.error(f"Batch delete of template failed: {e}")
            raise TemplateRepoError(
                "Failed to delete template and sets from database"
            ) from e

    def delete_set(
        self, user_sub: str, template_id: str, set_number: int
    ) -> None:
        """
        Delete a specific template set.
        """
        pk = db.build_user_pk(user_sub)
        sk = db.build_template_set_sk(template_id, set_number)

        try:
            self._safe_delete(Key={"PK": pk, "SK": sk})
        except RepoError as e:
            logger.error(f"Failed to delete template set: {e}")
            raise TemplateRepoError(
                "Failed to delete template set from database"
            ) from e

    # ----------------------- Copy to workout -----------------------------

    def copy_to_workout(
        self,
        user_sub: str,
        template_id: str,
        target_date: DateType,
        workout_repo,
        exercise_repo,
    ):
        """
        Create a new Workout from a template on target_date.

        - Verifies exercise ownership for every set before writing.
        - Uses the template's name as the workout name.
        - TemplateSet.reps defaults to 1 if None.
        - Returns the newly created Workout.
        """
        template, sets = self.get_template_with_sets(user_sub, template_id)

        workout_data = WorkoutCreate(date=target_date, name=template.name)
        workout = workout_repo.create_workout(user_sub, workout_data)

        sets_sorted = sorted(sets, key=lambda s: s.set_number)

        for template_set in sets_sorted:
            exercise = exercise_repo.get_exercise_by_id(
                user_sub, template_set.exercise_id
            )
            if not exercise:
                logger.warning(
                    f"Exercise {template_set.exercise_id} not found or not owned by "
                    f"user {user_sub} — skipping set {template_set.set_number}"
                )
                continue

            set_data = WorkoutSetCreate(
                reps=template_set.reps if template_set.reps is not None else 1,
                weight_kg=template_set.weight_kg,
                rpe=template_set.rpe,
            )

            workout_repo.add_set(
                user_sub,
                workout.date,
                workout.workout_id,
                template_set.exercise_id,
                set_data,
            )

        return workout
