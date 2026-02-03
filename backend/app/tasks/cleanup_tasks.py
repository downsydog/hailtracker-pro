"""
Cleanup Tasks
=============
Background tasks for cleaning up expired data.
"""

from datetime import datetime
from app.celery_app import celery_app
from app.extensions import db
from app.models.master.storm import Storm
from app.models.master.business import StormBusiness


@celery_app.task
def cleanup_expired_storms():
    """
    Clean up storms that have expired (older than 29 days).
    Runs daily via Celery Beat.

    Returns:
        Dictionary with cleanup stats
    """
    from app import create_app
    app = create_app()

    with app.app_context():
        # Find expired storms
        expired_storms = Storm.query.filter(
            Storm.expires_at < datetime.utcnow(),
            Storm.status == 'ready'
        ).all()

        cleaned = 0

        for storm in expired_storms:
            # Remove business links
            StormBusiness.query.filter_by(storm_id=storm.id).delete()

            # Mark as expired
            storm.status = 'expired'
            storm.business_count = 0

            cleaned += 1

        db.session.commit()

        return {
            'cleaned_storms': cleaned,
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task
def cleanup_orphaned_businesses():
    """
    Remove businesses that are not linked to any storm.

    Returns:
        Dictionary with deletion count
    """
    from app import create_app
    from app.models.master.business import Business
    from sqlalchemy import not_, exists

    app = create_app()

    with app.app_context():
        # Find businesses with no storm links
        orphaned = Business.query.filter(
            not_(exists().where(StormBusiness.business_id == Business.id))
        ).all()

        count = len(orphaned)

        for biz in orphaned:
            db.session.delete(biz)

        db.session.commit()

        return {'deleted_businesses': count}


@celery_app.task
def cleanup_old_api_usage():
    """
    Clean up API usage records older than 90 days.

    Returns:
        Dictionary with deletion count
    """
    from datetime import timedelta
    from app import create_app
    from app.models.master.api_usage import ApiUsage

    app = create_app()

    with app.app_context():
        cutoff = datetime.utcnow().date() - timedelta(days=90)

        deleted = ApiUsage.query.filter(ApiUsage.date < cutoff).delete()

        db.session.commit()

        return {'deleted_records': deleted}
