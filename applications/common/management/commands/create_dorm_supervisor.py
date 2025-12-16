from datetime import datetime
from django.core.management.base import BaseCommand
from applications.common.mongo import get_mongo_collection
from applications.teacher.views import _hash_password


class Command(BaseCommand):
    help = "Tạo tài khoản quản sinh (dorm_supervisor) với mật khẩu 123456"

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email cho tài khoản quản sinh (mặc định: quan_sinh@example.com)',
            default='quan_sinh@example.com'
        )
        parser.add_argument(
            '--full-name',
            type=str,
            help='Họ và tên đầy đủ (mặc định: Quản Sinh)',
            default='Quản Sinh'
        )

    def handle(self, *args, **options):
        users_coll = get_mongo_collection("users")
        
        email = options['email']
        full_name = options['full_name']
        
        # Kiểm tra xem email đã tồn tại chưa
        existing_user = users_coll.find_one({'email': email})
        if existing_user:
            self.stdout.write(
                self.style.WARNING(f'Email {email} đã tồn tại. User ID: {existing_user.get("_id")}')
            )
            # Cập nhật role nếu chưa phải dorm_supervisor
            if existing_user.get('role') != 'dorm_supervisor':
                users_coll.update_one(
                    {'_id': existing_user['_id']},
                    {
                        '$set': {
                            'role': 'dorm_supervisor',
                            'password_hash': _hash_password('123456'),
                            'updated_at': datetime.now().isoformat()
                        }
                    }
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Đã cập nhật user {email} thành dorm_supervisor với password 123456')
                )
            else:
                # Cập nhật password về 123456
                users_coll.update_one(
                    {'_id': existing_user['_id']},
                    {
                        '$set': {
                            'password_hash': _hash_password('123456'),
                            'updated_at': datetime.now().isoformat()
                        }
                    }
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Đã reset password của user {email} thành 123456')
                )
            return
        
        # Tạo username từ email
        username = email.split('@')[0] if '@' in email else email
        
        # Tách first_name và last_name
        name_parts = full_name.split()
        first_name = ' '.join(name_parts[:-1]) if len(name_parts) > 1 else full_name
        last_name = name_parts[-1] if len(name_parts) > 1 else ''
        
        now_iso = datetime.now().isoformat()
        doc = {
            'username': username,
            'email': email,
            'password_hash': _hash_password('123456'),
            'role': 'dorm_supervisor',
            'full_name': full_name,
            'first_name': first_name,
            'last_name': last_name,
            'status': 'active',
            'created_at': now_iso,
            'updated_at': now_iso,
        }
        
        result = users_coll.insert_one(doc)
        user_id = str(result.inserted_id)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Đã tạo tài khoản quản sinh thành công!\n'
                f'  Email: {email}\n'
                f'  Password: 123456\n'
                f'  User ID: {user_id}\n'
                f'  Full Name: {full_name}\n'
                f'  Role: dorm_supervisor'
            )
        )

