"""
Web routes module for HailTracker Pro
"""

from .crm import crm_bp
from .auth import auth_bp
from .home import home_bp
from .elite_sales import elite_sales_bp
from .mobile import mobile_bp

__all__ = ['crm_bp', 'auth_bp', 'home_bp', 'elite_sales_bp', 'mobile_bp']
