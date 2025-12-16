from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from applications.common.responses import ok, created, bad_request, not_found, forbidden, server_error
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from django.http import HttpResponse
import pandas as pd
import io
from datetime import datetime
from django.conf import settings
import logging
from bson import ObjectId

# Remove ORM model imports - using MongoDB only
from applications.common.mongo import get_mongo_collection, to_plain
import bcrypt


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_list(request):
    """API lấy danh sách giáo viên"""
    # Filter theo role của user
    user = request.user
    queryset = Teacher.objects.select_related('user')
    
    if user.role == 'teacher':
        # Giáo viên chỉ thấy thông tin của mình
        queryset = queryset.filter(user=user)
    # Admin thấy tất cả
    
    # Apply filters
    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(teacher_code__icontains=search) |
            Q(user__email__icontains=search) |
            Q(subject__icontains=search)
        )
    
    subject = request.query_params.get('subject')
    if subject:
        queryset = queryset.filter(subject__icontains=subject)
    
    # Ordering
    ordering = request.query_params.get('ordering', 'user__first_name')
    queryset = queryset.order_by(ordering)
    
    serializer = TeacherListSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_detail(request, id):
    """API lấy chi tiết giáo viên"""
    teacher = get_object_or_404(Teacher, id=id)
    
    # Check permissions
    user = request.user
    if user.role == 'teacher' and teacher.user != user:
        return Response(
            {'error': 'Không có quyền truy cập'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = TeacherSerializer(teacher)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def teacher_create(request):
    """API tạo giáo viên mới"""
    serializer = TeacherCreateRequestSerializer(data=request.data)
    if serializer.is_valid():
        with transaction.atomic():
            # Tạo user
            user_data = {
                'username': serializer.validated_data['username'],
                'email': serializer.validated_data['email'],
                'password': make_password(serializer.validated_data['password']),
                'first_name': serializer.validated_data['first_name'],
                'last_name': serializer.validated_data['last_name'],
                'role': 'teacher'
            }
            user = User.objects.create(**user_data)
            
            # Tạo teacher
            teacher_data = {
                'user': user,
                'teacher_code': serializer.validated_data['teacher_code'],
                'subject': serializer.validated_data.get('subject', '')
            }
            teacher = Teacher.objects.create(**teacher_data)
        
        response_serializer = TeacherSerializer(teacher)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def teacher_update(request, id):
    """API cập nhật giáo viên"""
    teacher = get_object_or_404(Teacher, id=id)
    
    # Check permissions
    user = request.user
    if user.role == 'teacher' and teacher.user != user:
        return Response(
            {'error': 'Không có quyền truy cập'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = TeacherUpdateRequestSerializer(teacher, data=request.data, partial=True)
    if serializer.is_valid():
        with transaction.atomic():
            # Update user fields
            user = teacher.user
            if 'first_name' in serializer.validated_data:
                user.first_name = serializer.validated_data['first_name']
            if 'last_name' in serializer.validated_data:
                user.last_name = serializer.validated_data['last_name']
            if 'email' in serializer.validated_data:
                user.email = serializer.validated_data['email']
            user.save()
            
            # Update teacher fields
            if 'teacher_code' in serializer.validated_data:
                teacher.teacher_code = serializer.validated_data['teacher_code']
            if 'subject' in serializer.validated_data:
                teacher.subject = serializer.validated_data['subject']
            teacher.save()
        
        response_serializer = TeacherSerializer(teacher)
        return Response(response_serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def teacher_delete(request, id):
    """API xóa giáo viên"""
    teacher = get_object_or_404(Teacher, id=id)
    
    # Check permissions - chỉ admin mới được xóa
    user = request.user
    if user.role != 'admin':
        return Response(
            {'error': 'Chỉ admin mới có quyền xóa giáo viên'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if teacher has homeroom classes
    if teacher.user.homeroom_classrooms.exists():
        return Response(
            {'error': 'Không thể xóa giáo viên đang chủ nhiệm lớp'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    with transaction.atomic():
        # Delete user (will cascade to teacher)
        teacher.user.delete()
    
    return Response({'message': 'Đã xóa giáo viên thành công'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_stats(request):
    """API lấy thống kê giáo viên"""
    total_teachers = Teacher.objects.count()
    teachers_with_classes = Teacher.objects.filter(user__homeroom_classrooms__isnull=False).distinct().count()
    
    # Thống kê theo môn học
    subject_stats = []
    subjects = Teacher.objects.values_list('subject', flat=True).distinct()
    for subject in subjects:
        if subject:  # Skip empty subjects
            count = Teacher.objects.filter(subject=subject).count()
            subject_stats.append({
                'subject': subject,
                'count': count
            })
    
    # Sắp xếp theo số lượng giảm dần
    subject_stats.sort(key=lambda x: x['count'], reverse=True)
    
    stats = {
        'total_teachers': total_teachers,
        'teachers_with_classes': teachers_with_classes,
        'teachers_without_classes': total_teachers - teachers_with_classes,
        'subject_stats': subject_stats[:10]  # Top 10 subjects
    }
    
    return Response(stats)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def teacher_import_excel(request):
    """API import giáo viên từ file Excel"""
    if 'file' not in request.FILES:
        return Response(
            {'error': 'Không tìm thấy file'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    file = request.FILES['file']
    
    # Validate file type
    if not file.name.endswith(('.xlsx', '.xls')):
        return Response(
            {'error': 'File phải là định dạng Excel (.xlsx hoặc .xls)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Read Excel file
        if file.name.endswith('.xlsx'):
            df = pd.read_excel(file, engine='openpyxl')
        else:
            df = pd.read_excel(file, engine='xlrd')
        
        # Validate required columns
        required_columns = ['username', 'email', 'password', 'first_name', 'last_name', 'teacher_code']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return Response(
                {'error': f'Thiếu các cột bắt buộc: {", ".join(missing_columns)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process data
        success_count = 0
        error_count = 0
        errors = []
        success_data = []
        
        for index, row in df.iterrows():
            row_number = index + 2  # Excel row number (1-based, +1 for header)
            
            try:
                # Prepare data
                data = {
                    'username': str(row['username']).strip(),
                    'email': str(row['email']).strip(),
                    'password': str(row['password']).strip(),
                    'first_name': str(row['first_name']).strip(),
                    'last_name': str(row['last_name']).strip(),
                    'teacher_code': str(row['teacher_code']).strip(),
                    'subject': str(row.get('subject', '')).strip()
                }
                
                # Validate data
                serializer = TeacherImportSerializer(data=data)
                if serializer.is_valid():
                    with transaction.atomic():
                        # Create user
                        user_data = {
                            'username': data['username'],
                            'email': data['email'],
                            'password': make_password(data['password']),
                            'first_name': data['first_name'],
                            'last_name': data['last_name'],
                            'role': 'teacher'
                        }
                        user = User.objects.create(**user_data)
                        
                        # Create teacher
                        teacher_data = {
                            'user': user,
                            'teacher_code': data['teacher_code'],
                            'subject': data['subject']
                        }
                        teacher = Teacher.objects.create(**teacher_data)
                    
                    success_count += 1
                    success_data.append({
                        'row': row_number,
                        'username': data['username'],
                        'teacher_code': data['teacher_code'],
                        'full_name': f"{data['first_name']} {data['last_name']}"
                    })
                else:
                    error_count += 1
                    errors.append({
                        'row': row_number,
                        'errors': serializer.errors
                    })
                    
            except Exception as e:
                error_count += 1
                errors.append({
                    'row': row_number,
                    'errors': {'general': f'Lỗi xử lý: {str(e)}'}
                })
        
        result = {
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors,
            'success_data': success_data
        }
        
        return Response(result)
        
    except Exception as e:
        return Response(
            {'error': f'Lỗi đọc file Excel: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_import_template(request):
    """API tải template Excel cho import giáo viên"""
    # Create sample data
    sample_data = [
        {
            'username': 'teacher1',
            'email': 'teacher1@school.edu.vn',
            'password': 'password123',
            'first_name': 'Nguyễn',
            'last_name': 'Văn A',
            'teacher_code': 'GV001',
            'subject': 'Toán'
        },
        {
            'username': 'teacher2',
            'email': 'teacher2@school.edu.vn',
            'password': 'password123',
            'first_name': 'Trần',
            'last_name': 'Thị B',
            'teacher_code': 'GV002',
            'subject': 'Văn'
        },
        {
            'username': 'teacher3',
            'email': 'teacher3@school.edu.vn',
            'password': 'password123',
            'first_name': 'Lê',
            'last_name': 'Văn C',
            'teacher_code': 'GV003',
            'subject': 'Anh'
        }
    ]
    
    # Create DataFrame
    df = pd.DataFrame(sample_data)
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Teachers', index=False)
        
        # Get the workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['Teachers']
        
        # Add instructions
        instructions = [
            'HƯỚNG DẪN IMPORT GIÁO VIÊN',
            '',
            '1. Các cột bắt buộc:',
            '   - username: Tên đăng nhập (không được trùng)',
            '   - email: Email (không được trùng)',
            '   - password: Mật khẩu',
            '   - first_name: Tên',
            '   - last_name: Họ',
            '   - teacher_code: Mã giáo viên (không được trùng)',
            '',
            '2. Các cột tùy chọn:',
            '   - subject: Môn dạy',
            '',
            '3. Lưu ý:',
            '   - Không được để trống các cột bắt buộc',
            '   - Username, email, teacher_code phải là duy nhất',
            '   - Password nên có ít nhất 6 ký tự',
            ''
        ]
        
        # Add instructions to worksheet
        for i, instruction in enumerate(instructions):
            worksheet.cell(row=i+1, column=len(df.columns)+2, value=instruction)
    
    output.seek(0)
    
    # Create response
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="teacher_import_template_{datetime.now().strftime("%Y%m%d")}.xlsx"'
    
    return response


# --- Mongo-backed teachers ---

def _mongo_users_coll():
    coll = getattr(settings, 'MONGO_USERS_COLLECTION', None) or 'users'
    return get_mongo_collection(coll)


def _generate_teacher_code(full_name: str) -> str:
    base = ''.join([p[0].upper() for p in full_name.split() if p]) or 'GV'
    return base


def _hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _gen_username(email: str, teacher_code: str) -> str:
    if email:
        return email.split('@')[0]
    return f"{teacher_code.lower()}"

    return f"{base}{datetime.now().strftime('%H%M%S')}"


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_teachers_list(request):
    try:
        coll = _mongo_users_coll()
        subject = request.query_params.get('subject')
        search = request.query_params.get('search')
        ordering = request.query_params.get('ordering', 'full_name')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 12))
        page = max(1, page)
        page_size = max(1, min(200, page_size))
        
        query = {'role': 'teacher'}  # Only get teachers
        if subject:
            query['subject'] = subject
        if search:
            query['$or'] = [
                {'full_name': {'$regex': search, '$options': 'i'}},
                {'first_name': {'$regex': search, '$options': 'i'}},
                {'last_name': {'$regex': search, '$options': 'i'}},
                {'teacher_code': {'$regex': search, '$options': 'i'}},
                {'email': {'$regex': search, '$options': 'i'}},
                {'subject': {'$regex': search, '$options': 'i'}},
            ]

        total_count = coll.count_documents(query)
        skip_count = (page - 1) * page_size
        docs = list(coll.find(query).sort(ordering, 1).skip(skip_count).limit(page_size))
        result = []
        for d in docs:
            t = to_plain(d)
            full_name = t.get('full_name') or ''
            email = t.get('email') or ''
            parts = full_name.split()
            first_name = ' '.join(parts[:-1]) if len(parts) > 1 else full_name
            last_name = parts[-1] if len(parts) > 1 else ''
            result.append({
                'id': t.get('id'),
                'teacher_code': t.get('teacher_code'),
                'subject': t.get('subject'),
                'created_at': t.get('created_at'),
                'updated_at': t.get('updated_at'),
                'full_name': full_name,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'username': email.split('@')[0] if email else '',
                'role': 'teacher',
                'homeroom_class': t.get('homeroom_class', ''),
                'homeroom_class_id': t.get('homeroom_class_id', '')
            })
        return Response({
            'results': result,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
        })
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_teachers_list error')
        return server_error(exc)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mongo_teachers_create(request):
    try:
        coll = _mongo_users_coll()
        payload = request.data or {}
        full_name = (payload.get('full_name') or '').strip()
        subject = payload.get('subject')
        email = payload.get('email')
        phone = payload.get('phone')
        if not full_name:
            return bad_request('full_name là bắt buộc')
        # Unique email check (if provided)
        if email:
            if coll.find_one({'email': email}):
                return bad_request('Email đã tồn tại')
        teacher_code = _generate_teacher_code(full_name)
        # Create unified user document with teacher-specific fields
        temp_password = payload.get('password') or '123456'
        doc = {
            'username': email or '',
            'email': email or '',
            'password_hash': _hash_password(temp_password),
            'role': 'teacher',
            'first_name': ' '.join(full_name.split()[:-1]) if len(full_name.split()) > 1 else full_name,
            'last_name': full_name.split()[-1] if len(full_name.split()) > 1 else '',
            'full_name': full_name,
            'phone': phone,
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            
            # Teacher-specific fields
            'teacher_code': teacher_code,
            'subject': subject,
        }
        res = coll.insert_one(doc)
        inserted = to_plain(coll.find_one({'_id': res.inserted_id}))
        full_name = inserted.get('full_name') or ''
        email = inserted.get('email') or ''
        parts = full_name.split()
        first_name = ' '.join(parts[:-1]) if len(parts) > 1 else full_name
        last_name = parts[-1] if len(parts) > 1 else ''
        payload = {
            'id': inserted.get('id'),
            'teacher_code': inserted.get('teacher_code'),
            'subject': inserted.get('subject'),
            'created_at': inserted.get('created_at'),
            'updated_at': inserted.get('updated_at'),
            'full_name': full_name,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'username': email.split('@')[0] if email else '',
            'role': 'teacher'
        }
        return Response(payload, status=status.HTTP_201_CREATED)
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_teachers_create error')
        return server_error(exc)


# --- Mongo-backed teachers (detail & update) ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_teachers_detail(request, id: str):
    try:
        coll = _mongo_users_coll()
        doc = coll.find_one({'_id': ObjectId(id)})
        if not doc:
            return not_found('Teacher not found')
        t = to_plain(doc)
        full_name = t.get('full_name') or ''
        email = t.get('email') or ''
        parts = full_name.split()
        first_name = ' '.join(parts[:-1]) if len(parts) > 1 else full_name
        last_name = parts[-1] if len(parts) > 1 else ''
        return Response({
            'id': t.get('id'),
            'teacher_code': t.get('teacher_code'),
            'subject': t.get('subject'),
            'created_at': t.get('created_at'),
            'updated_at': t.get('updated_at'),
            'full_name': full_name,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'username': email.split('@')[0] if email else '',
            'role': 'teacher',
            'homeroom_class': t.get('homeroom_class', ''),
            'homeroom_class_id': t.get('homeroom_class_id', '')
        })
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_teachers_detail error')
        return server_error(exc)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mongo_teachers_update(request, id: str):
    try:
        coll = _mongo_users_coll()
        payload = request.data or {}
        updates = {}
        if 'full_name' in payload:
            updates['full_name'] = (payload.get('full_name') or '').strip()
        if 'subject' in payload:
            updates['subject'] = payload.get('subject')
        if 'email' in payload:
            email = payload.get('email')
            if email and coll.find_one({'email': email, '_id': {'$ne': ObjectId(id)}}):
                return bad_request('Email đã tồn tại')
            updates['email'] = email
        if 'phone' in payload:
            updates['phone'] = payload.get('phone')
        if not updates:
            return bad_request('No updates provided')
        updates['updated_at'] = datetime.now().isoformat()
        coll.update_one({'_id': ObjectId(id)}, {'$set': updates})
        # Sync user snapshot if present
        doc = to_plain(coll.find_one({'_id': ObjectId(id)}))
        user_id = doc.get('user_id')
        if user_id:
            users = _mongo_users_coll()
            user_updates = {}
            if 'full_name' in updates:
                user_updates['full_name'] = updates['full_name']
                # also split names
                parts = updates['full_name'].split()
                user_updates['first_name'] = ' '.join(parts[:-1]) if len(parts) > 1 else updates['full_name']
                user_updates['last_name'] = parts[-1] if len(parts) > 1 else ''
            if 'email' in updates:
                if updates['email'] and users.find_one({'email': updates['email'], '_id': {'$ne': ObjectId(user_id)}}):
                    return Response({'detail': 'Email đã tồn tại (users)'}, status=status.HTTP_400_BAD_REQUEST)
                user_updates['email'] = updates['email']
            if user_updates:
                user_updates['updated_at'] = datetime.now().isoformat()
                try:
                    users.update_one({'_id': ObjectId(user_id)}, {'$set': user_updates})
                except Exception:
                    users.update_one({'id': user_id}, {'$set': user_updates})
        return Response(to_plain(coll.find_one({'_id': ObjectId(id)})))
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_teachers_update error')
        return server_error(exc)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def mongo_teachers_delete(request, id: str):
    try:
        coll = _mongo_users_coll()
        res = coll.delete_one({'_id': ObjectId(id)})
        if res.deleted_count == 0:
            return not_found('Teacher not found')
        return Response({'message': 'Đã xóa giáo viên (Mongo) thành công'})
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_teachers_delete error')
        return server_error(exc)