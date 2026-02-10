"""
Dispute Pack Generator Service

Generates a ZIP bundle containing all estimate-related documents:
- Estimate PDF
- Photo Sheet PDF
- All Supplement PDFs
- Activity Log (text file)
- Phase 7C additions:
  - denial_ammo.txt (R&I denial pack copy blocks)
  - ri_summary.json (R&I operations summary)
  - parts_requests.csv (open parts requests)
  - parts_exposure.txt (pricing exposure summary)

Used for adjuster disputes and record-keeping.
"""

import io
import csv
import json
import zipfile
from datetime import datetime
from typing import Optional, List, Dict, Any

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from app.services.pdr_pdf_generator import generate_pdr_estimate_pdf
from app.services.photo_sheet_generator import generate_photo_sheet_pdf
from app.services.supplement_pdf_generator import generate_supplement_pdf


def generate_activity_log_text(
    estimate_data: Dict[str, Any],
    activities: List[Dict[str, Any]],
    supplements: List[Dict[str, Any]]
) -> str:
    """
    Generate a plain text activity log for the dispute pack.

    Args:
        estimate_data: The estimate dictionary
        activities: List of activity records
        supplements: List of supplement records

    Returns:
        Plain text content for activity log file
    """
    lines = []

    # Header
    lines.append("=" * 60)
    lines.append("ESTIMATE ACTIVITY LOG")
    lines.append("=" * 60)
    lines.append("")

    # Estimate info
    estimate_number = estimate_data.get('estimate_number', 'N/A')
    vehicle_info = f"{estimate_data.get('vehicle_year', '')} {estimate_data.get('vehicle_make', '')} {estimate_data.get('vehicle_model', '')}".strip()
    customer_name = estimate_data.get('customer_name', 'N/A')

    lines.append(f"Estimate Number: {estimate_number}")
    lines.append(f"Vehicle: {vehicle_info or 'N/A'}")
    lines.append(f"Customer: {customer_name}")
    lines.append(f"Report Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")

    # Supplements summary
    lines.append("-" * 60)
    lines.append("SUPPLEMENTS SUMMARY")
    lines.append("-" * 60)

    if supplements:
        for supp in supplements:
            supp_num = supp.get('supplement_number', 'N/A')
            supp_status = supp.get('status', 'unknown')
            delta = supp.get('delta_amount')
            delta_str = f"${delta:,.2f}" if delta is not None else "N/A"
            created = supp.get('created_at', 'N/A')
            if isinstance(created, datetime):
                created = created.strftime('%Y-%m-%d %H:%M')
            discovery_type = supp.get('discovery_type', 'N/A').replace('_', ' ').title()

            lines.append(f"  Supplement #{supp_num}")
            lines.append(f"    Status: {supp_status}")
            lines.append(f"    Type: {discovery_type}")
            lines.append(f"    Delta Amount: {delta_str}")
            lines.append(f"    Created: {created}")
            lines.append("")
    else:
        lines.append("  No supplements on file.")
        lines.append("")

    # Activity timeline
    lines.append("-" * 60)
    lines.append("ACTIVITY TIMELINE")
    lines.append("-" * 60)

    if activities:
        for activity in activities:
            act_type = activity.get('activity_type', 'unknown').replace('_', ' ').title()
            created = activity.get('created_at', 'N/A')
            if isinstance(created, datetime):
                created = created.strftime('%Y-%m-%d %H:%M:%S')

            metadata = activity.get('metadata', {}) or {}

            lines.append(f"  [{created}] {act_type}")

            # Add relevant metadata
            if 'recipient' in metadata:
                lines.append(f"    Recipient: {metadata['recipient']}")
            if 'subject' in metadata:
                lines.append(f"    Subject: {metadata['subject']}")
            if 'supplement_id' in metadata:
                lines.append(f"    Supplement ID: {metadata['supplement_id']}")
            if 'supplement_number' in metadata:
                lines.append(f"    Supplement #: {metadata['supplement_number']}")
            if 'error' in metadata:
                lines.append(f"    Error: {metadata['error']}")

            lines.append("")
    else:
        lines.append("  No activity recorded.")
        lines.append("")

    # Footer
    lines.append("-" * 60)
    lines.append("END OF ACTIVITY LOG")
    lines.append("-" * 60)

    return "\n".join(lines)


