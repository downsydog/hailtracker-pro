"""
PDR CRM Managers
Business logic for customer, lead, job, insurance, payment, estimate, parts, tech, scheduling, analytics, email, document, commission, portal, admin, and hail event management
"""

from .customer_manager import CustomerManager
from .vehicle_manager import VehicleManager
from .job_manager import JobManager
from .insurance_manager import InsuranceManager
from .payment_manager import PaymentManager
from .estimate_manager import EstimateManager
from .parts_manager import PartsManager
from .tech_manager import TechManager
from .scheduling_manager import SchedulingManager
from .analytics_manager import AnalyticsManager
from .email_manager import EmailManager
from .document_manager import DocumentManager
from .commission_manager import CommissionManager
from .portal_manager import PortalManager
from .admin_manager import AdminManager
from .hail_event_manager import HailEventManager
from .photo_manager import PhotoManager
from .dent_mapper import DentMapper
from .damage_assessment_manager import DamageAssessmentManager
from .mobile_estimator_manager import MobileEstimatorManager
from .fleet_manager import FleetManager
from .dealership_portal_manager import DealershipPortalManager
from .insurance_partner_manager import InsurancePartnerManager
from .customer_portal_manager import CustomerPortalManager
from .marketing_manager import MarketingManager
from .business_intelligence_manager import BusinessIntelligenceManager
from .ai_analytics_manager import AIAnalyticsManager
from .sales_territory_manager import SalesTerritoryManager
from .field_sales_manager import FieldSalesManager

__all__ = [
    'CustomerManager',
    'VehicleManager',
    'JobManager',
    'InsuranceManager',
    'PaymentManager',
    'EstimateManager',
    'PartsManager',
    'TechManager',
    'SchedulingManager',
    'AnalyticsManager',
    'EmailManager',
    'DocumentManager',
    'CommissionManager',
    'PortalManager',
    'AdminManager',
    'HailEventManager',
    'PhotoManager',
    'DentMapper',
    'DamageAssessmentManager',
    'MobileEstimatorManager',
    'FleetManager',
    'DealershipPortalManager',
    'InsurancePartnerManager',
    'CustomerPortalManager',
    'MarketingManager',
    'BusinessIntelligenceManager',
    'AIAnalyticsManager',
    'SalesTerritoryManager',
    'FieldSalesManager'
]
