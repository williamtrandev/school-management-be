"""
Script để đồng bộ homeroom_teacher_id trong classrooms từ homeroom_class_id trong teachers.
Chạy script này để fix dữ liệu hiện có.
"""
from django.core.management.base import BaseCommand
from bson import ObjectId
from applications.common.mongo import get_mongo_collection


class Command(BaseCommand):
    help = "Đồng bộ homeroom_teacher_id trong classrooms từ homeroom_class_id trong teachers"

    def handle(self, *args, **options):
        users_coll = get_mongo_collection("users")
        classrooms_coll = get_mongo_collection("classrooms")

        # Lấy tất cả teachers có homeroom_class_id
        teachers = list(users_coll.find({
            'role': 'teacher',
            'homeroom_class_id': {'$exists': True, '$ne': None}
        }))

        self.stdout.write(self.style.SUCCESS(f"Found {len(teachers)} teachers with homeroom_class_id"))

        # Nhóm teachers theo classroom_id để phát hiện lớp có nhiều GVCN
        classroom_to_teachers = {}
        for teacher in teachers:
            classroom_id = teacher.get('homeroom_class_id')
            if classroom_id:
                if classroom_id not in classroom_to_teachers:
                    classroom_to_teachers[classroom_id] = []
                classroom_to_teachers[classroom_id].append(teacher)

        # Xử lý các lớp có nhiều giáo viên: chỉ giữ lại 1 giáo viên, xóa các giáo viên khác
        removed_count = 0
        for classroom_id, teacher_list in classroom_to_teachers.items():
            if len(teacher_list) > 1:
                # Chọn giáo viên đầu tiên (hoặc có thể chọn giáo viên mới nhất dựa trên created_at)
                # Sắp xếp theo created_at để chọn giáo viên mới nhất
                teacher_list.sort(key=lambda t: t.get('created_at', ''), reverse=True)
                selected_teacher = teacher_list[0]
                other_teachers = teacher_list[1:]
                
                # Xóa homeroom_class_id khỏi các giáo viên khác
                for other_teacher in other_teachers:
                    other_teacher_id = str(other_teacher.get('_id'))
                    users_coll.update_one(
                        {'_id': other_teacher.get('_id')},
                        {'$unset': {'homeroom_class_id': '', 'homeroom_class': ''}}
                    )
                    removed_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠ Removed homeroom_class_id from teacher {other_teacher.get('full_name', 'Unknown')} "
                            f"({other_teacher_id}) - classroom {classroom_id} already has teacher"
                        )
                    )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Kept teacher {selected_teacher.get('full_name', 'Unknown')} "
                        f"for classroom {classroom_id} (removed {len(other_teachers)} duplicate assignments)"
                    )
                )

        # Cập nhật classrooms với homeroom_teacher_id
        updated_count = 0
        for classroom_id, teacher_list in classroom_to_teachers.items():
            # Lấy giáo viên được chọn (đã xử lý ở trên nếu có nhiều giáo viên)
            selected_teacher = teacher_list[0] if teacher_list else None
            
            if not selected_teacher:
                continue

            teacher_id = str(selected_teacher.get('_id'))
            
            try:
                # Kiểm tra xem classroom đã có homeroom_teacher_id chưa
                classroom_doc = classrooms_coll.find_one({'_id': ObjectId(classroom_id)})
                if not classroom_doc:
                    self.stdout.write(
                        self.style.WARNING(f"✗ Classroom {classroom_id} not found")
                    )
                    continue
                
                existing_teacher_id = classroom_doc.get('homeroom_teacher_id')
                if existing_teacher_id and existing_teacher_id != teacher_id:
                    # Nếu classroom đã có giáo viên khác, xóa homeroom_class_id khỏi teacher này
                    users_coll.update_one(
                        {'_id': selected_teacher.get('_id')},
                        {'$unset': {'homeroom_class_id': '', 'homeroom_class': ''}}
                    )
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠ Classroom {classroom_doc.get('full_name', 'Unknown')} ({classroom_id}) "
                            f"already has teacher {existing_teacher_id}, removed assignment from "
                            f"teacher {selected_teacher.get('full_name', 'Unknown')} ({teacher_id})"
                        )
                    )
                    continue
                
                # Cập nhật classroom với homeroom_teacher_id
                result = classrooms_coll.update_one(
                    {'_id': ObjectId(classroom_id)},
                    {'$set': {'homeroom_teacher_id': teacher_id}}
                )
                
                if result.modified_count > 0:
                    updated_count += 1
                    teacher_name = selected_teacher.get('full_name', 'Unknown')
                    classroom_name = classroom_doc.get('full_name', 'Unknown')
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Updated classroom {classroom_name} ({classroom_id}) "
                            f"with teacher {teacher_name} ({teacher_id})"
                        )
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"✗ Failed to update classroom {classroom_id} with teacher {teacher_id}: {e}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Updated {updated_count} classrooms. Removed {removed_count} duplicate assignments."
            )
        )

