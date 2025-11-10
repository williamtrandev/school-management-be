"""
Hệ thống đánh dấu mốc tuần đầu tiên
"""

from datetime import datetime
from applications.common.mongo import get_mongo_collection, to_plain

class WeekMilestoneManager:
    """Quản lý mốc tuần đầu tiên của hệ thống"""
    
    @staticmethod
    def get_or_create_week_milestone():
        """Lấy hoặc tạo mốc tuần đầu tiên"""
        
        milestones_coll = get_mongo_collection('week_milestones')
        
        # Kiểm tra xem đã có mốc tuần chưa
        milestone = milestones_coll.find_one({'is_active': True})
        
        if milestone:
            return to_plain(milestone)
        
        # Tạo mốc tuần đầu tiên
        today = datetime.now()
        current_week = today.isocalendar()[1]
        current_year = today.year
        
        milestone_doc = {
            'start_date': today.strftime('%Y-%m-%d'),
            'week_number': current_week,
            'year': current_year,
            'created_at': datetime.now().isoformat(),
            'description': f'Tuần đầu tiên của hệ thống - Tuần {current_week}/{current_year}',
            'is_active': True
        }
        
        result = milestones_coll.insert_one(milestone_doc)
        milestone_doc['_id'] = result.inserted_id
        
        return milestone_doc
    
    @staticmethod
    def get_current_week_number():
        """Lấy số tuần hiện tại (tính từ mốc)"""
        
        milestone = WeekMilestoneManager.get_or_create_week_milestone()
        
        if not milestone:
            return 1
        
        start_date = datetime.strptime(milestone['start_date'], '%Y-%m-%d')
        current_week = datetime.now().isocalendar()[1]
        current_year = datetime.now().year
        
        # Tính tuần thứ mấy
        weeks_since_start = current_week - milestone['week_number']
        if current_year > milestone['year']:
            weeks_since_start += 52
        
        return weeks_since_start + 1
    
    @staticmethod
    def get_week_info():
        """Lấy thông tin tuần hiện tại"""
        
        milestone = WeekMilestoneManager.get_or_create_week_milestone()
        current_week = datetime.now().isocalendar()[1]
        current_year = datetime.now().year
        
        return {
            'milestone_date': milestone['start_date'],
            'milestone_week': milestone['week_number'],
            'milestone_year': milestone['year'],
            'current_week': current_week,
            'current_year': current_year,
            'week_number': WeekMilestoneManager.get_current_week_number()
        }
    
    @staticmethod
    def reset_week_milestone():
        """Reset mốc tuần (xóa mốc cũ, tạo mốc mới)"""
        
        milestones_coll = get_mongo_collection('week_milestones')
        
        # Xóa mốc tuần cũ
        milestones_coll.delete_many({})
        
        # Tạo mốc tuần mới
        milestone = WeekMilestoneManager.get_or_create_week_milestone()
        return to_plain(milestone)
