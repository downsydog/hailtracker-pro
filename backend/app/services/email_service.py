"""
Email Service for sending estimate packages to adjusters.

Supports:
- SMTP sending when configured (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS)
- Dev fallback that writes .eml files to app/tmp/outbox/
"""

import os
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr, formatdate
from datetime import datetime
from typing import Optional, List, Dict, Any
from io import BytesIO

from flask import current_app

from app.models.tenant import EstimateActivity
from app.services.pdf_generator import generate_estimate_pdf
from app.services.photo_sheet_generator import generate_photo_sheet


class EmailResult:
    """Result of an email send attempt."""

    def __init__(self, success: bool, message_id: str = None, error: str = None):
        self.success = success
        self.message_id = message_id
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': 'sent' if self.success else 'failed',
            'message_id': self.message_id,
            'error': self.error
        }


class EmailService:
    """
    Service for sending estimate packages via email.

    Usage:
        service = EmailService()
        result = service.send_estimate_package(
            estimate_id=123,
            to='adjuster@insurance.com',
            cc=['shop@example.com'],
            subject='Estimate #EST-123',
            message='Please review the attached estimate.'
        )
    """

    def __init__(self):
        self.smtp_host = os.environ.get('SMTP_HOST')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_user = os.environ.get('SMTP_USER')
        self.smtp_pass = os.environ.get('SMTP_PASS')
        self.smtp_from = os.environ.get('SMTP_FROM', self.smtp_user)
        self.smtp_from_name = os.environ.get('SMTP_FROM_NAME', 'HailTracker Pro')
        self.smtp_use_tls = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'

        # Dev mode outbox directory
        self.dev_outbox = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'tmp', 'outbox'
        )

    @property
    def is_configured(self) -> bool:
        """Check if SMTP is configured."""
        return bool(self.smtp_host and self.smtp_user and self.smtp_pass)

    def send_simple(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None
    ) -> EmailResult:
        """
        Send a simple plain text email without attachments.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Plain text body
            cc: Optional list of CC addresses

        Returns:
            EmailResult with success status and message_id or error
        """
        try:
            # Use SMTP if configured, otherwise dev mode
            if self.is_configured:
                result = self._send_smtp(to, cc, subject, body, [])
            else:
                result = self._send_dev_mode(to, cc, subject, body, [])

            return result

        except Exception as e:
            error_msg = str(e)
            current_app.logger.error(f"Simple email send error: {error_msg}")
            return EmailResult(False, error=error_msg)

    def send_estimate_package(
        self,
        estimate_id: int,
        to: str,
        cc: Optional[List[str]] = None,
        subject: Optional[str] = None,
        message: Optional[str] = None,
        user_id: Optional[int] = None,
        estimate_data: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[int] = None
    ) -> EmailResult:
        """
        Send estimate PDF + photo sheet to an adjuster.

        Args:
            estimate_id: The estimate to send
            to: Recipient email address
            cc: Optional list of CC addresses
            subject: Optional custom subject (auto-generated if not provided)
            message: Optional custom message body
            user_id: Optional user ID for activity logging
            estimate_data: Optional dict with estimate data (fetched from DB if not provided)
            tenant_id: Optional tenant ID for shop info

        Returns:
            EmailResult with success status and message_id or error
        """
        try:
            # Use provided estimate_data or fetch from database
            if not estimate_data:
                # Try to fetch from database (PDR estimates table)
                # For now, use placeholder data if not found
                estimate_data = self._fetch_estimate_data(estimate_id)

            if not estimate_data:
                return EmailResult(False, error='Estimate not found')

            # Extract estimate info
            vehicle_year = estimate_data.get('vehicle_year', '')
            vehicle_make = estimate_data.get('vehicle_make', '')
            vehicle_model = estimate_data.get('vehicle_model', '')
            vehicle_info = f"{vehicle_year} {vehicle_make} {vehicle_model}".strip()
            estimate_num = estimate_data.get('estimate_number') or f"EST-{estimate_id}"
            customer_name = estimate_data.get('customer_name', '')
            vin = estimate_data.get('vin', '')

            # Build default subject if not provided
            if not subject:
                subject = f"Estimate {estimate_num} — {vehicle_info}" if vehicle_info else f"Estimate {estimate_num}"

            # Build default message if not provided
            if not message:
                message = self._default_message_from_data(estimate_data, estimate_num)

            # Get shop info
            shop_info = self._get_shop_info(tenant_id)

            # Generate PDFs in memory
            estimate_pdf = self._generate_estimate_pdf(estimate_data, shop_info)
            photosheet_pdf = self._generate_photosheet_pdf(estimate_id, estimate_data, shop_info)

            # Build attachments list
            attachments = []
            estimate_filename = f"Estimate-{estimate_num}.pdf"
            photosheet_filename = f"PhotoSheet-{estimate_num}.pdf"

            if estimate_pdf:
                attachments.append((estimate_filename, estimate_pdf, 'application/pdf'))
            if photosheet_pdf:
                attachments.append((photosheet_filename, photosheet_pdf, 'application/pdf'))

            # Send email
            if self.is_configured:
                result = self._send_smtp(to, cc, subject, message, attachments)
            else:
                result = self._send_dev_mode(to, cc, subject, message, attachments)

            # Log activity
            activity_metadata = {
                'to': to,
                'cc': cc or [],
                'subject': subject,
                'attachments': [a[0] for a in attachments],
                'message_id': result.message_id
            }

            if result.success:
                EstimateActivity.log(
                    estimate_id=estimate_id,
                    activity_type='email_sent',
                    user_id=user_id,
                    activity_data=activity_metadata
                )
            else:
                activity_metadata['error'] = result.error
                EstimateActivity.log(
                    estimate_id=estimate_id,
                    activity_type='email_failed',
                    user_id=user_id,
                    activity_data=activity_metadata
                )

            return result

        except Exception as e:
            error_msg = str(e)
            current_app.logger.error(f"Email send error: {error_msg}")

            # Log failure
            EstimateActivity.log(
                estimate_id=estimate_id,
                activity_type='email_failed',
                user_id=user_id,
                activity_data={'to': to, 'error': error_msg}
            )

            return EmailResult(False, error=error_msg)

    def _fetch_estimate_data(self, estimate_id: int) -> Optional[Dict[str, Any]]:
        """Fetch estimate data from database."""
        # TODO: Implement proper PDR estimate fetching when model is created
        # For now, return placeholder data
        return {
            'id': estimate_id,
            'estimate_number': f'EST-{estimate_id:05d}',
            'vehicle_year': 2024,
            'vehicle_make': 'Vehicle',
            'vehicle_model': 'Sample',
            'customer_name': 'Customer',
            'panels': [],
            'labor_total': 0,
            'ri_total': 0,
            'total_price': 0
        }

    def _get_shop_info(self, tenant_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """Get shop info for PDF headers."""
        if not tenant_id:
            return None
        try:
            from app.models.master.tenant import Tenant
            tenant = Tenant.query.get(tenant_id)
            if tenant:
                return {'company_name': tenant.company_name}
        except Exception:
            pass
        return None

    def _default_message_from_data(self, estimate_data: Dict[str, Any], estimate_num: str) -> str:
        """Generate default email message body from estimate data."""
        vehicle_year = estimate_data.get('vehicle_year', '')
        vehicle_make = estimate_data.get('vehicle_make', '')
        vehicle_model = estimate_data.get('vehicle_model', '')
        vehicle_info = f"{vehicle_year} {vehicle_make} {vehicle_model}".strip()
        vin = estimate_data.get('vin', '')
        customer_name = estimate_data.get('customer_name', '')

        return f"""Hello,

Please find attached the PDR estimate and photo documentation for:

Vehicle: {vehicle_info or 'N/A'}
Estimate #: {estimate_num}
{f"VIN: {vin}" if vin else ""}
{f"Customer: {customer_name}" if customer_name else ""}

The attached documents include:
- Detailed estimate with panel breakdown and pricing
- Photo sheet with damage documentation

Please review and let us know if you have any questions or need additional information.

Thank you,
{self.smtp_from_name}
"""

    def _generate_estimate_pdf(self, estimate_data: Dict[str, Any], shop_info: Optional[Dict[str, Any]]) -> Optional[bytes]:
        """Generate estimate PDF in memory."""
        try:
            buffer = generate_estimate_pdf(estimate_data, shop_info)
            return buffer.read()
        except Exception as e:
            current_app.logger.error(f"Failed to generate estimate PDF: {e}")
            return None

    def _generate_photosheet_pdf(self, estimate_id: int, estimate_data: Dict[str, Any], shop_info: Optional[Dict[str, Any]]) -> Optional[bytes]:
        """Generate photo sheet PDF in memory."""
        try:
            from app.models.tenant import EstimatePhoto

            # Get photos for this estimate
            try:
                photos = EstimatePhoto.query.filter_by(estimate_id=estimate_id).all()
                photos_list = [p.to_dict() for p in photos] if photos else []
            except Exception:
                photos_list = []

            buffer = generate_photo_sheet(estimate_data, photos_list, shop_info)
            return buffer.read()
        except Exception as e:
            current_app.logger.error(f"Failed to generate photo sheet PDF: {e}")
            return None

    def _send_smtp(
        self,
        to: str,
        cc: Optional[List[str]],
        subject: str,
        message: str,
        attachments: List[tuple]
    ) -> EmailResult:
        """Send email via SMTP."""
        try:
            # Build message
            msg = MIMEMultipart()
            msg['From'] = formataddr((self.smtp_from_name, self.smtp_from))
            msg['To'] = to
            if cc:
                msg['Cc'] = ', '.join(cc)
            msg['Subject'] = subject
            msg['Date'] = formatdate(localtime=True)

            # Generate message ID
            message_id = f"<{uuid.uuid4()}@hailtracker.pro>"
            msg['Message-ID'] = message_id

            # Add body
            msg.attach(MIMEText(message, 'plain'))

            # Add attachments
            for filename, content, content_type in attachments:
                part = MIMEApplication(content, Name=filename)
                part['Content-Disposition'] = f'attachment; filename="{filename}"'
                msg.attach(part)

            # Send via SMTP
            recipients = [to] + (cc or [])

            if self.smtp_use_tls:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.smtp_from, recipients, msg.as_string())
            else:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.smtp_from, recipients, msg.as_string())

            return EmailResult(True, message_id=message_id)

        except smtplib.SMTPException as e:
            return EmailResult(False, error=f"SMTP error: {str(e)}")
        except Exception as e:
            return EmailResult(False, error=str(e))

    def _send_dev_mode(
        self,
        to: str,
        cc: Optional[List[str]],
        subject: str,
        message: str,
        attachments: List[tuple]
    ) -> EmailResult:
        """
        Dev mode: write email to .eml file instead of sending.
        """
        try:
            # Ensure outbox directory exists
            os.makedirs(self.dev_outbox, exist_ok=True)

            # Build message
            msg = MIMEMultipart()
            msg['From'] = formataddr((self.smtp_from_name, 'dev@localhost'))
            msg['To'] = to
            if cc:
                msg['Cc'] = ', '.join(cc)
            msg['Subject'] = subject
            msg['Date'] = formatdate(localtime=True)

            # Generate message ID
            message_id = f"<dev-{uuid.uuid4()}@localhost>"
            msg['Message-ID'] = message_id

            # Add body
            msg.attach(MIMEText(message, 'plain'))

            # Add attachments
            for filename, content, content_type in attachments:
                part = MIMEApplication(content, Name=filename)
                part['Content-Disposition'] = f'attachment; filename="{filename}"'
                msg.attach(part)

            # Write to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_to = to.replace('@', '_at_').replace('.', '_')
            filename = f"{timestamp}_{safe_to}.eml"
            filepath = os.path.join(self.dev_outbox, filename)

            with open(filepath, 'w') as f:
                f.write(msg.as_string())

            current_app.logger.info(f"[DEV] Email written to: {filepath}")

            return EmailResult(True, message_id=f"{message_id} (dev-mode)")

        except Exception as e:
            return EmailResult(False, error=f"Dev mode error: {str(e)}")


# Singleton instance
_email_service = None


def get_email_service() -> EmailService:
    """Get the email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
