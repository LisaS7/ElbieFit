from datetime import date, datetime

from app.utils import db

USER_SUB = "abc-123"
USER_PK = db.build_user_pk(USER_SUB)
USER_EMAIL = "lisa@example.com"

TEST_DATE_1 = date(2025, 11, 1)
TEST_DATE_2 = date(2025, 11, 3)
TEST_DATE_3 = date(2025, 11, 16)

TEST_CREATED_DATETIME = datetime(2025, 1, 1, 12, 0, 0)
TEST_UPDATED_DATETIME = datetime(2025, 1, 2, 12, 0, 0)

TEST_WORKOUT_ID_1 = "1"
TEST_WORKOUT_ID_2 = "2"

TEST_WORKOUT_SK_1 = db.build_workout_sk(TEST_DATE_1, TEST_WORKOUT_ID_1)
TEST_WORKOUT_SK_2 = db.build_workout_sk(TEST_DATE_2, TEST_WORKOUT_ID_2)

TEST_SET_SK_1 = db.build_set_sk(TEST_DATE_1, TEST_WORKOUT_ID_1, 1)
TEST_SET_SK_2 = db.build_set_sk(TEST_DATE_2, TEST_WORKOUT_ID_2, 1)
