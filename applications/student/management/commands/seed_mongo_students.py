from django.core.management.base import BaseCommand
from django.utils import timezone
from applications.common.mongo import get_mongo_collection
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = "Seed Mongo students: add N students per classroom (default 30)"

    def add_arguments(self, parser):
        parser.add_argument('--per-class', type=int, default=30, help='Number of students per classroom')
        parser.add_argument('--dry-run', action='store_true', help='Do not write, only print')
        parser.add_argument('--class-filter', type=str, default='', help='Only seed classes whose full_name contains this substring')

    def handle(self, *args, **options):
        per_class = options['per_class']
        dry_run = options['dry_run']
        class_filter = (options.get('class_filter') or '').strip().lower()

        class_coll = get_mongo_collection('classrooms')
        stud_coll = get_mongo_collection('students')

        now_iso = timezone.now().isoformat()
        created = 0
        skipped = 0

        classrooms = list(class_coll.find({}))
        for c in classrooms:
            c_id = str(c.get('id') or c.get('_id'))
            c_full_name = c.get('full_name') or c.get('name') or ''
            if class_filter and class_filter not in str(c_full_name).lower():
                continue

            # Determine starting index to avoid duplicates by student_code
            existing = list(stud_coll.find({'classroom.id': c_id}))
            existing_codes = {s.get('student_code') for s in existing}

            seq = 1
            while len([code for code in existing_codes if code]) >= per_class and seq <= per_class:
                seq += 1

            i = 1
            while i <= per_class:
                code = f"{c_full_name or 'CLS'}-{i:03d}"
                if code in existing_codes:
                    i += 1
                    continue

                # Simple generated data
                first_name = f"HS {c_full_name}".strip()
                last_name = f"{i:03d}"
                full_name = f"{first_name} {last_name}".strip()
                email = f"hs.{c_full_name.replace(' ', '').lower()}.{i:03d}@example.com"
                gender = 'male' if i % 2 == 1 else 'female'
                dob = (datetime(2010, 1, 1) + timedelta(days=i * 30)).date().isoformat()

                doc = {
                    'user': {
                        'id': '',  # optional link to auth user not used here
                        'username': '',
                        'first_name': first_name,
                        'last_name': last_name,
                        'full_name': full_name,
                        'email': email,
                        'role': 'student',
                        'phone': '',
                        'created_at': now_iso,
                        'updated_at': now_iso,
                    },
                    'student_code': code,
                    'classroom': {
                        'id': c_id,
                        'full_name': c_full_name,
                    },
                    'date_of_birth': dob,
                    'gender': gender,
                    'address': '',
                    'parent_phone': '',
                    'created_at': now_iso,
                    'updated_at': now_iso,
                }

                if dry_run:
                    self.stdout.write(self.style.WARNING(f"[dry-run] would insert student: {full_name} ({code}) in {c_full_name}"))
                else:
                    stud_coll.insert_one(doc)
                    created += 1

                i += 1

        self.stdout.write(self.style.SUCCESS(f"Done. created={created}, skipped={skipped}"))



