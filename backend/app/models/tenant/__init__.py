"""Tenant database models - per-customer CRM data."""

from .lead import Lead
from .contact import Contact
from .call import Call
from .job import Job
from .estimate import Estimate
from .estimate_photo import EstimatePhoto
from .estimate_activity import EstimateActivity
from .estimate_version import EstimateVersion
from .estimate_supplement import EstimateSupplement, SupplementPhotoLink, DISCOVERY_TYPES
from .pdr_estimate import PDREstimate
from .pdr_estimate_panel import PDREstimatePanel
from .invoice import Invoice, InvoiceLineItem, Payment
from .part_request import PartRequest, PARTS_STATUS_VALUES
# Phase 6A: R&I Justification Engine models
from .ri_operation import RIOperation, RI_RISK_LEVELS, RI_CATEGORIES
from .ri_step import RIStep, RI_DENIAL_RESISTANCE
from .ri_modifier import RIModifier, RI_MODIFIER_CATEGORIES
from .pdr_estimate_ri import (
    PDREstimateRIOperation,
    PDREstimateRIStepOverride,
    PDREstimateRIModifierSelection,
)

__all__ = [
    'Lead', 'Contact', 'Call', 'Job', 'Estimate',
    'EstimatePhoto', 'EstimateActivity',
    'EstimateVersion', 'EstimateSupplement', 'SupplementPhotoLink', 'DISCOVERY_TYPES',
    'PDREstimate', 'PDREstimatePanel',
    'Invoice', 'InvoiceLineItem', 'Payment',
    'PartRequest', 'PARTS_STATUS_VALUES',
    # R&I Justification Engine
    'RIOperation', 'RI_RISK_LEVELS', 'RI_CATEGORIES',
    'RIStep', 'RI_DENIAL_RESISTANCE',
    'RIModifier', 'RI_MODIFIER_CATEGORIES',
    'PDREstimateRIOperation', 'PDREstimateRIStepOverride', 'PDREstimateRIModifierSelection',
]
