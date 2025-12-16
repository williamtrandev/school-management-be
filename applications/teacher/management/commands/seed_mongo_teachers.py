import random
from datetime import datetime

from django.core.management.base import BaseCommand

from applications.common.mongo import get_mongo_collection
from applications.teacher.views import _hash_password


FIRST_NAMES = [
    "Nguyễn Văn", "Trần Thị", "Lê Văn", "Phạm Thị", "Hoàng Văn",
    "Võ Thị", "Đặng Văn", "Bùi Thị", "Đỗ Văn", "Hồ Thị"
]

LAST_NAMES = [
    "An", "Bình", "Chi", "Dũng", "Hạnh",
    "Lan", "Minh", "Ngọc", "Phương", "Quang",
    "Sơn", "Trang", "Tuấn", "Vy", "Yến"
]

SUBJECTS = [
    "Toán", "Văn", "Anh", "Lý", "Hóa",
    "Sinh", "Sử", "Địa", "Tin", "GDCD"
]


class Command(BaseCommand):
    help = "Seed thêm 20 giáo viên Mongo để test (mật khẩu 123456, gán lớp chủ nhiệm bất kỳ nếu có lớp)"

    def handle(self, *args, **options):
        users_coll = get_mongo_collection("users")
        classrooms_coll = get_mongo_collection("classrooms")

        # Lấy danh sách lớp hiện có và chỉ lấy các lớp chưa có GVCN
        classrooms = list(classrooms_coll.find({}))
        # Lấy danh sách lớp chưa có homeroom_teacher_id
        available_classrooms = [
            c for c in classrooms 
            if not c.get("homeroom_teacher_id")
        ]
        available_classroom_ids = [str(c.get("_id")) for c in available_classrooms]

        self.stdout.write(self.style.SUCCESS(f"Found {len(classrooms)} total classrooms"))
        self.stdout.write(self.style.SUCCESS(f"Found {len(available_classroom_ids)} classrooms without homeroom teacher"))

        created = 0
        assigned_count = 0
        
        for i in range(20):
            full_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            subject = random.choice(SUBJECTS)
            # Tạo email đơn giản từ tên + index để tránh trùng
            email_local = f"gv{datetime.now().strftime('%H%M%S')}{i}"
            email = f"{email_local}@example.com"

            now_iso = datetime.now().isoformat()
            doc = {
                "username": email_local,
                "email": email,
                "password_hash": _hash_password("123456"),
                "role": "teacher",
                "full_name": full_name,
                "first_name": " ".join(full_name.split()[:-1]) if len(full_name.split()) > 1 else full_name,
                "last_name": full_name.split()[-1] if len(full_name.split()) > 1 else "",
                "subject": subject,
                "status": "active",
                "created_at": now_iso,
                "updated_at": now_iso,
            }

            res = users_coll.insert_one(doc)
            teacher_id = str(res.inserted_id)
            created += 1
            
            # Ngẫu nhiên gán lớp chủ nhiệm nếu có lớp chưa có GVCN
            # Chỉ gán nếu còn lớp chưa có GVCN và random < 0.7
            if available_classroom_ids and random.random() < 0.7:  # ~70% giáo viên có lớp chủ nhiệm
                # Chọn ngẫu nhiên 1 lớp từ danh sách lớp chưa có GVCN
                cls_id = random.choice(available_classroom_ids)
                # Loại bỏ lớp này khỏi danh sách để đảm bảo mỗi lớp chỉ được gán 1 lần
                available_classroom_ids.remove(cls_id)
                
                # Thử thêm tên lớp nếu có
                cls_doc = next((c for c in available_classrooms if str(c.get("_id")) == cls_id), None)
                homeroom_class_name = ""
                if cls_doc:
                    homeroom_class_name = cls_doc.get("full_name") or cls_doc.get("name", "")
                
                # Đồng bộ: Cập nhật teacher với homeroom_class_id và classroom với homeroom_teacher_id
                try:
                    from bson import ObjectId
                    # Cập nhật teacher document với homeroom_class_id
                    users_coll.update_one(
                        {'_id': res.inserted_id},
                        {'$set': {
                            'homeroom_class_id': cls_id,
                            'homeroom_class': homeroom_class_name
                        }}
                    )
                    # Cập nhật classroom với homeroom_teacher_id
                    classrooms_coll.update_one(
                        {'_id': ObjectId(cls_id)},
                        {'$set': {'homeroom_teacher_id': teacher_id}}
                    )
                    assigned_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  → Assigned teacher {full_name} ({teacher_id}) to classroom {homeroom_class_name} ({cls_id})"
                        )
                    )
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"  → Failed to update classroom {cls_id}: {e}"))
            
            self.stdout.write(self.style.NOTICE(f"Created teacher {full_name} with _id={teacher_id}"))

        self.stdout.write(self.style.SUCCESS(f"\nDone. Created {created} teachers. Assigned {assigned_count} teachers to classrooms."))