def generate_denial_ammo_text(ri_denial_pack: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Generate denial ammo text file content from R&I denial pack.

    Phase 7C: Provides copy-ready text for adjuster disputes.
    """
    if not ri_denial_pack:
        return None

    copy_blocks = ri_denial_pack.get('copy_blocks', {})
    full_text = copy_blocks.get('full')
    if not full_text:
        return None

    lines = []
    lines.append("=" * 60)
    lines.append("R&I DENIAL AMMO - ADJUSTER DISPUTE SUPPORT")
    lines.append("=" * 60)
    lines.append("")

    # Overall rating
    rating = ri_denial_pack.get('overall_rating', 'unknown').upper()
    score = ri_denial_pack.get('overall_score', 0)
    lines.append(f"Denial Resistance: {rating} (Score: {score}/100)")
    lines.append("")

    # Summary
    summary = ri_denial_pack.get('summary_text', '')
    if summary:
        lines.append("SUMMARY:")
        lines.append(summary)
        lines.append("")

    # Adjuster bullets
    bullets = ri_denial_pack.get('adjuster_bullets', [])
    if bullets:
        lines.append("-" * 40)
        lines.append("KEY TALKING POINTS:")
        for bullet in bullets:
            lines.append(f"  • {bullet}")
        lines.append("")

    # Full copy block
    lines.append("-" * 40)
    lines.append("FULL NARRATIVE (COPY-READY):")
    lines.append("-" * 40)
    lines.append("")
    lines.append(full_text)
    lines.append("")
    lines.append("-" * 60)
    lines.append("END OF DENIAL AMMO")
    lines.append("-" * 60)

    return "\n".join(lines)


def generate_ri_summary_json(ri_summary: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Generate R&I summary JSON for dispute pack.

    Phase 7C: Machine-readable R&I breakdown.
    """
    if not ri_summary:
        return None

    # Build clean summary object
    export_data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "estimate_id": ri_summary.get('estimate_id'),
        "total_ri_time_hours": ri_summary.get('total_ri_time_hours', 0),
        "total_ri_cost": ri_summary.get('total_ri_cost', 0),
        "operation_count": ri_summary.get('operation_count', 0),
        "labor_rate": {
            "rate": ri_summary.get('ri_labor_rate'),
            "source": ri_summary.get('ri_labor_rate_source'),
            "reason": ri_summary.get('ri_labor_rate_reason')
        },
        "operations": []
    }

    for op in ri_summary.get('operations', []):
        op_data = {
            "code": op.get('code'),
            "display_name": op.get('display_name'),
            "category": op.get('category'),
            "risk_level": op.get('risk_level'),
            "totals": op.get('totals', {}),
            "justification_text": op.get('justification_text', ''),
            "steps": [
                {
                    "step_code": s.get('step_code'),
                    "label": s.get('label'),
                    "hours": s.get('effective_time_hours'),
                    "included": s.get('included'),
                    "denial_resistance": s.get('denial_resistance')
                }
                for s in op.get('steps', []) if s.get('included')
            ]
        }
        export_data['operations'].append(op_data)

    return json.dumps(export_data, indent=2)


def generate_parts_requests_csv(parts_requests: List[Dict[str, Any]]) -> Optional[str]:
    """
    Generate CSV of parts requests for dispute pack.

    Phase 7C: Parts tracking for supplement support.
    """
    if not parts_requests:
        return None

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        'Part Name', 'Part Number', 'Vendor', 'Status', 'ETA',
        'Approved', 'Approved Amount', 'PO Number', 'Notes'
    ])

    for part in parts_requests:
        writer.writerow([
            part.get('part_name', ''),
            part.get('part_number', ''),
            part.get('vendor', ''),
            part.get('parts_status', 'needed'),
            part.get('eta', ''),
            'Yes' if part.get('approved_to_order') else 'No',
            f"${part.get('approved_amount', 0):.2f}" if part.get('approved_amount') else '',
            part.get('po_number', ''),
            part.get('notes', '')
        ])

    return output.getvalue()


