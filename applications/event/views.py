from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum, Count
from django.db import transaction
from datetime import datetime, timedelta
import uuid

from .models import Event, EventType, StudentEventPermission
from .serializers import (
    EventCreateRequestSerializer, EventUpdateRequestSerializer, EventResponseSerializer,
    EventTypeResponseSerializer, EventBulkCreateRequestSerializer, EventBulkCreateResponseSerializer,
    EventBulkSyncRequestSerializer, EventBulkSyncResponseSerializer, EventBulkApprovalRequestSerializer,
    StudentEventPermissionCreateSerializer, StudentEventPermissionUpdateSerializer, 
    StudentEventPermissionResponseSerializer
)
from applications.permissions import IsAdminOrTeacher
from applications.common.mongo import get_mongo_collection
from django.conf import settings
import logging
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def events_bulk_approve(request):
    """Approve (or reject) events in bulk by scope (classroom/date/period) or explicit ids."""
    user = request.user
    serializer = EventBulkApprovalRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    event_ids = serializer.validated_data.get('event_ids')
    rejection_notes = serializer.validated_data.get('rejection_notes')
    classroom = serializer.validated_data.get('classroom')
    date = serializer.validated_data.get('date')
    period = serializer.validated_data.get('period')

    qs = Event.objects.all()
    if event_ids:
        qs = qs.filter(id__in=event_ids)
    else:
        if classroom:
            qs = qs.filter(classroom=classroom)
        if date:
            qs = qs.filter(date=date)
        if period is not None:
            qs = qs.filter(period=period)

    # Only homeroom teacher of the classroom(s) or admin can approve
    if getattr(user, 'role', None) == 'teacher':
        qs = qs.filter(classroom__homeroom_teacher=user)

    approve = rejection_notes is None or rejection_notes == ''
    updated = 0
    with transaction.atomic():
        for ev in qs:
            if approve:
                ev.status = 'approved'
                ev.approved_by = user
                ev.approved_at = datetime.now()
                ev.rejection_notes = None
            else:
                ev.status = 'rejected'
                ev.approved_by = user
                ev.approved_at = datetime.now()
                ev.rejection_notes = rejection_notes
            ev.save(update_fields=['status', 'approved_by', 'approved_at', 'rejection_notes', 'updated_at'])
            updated += 1

    return Response({ 'message': 'Updated', 'updated_count': updated })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def events_pending(request):
    """List pending events scoped to homeroom teacher (or all for admin)."""
    user = request.user
    qs = Event.objects.select_related('event_type', 'classroom', 'student__user', 'recorded_by').filter(status='pending')
    if getattr(user, 'role', None) == 'teacher':
        qs = qs.filter(classroom__homeroom_teacher=user)
    classroom_id = request.query_params.get('classroom_id')
    date = request.query_params.get('date')
    period = request.query_params.get('period')
    if classroom_id:
        qs = qs.filter(classroom_id=classroom_id)
    if date:
        qs = qs.filter(date=date)
    if period is not None:
        try:
            qs = qs.filter(period=int(period))
        except Exception:
            pass
    qs = qs.order_by('date', 'classroom__grade__name', 'classroom__name', 'period', 'created_at')
    return Response(EventResponseSerializer(qs, many=True).data)


