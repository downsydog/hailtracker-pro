"""
Portal API Routes
=================
RESTful API for customer portal (frontend React app).

Endpoints:
- GET  /api/portal/jobs          - List customer jobs
- GET  /api/portal/jobs/:id      - Get job details with timeline, photos, documents
- GET  /api/portal/jobs/:id/photos - Get job photos
- GET  /api/portal/dashboard     - Dashboard data
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
import random

portal_api_bp = Blueprint('portal_api', __name__, url_prefix='/api/portal')


# Demo data for testing
DEMO_JOBS = [
    {
        "id": 1,
        "job_number": "JOB-2026-001",
        "vehicle_year": 2023,
        "vehicle_make": "Toyota",
        "vehicle_model": "Camry",
        "vehicle_color": "Silver",
        "vehicle_vin": "1HGBH41JXMN109186",
        "status": "IN_PROGRESS",
        "status_label": "In Progress",
        "damage_type": "Hail Damage",
        "estimated_completion": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
        "scheduled_date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
        "tech_name": "Mike Johnson",
        "tech_photo": None,
        "progress_percent": 65,
        "photos_count": 8,
        "documents_count": 3,
        "messages_count": 5,
        "created_at": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
        "updated_at": datetime.now().strftime("%Y-%m-%d"),
    },
    {
        "id": 2,
        "job_number": "JOB-2026-002",
        "vehicle_year": 2022,
        "vehicle_make": "Honda",
        "vehicle_model": "Accord",
        "vehicle_color": "Blue",
        "vehicle_vin": "2HGFC2F59MH123456",
        "status": "READY_FOR_PICKUP",
        "status_label": "Ready for Pickup",
        "damage_type": "Hail Damage",
        "estimated_completion": datetime.now().strftime("%Y-%m-%d"),
        "scheduled_date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "tech_name": "Sarah Williams",
        "tech_photo": None,
        "progress_percent": 100,
        "photos_count": 12,
        "documents_count": 4,
        "messages_count": 3,
        "created_at": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "updated_at": datetime.now().strftime("%Y-%m-%d"),
    },
    {
        "id": 3,
        "job_number": "JOB-2025-089",
        "vehicle_year": 2021,
        "vehicle_make": "Ford",
        "vehicle_model": "F-150",
        "vehicle_color": "White",
        "vehicle_vin": "1FTFW1E50MFA12345",
        "status": "COMPLETED",
        "status_label": "Completed",
        "damage_type": "Hail Damage",
        "estimated_completion": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        "scheduled_date": (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d"),
        "tech_name": "Mike Johnson",
        "tech_photo": None,
        "progress_percent": 100,
        "photos_count": 15,
        "documents_count": 5,
        "messages_count": 8,
        "created_at": (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d"),
        "updated_at": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
    },
]


def get_job_timeline(job_id):
    """Generate timeline events for a job"""
    base_date = datetime.now() - timedelta(days=3)
    return [
        {
            "id": 1,
            "type": "check_in",
            "title": "Vehicle Checked In",
            "description": "Your vehicle was received at our facility",
            "timestamp": base_date.strftime("%Y-%m-%dT09:30:00"),
            "color": "blue",
        },
        {
            "id": 2,
            "type": "document",
            "title": "Estimate Created",
            "description": "Initial damage assessment completed - $3,450",
            "timestamp": (base_date + timedelta(hours=4)).strftime("%Y-%m-%dT14:00:00"),
            "color": "blue",
        },
        {
            "id": 3,
            "type": "in_progress",
            "title": "Repair Started",
            "description": "Technician has begun repairs on your vehicle",
            "timestamp": (base_date + timedelta(days=1)).strftime("%Y-%m-%dT08:00:00"),
            "color": "yellow",
        },
        {
            "id": 4,
            "type": "photo",
            "title": "Progress Photos Added",
            "description": "New photos documenting repair progress",
            "timestamp": (base_date + timedelta(days=2)).strftime("%Y-%m-%dT15:30:00"),
            "color": "blue",
        },
    ]


def get_job_photos(job_id):
    """Generate photos for a job"""
    # Use picsum.photos for real placeholder images
    base_date = datetime.now() - timedelta(days=3)
    return [
        {
            "id": 1,
            "url": "https://picsum.photos/seed/hail1/800/600",
            "thumbnail_url": "https://picsum.photos/seed/hail1/200/150",
            "type": "before",
            "description": "Hood damage - multiple dents visible",
            "uploaded_at": base_date.strftime("%Y-%m-%d"),
        },
        {
            "id": 2,
            "url": "https://picsum.photos/seed/hail2/800/600",
            "thumbnail_url": "https://picsum.photos/seed/hail2/200/150",
            "type": "before",
            "description": "Roof damage overview",
            "uploaded_at": base_date.strftime("%Y-%m-%d"),
        },
        {
            "id": 3,
            "url": "https://picsum.photos/seed/hail3/800/600",
            "thumbnail_url": "https://picsum.photos/seed/hail3/200/150",
            "type": "before",
            "description": "Trunk lid damage",
            "uploaded_at": base_date.strftime("%Y-%m-%d"),
        },
        {
            "id": 4,
            "url": "https://picsum.photos/seed/hail4/800/600",
            "thumbnail_url": "https://picsum.photos/seed/hail4/200/150",
            "type": "during",
            "description": "Hood repair in progress - 50% complete",
            "uploaded_at": (base_date + timedelta(days=2)).strftime("%Y-%m-%d"),
        },
        {
            "id": 5,
            "url": "https://picsum.photos/seed/hail5/800/600",
            "thumbnail_url": "https://picsum.photos/seed/hail5/200/150",
            "type": "during",
            "description": "Roof repair - PDR tools in use",
            "uploaded_at": (base_date + timedelta(days=2)).strftime("%Y-%m-%d"),
        },
        {
            "id": 6,
            "url": "https://picsum.photos/seed/hail6/800/600",
            "thumbnail_url": "https://picsum.photos/seed/hail6/200/150",
            "type": "after",
            "description": "Hood repair completed - no visible dents",
            "uploaded_at": (base_date + timedelta(days=3)).strftime("%Y-%m-%d"),
        },
        {
            "id": 7,
            "url": "https://picsum.photos/seed/hail7/800/600",
            "thumbnail_url": "https://picsum.photos/seed/hail7/200/150",
            "type": "after",
            "description": "Roof repair completed",
            "uploaded_at": (base_date + timedelta(days=3)).strftime("%Y-%m-%d"),
        },
        {
            "id": 8,
            "url": "https://picsum.photos/seed/hail8/800/600",
            "thumbnail_url": "https://picsum.photos/seed/hail8/200/150",
            "type": "after",
            "description": "Final inspection - all panels repaired",
            "uploaded_at": (base_date + timedelta(days=3)).strftime("%Y-%m-%d"),
        },
    ]


def get_job_documents(job_id):
    """Generate documents for a job"""
    base_date = datetime.now() - timedelta(days=3)
    return [
        {
            "id": 1,
            "type": "estimate",
            "name": "Initial Repair Estimate",
            "url": "#",
            "created_at": base_date.strftime("%Y-%m-%d"),
        },
        {
            "id": 2,
            "type": "insurance",
            "name": "Insurance Authorization",
            "url": "#",
            "created_at": (base_date + timedelta(days=1)).strftime("%Y-%m-%d"),
        },
        {
            "id": 3,
            "type": "other",
            "name": "Vehicle Inspection Report",
            "url": "#",
            "created_at": base_date.strftime("%Y-%m-%d"),
        },
    ]


def get_job_estimate(job_id):
    """Generate estimate for a job"""
    base_date = datetime.now() - timedelta(days=3)
    return {
        "id": 1,
        "estimate_number": f"EST-2026-{job_id:03d}",
        "subtotal": 3200.00,
        "tax": 264.00,
        "total": 3464.00,
        "status": "approved",
        "items": [
            {"id": 1, "service_type": "PDR", "description": "Hood - PDR repair (42 dents)", "quantity": 1, "unit_price": 750.00, "total": 750.00},
            {"id": 2, "service_type": "PDR", "description": "Roof - PDR repair (65 dents)", "quantity": 1, "unit_price": 950.00, "total": 950.00},
            {"id": 3, "service_type": "PDR", "description": "Trunk - PDR repair (28 dents)", "quantity": 1, "unit_price": 550.00, "total": 550.00},
            {"id": 4, "service_type": "PDR", "description": "Left Fender - PDR repair", "quantity": 1, "unit_price": 475.00, "total": 475.00},
            {"id": 5, "service_type": "PDR", "description": "Right Fender - PDR repair", "quantity": 1, "unit_price": 475.00, "total": 475.00},
        ],
        "created_at": base_date.strftime("%Y-%m-%d"),
        "approved_at": (base_date + timedelta(days=1)).strftime("%Y-%m-%d"),
    }


# ============================================================================
# API Routes
# ============================================================================

@portal_api_bp.route('/jobs')
def list_jobs():
    """List all jobs for the customer"""
    return jsonify({"jobs": DEMO_JOBS})


@portal_api_bp.route('/jobs/<int:job_id>')
def get_job(job_id):
    """Get job details with timeline, photos, documents, estimate"""
    job = next((j for j in DEMO_JOBS if j["id"] == job_id), None)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Build full job detail
    job_detail = {
        **job,
        "timeline": get_job_timeline(job_id),
        "photos": get_job_photos(job_id),
        "documents": get_job_documents(job_id),
        "estimate": get_job_estimate(job_id),
    }

    return jsonify(job_detail)


@portal_api_bp.route('/jobs/<int:job_id>/photos')
def get_photos(job_id):
    """Get photos for a specific job"""
    job = next((j for j in DEMO_JOBS if j["id"] == job_id), None)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({"photos": get_job_photos(job_id)})


@portal_api_bp.route('/jobs/<int:job_id>/timeline')
def get_timeline(job_id):
    """Get timeline events for a job"""
    job = next((j for j in DEMO_JOBS if j["id"] == job_id), None)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({"events": get_job_timeline(job_id)})


@portal_api_bp.route('/dashboard')
def get_dashboard():
    """Get dashboard data"""
    active_jobs = [j for j in DEMO_JOBS if j["status"] in ["IN_PROGRESS", "READY_FOR_PICKUP", "CHECKED_IN"]]
    completed_jobs = [j for j in DEMO_JOBS if j["status"] == "COMPLETED"]

    return jsonify({
        "customer": {
            "id": 1,
            "first_name": "John",
            "last_name": "Smith",
            "email": "john.smith@example.com",
            "phone": "(555) 123-4567",
        },
        "active_jobs": active_jobs,
        "completed_jobs": completed_jobs,
        "upcoming_appointments": [
            {
                "id": 1,
                "job_id": 1,
                "type": "pick_up",
                "scheduled_at": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%dT14:00:00"),
                "location": "123 Main St, Dallas, TX",
                "notes": "Vehicle will be ready for pickup",
                "status": "scheduled",
            }
        ],
        "unread_messages": 2,
        "pending_actions": [
            {
                "id": "1",
                "type": "approve_estimate",
                "title": "Approve Supplemental Estimate",
                "description": "Additional repairs found - please review and approve",
                "job_id": 1,
                "priority": "high",
            }
        ],
    })


@portal_api_bp.route('/documents')
def list_documents():
    """List all documents"""
    job_id = request.args.get('job_id', type=int)

    if job_id:
        return jsonify({"documents": get_job_documents(job_id)})

    # Return documents for all jobs
    all_docs = []
    for job in DEMO_JOBS:
        docs = get_job_documents(job["id"])
        for doc in docs:
            doc["job_id"] = job["id"]
            doc["job_number"] = job["job_number"]
        all_docs.extend(docs)

    return jsonify({"documents": all_docs})


@portal_api_bp.route('/messages')
def list_messages():
    """List messages"""
    job_id = request.args.get('job_id', type=int)

    messages = [
        {
            "id": 1,
            "job_id": 1,
            "sender_type": "staff",
            "sender_name": "Mike Johnson",
            "message": "Hi! Your vehicle is progressing well. We've completed the hood and are moving to the roof today.",
            "read_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
        },
        {
            "id": 2,
            "job_id": 1,
            "sender_type": "customer",
            "sender_name": "John Smith",
            "message": "Thanks for the update! Any estimate on completion time?",
            "read_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "created_at": (datetime.now() - timedelta(hours=20)).isoformat(),
        },
        {
            "id": 3,
            "job_id": 1,
            "sender_type": "staff",
            "sender_name": "Mike Johnson",
            "message": "We're on track for completion by Friday. I'll send photos once the roof is done.",
            "read_at": None,
            "created_at": (datetime.now() - timedelta(hours=5)).isoformat(),
        },
    ]

    if job_id:
        messages = [m for m in messages if m["job_id"] == job_id]

    return jsonify({"messages": messages})


@portal_api_bp.route('/appointments')
def list_appointments():
    """List appointments"""
    return jsonify({
        "appointments": [
            {
                "id": 1,
                "job_id": 1,
                "type": "drop_off",
                "scheduled_at": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%dT09:00:00"),
                "location": "HailTracker Pro - Dallas",
                "notes": "Vehicle dropped off",
                "status": "completed",
            },
            {
                "id": 2,
                "job_id": 1,
                "type": "pick_up",
                "scheduled_at": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%dT14:00:00"),
                "location": "HailTracker Pro - Dallas",
                "notes": "Estimated pickup date",
                "status": "scheduled",
            },
        ]
    })


@portal_api_bp.route('/profile')
def get_profile():
    """Get customer profile"""
    return jsonify({
        "id": 1,
        "first_name": "John",
        "last_name": "Smith",
        "email": "john.smith@example.com",
        "phone": "(555) 123-4567",
    })
