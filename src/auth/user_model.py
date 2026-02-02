"""
Flask-Login User Model
"""

from flask_login import UserMixin


class User(UserMixin):
    """User model for Flask-Login"""

    def __init__(self, user_dict):
        self.id = user_dict['id']
        self.email = user_dict['email']
        self.username = user_dict['username']
        self.full_name = user_dict['full_name']
        self.role = user_dict['role']
        self.company_id = user_dict.get('company_id')
        self.active = user_dict['active']

    def is_active(self):
        """Required by Flask-Login"""
        return self.active

    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'

    def is_manager(self):
        """Check if user is manager or admin"""
        return self.role in ['admin', 'manager']

    def can(self, resource, action):
        """Check if user has permission"""
        from src.auth.auth_manager import AuthManager
        auth = AuthManager()
        return auth.check_permission(self.id, resource, action)

    def get_id(self):
        """Required by Flask-Login - return unique identifier"""
        return str(self.id)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