# Event Type Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def event_type_list(request):
    """Danh sách loại sự kiện"""
    user_role = request.user.role
    
    # Lọc theo vai trò
    if user_role == 'student':
        # Học sinh chỉ thấy loại sự kiện được phép tạo
        event_types = EventType.objects.filter(
            is_active=True,
            allowed_roles__in=['student', 'both']
        )
    elif user_role in ['teacher', 'admin']:
        # Giáo viên và admin thấy tất cả
        event_types = EventType.objects.filter(is_active=True)
    else:
        event_types = EventType.objects.filter(is_active=True)
    
    serializer = EventTypeResponseSerializer(event_types, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def event_type_create(request):
    """Tạo loại sự kiện mới"""
    serializer = EventTypeResponseSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def event_type_detail(request, pk):
    """Chi tiết loại sự kiện"""
    try:
        event_type = EventType.objects.get(pk=pk)
        serializer = EventTypeResponseSerializer(event_type)
        return Response(serializer.data)
    except EventType.DoesNotExist:
        return Response({'error': 'Loại sự kiện không tồn tại'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def event_type_update(request, pk):
    """Cập nhật loại sự kiện"""
    try:
        event_type = EventType.objects.get(pk=pk)
        serializer = EventTypeResponseSerializer(event_type, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except EventType.DoesNotExist:
        return Response({'error': 'Loại sự kiện không tồn tại'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def event_type_delete(request, pk):
    """Xóa loại sự kiện"""
    try:
        event_type = EventType.objects.get(pk=pk)
        event_type.delete()
        return Response({'message': 'Xóa loại sự kiện thành công'})
    except EventType.DoesNotExist:
        return Response({'error': 'Loại sự kiện không tồn tại'}, status=status.HTTP_404_NOT_FOUND)


# Event Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def event_list(request):
    """Danh sách sự kiện"""
    events = Event.objects.select_related(
        'event_type', 'classroom', 'student__user', 'recorded_by'
    ).all()

    # Note: This MySQL API is deprecated, use MongoDB API instead
    # MongoDB API handles role-based filtering automatically
    
    # Filter theo các tham số
    classroom_id = request.query_params.get('classroom_id', None)
    if classroom_id:
        try:
            uuid.UUID(str(classroom_id))
            events = events.filter(classroom_id=classroom_id)
        except Exception:
            return Response({'error': 'classroom_id must be UUID'}, status=status.HTTP_400_BAD_REQUEST)
    
    event_type_id = request.query_params.get('event_type_id', None)
    if event_type_id:
        try:
            uuid.UUID(str(event_type_id))
            events = events.filter(event_type_id=event_type_id)
        except Exception:
            return Response({'error': 'event_type_id must be UUID'}, status=status.HTTP_400_BAD_REQUEST)
    
    student_id = request.query_params.get('student_id', None)
    if student_id:
        try:
            uuid.UUID(str(student_id))
            events = events.filter(student_id=student_id)
        except Exception:
            return Response({'error': 'student_id must be UUID'}, status=status.HTTP_400_BAD_REQUEST)
    
    date = request.query_params.get('date', None)
    if date:
        events = events.filter(date=date)
    
    start_date = request.query_params.get('start_date', None)
    if start_date:
        events = events.filter(date__gte=start_date)
    
    end_date = request.query_params.get('end_date', None)
    if end_date:
        events = events.filter(date__lte=end_date)

    # Status filter (pending/approved/rejected)
    status_param = request.query_params.get('status', None)
    if status_param in ['pending', 'approved', 'rejected']:
        events = events.filter(status=status_param)
    
    # Default ordering to keep list stable across requests
    # Order by date, classroom name, period, and student name
    # Sort primarily by lesson period and then creation time to preserve input order
    events = events.order_by(
        'date',
        'classroom__grade__name',
        'classroom__name',
        'period',
        'created_at'
    )

    serializer = EventResponseSerializer(events, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def event_create(request):
    """Tạo sự kiện mới"""
    user = request.user
    serializer = EventCreateRequestSerializer(data=request.data)
    
    if serializer.is_valid():
        # Kiểm tra quyền tạo sự kiện
        if user.role == 'student':
            # Học sinh chỉ có thể tạo sự kiện cho chính mình
            student_id = serializer.validated_data.get('student')
            if not student_id:
                return Response(
                    {'error': 'Học sinh phải chỉ định học sinh cụ thể'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Kiểm tra xem học sinh có quyền tạo sự kiện không
            try:
                from applications.student.models import Student
                student = Student.objects.get(user=user)
                if student.id != student_id.id:
                    return Response(
                        {'error': 'Bạn chỉ có thể tạo sự kiện cho chính mình'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Kiểm tra quyền tạo sự kiện
                permission = StudentEventPermission.objects.filter(
                    student=student,
                    classroom=serializer.validated_data['classroom'],
                    is_active=True
                ).first()
                
                if not permission or not permission.is_valid:
                    return Response(
                        {'error': 'Bạn không có quyền tạo sự kiện trong lớp này'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Student.DoesNotExist:
                return Response(
                    {'error': 'Không tìm thấy thông tin học sinh'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Students create as pending; teachers/admins approved
        status_value = 'pending' if user.role == 'student' else 'approved'
        event = serializer.save(recorded_by=user, status=status_value,
                                approved_by=user if status_value == 'approved' else None,
                                approved_at=datetime.now() if status_value == 'approved' else None)
        response_serializer = EventResponseSerializer(event)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def events_bulk_sync(request):
    """Bulk sync events: update existing, create new, delete removed within scopes.
    Scope is defined by (classroom, date, period). Input is the desired list of events.
    """
    user = request.user
    serializer = EventBulkSyncRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    desired_events = serializer.validated_data['events']
    scope_override = (
        str(serializer.validated_data['classroom'].id) if serializer.validated_data.get('classroom') else None,
        serializer.validated_data.get('date'),
        serializer.validated_data.get('period') if 'period' in serializer.validated_data else None,
    )

    # Collect scopes from desired input
    scopes = set()
    # Helpers to normalize primary keys from instance/UUID/string
    def pk_of(value):
        if value is None:
            return None
        if hasattr(value, 'id'):
            return getattr(value, 'id')
        if hasattr(value, 'pk'):
            return getattr(value, 'pk')
        return value  # already pk/UUID/str
    for ev in desired_events:
        scopes.add((str(pk_of(ev['classroom'])), ev['date'], ev.get('period')))
    # If scope override provided but no events (to delete all), include it
    if scope_override[0] and scope_override[1] is not None:
        scopes.add(scope_override)

    # Also include scopes that might exist already even if empty in desired
    # (frontend can send empty desired for a period to delete all)
    # No extra collection here; assume client covers scopes they want to manage.

    created_count = 0
    updated_count = 0
    deleted_count = 0

    # Helpers to normalize primary keys from instance/UUID/string (defined above)

    # Organize desired by key for diff
    def key_for_desired(ev):
        et = pk_of(ev['event_type'])
        st = pk_of(ev.get('student')) if ev.get('student') else ''
        pr = ev.get('period') or ''
        return f"{str(et)}:{str(st)}:{pr}"

    desired_by_scope = {}
    for ev in desired_events:
        scope = (str(pk_of(ev['classroom'])), ev['date'], ev.get('period'))
        scope = (str(pk_of(ev['classroom'])), ev['date'], ev.get('period'))
        arr = desired_by_scope.get(scope, [])
        arr.append(ev)
        desired_by_scope[scope] = arr
    # Ensure empty list for scope override if provided (to delete all)
    if scope_override[0] and scope_override in scopes and scope_override not in desired_by_scope:
        desired_by_scope[scope_override] = []

    from applications.classroom.models import Classroom
    with transaction.atomic():
        for scope in scopes:
            classroom_id, date, period = scope
            # Teacher can only sync for their homeroom class
            if getattr(user, 'role', None) == 'teacher':
                try:
                    cls = Classroom.objects.get(pk=classroom_id)
                except Classroom.DoesNotExist:
                    return Response({'error': 'Lớp không tồn tại'}, status=status.HTTP_400_BAD_REQUEST)
                if cls.homeroom_teacher_id != user.id:
                    return Response({'error': 'Bạn chỉ có thể thao tác lớp chủ nhiệm của mình'}, status=status.HTTP_403_FORBIDDEN)
            existing_qs = Event.objects.select_related('event_type', 'student__user').filter(
                classroom_id=str(classroom_id),
                date=date,
                period=period
            ).order_by('created_at')

            existing_list = list(existing_qs)

            # Build maps by key
            def key_for_existing(e: Event):
                return f"{str(e.event_type_id)}:{str(e.student_id) if e.student_id else ''}:{e.period or ''}"

            existing_map = {}
            for e in existing_list:
                k = key_for_existing(e)
                existing_map.setdefault(k, []).append(e)

            desired_list = desired_by_scope.get(scope, [])
            desired_map = {}
            for ev in desired_list:
                k = key_for_desired(ev)
                desired_map.setdefault(k, []).append(ev)

            # Update overlaps
            for k, d_list in desired_map.items():
                e_list = existing_map.get(k, [])
                count_to_update = min(len(e_list), len(d_list))
                for i in range(count_to_update):
                    ex = e_list[i]
                    de = d_list[i]
                    # Update mutable fields
                    ex.points = de['points']
                    ex.description = de.get('description')
                    # Student updates should reset to pending
                    if getattr(user, 'role', None) == 'student':
                        ex.status = 'pending'
                        ex.approved_by = None
                        ex.approved_at = None
                        ex.rejection_notes = None
                    ex.save(update_fields=['points', 'description', 'updated_at'])
                    updated_count += 1

            # Create extras
            for k, d_list in desired_map.items():
                e_count = len(existing_map.get(k, []))
                for i in range(e_count, len(d_list)):
                    de = d_list[i]
                    new_event = Event.objects.create(
                        event_type_id=str(pk_of(de['event_type'])),
                        classroom_id=str(pk_of(de['classroom'])),
                        student_id=str(pk_of(de.get('student'))) if de.get('student') else None,
                        date=de['date'],
                        period=de.get('period'),
                        points=de['points'],
                        description=de.get('description'),
                        recorded_by=user,
                    )
                    # Set status per role
                    if getattr(user, 'role', None) == 'student':
                        new_event.status = 'pending'
                        new_event.save(update_fields=['status', 'updated_at'])
                    else:
                        new_event.status = 'approved'
                        new_event.approved_by = user
                        new_event.approved_at = datetime.now()
                        new_event.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
                    created_count += 1

            # Delete extras
            for k, e_list in existing_map.items():
                d_count = len(desired_map.get(k, []))
                for i in range(d_count, len(e_list)):
                    e_list[i].delete()
                    deleted_count += 1

    # Return all events for input scopes after sync
    all_events = Event.objects.select_related('event_type', 'classroom', 'student__user', 'recorded_by')
    if scopes:
        class_ids = list({cid for cid, _, _ in scopes})
        dates = list({dt for _, dt, _ in scopes})
        all_events = all_events.filter(classroom_id__in=class_ids, date__in=dates)
    serializer_resp = EventResponseSerializer(all_events, many=True)
    return Response({
        'message': 'Synced successfully',
        'created_count': created_count,
        'updated_count': updated_count,
        'deleted_count': deleted_count,
        'events': serializer_resp.data
    })
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def event_detail(request, pk):
    """Chi tiết sự kiện"""
    try:
        event = Event.objects.select_related(
            'event_type', 'classroom', 'student__user', 'recorded_by'
        ).get(pk=pk)
        serializer = EventResponseSerializer(event)
        return Response(serializer.data)
    except Event.DoesNotExist:
        return Response({'error': 'Sự kiện không tồn tại'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def event_update(request, pk):
    """Cập nhật sự kiện"""
    try:
        event = Event.objects.get(pk=pk)
        user = request.user
        # Permission rules:
        # - Admin: allowed
        # - Teacher: only if homeroom teacher of the event's classroom
        # - Student: only if they created the event (recorded_by)
        if getattr(user, 'role', None) == 'teacher':
            if event.classroom.homeroom_teacher_id != user.id:
                return Response({'error': 'Bạn không có quyền cập nhật sự kiện này'}, status=status.HTTP_403_FORBIDDEN)
        elif getattr(user, 'role', None) == 'student':
            if event.recorded_by_id != user.id:
                return Response({'error': 'Bạn chỉ có thể cập nhật sự kiện do bạn tạo'}, status=status.HTTP_403_FORBIDDEN)
        elif getattr(user, 'role', None) != 'admin':
            return Response({'error': 'Không có quyền'}, status=status.HTTP_403_FORBIDDEN)

        serializer = EventUpdateRequestSerializer(event, data=request.data, partial=True)
        if serializer.is_valid():
            updated_event = serializer.save()
            # If student updates, reset to pending
            if getattr(user, 'role', None) == 'student':
                updated_event.status = 'pending'
                updated_event.approved_by = None
                updated_event.approved_at = None
                updated_event.rejection_notes = None
                updated_event.save(update_fields=['status', 'approved_by', 'approved_at', 'rejection_notes', 'updated_at'])
            response_serializer = EventResponseSerializer(event)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Event.DoesNotExist:
        return Response({'error': 'Sự kiện không tồn tại'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def event_delete(request, pk):
    """Xóa sự kiện"""
    try:
        event = Event.objects.get(pk=pk)
        event.delete()
        return Response({'message': 'Xóa sự kiện thành công'})
    except Event.DoesNotExist:
        return Response({'error': 'Sự kiện không tồn tại'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def event_bulk_create(request):
    """Tạo nhiều events cùng lúc (Admin/Teacher only)"""
    serializer = EventBulkCreateRequestSerializer(data=request.data)
    if serializer.is_valid():
        events_data = serializer.validated_data['events']
        created_events = []
        
        for event_data in events_data:
            event_data['recorded_by'] = request.user
            event = Event.objects.create(**event_data)
            created_events.append(event)
        
        response_data = {
            'message': f'Đã tạo {len(created_events)} events thành công',
            'created_count': len(created_events),
            'events': EventResponseSerializer(created_events, many=True).data
        }
        
        response_serializer = EventBulkCreateResponseSerializer(data=response_data)
        response_serializer.is_valid()
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def event_bulk_create_student(request):
    """Tạo nhiều events cùng lúc (dành cho học sinh) - Tối ưu hóa cho 7 tiết học"""
    try:
        from applications.common.mongo import get_mongo_collection, to_plain
        from bson import ObjectId
        from datetime import datetime
        
        user = request.user
        events_data = request.data.get('events', [])
        
        if not events_data:
            return Response({'error': 'Không có sự kiện nào để tạo'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Lấy thông tin học sinh (không cần kiểm tra quyền)
        if user.role == 'student':
            students_coll = get_mongo_collection('students')
            student_doc = students_coll.find_one({'user.id': str(user.id)})
            
            if not student_doc:
                return Response({'error': 'Không tìm thấy thông tin học sinh'}, status=status.HTTP_404_NOT_FOUND)
            
            student_classroom_id = student_doc.get('classroom', {}).get('id')
            if not student_classroom_id:
                return Response({'error': 'Học sinh chưa được phân lớp'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Tối ưu hóa: Nhóm events theo ngày và lớp để lưu trữ hiệu quả
        events_by_date_class = {}
        
        # Tự động lấy lớp của học sinh nếu là student
        if user.role == 'student':
            student_classroom_id = student_doc.get('classroom', {}).get('id')
            if not student_classroom_id:
                return Response({'error': 'Học sinh chưa được phân lớp'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            student_classroom_id = None
        
        for event_data in events_data:
            if not event_data.get('event_type'):
                continue
                
            date = event_data.get('date')
            # Tự động sử dụng lớp của học sinh nếu là student
            classroom_id = student_classroom_id if user.role == 'student' else event_data.get('classroom')
            period = event_data.get('period')
            
            if not date or not classroom_id or not period:
                continue
            
            key = f"{date}_{classroom_id}"
            if key not in events_by_date_class:
                events_by_date_class[key] = {
                    'date': date,
                    'classroom_id': classroom_id,
                    'periods': {}
                }
            
            if period not in events_by_date_class[key]['periods']:
                events_by_date_class[key]['periods'][period] = []
            
            events_by_date_class[key]['periods'][period].append({
                'event_type_id': event_data.get('event_type'),
                'student_id': event_data.get('student'),
                'points': event_data.get('points', 0),
                'description': event_data.get('description', ''),
                'recorded_by_id': str(user.id),
                'recorded_by_name': user.full_name or f"{user.first_name} {user.last_name}".strip(),
                'created_at': datetime.now().isoformat(),
            })
        
        # Lưu trữ vào MongoDB với cấu trúc tối ưu
        events_coll = get_mongo_collection('events')
        created_events = []
        
        for key, day_data in events_by_date_class.items():
            # Tạo document cho mỗi ngày-lớp
            day_doc = {
                'date': day_data['date'],
                'classroom_id': day_data['classroom_id'],
                'periods': day_data['periods'],
                'total_events': sum(len(period_events) for period_events in day_data['periods'].values()),
                'created_by': str(user.id),
                'created_by_name': user.full_name or f"{user.first_name} {user.last_name}".strip(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            }
            
            # Kiểm tra xem đã có document cho ngày-lớp này chưa
            existing = events_coll.find_one({
                'date': day_data['date'],
                'classroom_id': day_data['classroom_id']
            })
            
            if existing:
                # Cập nhật document hiện có
                events_coll.update_one(
                    {'_id': existing['_id']},
                    {
                        '$set': {
                            'periods': day_data['periods'],
                            'total_events': day_data['total_events'],
                            'updated_at': datetime.now().isoformat(),
                        }
                    }
                )
                day_doc['_id'] = existing['_id']
            else:
                # Tạo document mới
                result = events_coll.insert_one(day_doc)
                day_doc['_id'] = result.inserted_id
            
            created_events.append(to_plain(day_doc))
        
        return Response({
            'message': f'Đã tạo/cập nhật {len(created_events)} ngày sự kiện',
            'created_count': len(created_events),
            'events': created_events
        }, status=status.HTTP_201_CREATED)
        
    except Exception as exc:
        logging.getLogger(__name__).exception('event_bulk_create_student error')
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_events_optimized_list(request):
    """Lấy danh sách events tối ưu hóa cho 7 tiết học mỗi ngày"""
    try:
        from applications.common.mongo import get_mongo_collection, to_plain
        from bson import ObjectId
        
        classroom_id = request.query_params.get('classroom_id')
        date = request.query_params.get('date')
        
        coll = get_mongo_collection('events')
        query = {}
        
        if classroom_id:
            query['classroom_id'] = classroom_id
        if date:
            query['date'] = date
        
        docs = list(coll.find(query).sort('date', -1))
        out = []
        for d in docs:
            t = to_plain(d)
            t['created_at'] = t.get('created_at') or ''
            t['updated_at'] = t.get('updated_at') or t['created_at']
            
            # Flatten events từ periods để tương thích với frontend
            flattened_events = []
            periods = t.get('periods', {})
            for period_num, period_events in periods.items():
                for event in period_events:
                    flattened_events.append({
                        'id': f"{t['id']}_{period_num}_{len(flattened_events)}",
                        'event_type': event.get('event_type_id'),
                        'student': event.get('student_id'),
                        'date': t['date'],
                        'period': int(period_num),
                        'points': event.get('points', 0),
                        'description': event.get('description', ''),
                        'recorded_by': event.get('recorded_by_id'),
                        'created_at': event.get('created_at', t['created_at']),
                        'updated_at': event.get('created_at', t['updated_at']),
                    })
            
            t['events'] = flattened_events
            out.append(t)
        
        return Response(out)
        
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_events_optimized_list error')
        return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Student Event Permission Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_event_permissions_list(request):
    """Danh sách quyền tạo sự kiện của học sinh"""
    user = request.user
    
    # Lọc theo quyền của user
    if user.role == 'admin':
        permissions = StudentEventPermission.objects.all()
    elif user.role == 'teacher':
        # Giáo viên chỉ xem quyền của học sinh trong lớp họ chủ nhiệm
        permissions = StudentEventPermission.objects.filter(
            classroom__homeroom_teacher=user
        )
    else:
        return Response(
            {'error': 'Không có quyền truy cập'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Lọc theo classroom nếu có
    classroom_id = request.query_params.get('classroom_id')
    if classroom_id:
        permissions = permissions.filter(classroom_id=classroom_id)
    
    # Lọc theo trạng thái
    is_active = request.query_params.get('is_active')
    if is_active is not None:
        permissions = permissions.filter(is_active=is_active.lower() == 'true')
    
    permissions = permissions.select_related(
        'student', 'student__user', 'classroom', 'granted_by'
    ).order_by('-granted_at')
    
    serializer = StudentEventPermissionResponseSerializer(permissions, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAdminOrTeacher])
def student_event_permission_create(request):
    """Cấp quyền tạo sự kiện cho học sinh"""
    serializer = StudentEventPermissionCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        # Kiểm tra quyền của giáo viên
        user = request.user
        classroom = serializer.validated_data['classroom']
        
        if user.role == 'teacher' and classroom.homeroom_teacher != user:
            return Response(
                {'error': 'Bạn không phải giáo viên chủ nhiệm của lớp này'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Kiểm tra xem học sinh đã có quyền chưa
        existing_permission = StudentEventPermission.objects.filter(
            student=serializer.validated_data['student'],
            classroom=classroom
        ).first()
        
        if existing_permission:
            return Response(
                {'error': 'Học sinh này đã có quyền tạo sự kiện trong lớp'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Tạo quyền mới
        permission = serializer.save(granted_by=user)
        response_serializer = StudentEventPermissionResponseSerializer(permission)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminOrTeacher])
def student_event_permission_update(request, pk):
    """Cập nhật quyền tạo sự kiện của học sinh"""
    try:
        permission = StudentEventPermission.objects.get(pk=pk)
    except StudentEventPermission.DoesNotExist:
        return Response(
            {'error': 'Quyền không tồn tại'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Kiểm tra quyền của giáo viên
    user = request.user
    if user.role == 'teacher' and permission.classroom.homeroom_teacher != user:
        return Response(
            {'error': 'Bạn không có quyền cập nhật quyền này'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = StudentEventPermissionUpdateSerializer(
        permission, 
        data=request.data, 
        partial=request.method == 'PATCH'
    )
    
    if serializer.is_valid():
        serializer.save()
        response_serializer = StudentEventPermissionResponseSerializer(permission)
        return Response(response_serializer.data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAdminOrTeacher])
def student_event_permission_delete(request, pk):
    """Xóa quyền tạo sự kiện của học sinh"""
    try:
        permission = StudentEventPermission.objects.get(pk=pk)
    except StudentEventPermission.DoesNotExist:
        return Response(
            {'error': 'Quyền không tồn tại'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Kiểm tra quyền của giáo viên
    user = request.user
    if user.role == 'teacher' and permission.classroom.homeroom_teacher != user:
        return Response(
            {'error': 'Bạn không có quyền xóa quyền này'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    permission.delete()
    return Response(
        {'message': 'Xóa quyền thành công'},
        status=status.HTTP_204_NO_CONTENT
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_student_event_permission(request, student_id):
    """Kiểm tra quyền tạo sự kiện của học sinh"""
    user = request.user
    
    # Học sinh chỉ có thể kiểm tra quyền của chính mình
    if user.role == 'student':
        try:
            from applications.student.models import Student
            student = Student.objects.get(user=user)
            if student.id != student_id:
                return Response(
                    {'error': 'Không có quyền kiểm tra quyền của học sinh khác'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Student.DoesNotExist:
            return Response(
                {'error': 'Không tìm thấy thông tin học sinh'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Kiểm tra quyền
    try:
        permission = StudentEventPermission.objects.get(
            student_id=student_id,
            is_active=True
        )
        
        if permission.is_valid:
            return Response({
                'has_permission': True,
                'permission': StudentEventPermissionResponseSerializer(permission).data
            })
        else:
            return Response({
                'has_permission': False,
                'reason': 'expired' if permission.is_expired else 'inactive'
            })
    except StudentEventPermission.DoesNotExist:
        return Response({
            'has_permission': False,
            'reason': 'not_granted'
        })


# Event Statistics and Reports for School Management
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def event_statistics(request):
    """Thống kê tổng quan về sự kiện thi đua"""
    # Lấy tham số từ query
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    classroom_id = request.query_params.get('classroom_id')
    
    # Base queryset
    events = Event.objects.select_related('event_type', 'classroom', 'student__user', 'recorded_by')
    
    # Filter by date range
    if start_date:
        events = events.filter(date__gte=start_date)
    if end_date:
        events = events.filter(date__lte=end_date)
    if classroom_id:
        events = events.filter(classroom_id=classroom_id)
    
    # Statistics
    total_events = events.count()
    positive_events = events.filter(points__gt=0).count()
    negative_events = events.filter(points__lt=0).count()
    zero_events = events.filter(points=0).count()
    
    # Total points
    total_points = events.aggregate(total=Sum('points'))['total'] or 0
    
    # Events by classroom
    classroom_stats = events.values('classroom__full_name').annotate(
        count=Count('id'),
        total_points=Sum('points')
    ).order_by('-total_points')
    
    # Events by type
    type_stats = events.values('event_type__name', 'event_type__category').annotate(
        count=Count('id'),
        total_points=Sum('points')
    ).order_by('-count')
    
    # Recent events (last 7 days)
    recent_events = events.filter(
        created_at__gte=datetime.now() - timedelta(days=7)
    ).order_by('-created_at')[:10]
    
    return Response({
        'summary': {
            'total_events': total_events,
            'positive_events': positive_events,
            'negative_events': negative_events,
            'zero_events': zero_events,
            'total_points': total_points
        },
        'by_classroom': list(classroom_stats),
        'by_type': list(type_stats),
        'recent_events': EventResponseSerializer(recent_events, many=True).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrTeacher])
def event_export(request):
    """Xuất danh sách sự kiện ra file Excel"""
    # Lấy tham số từ query
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    classroom_id = request.query_params.get('classroom_id')
    
    # Base queryset
    events = Event.objects.select_related(
        'event_type', 'classroom', 'student__user', 'recorded_by'
    ).order_by('-date', '-created_at')
    
    # Filter by date range
    if start_date:
        events = events.filter(date__gte=start_date)
    if end_date:
        events = events.filter(date__lte=end_date)
    if classroom_id:
        events = events.filter(classroom_id=classroom_id)
    
    # Serialize data
    serializer = EventResponseSerializer(events, many=True)
    
    return Response({
        'events': serializer.data,
        'total_count': events.count(),
        'export_date': datetime.now().isoformat()
    }) 


# --- Mongo-backed events (gradual migration) ---

def _mongo_events_coll():
    coll = getattr(settings, 'MONGO_EVENTS_COLLECTION', None) or 'events'
    return get_mongo_collection(coll)


## Removed flat mongo events endpoints in favor of daily documents


# --- Mongo daily documents (group-by-day storage) ---

def _mongo_event_days_coll():
    coll = getattr(settings, 'MONGO_EVENT_DAYS_COLLECTION', None) or 'event_days'
    return get_mongo_collection(coll)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_event_days_list(request):
    """Trả về dữ liệu đã gom theo ngày: [{ date, classroom_id, events: [...] }]."""
    try:
        coll = _mongo_event_days_coll()
        query = {}
        classroom_id = request.query_params.get('classroom_id')
        date = request.query_params.get('date')
        if classroom_id:
            query['classroom_id'] = classroom_id
        if date:
            query['date'] = date
        docs = list(coll.find(query).sort('date', -1))
        # Chuẩn hóa id
        for d in docs:
            d['id'] = str(d.get('_id'))
            d.pop('_id', None)
        return Response(docs)
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_event_days_list error')
        return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminOrTeacher])
def mongo_event_days_add_event(request):
    """Lưu một event vào tài liệu theo ngày (upsert + push)."""
    try:
        coll = _mongo_event_days_coll()
        payload = request.data or {}
        date = payload.get('date')
        classroom_id = payload.get('classroom')
        if not date or not classroom_id:
            return Response({'detail': 'date và classroom là bắt buộc'}, status=status.HTTP_400_BAD_REQUEST)

        event_item = {
            'event_type': payload.get('event_type'),
            'student': payload.get('student'),
            'period': payload.get('period'),
            'points': payload.get('points'),
            'description': payload.get('description', ''),
            'recorded_by': getattr(request.user, 'id', None),
            'created_at': datetime.now().isoformat(),
        }

        res = coll.update_one(
            {'date': date, 'classroom_id': classroom_id},
            {
                '$setOnInsert': {
                    'date': date,
                    'classroom_id': classroom_id,
                    'created_at': datetime.now().isoformat(),
                },
                '$push': { 'events': event_item },
                '$set': { 'updated_at': datetime.now().isoformat() }
            },
            upsert=True
        )

        doc = coll.find_one({'date': date, 'classroom_id': classroom_id})
        doc_out = { 'id': str(doc.get('_id')), 'date': doc.get('date'), 'classroom_id': doc.get('classroom_id'), 'events': doc.get('events', []) }
        return Response(doc_out, status=status.HTTP_201_CREATED if res.upserted_id else status.HTTP_200_OK)
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_event_days_add_event error')
        return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAdminOrTeacher])
def mongo_event_days_replace(request):
    """Thay thế toàn bộ danh sách events cho (date, classroom). Body: { date, classroom, events: [...] }"""
    try:
        coll = _mongo_event_days_coll()
        payload = request.data or {}
        date = payload.get('date')
        classroom_id = payload.get('classroom')
        events = payload.get('events', [])
        if not date or not classroom_id or not isinstance(events, list):
            return Response({'detail': 'date, classroom, events (array) là bắt buộc'}, status=status.HTTP_400_BAD_REQUEST)

        # Optionally enrich each event
        normalized_events = []
        now_iso = datetime.now().isoformat()
        for e in events:
            normalized_events.append({
                'event_type': e.get('event_type'),
                'student': e.get('student'),
                'period': e.get('period'),
                'points': e.get('points'),
                'description': e.get('description', ''),
                'recorded_by': e.get('recorded_by') or getattr(request.user, 'id', None),
                'created_at': e.get('created_at') or now_iso,
            })

        res = coll.update_one(
            {'date': date, 'classroom_id': classroom_id},
            {
                '$setOnInsert': {
                    'date': date,
                    'classroom_id': classroom_id,
                    'created_at': now_iso,
                },
                '$set': {
                    'events': normalized_events,
                    'updated_at': now_iso,
                },
            },
            upsert=True,
        )

        doc = coll.find_one({'date': date, 'classroom_id': classroom_id})
        doc_out = {
            'id': str(doc.get('_id')),
            'date': doc.get('date'),
            'classroom_id': doc.get('classroom_id'),
            'events': doc.get('events', []),
        }
        status_code = status.HTTP_201_CREATED if res.upserted_id else status.HTTP_200_OK
        return Response(doc_out, status=status_code)
    except Exception as exc:
        logging.getLogger(__name__).exception('mongo_event_days_replace error')
        return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)