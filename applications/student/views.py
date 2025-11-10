import pandas as pd
import io
from datetime import datetime
from django.conf import settings
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from applications.common.responses import ok, created, bad_request, not_found, forbidden, server_error
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from django.utils import timezone
import pandas as pd
import io
from datetime import datetime
from bson import ObjectId
from django.db import models

from .serializers import (
    MongoStudentSerializer,
    MongoStudentCreateSerializer,
    MongoStudentUpdateSerializer
)
from applications.common.mongo import get_mongo_collection, to_plain
from bson import ObjectId


# --- Mongo-backed students ---

def _mongo_users_coll():
    coll = getattr(settings, 'MONGO_USERS_COLLECTION', None) or 'users'
    return get_mongo_collection(coll)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_students_list(request):
    try:
        coll = _mongo_users_coll()
        classroom_id = request.query_params.get('classroom_id')
        search = request.query_params.get('search')
        gender = request.query_params.get('gender')

        query = {'role': 'student'}  # Only get students
        if classroom_id and classroom_id != 'all':
            query['classroom_id'] = classroom_id
        if gender in ('male', 'female'):
            query['gender'] = gender
        if search:
            # basic regex OR on user fields and student_code
            query['$or'] = [
                {'full_name': {'$regex': search, '$options': 'i'}},
                {'first_name': {'$regex': search, '$options': 'i'}},
                {'last_name': {'$regex': search, '$options': 'i'}},
                {'student_code': {'$regex': search, '$options': 'i'}},
                {'email': {'$regex': search, '$options': 'i'}},
            ]

        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 12))
        page = max(1, page)
        page_size = max(1, min(200, page_size))

        total_count = coll.count_documents(query)
        skip_count = (page - 1) * page_size

        # Calculate gender stats
        male_count = coll.count_documents({**query, 'gender': 'male'})
        female_count = coll.count_documents({**query, 'gender': 'female'})

        docs = list(coll.find(query).sort('full_name', 1).skip(skip_count).limit(page_size))

        out = []
        for d in docs:
            t = to_plain(d)
            # ensure created_at/updated_at
            t['created_at'] = t.get('created_at') or ''
            t['updated_at'] = t.get('updated_at') or t['created_at']
            out.append(t)

        return Response({
            'results': out,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'male_count': male_count,
            'female_count': female_count,
        })
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_students_list error')
        return server_error(exc)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mongo_students_create_by_teacher(request):
    """API cho giáo viên tạo account học sinh"""
    try:
        from applications.common.mongo import get_mongo_collection
        import bcrypt
        from bson import ObjectId
        
        # Chỉ giáo viên mới được tạo account cho học sinh
        if request.user.role != 'teacher':
            return forbidden('Chỉ giáo viên mới được tạo account cho học sinh')
        
        students_coll = _mongo_users_coll()
        users_coll = get_mongo_collection('users')
        classrooms_coll = get_mongo_collection('classrooms')
        
        payload = request.data or {}
        full_name = (payload.get('full_name') or '').strip()
        email = payload.get('email')
        classroom_id = payload.get('classroom_id')
        date_of_birth = payload.get('date_of_birth')
        gender = payload.get('gender')
        address = payload.get('address')
        parent_phone = payload.get('parent_phone')
        
        if not full_name:
            return bad_request('full_name là bắt buộc')
        if not classroom_id:
            return bad_request('classroom_id là bắt buộc')
        if not email:
            return bad_request('email là bắt buộc')
        
        # Kiểm tra classroom có tồn tại không
        classroom_doc = classrooms_coll.find_one({'_id': ObjectId(classroom_id)})
        if not classroom_doc:
            return bad_request('Lớp học không tồn tại')
        
        # Tìm user đã tồn tại (được import trước đó)
        existing_user = users_coll.find_one({'email': email, 'role': 'student'})
        if not existing_user:
            return bad_request('Không tìm thấy học sinh với email này. Vui lòng import học sinh trước.')
        
        # Cập nhật password cho user đã tồn tại
        temp_password = '123456'  # Mật khẩu mặc định cho học sinh
        password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Cập nhật user với password mới
        users_coll.update_one(
            {'_id': existing_user['_id']},
            {
                '$set': {
                    'password_hash': password_hash,
                    'updated_at': datetime.now().isoformat()
                }
            }
        )
        
        # Trả về thông tin học sinh đã cập nhật
        updated_student = to_plain(users_coll.find_one({'_id': existing_user['_id']}))
        updated_student['created_at'] = updated_student.get('created_at') or ''
        updated_student['updated_at'] = updated_student.get('updated_at') or updated_student['created_at']
        
        return Response({
            'detail': f'Đã cấp account cho học sinh {existing_user.get("full_name", full_name)}. Email: {email}, Password: {temp_password}',
            'student': updated_student
        }, status=status.HTTP_200_OK)
        
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_students_create_by_teacher error')
        return server_error(exc)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mongo_students_create(request):
    try:
        coll = _mongo_users_coll()
        users_coll = get_mongo_collection('users')
        classrooms_coll = get_mongo_collection('classrooms')
        
        payload = request.data or {}
        email = payload.get('email')
        classroom_id = payload.get('classroom_id')
        
        if email and coll.find_one({'email': email}):
            return bad_request('Email đã tồn tại')
        
        # Lấy thông tin classroom
        classroom = classrooms_coll.find_one({'_id': ObjectId(classroom_id)})
        if not classroom:
            return bad_request('Lớp học không tồn tại')
        
        # Tạo user account cho học sinh
        user_data = {
            'email': email,
            'password_hash': '',  # Sẽ được set khi login
            'role': 'student',
            'first_name': payload.get('first_name', ''),
            'last_name': payload.get('last_name', ''),
            'full_name': payload.get('full_name') or (payload.get('first_name', '') + ' ' + payload.get('last_name', '')).strip(),
            'phone': payload.get('phone', ''),
            'is_active': True,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        user_result = users_coll.insert_one(user_data)
        user_id = str(user_result.inserted_id)
        
        # Tạo user với role = 'student' và các field student-specific
        doc = {
            'first_name': user_data['first_name'],
            'last_name': user_data['last_name'],
            'full_name': user_data['full_name'],
            'email': email,
            'role': 'student',
            'phone': user_data['phone'],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            
            # Student-specific fields
            'student_code': payload.get('student_code'),
            'classroom_id': classroom_id,
            'classroom_name': classroom.get('name', ''),
            'classroom_grade': classroom.get('grade', ''),
            'gender': payload.get('gender'),
            'date_of_birth': payload.get('date_of_birth'),
            'address': payload.get('address', ''),
            'parent_phone': payload.get('parent_phone', ''),
            'is_special': False,
        }
        
        res = coll.insert_one(doc)
        inserted = to_plain(coll.find_one({'_id': res.inserted_id}))
        
        # Cập nhật student_count trong classroom
        classrooms_coll.update_one(
            {'_id': ObjectId(classroom_id)},
            {'$inc': {'student_count': 1}}
        )
        
        return Response(inserted, status=status.HTTP_201_CREATED)
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_students_create error')
        return server_error(exc)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_students_detail(request, id: str):
    try:
        coll = _mongo_users_coll()
        doc = coll.find_one({'_id': ObjectId(id)})
        if not doc:
            return not_found('Student not found')
        t = to_plain(doc)
        return Response(t)
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_students_detail error')
        return server_error(exc)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mongo_students_update(request, id: str):
    try:
        coll = _mongo_users_coll()
        payload = request.data or {}
        updates = {}
        if 'full_name' in payload:
            updates.setdefault('user', {})
            updates['user']['full_name'] = (payload.get('full_name') or '').strip()
        if 'first_name' in payload:
            updates.setdefault('user', {})
            updates['user']['first_name'] = payload.get('first_name') or ''
        if 'last_name' in payload:
            updates.setdefault('user', {})
            updates['user']['last_name'] = payload.get('last_name') or ''
        if 'student_code' in payload:
            updates['student_code'] = payload.get('student_code')
        if 'classroom_id' in payload:
            updates['classroom.id'] = payload.get('classroom_id')
        if 'gender' in payload:
            updates['gender'] = payload.get('gender')
        if 'email' in payload:
            email = payload.get('email')
            if email and coll.find_one({'user.email': email, '_id': {'$ne': ObjectId(id)}}):
                return bad_request('Email đã tồn tại')
            updates.setdefault('user', {})
            updates['user']['email'] = email
        if 'phone' in payload:
            updates['phone'] = payload.get('phone')
        if not updates:
            return bad_request('No updates provided')
        updates['updated_at'] = datetime.now().isoformat()
        coll.update_one({'_id': ObjectId(id)}, {'$set': updates})
        return mongo_students_detail(request, id)
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_students_update error')
        return server_error(exc)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def mongo_students_delete(request, id: str):
    try:
        coll = _mongo_users_coll()
        res = coll.delete_one({'_id': ObjectId(id)})
        if res.deleted_count == 0:
            return not_found('Student not found')
        return Response({'message': 'Đã xóa học sinh (Mongo) thành công'})
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_students_delete error')
        return server_error(exc)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_students_my_classroom(request):
    """API lấy học sinh theo lớp của giáo viên chủ nhiệm hoặc học sinh hiện tại"""
    try:
        from applications.common.mongo import get_mongo_collection
        from bson import ObjectId
        
        logging.getLogger(__name__).info(f"mongo_students_my_classroom called with user: {request.user}")
        
        user = request.user
        logging.getLogger(__name__).info(f"User role: {user.role}, email: {user.email}")
        students_coll = _mongo_users_coll()
        classrooms_coll = get_mongo_collection('classrooms')
        
        # Tìm lớp của user hiện tại
        classroom_id = None
        classroom_info = None
        
        if user.role == 'teacher':
            # Tìm lớp mà giáo viên này là chủ nhiệm
            user_id_str = str(user.id)
            logging.getLogger(__name__).info(f"Looking for teacher with Django user_id: {user_id_str}")
            
            # Tìm teacher document trong users collection
            teacher_doc = students_coll.find_one({'email': user.email, 'role': 'teacher'})
            
            if teacher_doc:
                teacher_id = str(teacher_doc['_id'])
                logging.getLogger(__name__).info(f"Found teacher doc: {teacher_doc}")
                
                # Tìm classroom với teacher_id này
                classroom_doc = classrooms_coll.find_one({'homeroom_teacher_id': teacher_id})
                if classroom_doc:
                    classroom_id = str(classroom_doc['_id'])
                    classroom_info = {
                        'id': classroom_id,
                        'name': classroom_doc.get('name', ''),
                        'full_name': classroom_doc.get('full_name', ''),
                        'grade': classroom_doc.get('grade', ''),
                    }
                    logging.getLogger(__name__).info(f"Found classroom: {classroom_info}")
                else:
                    logging.getLogger(__name__).warning(f"No classroom found for teacher_id: {teacher_id}")
            else:
                logging.getLogger(__name__).warning(f"No teacher doc found for email: {user.email}")
        elif user.role == 'student':
            # Tìm lớp của học sinh này
            student_doc = students_coll.find_one({'email': user.email, 'role': 'student'})
            if student_doc and student_doc.get('classroom_id'):
                classroom_id = student_doc['classroom_id']
                # Lấy thông tin classroom
                classroom_doc = classrooms_coll.find_one({'_id': ObjectId(classroom_id)})
                if classroom_doc:
                    classroom_info = {
                        'id': classroom_id,
                        'name': classroom_doc.get('name', ''),
                        'full_name': classroom_doc.get('full_name', ''),
                        'grade': classroom_doc.get('grade', ''),
                    }
        
        if not classroom_id:
            if user.role == 'teacher':
                logging.getLogger(__name__).warning(f"Teacher {user.email} not assigned to any classroom")
                return Response({
                    'detail': 'Bạn chưa được phân công làm giáo viên chủ nhiệm của lớp nào',
                    'classroom': None,
                    'results': [],
                    'total': 0,
                    'page': 1,
                    'page_size': 12,
                    'total_pages': 0,
                    'male_count': 0,
                    'female_count': 0,
                }, status=status.HTTP_404_NOT_FOUND)
            else:
                logging.getLogger(__name__).warning(f"Student {user.email} not assigned to any classroom")
                return Response({
                    'detail': 'Không tìm thấy thông tin lớp học',
                    'classroom': None,
                    'results': [],
                    'total': 0,
                    'page': 1,
                    'page_size': 12,
                    'total_pages': 0,
                    'male_count': 0,
                    'female_count': 0,
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Lấy học sinh trong lớp
        query = {'classroom_id': classroom_id, 'role': 'student'}
        
        # Apply filters
        search = request.query_params.get('search')
        gender = request.query_params.get('gender')
        
        if gender in ('male', 'female'):
            query['gender'] = gender
        if search:
            query['$or'] = [
                {'full_name': {'$regex': search, '$options': 'i'}},
                {'first_name': {'$regex': search, '$options': 'i'}},
                {'last_name': {'$regex': search, '$options': 'i'}},
                {'student_code': {'$regex': search, '$options': 'i'}},
                {'email': {'$regex': search, '$options': 'i'}},
            ]
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 12))
        page = max(1, page)
        page_size = max(1, min(200, page_size))
        
        total_count = students_coll.count_documents(query)
        skip_count = (page - 1) * page_size
        
        docs = list(students_coll.find(query).sort('full_name', 1).skip(skip_count).limit(page_size))
        
        out = []
        for d in docs:
            t = to_plain(d)
            t['created_at'] = t.get('created_at') or ''
            t['updated_at'] = t.get('updated_at') or t['created_at']
            # Thêm thông tin có account hay không
            t['has_account'] = bool(t.get('password_hash'))
            out.append(t)
        
        # Calculate gender counts for the entire class (not just current page)
        male_count = students_coll.count_documents({'classroom_id': classroom_id, 'role': 'student', 'gender': 'male'})
        female_count = students_coll.count_documents({'classroom_id': classroom_id, 'role': 'student', 'gender': 'female'})
        
        result = {
            'classroom': classroom_info,
            'results': out,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'male_count': male_count,
            'female_count': female_count,
        }
        
        logging.getLogger(__name__).info(f"mongo_students_my_classroom returning: {result}")
        return Response(result)
        
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_students_my_classroom error')
        return server_error(exc)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_students_dropdown(request):
    """API dropdown cho students - chỉ trả về id, name, full_name"""
    try:
        classroom_id = request.query_params.get('classroom_id')
        
        coll = _mongo_users_coll()
        query = {'role': 'student'}
        
        if classroom_id:
            query['classroom_id'] = classroom_id
        
        # Chỉ lấy id, user info, student_code để giảm payload
        docs = list(coll.find(query, {'id': 1, 'full_name': 1, 'first_name': 1, 'last_name': 1, 'student_code': 1}).sort('full_name', 1))
        
        out = []
        for d in docs:
            t = to_plain(d)
            first_name = t.get('first_name', '')
            last_name = t.get('last_name', '')
            full_name = t.get('full_name', '') or f"{first_name} {last_name}".strip()
            
            out.append({
                'id': t.get('id', ''),
                'name': first_name,
                'full_name': full_name,
                'student_code': t.get('student_code', '')
            })
        
        return ok(out)
        
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_students_dropdown error')
        return server_error(exc)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_students_my_classroom_dropdown(request):
    """API dropdown cho my classroom students - chỉ trả về id, name, full_name"""
    try:
        user = request.user
        if not hasattr(user, 'id'):
            return bad_request('User not authenticated')
        
        # Lấy thông tin teacher/student
        users_coll = get_mongo_collection('users')
        user_doc = users_coll.find_one({'_id': ObjectId(user.id)})
        if not user_doc:
            return not_found('User not found')
        
        user_data = to_plain(user_doc)
        
        # Tìm classroom của user
        classroom_id = None
        if user_data.get('role') == 'teacher':
            # Tìm lớp chủ nhiệm
            classrooms_coll = get_mongo_collection('classrooms')
            classroom_doc = classrooms_coll.find_one({'homeroom_teacher_id': user_data.get('id')})
            if classroom_doc:
                classroom_id = to_plain(classroom_doc).get('id')
        elif user_data.get('role') == 'student':
            # Lấy classroom_id từ student record
            students_coll = get_mongo_collection('students')
            student_doc = students_coll.find_one({'user.id': user_data.get('id')})
            if student_doc:
                classroom_data = to_plain(student_doc).get('classroom', {})
                classroom_id = classroom_data.get('id')
        
        if not classroom_id:
            return bad_request('No classroom found for user')
        
        # Lấy students của classroom
        students_coll = get_mongo_collection('students')
        docs = list(students_coll.find({'classroom.id': classroom_id}, {'id': 1, 'user': 1, 'student_code': 1}).sort('user.full_name', 1))
        
        out = []
        for d in docs:
            t = to_plain(d)
            user = t.get('user', {})
            first_name = user.get('first_name', '')
            last_name = user.get('last_name', '')
            full_name = user.get('full_name', '') or f"{first_name} {last_name}".strip()
            
            out.append({
                'id': t.get('id', ''),
                'name': first_name,
                'full_name': full_name,
                'student_code': t.get('student_code', '')
            })
        
        return ok(out)
        
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_students_my_classroom_dropdown error')
        return server_error(exc)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mongo_students_import(request):
    """Import học sinh từ file Excel vào MongoDB"""
    try:
        if 'file' not in request.FILES:
            return bad_request('Không tìm thấy file')
        
        file = request.FILES['file']
        
        # Kiểm tra định dạng file
        if not file.name.endswith(('.xlsx', '.xls')):
            return bad_request('Chỉ chấp nhận file Excel (.xlsx, .xls)')
        
        # Đọc file Excel
        try:
            df = pd.read_excel(file)
        except Exception as e:
            return bad_request(f'Không thể đọc file Excel: {str(e)}')
        
        # Kiểm tra cột bắt buộc
        required_columns = ['Họ tên', 'Mã học sinh', 'Lớp', 'Giới tính', 'Ngày sinh']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return bad_request(f'Thiếu các cột bắt buộc: {", ".join(missing_columns)}')
        
        # Kết nối MongoDB
        students_coll = get_mongo_collection('students')
        classrooms_coll = get_mongo_collection('classrooms')
        users_coll = get_mongo_collection('users')
        
        success_count = 0
        error_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Lấy thông tin từ Excel
                full_name = str(row['Họ tên']).strip()
                student_code = str(row['Mã học sinh']).strip()
                classroom_name = str(row['Lớp']).strip()
                gender = str(row['Giới tính']).strip().lower()
                birth_date = row['Ngày sinh']
                
                # Validate dữ liệu
                if not full_name or not student_code or not classroom_name:
                    errors.append({
                        'row': index + 2,  # +2 vì Excel bắt đầu từ 1 và có header
                        'error': 'Thiếu thông tin bắt buộc'
                    })
                    error_count += 1
                    continue
                
                # Tìm classroom
                classroom = classrooms_coll.find_one({'name': classroom_name})
                if not classroom:
                    errors.append({
                        'row': index + 2,
                        'error': f'Không tìm thấy lớp: {classroom_name}'
                    })
                    error_count += 1
                    continue
                
                # Kiểm tra học sinh đã tồn tại
                existing_student = students_coll.find_one({'student_code': student_code})
                if existing_student:
                    errors.append({
                        'row': index + 2,
                        'error': f'Mã học sinh đã tồn tại: {student_code}'
                    })
                    error_count += 1
                    continue
                
                # Tạo user cho học sinh
                user_data = {
                    'first_name': full_name.split()[0] if full_name.split() else '',
                    'last_name': ' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
                    'full_name': full_name,
                    'email': f'{student_code}@student.local',
                    'role': 'student',
                    'is_active': True,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                user_result = users_coll.insert_one(user_data)
                user_id = str(user_result.inserted_id)
                
                # Tạo user với role = 'student' và các field student-specific
                student_data = {
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'full_name': user_data['full_name'],
                    'email': user_data['email'],
                    'role': 'student',
                    'phone': '',
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    
                    # Student-specific fields
                    'student_code': student_code,
                    'classroom_id': str(classroom['_id']),
                    'classroom_name': classroom['name'],
                    'classroom_grade': classroom.get('grade', ''),
                    'gender': 'male' if gender in ['nam', 'male', 'm'] else 'female',
                    'date_of_birth': birth_date.strftime('%Y-%m-%d') if hasattr(birth_date, 'strftime') else str(birth_date),
                    'address': '',
                    'parent_phone': '',
                    'is_special': False,
                }
                
                students_coll.insert_one(student_data)
                
                # Cập nhật student_count trong classroom
                classrooms_coll.update_one(
                    {'_id': classroom['_id']},
                    {'$inc': {'student_count': 1}}
                )
                
                success_count += 1
                
            except Exception as e:
                errors.append({
                    'row': index + 2,
                    'error': f'Lỗi xử lý: {str(e)}'
                })
                error_count += 1
        
        return ok({
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors,
            'message': f'Import hoàn thành: {success_count} thành công, {error_count} lỗi'
        })
        
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_students_import error')
        return server_error(str(exc))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_students_import_template(request):
    """Tải template Excel cho import học sinh"""
    try:
        # Tạo DataFrame mẫu
        sample_data = {
            'Họ tên': ['Nguyễn Văn A', 'Trần Thị B', 'Lê Văn C'],
            'Mã học sinh': ['HS001', 'HS002', 'HS003'],
            'Lớp': ['10A1', '10A2', '11A1'],
            'Giới tính': ['Nam', 'Nữ', 'Nam'],
            'Ngày sinh': ['2005-01-15', '2005-03-20', '2004-12-10']
        }
        
        df = pd.DataFrame(sample_data)
        
        # Tạo file Excel trong memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Học sinh', index=False)
        
        output.seek(0)
        
        # Trả về file
        from django.http import HttpResponse
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="template_import_hoc_sinh.xlsx"'
        return response
        
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_students_import_template error')
        return server_error(str(exc))
