from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from applications.common.responses import ok, created, bad_request, not_found, server_error
from django.shortcuts import get_object_or_404
from django.db.models import Q

# Remove ORM serializers - using MongoDB only
from applications.common.mongo import get_mongo_collection, to_plain
from bson import ObjectId
import logging
from datetime import datetime


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def classroom_list(request):
    """API lấy danh sách lớp học"""
    # Filter theo role của user
    user = request.user
    queryset = Classroom.objects.select_related('grade', 'homeroom_teacher')
    
    if user.role == 'student':
        # Học sinh chỉ thấy lớp của mình
        if hasattr(user, 'student'):
            queryset = queryset.filter(id=user.student.classroom.id)
        else:
            queryset = queryset.none()
    elif user.role == 'teacher':
        # Giáo viên thấy lớp mình chủ nhiệm và tất cả lớp khác
        queryset = queryset.filter(
            Q(homeroom_teacher=user) | Q(homeroom_teacher__isnull=True)
        )
    # Admin thấy tất cả
    
    # Apply filters
    grade = request.query_params.get('grade')
    if grade:
        queryset = queryset.filter(grade_id=grade)
    
    is_special = request.query_params.get('is_special')
    if is_special is not None:
        queryset = queryset.filter(is_special=is_special.lower() == 'true')
    
    homeroom_teacher = request.query_params.get('homeroom_teacher')
    if homeroom_teacher:
        queryset = queryset.filter(homeroom_teacher_id=homeroom_teacher)
    
    # Search
    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) | Q(grade__name__icontains=search)
        )
    
    # Ordering
    ordering = request.query_params.get('ordering', 'grade__name')
    if ordering:
        queryset = queryset.order_by(ordering)
    else:
        queryset = queryset.order_by('grade__name', 'name')
    
    serializer = ClassroomListSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def classroom_detail(request, id):
    """API lấy chi tiết lớp học"""
    # Filter theo role của user
    user = request.user
    queryset = Classroom.objects.select_related('grade', 'homeroom_teacher')
    
    if user.role == 'student':
        # Học sinh chỉ thấy lớp của mình
        if hasattr(user, 'student'):
            queryset = queryset.filter(id=user.student.classroom.id)
        else:
            queryset = queryset.none()
    elif user.role == 'teacher':
        # Giáo viên thấy lớp mình chủ nhiệm và tất cả lớp khác
        queryset = queryset.filter(
            Q(homeroom_teacher=user) | Q(homeroom_teacher__isnull=True)
        )
    # Admin thấy tất cả
    
    classroom = get_object_or_404(queryset, id=id)
    serializer = ClassroomSerializer(classroom)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def classroom_create(request):
    """API tạo lớp học mới"""
    serializer = ClassroomCreateRequestSerializer(data=request.data)
    if serializer.is_valid():
        # Tạo classroom từ validated data
        classroom = Classroom.objects.create(
            name=serializer.validated_data['name'],
            grade_id=serializer.validated_data['grade_id'],
            homeroom_teacher_id=serializer.validated_data.get('homeroom_teacher_id'),
            is_special=serializer.validated_data.get('is_special', False)
        )
        response_serializer = ClassroomSerializer(classroom)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def classroom_update(request, id):
    """API cập nhật lớp học"""
    classroom = get_object_or_404(Classroom, id=id)
    serializer = ClassroomUpdateRequestSerializer(classroom, data=request.data, partial=True)
    if serializer.is_valid():
        # Cập nhật classroom từ validated data
        if 'name' in serializer.validated_data:
            classroom.name = serializer.validated_data['name']
        if 'grade_id' in serializer.validated_data:
            classroom.grade_id = serializer.validated_data['grade_id']
        if 'homeroom_teacher_id' in serializer.validated_data:
            classroom.homeroom_teacher_id = serializer.validated_data['homeroom_teacher_id']
        if 'is_special' in serializer.validated_data:
            classroom.is_special = serializer.validated_data['is_special']
        classroom.save()
        
        response_serializer = ClassroomSerializer(classroom)
        return Response(response_serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def classroom_delete(request, id):
    """API xóa lớp học"""
    classroom = get_object_or_404(Classroom, id=id)
    
    # Kiểm tra xem lớp có học sinh không (tạm thời bỏ qua vì chưa có model Student)
    # if classroom.students.exists():
    #     return Response(
    #         {'error': 'Không thể xóa lớp học đang có học sinh'},
    #         status=status.HTTP_400_BAD_REQUEST
    #     )
    
    classroom.delete()
    return Response(
        {'message': 'Xóa lớp học thành công'},
        status=status.HTTP_204_NO_CONTENT
    )


# Grades endpoint removed: Frontend uses static grades 10,11,12 in Mongo flow


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_teachers(request):
    """API lấy danh sách giáo viên"""
    from .serializers import TeacherSerializer
    teachers = User.objects.filter(role='teacher').order_by('first_name', 'last_name')
    serializer = TeacherSerializer(teachers, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_classroom_stats(request):
    """API lấy thống kê lớp học"""
    total_classrooms = Classroom.objects.count()
    special_classrooms = Classroom.objects.filter(is_special=True).count()
    regular_classrooms = total_classrooms - special_classrooms
    classrooms_with_teacher = Classroom.objects.filter(homeroom_teacher__isnull=False).count()
    classrooms_without_teacher = total_classrooms - classrooms_with_teacher
    
    stats = {
        'total_classrooms': total_classrooms,
        'special_classrooms': special_classrooms,
        'regular_classrooms': regular_classrooms,
        'classrooms_with_teacher': classrooms_with_teacher,
        'classrooms_without_teacher': classrooms_without_teacher,
    }
    
    return Response(stats) 


# ===================== Mongo endpoints (parallel during migration) =====================

def _mongo_classrooms_coll():
    coll_name = 'classrooms'
    return get_mongo_collection(coll_name)


def _mongo_teachers_coll():
    return get_mongo_collection('teachers')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_classrooms_dropdown(request):
    """API dropdown cho classrooms - chỉ trả về id và name"""
    try:
        coll = _mongo_classrooms_coll()
        
        # Chỉ lấy id và full_name để giảm payload
        docs = list(coll.find(
            {},
            {'id': 1, 'full_name': 1, 'name': 1, 'homeroom_teacher_id': 1}
        ).sort('name', 1))
        
        out = []
        for d in docs:
            t = to_plain(d)
            out.append({
                'id': t.get('id', ''),
                'name': t.get('name', ''),
                'full_name': t.get('full_name', ''),
                'homeroom_teacher_id': t.get('homeroom_teacher_id', ''),
            })
        
        return ok(out)
        
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_classrooms_dropdown error')
        return server_error(exc)


@api_view(['GET'])
@permission_classes([AllowAny])  # Explicitly allow any user
def mongo_classrooms_dropdown_public(request):
    """Public API dropdown cho classrooms - không cần authentication"""
    try:
        coll = _mongo_classrooms_coll()
        
        # Chỉ lấy id và full_name để giảm payload
        docs = list(coll.find({}, {'id': 1, 'full_name': 1, 'name': 1}).sort('name', 1))
        
        out = []
        for d in docs:
            t = to_plain(d)
            out.append({
                'id': t.get('id', ''),
                'name': t.get('name', ''),
                'full_name': t.get('full_name', '')
            })
        
        return Response(out, status=status.HTTP_200_OK)
        
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_classrooms_dropdown_public error')
        return server_error(exc)


def _build_teacher_public_obj(tdoc: dict):
    t = to_plain(tdoc)
    # Với unified users collection, tất cả fields đều ở top level
    first_name = t.get('first_name') or ''
    last_name = t.get('last_name') or ''
    full_name = t.get('full_name') or ''
    if (not first_name and not last_name) and full_name:
        parts = str(full_name).strip().split(' ')
        if len(parts) >= 2:
            first_name = ' '.join(parts[:-1])
            last_name = parts[-1]
        else:
            first_name = full_name
    return {
        'id': t.get('id') or '',
        'first_name': first_name,
        'last_name': last_name,
        'full_name': full_name or f"{first_name} {last_name}".strip(),
        'email': t.get('email') or '',
    }


def _normalize_classroom_doc(doc: dict):
    d = to_plain(doc)
    # Ensure required denormalized fields
    d['full_name'] = d.get('full_name') or d.get('name', '')
    # homeroom teacher: store as string id in DB, normalize to object for FE
    ht = d.get('homeroom_teacher')
    if ht and isinstance(ht, dict):
        pass
    else:
        ht_id = d.get('homeroom_teacher_id')
        ht_name = d.get('homeroom_teacher_name')
        if ht_id or ht_name:
            d['homeroom_teacher'] = {'id': ht_id, 'first_name': '', 'last_name': ht_name or '', 'email': ''}
    # counts and timestamps
    d['student_count'] = d.get('student_count', 0)
    if 'created_at' not in d:
        d['created_at'] = datetime.utcnow().isoformat()
    if 'updated_at' not in d:
        d['updated_at'] = d['created_at']
    return d


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_classrooms_list(request):
    try:
        coll = _mongo_classrooms_coll()
        query = {}
        grade_id = request.query_params.get('grade') or request.query_params.get('grade_id')
        search = request.query_params.get('search')

        if grade_id and grade_id != 'all':
            # Support both new (string) and legacy (object) stored grades
            query['$or'] = [{'grade': grade_id}, {'grade.name': grade_id}, {'grade.id': grade_id}]
        if search:
            # simple case-insensitive search on full_name
            query['full_name'] = {'$regex': search, '$options': 'i'}

        # Sort by full_name to avoid mixed-type sort errors on grade
        page = max(1, int(request.query_params.get('page', '1')))
        page_size = max(1, min(200, int(request.query_params.get('page_size', '20'))))
        skip = (page - 1) * page_size
        total = _mongo_classrooms_coll().count_documents(query)
        pipeline = [
            {'$match': query},
            {
                '$lookup': {
                    'from': 'users',
                    'let': { 'hid': '$homeroom_teacher_id' },
                    'pipeline': [
                        { '$match': { '$expr': { '$and': [
                            { '$eq': ['$_id', { '$toObjectId': '$$hid' }] },
                            { '$eq': ['$role', 'teacher'] }
                        ] } } }
                    ],
                    'as': 'teacher_docs'
                }
            },
            { '$sort': { 'full_name': 1 } },
            { '$skip': skip },
            { '$limit': page_size }
        ]
        docs = list(coll.aggregate(pipeline))

        out = []
        for d in docs:
            nd = _normalize_classroom_doc(d)
            tdocs = d.get('teacher_docs') or []
            if tdocs:
                nd['homeroom_teacher'] = _build_teacher_public_obj(tdocs[0])
            out.append(nd)
        return Response({
            'results': out,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
        })
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_classrooms_list error')
        return server_error(exc)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_classrooms_detail(request, id: str):
    try:
        coll = _mongo_classrooms_coll()
        query = [{'id': id}]
        # Try to interpret as ObjectId if valid hex
        try:
            query.append({'_id': ObjectId(id)})
        except Exception:
            pass
        doc = coll.find_one({'$or': query})
        if not doc:
            return not_found('Not found')
        out = _normalize_classroom_doc(doc)
        # attach teacher info if possible
        hid = out.get('homeroom_teacher', {}).get('id') or out.get('homeroom_teacher_id')
        if hid:
            users_coll = get_mongo_collection('users')
            tdoc = users_coll.find_one({'$or': [{'id': hid}, {'_id': ObjectId(hid)}], 'role': 'teacher'})
            if tdoc:
                out['homeroom_teacher'] = _build_teacher_public_obj(tdoc)
        return Response(out)
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_classrooms_detail error')
        return server_error(exc)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mongo_classrooms_create(request):
    try:
        coll = _mongo_classrooms_coll()
        name = (request.data.get('name') or '').strip()
        grade = (request.data.get('grade') or '').strip()
        homeroom_teacher_id = request.data.get('homeroom_teacher_id')
        if not name or not grade:
            return bad_request('name and grade are required')
        # build full_name like 10A1 if name is A1
        full_name = name if grade in name else f"{grade}{name}"
        now = datetime.utcnow().isoformat()
        doc = {
            'name': name,
            'full_name': full_name,
            'grade': grade,
            'homeroom_teacher_id': homeroom_teacher_id if homeroom_teacher_id else None,
            'student_count': 0,
            'created_at': now,
            'updated_at': now,
        }
        res = coll.insert_one(doc)
        inserted = coll.find_one({'_id': res.inserted_id})
        return Response(_normalize_classroom_doc(inserted), status=status.HTTP_201_CREATED)
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_classrooms_create error')
        return server_error(exc)


@api_view(['PATCH', 'PUT'])
@permission_classes([IsAuthenticated])
def mongo_classrooms_update(request, id: str):
    try:
        coll = _mongo_classrooms_coll()
        
        # Lấy classroom document trước
        query = [{ 'id': id }]
        try:
            query.append({'_id': ObjectId(id)})
        except Exception:
            pass
        doc = coll.find_one({'$or': query})
        if not doc:
            return not_found('Not found')
        
        updates = {}
        if 'name' in request.data:
            updates['name'] = (request.data.get('name') or '').strip()
        if 'grade' in request.data:
            updates['grade'] = (request.data.get('grade') or '').strip()
        if 'homeroom_teacher_id' in request.data:
            htid = request.data.get('homeroom_teacher_id')
            updates['homeroom_teacher_id'] = htid if htid else None
            
            # Cập nhật teacher record với thông tin lớp
            if htid:
                # Cập nhật teacher với thông tin lớp mới
                teacher_coll = get_mongo_collection('users')
                teacher_coll.update_one(
                    {'_id': ObjectId(htid), 'role': 'teacher'},
                    {'$set': {
                        'homeroom_class': doc.get('full_name', ''),
                        'homeroom_class_id': str(doc['_id']),
                        'updated_at': datetime.utcnow().isoformat()
                    }}
                )
            else:
                # Xóa thông tin lớp khỏi teacher cũ (nếu có)
                old_teacher_id = doc.get('homeroom_teacher_id')
                if old_teacher_id:
                    teacher_coll = get_mongo_collection('users')
                    teacher_coll.update_one(
                        {'_id': ObjectId(old_teacher_id), 'role': 'teacher'},
                        {'$unset': {
                            'homeroom_class': '',
                            'homeroom_class_id': ''
                        }, '$set': {
                            'updated_at': datetime.utcnow().isoformat()
                        }}
                    )
        if updates:
            updates['updated_at'] = datetime.utcnow().isoformat()
        # recompute full_name if name/grade changed
        new_name = updates.get('name', doc.get('name'))
        new_grade = updates.get('grade', doc.get('grade'))
        if 'name' in updates or 'grade' in updates:
            updates['full_name'] = new_name if str(new_grade) in str(new_name) else f"{new_grade}{new_name}"
        coll.update_one({'_id': doc['_id']}, {'$set': updates})
        updated = coll.find_one({'_id': doc['_id']})
        return Response(_normalize_classroom_doc(updated))
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_classrooms_update error')
        return server_error(exc)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def mongo_classrooms_delete(request, id: str):
    try:
        coll = _mongo_classrooms_coll()
        query = [{ 'id': id }]
        try:
            query.append({'_id': ObjectId(id)})
        except Exception:
            pass
        doc = coll.find_one({'$or': query})
        if not doc:
            return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        coll.delete_one({'_id': doc['_id']})
        return Response({'message': 'Deleted'}, status=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_classrooms_delete error')
        return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)