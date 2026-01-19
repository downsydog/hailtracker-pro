"""
HailTracker Pro - Enterprise PDR CRM System

Salesforce-level CRM for paintless dent repair businesses with:
- Complex insurance claim workflows
- Multi-tech coordination
- Revenue tracking and splits
- Email tracking with adjusters
- Parts ordering and sourcing
- Hail event integration
"""

from .models.database import Database
from .models.schema import DatabaseSchema

__all__ = ['Database', 'DatabaseSchema']