def generate_parts_exposure_text(
    parts_requests: List[Dict[str, Any]],
    estimate_data: Dict[str, Any]
) -> Optional[str]:
    """
    Generate parts exposure summary text.

    Phase 7C: Highlights parts-related supplement exposure.
    """
    if not parts_requests:
        return None

    lines = []
    lines.append("=" * 60)
    lines.append("PARTS EXPOSURE SUMMARY")
    lines.append("=" * 60)
    lines.append("")

    estimate_number = estimate_data.get('estimate_number', 'N/A')
    lines.append(f"Estimate: {estimate_number}")
    lines.append(f"Report Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")

    # Summary stats
    total_parts = len(parts_requests)
    approved_parts = [p for p in parts_requests if p.get('approved_to_order')]
    pending_parts = [p for p in parts_requests if p.get('parts_status') in ('needed', 'pending', 'quoted')]
    received_parts = [p for p in parts_requests if p.get('parts_status') == 'received']

    total_approved = sum(p.get('approved_amount', 0) or 0 for p in approved_parts)

    lines.append("-" * 40)
    lines.append("SUMMARY:")
    lines.append(f"  Total Parts Requests: {total_parts}")
    lines.append(f"  Approved: {len(approved_parts)} (${total_approved:,.2f})")
    lines.append(f"  Pending: {len(pending_parts)}")
    lines.append(f"  Received: {len(received_parts)}")
    lines.append("")

    # Parts by status
    if pending_parts:
        lines.append("-" * 40)
        lines.append("PENDING PARTS (POTENTIAL SUPPLEMENT ITEMS):")
        for part in pending_parts:
            name = part.get('part_name', 'Unknown')
            vendor = part.get('vendor', 'TBD')
            eta = part.get('eta', 'TBD')
            status = part.get('parts_status', 'pending')
            lines.append(f"  • {name}")
            lines.append(f"    Vendor: {vendor} | ETA: {eta} | Status: {status}")
        lines.append("")

    if approved_parts:
        lines.append("-" * 40)
        lines.append("APPROVED PARTS:")
        for part in approved_parts:
            name = part.get('part_name', 'Unknown')
            amount = part.get('approved_amount', 0) or 0
            po = part.get('po_number', '')
            lines.append(f"  • {name}: ${amount:,.2f}" + (f" (PO: {po})" if po else ""))
        lines.append("")

    lines.append("-" * 60)
    lines.append("END OF PARTS EXPOSURE SUMMARY")
    lines.append("-" * 60)

    return "\n".join(lines)


