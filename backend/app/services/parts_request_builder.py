"""Parts Request Builder Service - Stage 5R

Generate suggested PartRequests from existing estimate data WITHOUT saving anything.
Used to preview what parts requests would be created before committing.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.tenant import PDREstimate, PDREstimatePanel, PartRequest, Job


class PartsSuggestion:
    """A suggested part request (not yet saved)."""

    def __init__(
        self,
        description: str,
        source_type: str,
        source_id: int,
        part_number: Optional[str] = None,
        qty: int = 1,
        notes: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        self.description = description
        self.source_type = source_type  # 'panel_ri', 'supplement', 'manual'
        self.source_id = source_id
        self.part_number = part_number
        self.qty = qty
        self.notes = notes
        self.reason = reason  # Why this is suggested
        self.already_exists = False  # Flag if duplicate found
        self.existing_id = None  # ID of existing request if duplicate

    def to_dict(self) -> Dict[str, Any]:
        return {
            'description': self.description,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'part_number': self.part_number,
            'qty': self.qty,
            'notes': self.notes,
            'reason': self.reason,
            'already_exists': self.already_exists,
            'existing_id': self.existing_id,
        }


class PartsRequestBuilder:
    """Build part request suggestions from estimate data."""

    # Common R&I operations that typically require ordering parts
    RI_PARTS_KEYWORDS = [
        'molding', 'moulding', 'trim', 'emblem', 'badge', 'clip', 'clips',
        'fastener', 'retainer', 'rivet', 'grommet', 'seal', 'gasket',
        'weatherstrip', 'antenna', 'mirror', 'handle', 'cap', 'cover',
    ]

    # R&I operations that usually DON'T need parts (just labor)
    RI_NO_PARTS_KEYWORDS = [
        'headliner', 'liner', 'insulation', 'carpet', 'panel', 'fender liner',
        'a/c', 'air bag', 'airbag', 'wiper', 'glass', 'windshield',
    ]

    def __init__(self, estimate: PDREstimate, tenant_id: int):
        self.estimate = estimate
        self.tenant_id = tenant_id
        self.suggestions: List[PartsSuggestion] = []

        # Fetch existing requests for de-dupe
        self._existing_requests = self._load_existing_requests()

    def _load_existing_requests(self) -> Dict[str, PartRequest]:
        """Load existing part requests for this estimate to avoid duplicates."""
        existing = {}

        # Check by estimate_id
        requests = PartRequest.query.filter_by(
            tenant_id=self.tenant_id,
            estimate_id=self.estimate.id,
        ).all()

        for req in requests:
            # Key by normalized description for matching
            key = self._normalize_description(req.description)
            existing[key] = req

        # Also check by job_id if estimate has a linked job
        job = Job.query.filter_by(
            tenant_id=self.tenant_id,
            estimate_id=self.estimate.id,
        ).first()

        if job:
            job_requests = PartRequest.query.filter_by(
                tenant_id=self.tenant_id,
                job_id=job.id,
            ).all()
            for req in job_requests:
                key = self._normalize_description(req.description)
                if key not in existing:
                    existing[key] = req

        return existing

    def _normalize_description(self, desc: str) -> str:
        """Normalize description for duplicate matching."""
        return desc.lower().strip().replace('-', ' ').replace('_', ' ')

    def _check_duplicate(self, suggestion: PartsSuggestion) -> None:
        """Check if suggestion already exists and mark it."""
        key = self._normalize_description(suggestion.description)
        if key in self._existing_requests:
            suggestion.already_exists = True
            suggestion.existing_id = self._existing_requests[key].id

    def _should_suggest_parts_for_ri(self, item_name: str) -> bool:
        """Determine if an R&I operation typically requires parts."""
        name_lower = item_name.lower()

        # Check for no-parts keywords first
        for keyword in self.RI_NO_PARTS_KEYWORDS:
            if keyword in name_lower:
                return False

        # Check for parts keywords
        for keyword in self.RI_PARTS_KEYWORDS:
            if keyword in name_lower:
                return True

        # Default: don't suggest (conservative)
        return False

    def build_from_panels(self) -> 'PartsRequestBuilder':
        """Extract parts suggestions from panel R&I operations."""
        panels = PDREstimatePanel.query.filter_by(
            estimate_id=self.estimate.id
        ).all()

        for panel in panels:
            if not panel.ri_operations:
                continue

            # ri_operations is a JSON list of operation data
            ri_ops = panel.ri_operations if isinstance(panel.ri_operations, list) else []

            for ri_op in ri_ops:
                # Handle different possible formats
                if isinstance(ri_op, dict):
                    item_name = ri_op.get('item_name') or ri_op.get('name', '')
                    op_code = ri_op.get('operation_code') or ri_op.get('code', '')
                elif isinstance(ri_op, str):
                    item_name = ri_op
                    op_code = ''
                else:
                    continue

                if not item_name:
                    continue

                # Check if this R&I operation typically needs parts
                if self._should_suggest_parts_for_ri(item_name):
                    panel_label = panel.panel_label or panel.panel_name

                    suggestion = PartsSuggestion(
                        description=f"{item_name} - {panel_label}",
                        source_type='panel_ri',
                        source_id=panel.id,
                        part_number=op_code if op_code else None,
                        qty=1,
                        notes=f"From R&I on {panel_label}",
                        reason=f"R&I operation '{item_name}' typically requires replacement clips/fasteners",
                    )

                    self._check_duplicate(suggestion)
                    self.suggestions.append(suggestion)

        return self

    def build_from_supplements(self) -> 'PartsRequestBuilder':
        """Extract parts suggestions from supplements."""
        # Import here to avoid circular imports
        from app.models.tenant import EstimateSupplement

        supplements = EstimateSupplement.query.filter_by(
            estimate_id=self.estimate.id
        ).filter(
            EstimateSupplement.status.in_(['sent', 'approved'])
        ).all()

        for supp in supplements:
            # Check discovery_type for parts-related supplements
            if supp.discovery_type in ['hidden_damage', 'additional_repair']:
                # Supplements often indicate additional work that may need parts
                suggestion = PartsSuggestion(
                    description=f"Parts for Supplement #{supp.supplement_number}",
                    source_type='supplement',
                    source_id=supp.id,
                    qty=1,
                    notes=supp.notes or f"Supplement discovered: {supp.discovery_type}",
                    reason=f"Supplement #{supp.supplement_number} may require additional parts",
                )

                self._check_duplicate(suggestion)
                self.suggestions.append(suggestion)

        return self

    def build_from_conventional_repair(self) -> 'PartsRequestBuilder':
        """Suggest parts for panels marked as needing conventional repair."""
        panels = PDREstimatePanel.query.filter_by(
            estimate_id=self.estimate.id
        ).all()

        for panel in panels:
            # Check if panel needs conventional repair (CR)
            # This is typically indicated by severity or a flag
            severity = getattr(panel, 'severity', None)
            is_cr = severity == 'severe' or getattr(panel, 'is_conventional_repair', False)

            if is_cr:
                panel_label = panel.panel_label or panel.panel_name

                suggestion = PartsSuggestion(
                    description=f"Conventional Repair Parts - {panel_label}",
                    source_type='panel_cr',
                    source_id=panel.id,
                    qty=1,
                    notes=f"Panel marked for conventional repair",
                    reason=f"{panel_label} requires conventional repair which may need body shop parts",
                )

                self._check_duplicate(suggestion)
                self.suggestions.append(suggestion)

        return self

    def build_all(self) -> 'PartsRequestBuilder':
        """Run all suggestion builders."""
        return (
            self.build_from_panels()
            .build_from_supplements()
            .build_from_conventional_repair()
        )

    def get_suggestions(self, include_duplicates: bool = True) -> List[Dict[str, Any]]:
        """Get all suggestions as dicts."""
        if include_duplicates:
            return [s.to_dict() for s in self.suggestions]
        else:
            return [s.to_dict() for s in self.suggestions if not s.already_exists]

    def get_new_suggestions(self) -> List[Dict[str, Any]]:
        """Get only new suggestions (not duplicates)."""
        return self.get_suggestions(include_duplicates=False)

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        total = len(self.suggestions)
        new_count = sum(1 for s in self.suggestions if not s.already_exists)
        duplicate_count = total - new_count

        by_source = {}
        for s in self.suggestions:
            by_source[s.source_type] = by_source.get(s.source_type, 0) + 1

        return {
            'total_suggestions': total,
            'new_suggestions': new_count,
            'duplicates': duplicate_count,
            'by_source_type': by_source,
        }


def get_parts_suggestions(estimate_id: int, tenant_id: int) -> Dict[str, Any]:
    """
    Get parts suggestions for an estimate.

    Returns a preview of what PartRequests would be created.
    Does NOT save anything to the database.
    """
    estimate = PDREstimate.query.filter_by(
        id=estimate_id,
        tenant_id=tenant_id,
    ).first()

    if not estimate:
        return {
            'success': False,
            'error': 'Estimate not found',
            'suggestions': [],
            'stats': {},
        }

    builder = PartsRequestBuilder(estimate, tenant_id)
    builder.build_all()

    return {
        'success': True,
        'estimate_id': estimate_id,
        'estimate_number': estimate.estimate_number,
        'suggestions': builder.get_suggestions(),
        'new_suggestions': builder.get_new_suggestions(),
        'stats': builder.get_stats(),
    }


def create_parts_requests_from_suggestions(
    estimate_id: int,
    tenant_id: int,
    user_id: int,
    selected_indices: Optional[List[int]] = None,
    skip_duplicates: bool = True,
) -> Dict[str, Any]:
    """
    Create PartRequests from suggestions.

    Args:
        estimate_id: The estimate to generate parts for
        tenant_id: Tenant context
        user_id: User creating the requests
        selected_indices: If provided, only create requests for these indices
        skip_duplicates: If True, skip suggestions that already exist

    Returns:
        Summary of created requests
    """
    from app.extensions import db
    from app.models.tenant import EstimateActivity

    estimate = PDREstimate.query.filter_by(
        id=estimate_id,
        tenant_id=tenant_id,
    ).first()

    if not estimate:
        return {
            'success': False,
            'error': 'Estimate not found',
            'created': [],
        }

    # Get linked job if exists
    job = Job.query.filter_by(
        tenant_id=tenant_id,
        estimate_id=estimate_id,
    ).first()

    builder = PartsRequestBuilder(estimate, tenant_id)
    builder.build_all()

    suggestions = builder.suggestions
    created = []
    skipped_duplicates = 0

    for i, suggestion in enumerate(suggestions):
        # Filter by selected indices if provided
        if selected_indices is not None and i not in selected_indices:
            continue

        # Skip duplicates if requested
        if skip_duplicates and suggestion.already_exists:
            skipped_duplicates += 1
            continue

        # Create the PartRequest
        part_request = PartRequest(
            tenant_id=tenant_id,
            estimate_id=estimate_id,
            job_id=job.id if job else None,
            description=suggestion.description,
            part_number=suggestion.part_number,
            qty=suggestion.qty,
            parts_status='needed',
            notes=suggestion.notes,
            priority=50,  # Default priority
            created_by=user_id,
        )

        db.session.add(part_request)
        db.session.flush()  # Get the ID

        # Log activity
        activity = EstimateActivity(
            tenant_id=tenant_id,
            estimate_id=estimate_id,
            activity_type='parts_request_created',
            user_id=user_id,
            data={
                'part_request_id': part_request.id,
                'description': suggestion.description,
                'source_type': suggestion.source_type,
                'source_id': suggestion.source_id,
                'auto_generated': True,
            }
        )
        db.session.add(activity)

        created.append(part_request.to_dict())

    db.session.commit()

    return {
        'success': True,
        'estimate_id': estimate_id,
        'created_count': len(created),
        'skipped_duplicates': skipped_duplicates,
        'created': created,
    }
