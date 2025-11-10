"""
MongoDB-based week summary views - Thay thế MySQL
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timedelta
import logging

from applications.common.mongo import get_mongo_collection, to_plain
from applications.common.responses import ok, created, bad_request, not_found, server_error
from bson import ObjectId
from .week_milestone import WeekMilestoneManager

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_test(request):
    """Test endpoint to verify MongoDB views are working"""
    return Response({'message': 'MongoDB views are working!', 'status': 'ok'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_debug_events(request):
    """Debug endpoint to check events data"""
    try:
        from datetime import datetime
        
        # Get current week
        now = datetime.now()
        iso = now.isocalendar()
        start_dt = datetime.fromisocalendar(iso[0], iso[1], 1)
        end_dt = datetime.fromisocalendar(iso[0], iso[1], 7)
        
        # Get events
        events_coll = get_mongo_collection('events')
        query = {
            'date': {
                '$gte': start_dt.strftime('%Y-%m-%d'),
                '$lte': end_dt.strftime('%Y-%m-%d')
            }
        }
        
        events = list(events_coll.find(query).limit(10))
        
        # Debug info
        debug_info = {
            'date_range': {
                'start': start_dt.strftime('%Y-%m-%d'),
                'end': end_dt.strftime('%Y-%m-%d')
            },
            'query': query,
            'events_count': len(events),
            'events': []
        }
        
        for event in events:
            debug_info['events'].append({
                'id': str(event.get('_id')),
                'date': event.get('date'),
                'classroom_id': event.get('classroom_id'),
                'points': event.get('points'),
                'event_type_key': event.get('event_type_key'),
                'student_id': event.get('student_id')
            })
        
        return Response(debug_info)
        
    except Exception as exc:
        logger.exception('mongo_debug_events error')
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_realtime_rankings(request):
    """Compute rankings in real-time from MongoDB events for a given week/year or date range."""
    try:
        user = request.user
        week_number = request.query_params.get('week_number')
        year = request.query_params.get('year')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        # Resolve date range
        try:
            if week_number and year:
                # Tính tuần từ mốc 6/10/2025
                week = int(week_number)
                milestone_date = datetime(2025, 10, 6)  # Mốc tuần đầu tiên
                start_dt = milestone_date + timedelta(weeks=week-1)
                end_dt = start_dt + timedelta(days=6)
            elif start_date_str and end_date_str:
                start_dt = datetime.fromisoformat(start_date_str)
                end_dt = datetime.fromisoformat(end_date_str)
            else:
                # Sử dụng mốc tuần nếu không có tham số
                week_info = WeekMilestoneManager.get_week_info()
                current_week = week_info['current_week']
                current_year = week_info['current_year']
                start_dt = datetime.fromisocalendar(current_year, current_week, 1)
                end_dt = datetime.fromisocalendar(current_year, current_week, 7)
        except ValueError:
            return Response({'error': 'Invalid date/week parameters'}, status=status.HTTP_400_BAD_REQUEST)

        # Get events from MongoDB
        events_coll = get_mongo_collection('events')
        
        # Build query for events in date range - chỉ lấy events đã được duyệt
        query = {
            'date': {
                '$gte': start_dt.strftime('%Y-%m-%d'),
                '$lte': end_dt.strftime('%Y-%m-%d')
            },
            'approval_status': 'approved'  # Chỉ tính events đã được duyệt
        }
        
        # Role-based filtering - Chỉ admin mới được xem rankings
        if user.role == 'student':
            return Response({'error': 'Học sinh không có quyền xem xếp hạng'}, status=status.HTTP_403_FORBIDDEN)
        elif user.role == 'teacher':
            return Response({'error': 'Giáo viên không có quyền xem xếp hạng'}, status=status.HTTP_403_FORBIDDEN)
        elif user.role != 'admin':
            return Response({'error': 'Chỉ admin mới có quyền xem xếp hạng'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get all events in date range
        events = list(events_coll.find(query))
        
        # Debug logging
        logger.info(f"Query: {query}")
        logger.info(f"Found {len(events)} events")
        logger.info(f"Date range: {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}")
        
        # Aggregate by classroom
        classroom_stats = {}
        
        for event_doc in events:
            classroom_id = event_doc.get('classroom_id')
            periods = event_doc.get('periods', {})
            
            logger.info(f"Processing event doc: classroom_id={classroom_id}, periods={list(periods.keys())}")
            
            if not classroom_id:
                continue
                
            if classroom_id not in classroom_stats:
                classroom_stats[classroom_id] = {
                    'positive_points': 0,
                    'negative_points': 0,
                    'total_points': 0
                }
            
            # Process all periods in this event document
            for period_num, period_events in periods.items():
                logger.info(f"Processing period {period_num} with {len(period_events)} events")
                
                for period_event in period_events:
                    points = period_event.get('points', 0)
                    event_type = period_event.get('event_type_key', '')
                    student_id = period_event.get('student_id')
                    
                    logger.info(f"Period event: {event_type}, student_id={student_id}, points={points}")
                    
                    if points > 0:
                        classroom_stats[classroom_id]['positive_points'] += points
                        logger.info(f"Added positive points: {points}")
                    elif points < 0:
                        classroom_stats[classroom_id]['negative_points'] += abs(points)  # Store as positive number
                        logger.info(f"Added negative points: {abs(points)}")
                    
                    classroom_stats[classroom_id]['total_points'] += points
                    logger.info(f"Total points for {classroom_id}: {classroom_stats[classroom_id]['total_points']}")
        
        # Debug: Log classroom stats
        logger.info(f"Classroom stats: {classroom_stats}")
        
        # Get classroom details
        classrooms_coll = get_mongo_collection('classrooms')
        rankings = []
        
        for classroom_id, stats in classroom_stats.items():
            logger.info(f"Processing classroom {classroom_id}: {stats}")
            try:
                classroom_doc = classrooms_coll.find_one({'_id': ObjectId(classroom_id)})
                if not classroom_doc:
                    continue
                
                # Get homeroom teacher info from users collection
                homeroom_teacher = None
                homeroom_teacher_id = classroom_doc.get('homeroom_teacher_id')
                if homeroom_teacher_id:
                    users_coll = get_mongo_collection('users')
                    teacher_doc = users_coll.find_one({'_id': ObjectId(homeroom_teacher_id), 'role': 'teacher'})
                    if teacher_doc:
                        homeroom_teacher = {
                            'id': str(teacher_doc['_id']),
                            'full_name': teacher_doc.get('full_name', ''),
                            'first_name': teacher_doc.get('first_name', ''),
                            'last_name': teacher_doc.get('last_name', '')
                        }
                
                rankings.append({
                    'id': f"realtime_{classroom_id}",
                    'classroom': {
                        'id': str(classroom_doc['_id']),
                        'full_name': classroom_doc.get('full_name', ''),
                        'homeroom_teacher': homeroom_teacher
                    },
                    'week_number': int(week_number) if week_number else start_dt.isocalendar()[1],
                    'year': int(year) if year else start_dt.year,
                    'positive_points': stats['positive_points'],
                    'negative_points': stats['negative_points'],
                    'total_points': stats['total_points'],
                    'is_approved': True,
                })
            except Exception as e:
                logger.error(f"Error processing classroom {classroom_id}: {e}")
                continue
        
        # Sort by total points descending
        rankings.sort(key=lambda r: r['total_points'], reverse=True)
        
        # Assign ranks
        for idx, ranking in enumerate(rankings):
            ranking['rank'] = idx + 1
        
        return Response(rankings)
        
    except Exception as exc:
        logger.exception('mongo_realtime_rankings error')
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_week_summary_list(request):
    """API lấy danh sách tổng kết tuần từ MongoDB"""
    try:
        user = request.user
        
        # Get week summaries from MongoDB
        week_summaries_coll = get_mongo_collection('week_summaries')
        
        # Build query
        query = {}
        
        # Role-based filtering
        if user.role == 'student':
            # Get student's classroom
            students_coll = get_mongo_collection('students')
            student_doc = students_coll.find_one({'user.id': str(user.id)})
            if not student_doc:
                return Response([])
            
            student_classroom_id = student_doc.get('classroom', {}).get('id')
            if not student_classroom_id:
                return Response([])
            
            query['classroom_id'] = student_classroom_id
        elif user.role == 'teacher':
            # Get classrooms where user is homeroom teacher
            classrooms_coll = get_mongo_collection('classrooms')
            teacher_classrooms = classrooms_coll.find({'homeroom_teacher.id': str(user.id)})
            classroom_ids = [str(doc['_id']) for doc in teacher_classrooms]
            if classroom_ids:
                query['classroom_id'] = {'$in': classroom_ids}
            else:
                return Response([])
        
        # Apply filters
        classroom_id = request.query_params.get('classroom_id')
        if classroom_id:
            query['classroom_id'] = classroom_id
        
        week_number = request.query_params.get('week_number')
        if week_number:
            query['week_number'] = int(week_number)
        
        year = request.query_params.get('year')
        if year:
            query['year'] = int(year)
        
        is_approved = request.query_params.get('is_approved')
        if is_approved is not None:
            query['is_approved'] = is_approved.lower() == 'true'
        
        # Get week summaries
        week_summaries = list(week_summaries_coll.find(query).sort([
            ('year', -1),
            ('week_number', -1),
            ('total_points', -1)
        ]))
        
        # Convert to response format
        result = []
        for doc in week_summaries:
            # Get classroom details
            classrooms_coll = get_mongo_collection('classrooms')
            classroom_doc = classrooms_coll.find_one({'_id': ObjectId(doc['classroom_id'])})
            
            if not classroom_doc:
                continue
            
            # Get homeroom teacher info
            homeroom_teacher = None
            if classroom_doc.get('homeroom_teacher'):
                teachers_coll = get_mongo_collection('teachers')
                teacher_doc = teachers_coll.find_one({'user.id': classroom_doc['homeroom_teacher']['id']})
                if teacher_doc:
                    homeroom_teacher = {
                        'id': teacher_doc['user']['id'],
                        'full_name': teacher_doc['user'].get('full_name', ''),
                        'first_name': teacher_doc['user'].get('first_name', ''),
                        'last_name': teacher_doc['user'].get('last_name', '')
                    }
            
            result.append({
                'id': str(doc['_id']),
                'classroom': {
                    'id': str(classroom_doc['_id']),
                    'full_name': classroom_doc.get('full_name', ''),
                    'homeroom_teacher': homeroom_teacher
                },
                'week_number': doc.get('week_number'),
                'year': doc.get('year'),
                'positive_points': doc.get('positive_points', 0),
                'negative_points': doc.get('negative_points', 0),
                'total_points': doc.get('total_points', 0),
                'is_approved': doc.get('is_approved', False),
                'approved_by': doc.get('approved_by'),
                'created_at': doc.get('created_at'),
                'updated_at': doc.get('updated_at')
            })
        
        return Response(result)
        
    except Exception as exc:
        logger.exception('mongo_week_summary_list error')
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mongo_week_summary_detail(request, id):
    """API lấy chi tiết tổng kết tuần từ MongoDB"""
    try:
        week_summaries_coll = get_mongo_collection('week_summaries')
        
        try:
            doc = week_summaries_coll.find_one({'_id': ObjectId(id)})
        except:
            return Response({'error': 'Invalid ID format'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not doc:
            return Response({'error': 'Week summary not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get classroom details
        classrooms_coll = get_mongo_collection('classrooms')
        classroom_doc = classrooms_coll.find_one({'_id': ObjectId(doc['classroom_id'])})
        
        if not classroom_doc:
            return Response({'error': 'Classroom not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get homeroom teacher info
        homeroom_teacher = None
        if classroom_doc.get('homeroom_teacher'):
            teachers_coll = get_mongo_collection('teachers')
            teacher_doc = teachers_coll.find_one({'user.id': classroom_doc['homeroom_teacher']['id']})
            if teacher_doc:
                homeroom_teacher = {
                    'id': teacher_doc['user']['id'],
                    'full_name': teacher_doc['user'].get('full_name', ''),
                    'first_name': teacher_doc['user'].get('first_name', ''),
                    'last_name': teacher_doc['user'].get('last_name', '')
                }
        
        result = {
            'id': str(doc['_id']),
            'classroom': {
                'id': str(classroom_doc['_id']),
                'full_name': classroom_doc.get('full_name', ''),
                'homeroom_teacher': homeroom_teacher
            },
            'week_number': doc.get('week_number'),
            'year': doc.get('year'),
            'positive_points': doc.get('positive_points', 0),
            'negative_points': doc.get('negative_points', 0),
            'total_points': doc.get('total_points', 0),
            'is_approved': doc.get('is_approved', False),
            'approved_by': doc.get('approved_by'),
            'created_at': doc.get('created_at'),
            'updated_at': doc.get('updated_at')
        }
        
        return Response(result)
        
    except Exception as exc:
        logger.exception('mongo_week_summary_detail error')
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def mongo_week_milestone(request):
    """Quản lý mốc tuần đầu tiên của hệ thống"""
    try:
        if request.method == 'GET':
            # Lấy thông tin mốc tuần
            week_info = WeekMilestoneManager.get_week_info()
            return Response(week_info)
        
        elif request.method == 'POST':
            # Reset mốc tuần
            milestone = WeekMilestoneManager.reset_week_milestone()
            return Response({
                'message': 'Đã reset mốc tuần thành công',
                'milestone': milestone
            })
        
    except Exception as exc:
        logger.exception('mongo_week_milestone error')
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