def generate_dispute_pack_zip(
    estimate_data: Dict[str, Any],
    panels: List[Dict[str, Any]],
    photos: List[Dict[str, Any]],
    supplements: List[Dict[str, Any]],
    activities: List[Dict[str, Any]],
    tenant_name: str = "HailTracker Pro",
    ri_summary: Optional[Dict[str, Any]] = None,
    ri_denial_pack: Optional[Dict[str, Any]] = None,
    parts_requests: Optional[List[Dict[str, Any]]] = None
) -> io.BytesIO:
    """
    Generate a ZIP file containing all dispute pack documents.

    Args:
        estimate_data: The estimate dictionary with all fields
        panels: List of panel damage records
        photos: List of photo records with URLs
        supplements: List of supplement records
        activities: List of activity records
        tenant_name: Company name for branding
        ri_summary: R&I operations summary (Phase 7C)
        ri_denial_pack: R&I denial pack with ammo (Phase 7C)
        parts_requests: List of parts requests (Phase 7C)

    Returns:
        BytesIO containing the ZIP file
    """
    estimate_number = estimate_data.get('estimate_number', 'EST-0000')
    safe_estimate_number = estimate_number.replace('/', '-').replace('\\', '-')

    # Create ZIP in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. Estimate PDF
        try:
            estimate_pdf = generate_pdr_estimate_pdf(
                estimate_data=estimate_data,
                panels=panels,
                photos=photos,
                tenant_name=tenant_name
            )
            zf.writestr(
                f"Estimate-{safe_estimate_number}.pdf",
                estimate_pdf.getvalue()
            )
        except Exception as e:
            # Log error but continue
            error_content = f"Error generating Estimate PDF: {str(e)}"
            zf.writestr(f"Estimate-{safe_estimate_number}-ERROR.txt", error_content)

        # 2. Photo Sheet PDF (only if photos exist)
        if photos:
            try:
                photo_sheet_pdf = generate_photo_sheet_pdf(
                    estimate_data=estimate_data,
                    photos=photos,
                    tenant_name=tenant_name
                )
                zf.writestr(
                    f"PhotoSheet-{safe_estimate_number}.pdf",
                    photo_sheet_pdf.getvalue()
                )
            except Exception as e:
                error_content = f"Error generating Photo Sheet PDF: {str(e)}"
                zf.writestr(f"PhotoSheet-{safe_estimate_number}-ERROR.txt", error_content)

        # 3. Supplement PDFs (for each supplement)
        for supp in supplements:
            try:
                supp_id = supp.get('id', 0)
                supp_num = supp.get('supplement_number', 0)
                created_at = supp.get('created_at')

                if isinstance(created_at, datetime):
                    date_str = created_at.strftime('%Y%m%d')
                elif isinstance(created_at, str):
                    # Parse ISO format
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        date_str = dt.strftime('%Y%m%d')
                    except:
                        date_str = 'unknown'
                else:
                    date_str = 'unknown'

                # Get supplement photos if available
                supp_photos = supp.get('photos', [])

                supp_pdf = generate_supplement_pdf(
                    estimate_data=estimate_data,
                    supplement_data=supp,
                    photos=supp_photos,
                    tenant_name=tenant_name
                )

                zf.writestr(
                    f"Supplement-{supp_num}-{date_str}.pdf",
                    supp_pdf.getvalue()
                )
            except Exception as e:
                error_content = f"Error generating Supplement PDF: {str(e)}"
                zf.writestr(f"Supplement-{supp_num}-ERROR.txt", error_content)

        # 4. Activity Log (text file)
        try:
            activity_log = generate_activity_log_text(
                estimate_data=estimate_data,
                activities=activities,
                supplements=supplements
            )
            zf.writestr(
                f"ActivityLog-{safe_estimate_number}.txt",
                activity_log.encode('utf-8')
            )
        except Exception as e:
            error_content = f"Error generating Activity Log: {str(e)}"
            zf.writestr(f"ActivityLog-{safe_estimate_number}-ERROR.txt", error_content)

        # Phase 7C: Additional dispute pack artifacts

        # 5. Denial Ammo (text file)
        if ri_denial_pack:
            try:
                denial_ammo = generate_denial_ammo_text(ri_denial_pack)
                if denial_ammo:
                    zf.writestr(
                        f"DenialAmmo-{safe_estimate_number}.txt",
                        denial_ammo.encode('utf-8')
                    )
            except Exception as e:
                error_content = f"Error generating Denial Ammo: {str(e)}"
                zf.writestr(f"DenialAmmo-{safe_estimate_number}-ERROR.txt", error_content)

        # 6. R&I Summary (JSON)
        if ri_summary:
            try:
                ri_json = generate_ri_summary_json(ri_summary)
                if ri_json:
                    zf.writestr(
                        f"RI-Summary-{safe_estimate_number}.json",
                        ri_json.encode('utf-8')
                    )
            except Exception as e:
                error_content = f"Error generating R&I Summary: {str(e)}"
                zf.writestr(f"RI-Summary-{safe_estimate_number}-ERROR.txt", error_content)

        # 7. Parts Requests (CSV)
        if parts_requests:
            try:
                parts_csv = generate_parts_requests_csv(parts_requests)
                if parts_csv:
                    zf.writestr(
                        f"PartsRequests-{safe_estimate_number}.csv",
                        parts_csv.encode('utf-8')
                    )
            except Exception as e:
                error_content = f"Error generating Parts CSV: {str(e)}"
                zf.writestr(f"PartsRequests-{safe_estimate_number}-ERROR.txt", error_content)

        # 8. Parts Exposure Summary (text file)
        if parts_requests:
            try:
                parts_exposure = generate_parts_exposure_text(parts_requests, estimate_data)
                if parts_exposure:
                    zf.writestr(
                        f"PartsExposure-{safe_estimate_number}.txt",
                        parts_exposure.encode('utf-8')
                    )
            except Exception as e:
                error_content = f"Error generating Parts Exposure: {str(e)}"
                zf.writestr(f"PartsExposure-{safe_estimate_number}-ERROR.txt", error_content)

    zip_buffer.seek(0)
    return zip_buffer


def get_dispute_pack_filename(estimate_number: str) -> str:
    """Generate the filename for the dispute pack ZIP."""
    safe_number = estimate_number.replace('/', '-').replace('\\', '-')
    return f"DisputePack-Estimate-{safe_number}.zip"
