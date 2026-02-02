"""
Core module for HailTracker Pro
Contains multi-tenant RBAC system and foundational components
"""

from .models.tenant_schema import TenantSchema, init_tenant_schema

__all__ = ['TenantSchema', 'init_tenant_schema']
