from django.core.management.base import BaseCommand
from django.utils import timezone
from applications.common.mongo import get_mongo_collection
import re


def build_class_name(grade_name: str, index: int) -> str:
    # Normalize like 10A1, 10A2... or 6A1 if grade_name is a number
    # Try to extract grade number
    m = re.match(r"^(\d+)", str(grade_name).strip())
    prefix = m.group(1) if m else str(grade_name).strip()
    return f"{prefix}A{index}"


class Command(BaseCommand):
    help = "Seed Mongo classrooms: create 6 classes per grade into classrooms collection"

    def add_arguments(self, parser):
        parser.add_argument('--per-grade', type=int, default=6, help='Number of classes per grade')
        parser.add_argument('--dry-run', action='store_true', help='Do not write, only print')

    def handle(self, *args, **options):
        per_grade = options['per_grade']
        dry_run = options['dry_run']

        coll = get_mongo_collection('classrooms')
        now_iso = timezone.now().isoformat()

        created = 0
        skipped = 0

        # Hardcode grades 10, 11, 12 (no dependency on relational Grade)
        for grade_num in [10, 11, 12]:
            grade_val = str(grade_num)

            for i in range(1, per_grade + 1):
                full_name = build_class_name(grade_val, i)

                # Skip if exists by full_name + grade.name
                exists = coll.find_one({'full_name': full_name, 'grade': grade_val})
                if exists:
                    skipped += 1
                    continue

                doc = {
                    'name': full_name,
                    'full_name': full_name,
                    'grade': grade_val,  # store grade as simple string
                    'homeroom_teacher_id': None,
                    'student_count': 0,
                    'created_at': now_iso,
                    'updated_at': now_iso,
                }

                if dry_run:
                    self.stdout.write(self.style.WARNING(f"[dry-run] would insert: {doc}"))
                else:
                    coll.insert_one(doc)
                    created += 1

        self.stdout.write(self.style.SUCCESS(f"Done. created={created}, skipped={skipped}"))


