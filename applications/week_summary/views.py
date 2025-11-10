from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Avg, Count, Case, When, F, IntegerField
from datetime import datetime, timedelta
from django.db import transaction

from .models import WeekSummary
from .serializers import WeekSummarySerializer
from applications.classroom.models import Classroom
from applications.event.models import Event


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def week_summary_list(request):
    """API lấy danh sách tổng kết tuần"""
    # Filter theo role của user
    user = request.user
    queryset = WeekSummary.objects.select_related('classroom', 'approved_by')
    
    if user.role == 'student':
        # Học sinh chỉ thấy lớp của mình
        if hasattr(user, 'student'):
            queryset = queryset.filter(classroom=user.student.classroom)
        else:
            queryset = queryset.none()
    elif user.role == 'teacher':
        # Giáo viên thấy lớp mình chủ nhiệm
        queryset = queryset.filter(classroom__homeroom_teacher=user)
    # Admin thấy tất cả
    
    # Apply filters
    classroom_id = request.query_params.get('classroom_id')
    if classroom_id:
        queryset = queryset.filter(classroom_id=classroom_id)
    
    week_number = request.query_params.get('week_number')
    if week_number:
        queryset = queryset.filter(week_number=week_number)
    
    year = request.query_params.get('year')
    if year:
        queryset = queryset.filter(year=year)
    
    is_approved = request.query_params.get('is_approved')
    if is_approved is not None:
        queryset = queryset.filter(is_approved=is_approved.lower() == 'true')
    
    # Ordering
    queryset = queryset.order_by('-year', '-week_number', 'total_points')
    
    serializer = WeekSummarySerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def week_summary_detail(request, id):
    """API lấy chi tiết tổng kết tuần"""
    week_summary = get_object_or_404(WeekSummary, id=id)
    serializer = WeekSummarySerializer(week_summary)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def week_summary_approve(request, id):
    """API duyệt tổng kết tuần"""
    week_summary = get_object_or_404(WeekSummary, id=id)
    
    # Chỉ admin mới được duyệt
    if request.user.role != 'admin':
        return Response(
            {'error': 'Chỉ admin mới được duyệt tổng kết tuần'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    week_summary.is_approved = True
    week_summary.approved_by = request.user
    week_summary.approved_at = datetime.now()
    week_summary.save()
    
    serializer = WeekSummarySerializer(week_summary)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_rankings(request):
    """API lấy bảng xếp hạng cho dashboard"""
    # Filter theo role của user
    user = request.user
    queryset = WeekSummary.objects.select_related('classroom', 'approved_by')
    
    if user.role == 'student':
        # Học sinh chỉ thấy lớp của mình
        if hasattr(user, 'student'):
            queryset = queryset.filter(classroom=user.student.classroom)
        else:
            queryset = queryset.none()
    elif user.role == 'teacher':
        # Giáo viên thấy lớp mình chủ nhiệm
        queryset = queryset.filter(classroom__homeroom_teacher=user)
    # Admin thấy tất cả
    
    # Get current week and year
    week_number = request.query_params.get('week_number')
    year = request.query_params.get('year')
    
    if week_number and year:
        queryset = queryset.filter(week_number=week_number, year=year)
    else:
        # Default to current week
        now = datetime.now()
        current_week = now.isocalendar()[1]
        current_year = now.year
        queryset = queryset.filter(week_number=current_week, year=current_year)
    
    # Order by total points descending
    queryset = queryset.order_by('-total_points')
    
    serializer = WeekSummarySerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def class_rankings(request):
    """API lấy bảng xếp hạng lớp học"""
    user = request.user
    queryset = WeekSummary.objects.select_related('classroom', 'approved_by')
    
    # Filter theo role
    if user.role == 'student':
        if hasattr(user, 'student'):
            queryset = queryset.filter(classroom=user.student.classroom)
        else:
            queryset = queryset.none()
    elif user.role == 'teacher':
        queryset = queryset.filter(classroom__homeroom_teacher=user)
    
    # Apply filters
    week_number = request.query_params.get('week_number')
    year = request.query_params.get('year')
    
    if week_number:
        queryset = queryset.filter(week_number=week_number)
    if year:
        queryset = queryset.filter(year=year)
    
    # Order by total points descending
    queryset = queryset.order_by('-total_points')
    
    # Convert to list to add rank
    summaries_list = list(queryset)
    
    # Add rank to each summary
    for index, summary in enumerate(summaries_list):
        summary.rank = index + 1
    
    serializer = WeekSummarySerializer(summaries_list, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_rankings(request):
    """API lấy bảng xếp hạng theo tháng"""
    user = request.user
    month = request.query_params.get('month')
    year = request.query_params.get('year')
    
    if not month or not year:
        return Response(
            {'error': 'Tháng và năm là bắt buộc'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Calculate week range for the month
    month_start = datetime(int(year), int(month), 1)
    month_end = datetime(int(year), int(month) + 1, 1) - timedelta(days=1)
    
    # Get week numbers in the month
    start_week = month_start.isocalendar()[1]
    end_week = month_end.isocalendar()[1]
    
    queryset = WeekSummary.objects.select_related('classroom', 'approved_by').filter(
        week_number__gte=start_week,
        week_number__lte=end_week,
        year=int(year)
    )
    
    # Filter theo role
    if user.role == 'student':
        if hasattr(user, 'student'):
            queryset = queryset.filter(classroom=user.student.classroom)
        else:
            queryset = queryset.none()
    elif user.role == 'teacher':
        queryset = queryset.filter(classroom__homeroom_teacher=user)
    
    # Aggregate by classroom
    from django.db.models import Sum
    aggregated_data = queryset.values('classroom').annotate(
        total_positive=Sum('positive_points'),
        total_negative=Sum('negative_points'),
        total_points=Sum('total_points'),
        week_count=Count('id')
    ).order_by('-total_points')
    
    # Create response data
    rankings = []
    for index, data in enumerate(aggregated_data):
        classroom = Classroom.objects.get(id=data['classroom'])
        rankings.append({
            'id': f"monthly_{data['classroom']}",
            'classroom': {
                'id': classroom.id,
                'full_name': classroom.full_name,
                'homeroom_teacher': {
                    'id': classroom.homeroom_teacher.id if classroom.homeroom_teacher else None,
                    'full_name': classroom.homeroom_teacher.full_name if classroom.homeroom_teacher else None,
                    'first_name': classroom.homeroom_teacher.first_name if classroom.homeroom_teacher else None,
                    'last_name': classroom.homeroom_teacher.last_name if classroom.homeroom_teacher else None,
                } if classroom.homeroom_teacher else None
            },
            'week_number': int(month),
            'year': int(year),
            'positive_points': data['total_positive'] or 0,
            'negative_points': data['total_negative'] or 0,
            'total_points': data['total_points'] or 0,
            'rank': index + 1,
            'is_approved': True,
            'week_count': data['week_count']
        })
    
    return Response(rankings)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def yearly_rankings(request):
    """API lấy bảng xếp hạng theo năm"""
    user = request.user
    year = request.query_params.get('year')
    
    if not year:
        return Response(
            {'error': 'Năm là bắt buộc'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    queryset = WeekSummary.objects.select_related('classroom', 'approved_by').filter(
        year=int(year)
    )
    
    # Filter theo role
    if user.role == 'student':
        if hasattr(user, 'student'):
            queryset = queryset.filter(classroom=user.student.classroom)
        else:
            queryset = queryset.none()
    elif user.role == 'teacher':
        queryset = queryset.filter(classroom__homeroom_teacher=user)
    
    # Aggregate by classroom
    from django.db.models import Sum, Avg
    aggregated_data = queryset.values('classroom').annotate(
        total_positive=Sum('positive_points'),
        total_negative=Sum('negative_points'),
        total_points=Sum('total_points'),
        week_count=Count('id'),
        avg_points=Avg('total_points')
    ).order_by('-total_points')
    
    # Create response data
    rankings = []
    for index, data in enumerate(aggregated_data):
        classroom = Classroom.objects.get(id=data['classroom'])
        rankings.append({
            'id': f"yearly_{data['classroom']}",
            'classroom': {
                'id': classroom.id,
                'full_name': classroom.full_name,
                'homeroom_teacher': {
                    'id': classroom.homeroom_teacher.id if classroom.homeroom_teacher else None,
                    'full_name': classroom.homeroom_teacher.full_name if classroom.homeroom_teacher else None,
                    'first_name': classroom.homeroom_teacher.first_name if classroom.homeroom_teacher else None,
                    'last_name': classroom.homeroom_teacher.last_name if classroom.homeroom_teacher else None,
                } if classroom.homeroom_teacher else None
            },
            'week_number': 0,  # Yearly summary
            'year': int(year),
            'positive_points': data['total_positive'] or 0,
            'negative_points': data['total_negative'] or 0,
            'total_points': data['total_points'] or 0,
            'rank': index + 1,
            'is_approved': True,
            'week_count': data['week_count'],
            'avg_points': round(data['avg_points'] or 0, 2)
        })
    
    return Response(rankings)


# Removed generate_week_summary - using real-time computation instead


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def realtime_rankings(request):
    """Compute rankings in real-time from events for a given week/year or date range."""
    user = request.user
    week_number = request.query_params.get('week_number')
    year = request.query_params.get('year')
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')

    # Resolve date range
    try:
        if week_number and year:
            week = int(week_number)
            yr = int(year)
            # ISO week: Monday=1, Sunday=7
            start_dt = datetime.fromisocalendar(yr, week, 1)
            end_dt = datetime.fromisocalendar(yr, week, 7)
        elif start_date_str and end_date_str:
            start_dt = datetime.fromisoformat(start_date_str)
            end_dt = datetime.fromisoformat(end_date_str)
        else:
            # Default to current ISO week
            now = datetime.now()
            iso = now.isocalendar()
            start_dt = datetime.fromisocalendar(iso[0], iso[1], 1)
            end_dt = datetime.fromisocalendar(iso[0], iso[1], 7)
    except ValueError:
        return Response({'error': 'Invalid date/week parameters'}, status=status.HTTP_400_BAD_REQUEST)

    # Base queryset
    events = Event.objects.select_related('classroom').filter(
        date__gte=start_dt.date(),
        date__lte=end_dt.date(),
    )

    # Role-based filtering (align with other endpoints)
    if user.role == 'student':
        if hasattr(user, 'student'):
            events = events.filter(classroom=user.student.classroom)
        else:
            events = events.none()
    elif user.role == 'teacher':
        events = events.filter(classroom__homeroom_teacher=user)

    # Aggregate by classroom using conditional sums
    aggregated = events.values('classroom').annotate(
        positive_points=Sum(
            Case(
                When(points__gt=0, then=F('points')),
                default=0,
                output_field=IntegerField(),
            )
        ),
        negative_points=Sum(
            Case(
                When(points__lt=0, then=F('points')),
                default=0,
                output_field=IntegerField(),
            )
        ),
    )

    # Build response list
    rankings = []
    for row in aggregated:
        cid = row['classroom']
        try:
            classroom = Classroom.objects.get(id=cid)
        except Classroom.DoesNotExist:
            continue
        total_positive = row['positive_points'] or 0
        total_negative = row['negative_points'] or 0
        total_points = (total_positive or 0) + (total_negative or 0)
        rankings.append({
            'id': f"realtime_{cid}",
            'classroom': {
                'id': classroom.id,
                'full_name': classroom.full_name,
                'homeroom_teacher': {
                    'id': classroom.homeroom_teacher.id if classroom.homeroom_teacher else None,
                    'full_name': classroom.homeroom_teacher.full_name if classroom.homeroom_teacher else None,
                    'first_name': classroom.homeroom_teacher.first_name if classroom.homeroom_teacher else None,
                    'last_name': classroom.homeroom_teacher.last_name if classroom.homeroom_teacher else None,
                } if classroom.homeroom_teacher else None
            },
            'week_number': int(week_number) if week_number else start_dt.isocalendar()[1],
            'year': int(year) if year else start_dt.year,
            'positive_points': total_positive,
            'negative_points': total_negative,
            'total_points': total_points,
            'is_approved': True,
        })

    # Sort and assign ranks
    rankings.sort(key=lambda r: r['total_points'], reverse=True)
    for idx, r in enumerate(rankings):
        r['rank'] = idx + 1

    return Response(rankings)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_performers(request):
    """API lấy top performers"""
    user = request.user
    week_number = request.query_params.get('week_number')
    year = request.query_params.get('year')
    
    if not week_number or not year:
        # Use current week
        now = datetime.now()
        week_number = now.isocalendar()[1]
        year = now.year
    
    # Get current week rankings
    current_rankings = WeekSummary.objects.select_related('classroom').filter(
        week_number=week_number,
        year=year
    ).order_by('-total_points')
    
    # Filter by role
    if user.role == 'student':
        if hasattr(user, 'student'):
            current_rankings = current_rankings.filter(classroom=user.student.classroom)
        else:
            current_rankings = current_rankings.none()
    elif user.role == 'teacher':
        current_rankings = current_rankings.filter(classroom__homeroom_teacher=user)
    
    # Get previous week for comparison
    prev_week = int(week_number) - 1
    prev_year = int(year)
    if prev_week <= 0:
        prev_week = 52
        prev_year -= 1
    
    previous_rankings = WeekSummary.objects.select_related('classroom').filter(
        week_number=prev_week,
        year=prev_year
    )
    
    # Filter previous rankings by role
    if user.role == 'student':
        if hasattr(user, 'student'):
            previous_rankings = previous_rankings.filter(classroom=user.student.classroom)
        else:
            previous_rankings = previous_rankings.none()
    elif user.role == 'teacher':
        previous_rankings = previous_rankings.filter(classroom__homeroom_teacher=user)
    
    # Calculate top performers
    best_class = current_rankings.first()
    
    # Most improved (simplified - compare with previous week)
    most_improved = None
    if previous_rankings.exists():
        # Find class with biggest improvement
        improvements = []
        for current in current_rankings:
            try:
                prev = previous_rankings.get(classroom=current.classroom)
                improvement = current.total_points - prev.total_points
                improvements.append((current, improvement))
            except WeekSummary.DoesNotExist:
                improvements.append((current, current.total_points))
        
        if improvements:
            most_improved = max(improvements, key=lambda x: x[1])[0]
    
    # Consistent performers (top 3 overall for the year)
    yearly_rankings = WeekSummary.objects.select_related('classroom').filter(
        year=year
    )
    
    # Filter by role
    if user.role == 'student':
        if hasattr(user, 'student'):
            yearly_rankings = yearly_rankings.filter(classroom=user.student.classroom)
        else:
            yearly_rankings = yearly_rankings.none()
    elif user.role == 'teacher':
        yearly_rankings = yearly_rankings.filter(classroom__homeroom_teacher=user)
    
    # Aggregate by classroom for consistent performers
    consistent_data = yearly_rankings.values('classroom').annotate(
        total_points=Sum('total_points'),
        week_count=Count('id')
    ).order_by('-total_points')[:3]
    
    consistent_performers = []
    for data in consistent_data:
        classroom = Classroom.objects.get(id=data['classroom'])
        consistent_performers.append({
            'id': classroom.id,
            'full_name': classroom.full_name,
            'total_points': data['total_points'],
            'week_count': data['week_count']
        })
    
    return Response({
        'best_class': {
            'id': best_class.classroom.id,
            'full_name': best_class.classroom.full_name,
            'total_points': best_class.total_points
        } if best_class else None,
        'most_improved': {
            'id': most_improved.classroom.id,
            'full_name': most_improved.classroom.full_name,
            'total_points': most_improved.total_points
        } if most_improved else None,
        'consistent_performers': consistent_performers
    })


# Removed create_sample_rankings - using real-time computation instead


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_rankings_data(request):
    """API test để kiểm tra dữ liệu rankings"""
    try:
        # Get all WeekSummary data
        all_summaries = WeekSummary.objects.select_related('classroom').all()
        
        # Get summaries for specific week/year if provided
        week_number = request.query_params.get('week_number')
        year = request.query_params.get('year')
        
        if week_number and year:
            summaries = all_summaries.filter(week_number=week_number, year=year)
        else:
            summaries = all_summaries
        
        # Count by week and year
        week_year_counts = {}
        for summary in all_summaries:
            key = f"Week {summary.week_number}/{summary.year}"
            week_year_counts[key] = week_year_counts.get(key, 0) + 1
        
        # Get classroom info
        classrooms = Classroom.objects.all()
        
        return Response({
            'total_summaries': all_summaries.count(),
            'filtered_summaries': summaries.count(),
            'week_year_counts': week_year_counts,
            'total_classrooms': classrooms.count(),
            'classrooms': [
                {
                    'id': str(c.id),
                    'name': c.name,
                    'full_name': c.full_name,
                    'grade': c.grade.name if c.grade else None
                } for c in classrooms
            ],
            'sample_summaries': [
                {
                    'id': str(s.id),
                    'classroom': s.classroom.full_name,
                    'week_number': s.week_number,
                    'year': s.year,
                    'total_points': s.total_points,
                    'rank': s.rank
                } for s in summaries[:5]  # First 5 summaries
            ]
        })
        
    except Exception as e:
        return Response(
            {'error': f'Lỗi khi kiểm tra dữ liệu: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 