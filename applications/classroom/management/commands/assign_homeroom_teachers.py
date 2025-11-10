from django.core.management.base import BaseCommand
from applications.common.mongo import get_mongo_collection
from bson import ObjectId
import random


class Command(BaseCommand):
    help = "Assign homeroom teachers to some classrooms"

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=5, help='Number of classrooms to assign teachers to')
        parser.add_argument('--dry-run', action='store_true', help='Do not write, only print')

    def handle(self, *args, **options):
        count = options['count']
        dry_run = options['dry_run']

        classrooms_coll = get_mongo_collection('classrooms')
        teachers_coll = get_mongo_collection('teachers')

        # Get classrooms without homeroom teachers
        classrooms_without_teachers = list(classrooms_coll.find({'homeroom_teacher_id': None}))
        
        # Get available teachers
        teachers = list(teachers_coll.find({}))
        
        if not teachers:
            self.stdout.write(self.style.WARNING("No teachers found. Please create teachers first."))
            return
            
        if not classrooms_without_teachers:
            self.stdout.write(self.style.WARNING("No classrooms without homeroom teachers found."))
            return

        assigned = 0
        for i in range(min(count, len(classrooms_without_teachers))):
            classroom = classrooms_without_teachers[i]
            teacher = random.choice(teachers)
            
            teacher_id = str(teacher['_id'])
            classroom_id = str(classroom['_id'])
            
            if dry_run:
                self.stdout.write(self.style.WARNING(f"[dry-run] Would assign teacher {teacher.get('full_name', 'Unknown')} ({teacher_id}) to classroom {classroom.get('full_name', 'Unknown')} ({classroom_id})"))
            else:
                classrooms_coll.update_one(
                    {'_id': ObjectId(classroom_id)},
                    {'$set': {'homeroom_teacher_id': teacher_id}}
                )
                assigned += 1
                self.stdout.write(self.style.SUCCESS(f"Assigned teacher {teacher.get('full_name', 'Unknown')} to classroom {classroom.get('full_name', 'Unknown')}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Assigned {assigned} teachers to classrooms."))

