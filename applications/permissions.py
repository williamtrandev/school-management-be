from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """Chỉ cho phép Admin truy cập"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsTeacherUser(permissions.BasePermission):
    """Chỉ cho phép Giáo viên truy cập"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'teacher'


class IsStudentUser(permissions.BasePermission):
    """Chỉ cho phép Học sinh truy cập"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'student'


class IsAdminOrTeacher(permissions.BasePermission):
    """Cho phép Admin hoặc Giáo viên truy cập"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'teacher']


class IsDormSupervisorUser(permissions.BasePermission):
    """Chỉ cho phép Quản sinh truy cập"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'dorm_supervisor'


class IsAdminOrTeacherOrDormSupervisor(permissions.BasePermission):
    """Cho phép Admin, Giáo viên hoặc Quản sinh truy cập"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'teacher', 'dorm_supervisor']


class IsReadOnlyForStudent(permissions.BasePermission):
    """Cho phép học sinh chỉ đọc"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Học sinh chỉ được đọc
        if request.user.role == 'student':
            return request.method in permissions.SAFE_METHODS
        
        return True 