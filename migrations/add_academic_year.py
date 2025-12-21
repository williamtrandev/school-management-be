"""
Migration script: add academic_year field to existing Mongo documents.

Collections:
  - events
  - week_summaries
  - week_milestones
  - classrooms
  - users (students)
"""

import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
  sys.path.append(BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_management.settings")

import django  # type: ignore

django.setup()

from applications.common.mongo import get_mongo_collection  # noqa: E402
from applications.common.academic_year import (  # noqa: E402
  get_academic_year_from_date,
  get_current_academic_year,
)


def migrate_events() -> int:
  coll = get_mongo_collection("events")
  docs = list(coll.find({"academic_year": {"$exists": False}}))
  migrated = 0
  for doc in docs:
    date_str = doc.get("date")
    if not date_str:
      continue
    ay = get_academic_year_from_date(date_str)
    coll.update_one({"_id": doc["_id"]}, {"$set": {"academic_year": ay}})
    migrated += 1
  print(f"[events] migrated {migrated} documents")
  return migrated


def migrate_week_summaries() -> int:
  coll = get_mongo_collection("week_summaries")
  docs = list(coll.find({"academic_year": {"$exists": False}}))
  migrated = 0
  for doc in docs:
    # ưu tiên lấy từ start_date nếu có, fallback current_year/current_week
    date_str = doc.get("start_date") or doc.get("date")
    if not date_str:
      # fallback: dùng current academic year
      ay = get_current_academic_year()
    else:
      ay = get_academic_year_from_date(date_str)
    coll.update_one({"_id": doc["_id"]}, {"$set": {"academic_year": ay}})
    migrated += 1
  print(f"[week_summaries] migrated {migrated} documents")
  return migrated


def migrate_week_milestones() -> int:
  coll = get_mongo_collection("week_milestones")
  docs = list(coll.find({"academic_year": {"$exists": False}}))
  migrated = 0
  for doc in docs:
    date_str = doc.get("start_date")
    if not date_str:
      ay = get_current_academic_year()
    else:
      ay = get_academic_year_from_date(date_str)
    coll.update_one({"_id": doc["_id"]}, {"$set": {"academic_year": ay}})
    migrated += 1
  print(f"[week_milestones] migrated {migrated} documents")
  return migrated


def migrate_classrooms() -> int:
  coll = get_mongo_collection("classrooms")
  docs = list(coll.find({"academic_year": {"$exists": False}}))
  migrated = 0
  current_ay = get_current_academic_year()
  for doc in docs:
    # classroom thường không có date rõ, dùng created_at nếu có
    created_at = doc.get("created_at")
    if created_at:
      try:
        date_str = created_at.split("T")[0]
        ay = get_academic_year_from_date(date_str)
      except Exception:
        ay = current_ay
    else:
      ay = current_ay
    coll.update_one({"_id": doc["_id"]}, {"$set": {"academic_year": ay}})
    migrated += 1
  print(f"[classrooms] migrated {migrated} documents")
  return migrated


def migrate_users_students() -> int:
  coll = get_mongo_collection("users")
  docs = list(
    coll.find(
      {
        "role": "student",
        "academic_year": {"$exists": False},
      }
    )
  )
  migrated = 0
  current_ay = get_current_academic_year()
  for doc in docs:
    created_at = doc.get("created_at")
    if created_at:
      try:
        date_str = created_at.split("T")[0]
        ay = get_academic_year_from_date(date_str)
      except Exception:
        ay = current_ay
    else:
      ay = current_ay
    coll.update_one({"_id": doc["_id"]}, {"$set": {"academic_year": ay}})
    migrated += 1
  print(f"[users(students)] migrated {migrated} documents")
  return migrated


def main():
  print("=== Academic Year Migration ===")
  start = datetime.now()
  e = migrate_events()
  ws = migrate_week_summaries()
  wm = migrate_week_milestones()
  c = migrate_classrooms()
  u = migrate_users_students()
  elapsed = datetime.now() - start
  print("--- Summary ---")
  print(f"events: {e}")
  print(f"week_summaries: {ws}")
  print(f"week_milestones: {wm}")
  print(f"classrooms: {c}")
  print(f"users(students): {u}")
  print(f"elapsed: {elapsed}")


if __name__ == "__main__":
  main()



