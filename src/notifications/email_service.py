"""
HC-XCDSS Real Transactional Email Service

Handles real SMTP-based transactional email delivery for administrator alerts, professional
verification approvals, and rejections, with a resilient fallback and safe development mode.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import logging
from dotenv import load_dotenv

logger = logging.getLogger("hc_xcdss.email")


def get_env_setting(keys: list, default: str = "") -> str:
    """Helper to retrieve first non-empty value from a list of environment variable names."""
    for k in keys:
        v = os.getenv(k)
        if v is not None and v.strip() != "":
            return v.strip()
    return default


class EmailService:
    """
    Centralized transactional email service for HC-XCDSS.
    """

    @classmethod
    def get_smtp_config(cls) -> Dict[str, Any]:
        """Retrieves and normalizes SMTP configuration from environment."""
        load_dotenv(override=True)
        host = get_env_setting(["SMTP_HOST", "MAIL_HOST", "EMAIL_HOST"], "smtp-relay.brevo.com")
        port_str = get_env_setting(["SMTP_PORT", "MAIL_PORT", "EMAIL_PORT"], "587")
        try:
            port = int(port_str)
        except ValueError:
            port = 587

        username = get_env_setting(["SMTP_USERNAME", "SMTP_USER", "MAIL_USERNAME", "EMAIL_USER"], "")
        password = get_env_setting(["SMTP_PASSWORD", "SMTP_PASS", "MAIL_PASSWORD", "EMAIL_PASSWORD"], "")
        
        use_tls_str = get_env_setting(["SMTP_USE_TLS", "SMTP_TLS", "MAIL_USE_TLS"], "true").lower()
        use_tls = use_tls_str in ("true", "1", "yes")

        from_email = get_env_setting(["SMTP_FROM_EMAIL", "EMAIL_FROM", "MAIL_FROM"], "hcxcdss.support@gmail.com")
        admin_email = get_env_setting(["ADMIN_EMAIL", "HC_ADMIN_EMAIL"], "hcxcdss.support@gmail.com")
        app_url = get_env_setting(["APP_BASE_URL", "FRONTEND_URL"], "http://localhost:5173")

        return {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "use_tls": use_tls,
            "from_email": from_email,
            "admin_email": admin_email,
            "app_url": app_url.rstrip("/"),
        }

    @classmethod
    def is_configured(cls) -> bool:
        """Returns True if minimum required SMTP settings are present."""
        cfg = cls.get_smtp_config()
        return bool(cfg["host"] and cfg["username"])

    @classmethod
    def send_email(
        cls,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> bool:
        """
        Sends an email using configured SMTP parameters.
        
        Returns:
            bool: True if delivered via SMTP, False if delivery failed or SMTP is not configured.
        """
        to_email = to_email.strip() if to_email else ""
        if not to_email:
            logger.warning("[EmailService] No recipient email specified.")
            return False

        cfg = cls.get_smtp_config()

        # If SMTP is not configured, do NOT crash or fake delivery
        if not cls.is_configured():
            logger.info(
                f"[EmailService:NOT_CONFIGURED] SMTP delivery is not configured. Email to '{to_email}' "
                f"was not dispatched. (Subject: '{subject}')"
            )
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = formataddr(("HC-XCDSS", cfg["from_email"]))
            msg["To"] = to_email

            part1 = MIMEText(body_text, "plain", "utf-8")
            msg.attach(part1)

            if body_html:
                part2 = MIMEText(body_html, "html", "utf-8")
                msg.attach(part2)

            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
                if cfg["use_tls"]:
                    server.starttls()
                if cfg["username"] and cfg["password"]:
                    try:
                        server.login(cfg["username"], cfg["password"])
                    except smtplib.SMTPAuthenticationError:
                        # Fallback for Gmail app passwords formatted with spaces
                        if " " in cfg["password"]:
                            server.login(cfg["username"], cfg["password"].replace(" ", "").strip())
                        else:
                            raise
                server.sendmail(cfg["from_email"], [to_email], msg.as_string())

            logger.info(f"[EmailService:SENT] Delivered email to '{to_email}' | Subject: '{subject}'")
            return True
        except Exception as e:
            # Safe logging: Never log password or credentials
            logger.error(f"[EmailService:DELIVERY_FAILED] Failed to send email to '{to_email}': {type(e).__name__}: {e}")
            return False

    @classmethod
    def notify_admin_new_professional_registration(
        cls,
        professional_name: str,
        professional_email: str,
        registration_number: Optional[str],
        state_medical_council: Optional[str],
        registration_year: Optional[str] = None,
        specialty: Optional[str] = None,
        location_city: Optional[str] = None,
        location_state: Optional[str] = None,
        submission_timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Sends administrative notification when a new healthcare professional registers.
        Trigger 1: PROFESSIONAL SIGNUP
        """
        cfg = cls.get_smtp_config()
        admin_email = cfg["admin_email"]

        ts_str = (
            submission_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            if submission_timestamp
            else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        location_str = ", ".join(filter(None, [location_city, location_state])) or "Not specified"

        subject = "New Professional Verification Request — HC-XCDSS"

        text = (
            f"Dear Administrator,\n\n"
            f"A new healthcare professional has registered on HC-XCDSS and is awaiting verification.\n\n"
            f"Applicant Details:\n"
            f"• Full Name: {professional_name}\n"
            f"• Email: {professional_email}\n"
            f"• Medical Registration No: {registration_number or 'N/A'}\n"
            f"• State Medical Council: {state_medical_council or 'N/A'}\n"
            f"• Registration Year: {registration_year or 'N/A'}\n"
            f"• Specialty: {specialty or 'General Medicine'}\n"
            f"• Location: {location_str}\n"
            f"• Submitted At: {ts_str}\n\n"
            f"Please sign in to the HC-XCDSS Administrator Dashboard to review this application and inspect the submitted credentials.\n\n"
            f"Portal: {cfg['app_url']}\n\n"
            f"HC-XCDSS Clinical Administration System"
        )

        html = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px;">
          <div style="border-bottom: 2px solid #0284c7; padding-bottom: 12px; margin-bottom: 20px;">
            <h2 style="color: #0284c7; margin: 0; font-size: 20px;">New Professional Verification Request</h2>
            <p style="color: #64748b; margin: 4px 0 0 0; font-size: 13px;">HC-XCDSS Clinical Administration</p>
          </div>
          <p>A new healthcare professional has registered on HC-XCDSS and is awaiting verification.</p>
          <table style="width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px;">
            <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #f1f5f9; width: 40%; color: #475569;">Applicant Name</td><td style="padding: 8px; border-bottom: 1px solid #f1f5f9; font-weight: 600; color: #0f172a;">{professional_name}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #f1f5f9; color: #475569;">Email</td><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">{professional_email}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #f1f5f9; color: #475569;">Registration Number</td><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">{registration_number or 'N/A'}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #f1f5f9; color: #475569;">Medical Council</td><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">{state_medical_council or 'N/A'}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #f1f5f9; color: #475569;">Registration Year</td><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">{registration_year or 'N/A'}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #f1f5f9; color: #475569;">Specialty</td><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">{specialty or 'General Medicine'}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #f1f5f9; color: #475569;">Location</td><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">{location_str}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #f1f5f9; color: #475569;">Submitted At</td><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">{ts_str}</td></tr>
          </table>
          <div style="text-align: center; margin: 24px 0;">
            <a href="{cfg['app_url']}" style="background-color: #0284c7; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; display: inline-block;">Open Admin Verification Dashboard</a>
          </div>
          <p style="margin-top: 24px; font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 12px;">
            HC-XCDSS AI-Assisted Chest X-Ray Decision Support Platform
          </p>
        </div>
        """
        return cls.send_email(admin_email, subject, text, html)

    @classmethod
    def notify_professional_verified(
        cls,
        professional_email: str,
        professional_name: str,
    ) -> bool:
        """
        Sends approval notification to professional upon administrator verification.
        Trigger 2: PROFESSIONAL VERIFICATION APPROVED
        """
        cfg = cls.get_smtp_config()
        subject = "Professional Verification Approved — HC-XCDSS"

        text = (
            f"Dear {professional_name},\n\n"
            f"Your professional credentials have been successfully verified on HC-XCDSS.\n\n"
            f"You can now log in and access the Professional Portal to review assigned chest X-ray cases, "
            f"view AI second-opinion analyses, and submit clinical assessments.\n\n"
            f"Log in here: {cfg['app_url']}\n\n"
            f"Best regards,\n"
            f"HC-XCDSS Clinical Administration Team"
        )

        html = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px;">
          <div style="border-bottom: 2px solid #059669; padding-bottom: 12px; margin-bottom: 20px;">
            <h2 style="color: #059669; margin: 0; font-size: 20px;">Professional Verification Approved</h2>
            <p style="color: #64748b; margin: 4px 0 0 0; font-size: 13px;">HC-XCDSS Clinical Governance</p>
          </div>
          <p>Dear {professional_name},</p>
          <p>Your professional credentials have been successfully verified on HC-XCDSS.</p>
          <div style="background-color: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 6px; padding: 16px; margin: 20px 0;">
            <strong style="color: #065f46; font-size: 15px;">✓ Professional Portal Access Unlocked</strong>
            <p style="margin: 8px 0 0 0; color: #047857; font-size: 13px;">
              You can now log in and access the Professional Portal to review assigned chest X-ray cases, inspect AI findings and Grad-CAM heatmaps, and submit your clinical assessments.
            </p>
          </div>
          <div style="text-align: center; margin: 24px 0;">
            <a href="{cfg['app_url']}" style="background-color: #059669; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; display: inline-block;">Access Professional Portal</a>
          </div>
          <p style="margin-top: 24px; font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 12px;">
            HC-XCDSS Clinical Decision Support Platform
          </p>
        </div>
        """
        return cls.send_email(professional_email, subject, text, html)

    @classmethod
    def notify_professional_rejected(
        cls,
        professional_email: str,
        professional_name: str,
        rejection_reason: str,
    ) -> bool:
        """
        Sends rejection notification with administrative reason to professional.
        Trigger 3: PROFESSIONAL VERIFICATION REJECTED
        """
        cfg = cls.get_smtp_config()
        admin_email = cfg["admin_email"]

        subject = "Professional Verification Update — HC-XCDSS"

        text = (
            f"Dear {professional_name},\n\n"
            f"Thank you for your interest in HC-XCDSS. We are writing to inform you that your professional verification was not approved at this time.\n\n"
            f"Administrator Decision Reason:\n"
            f"{rejection_reason or 'Credentials could not be validated.'}\n\n"
            f"If you wish to provide updated documentation or appeal this decision, please reach out to our administration team at {admin_email}.\n\n"
            f"Best regards,\n"
            f"HC-XCDSS Clinical Administration Team"
        )

        html = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px;">
          <div style="border-bottom: 2px solid #dc2626; padding-bottom: 12px; margin-bottom: 20px;">
            <h2 style="color: #dc2626; margin: 0; font-size: 20px;">Professional Verification Update</h2>
            <p style="color: #64748b; margin: 4px 0 0 0; font-size: 13px;">HC-XCDSS Clinical Administration</p>
          </div>
          <p>Dear {professional_name},</p>
          <p>We have reviewed your submitted credentials for the HC-XCDSS Professional Network. Verification was not approved at this time.</p>
          <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 16px; margin: 20px 0;">
            <strong style="color: #991b1b; font-size: 14px;">Administrator Feedback:</strong>
            <p style="margin: 8px 0 0 0; color: #b91c1c; font-size: 13px; line-height: 1.5;">{rejection_reason or 'Credentials could not be validated.'}</p>
          </div>
          <p style="font-size: 13px; color: #475569;">
            If you wish to submit updated documentation or have questions, please contact our administration team at <a href="mailto:{admin_email}">{admin_email}</a>.
          </p>
          <p style="margin-top: 24px; font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 12px;">
            HC-XCDSS Clinical Decision Support Platform
          </p>
        </div>
        """
        return cls.send_email(professional_email, subject, text, html)

    @classmethod
    def notify_patient_review_completed(
        cls,
        patient_email: str,
        patient_name: str,
        doctor_name: str,
        review_id: str,
    ) -> bool:
        """
        Sends notification to patient that their professional review is completed and available.
        Trigger 4: PROFESSIONAL REVIEW COMPLETED
        Privacy Rule: Does NOT include raw radiological findings, diagnoses, or X-ray image in email.
        """
        cfg = cls.get_smtp_config()
        subject = "Your Professional Review Is Now Available — HC-XCDSS"

        portal_url = cfg["app_url"]

        text = (
            f"Dear {patient_name},\n\n"
            f"Your professional review has been completed and is now available in your HC-XCDSS portal.\n\n"
            f"Reviewing Specialist: {doctor_name}\n"
            f"Review Reference: #{review_id[:8]}\n\n"
            f"Please log in to view the review and report:\n"
            f"{portal_url}\n\n"
            f"Clinical Notice: The professional review is provided as part of this clinical decision-support platform "
            f"and should be considered together with comprehensive clinical evaluation by your primary healthcare provider.\n\n"
            f"Best regards,\n"
            f"HC-XCDSS Clinical Team"
        )

        html = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px;">
          <div style="border-bottom: 2px solid #0284c7; padding-bottom: 12px; margin-bottom: 20px;">
            <h2 style="color: #0284c7; margin: 0; font-size: 20px;">Your Professional Review Is Now Available</h2>
            <p style="color: #64748b; margin: 4px 0 0 0; font-size: 13px;">HC-XCDSS Clinical Decision Support</p>
          </div>
          <p>Dear {patient_name},</p>
          <p>
            Your professional review has been completed and is now available in your HC-XCDSS portal.
          </p>
          <table style="width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; background-color: #f8fafc; border-radius: 6px; padding: 8px;">
            <tr><td style="padding: 10px; font-weight: bold; color: #475569; width: 40%;">Reviewing Specialist</td><td style="padding: 10px; font-weight: 600; color: #0f172a;">{doctor_name}</td></tr>
            <tr><td style="padding: 10px; font-weight: bold; color: #475569;">Review Reference</td><td style="padding: 10px; font-family: monospace; color: #0369a1;">#{review_id[:8]}</td></tr>
          </table>
          <p>Please log in to view the review and report.</p>
          <div style="text-align: center; margin: 24px 0;">
            <a href="{portal_url}" style="background-color: #0284c7; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; display: inline-block;">Log in to View Review & Report</a>
          </div>
          <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; margin: 20px 0; font-size: 12px; color: #64748b;">
            <strong>Clinical Safety Notice:</strong> This review is provided as part of the HC-XCDSS decision-support system. It should be evaluated in consultation with your attending healthcare provider.
          </div>
          <p style="margin-top: 24px; font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 12px;">
            HC-XCDSS Clinical Decision Support Platform
          </p>
        </div>
        """
        return cls.send_email(patient_email, subject, text, html)

    @classmethod
    def notify_professional_review_assigned(
        cls,
        professional_email: str,
        professional_name: str,
        patient_name: str,
        review_id: str,
        analysis_id: str,
    ) -> bool:
        """
        Sends transactional email to a verified professional when a paid review request is assigned to them.
        Privacy Rule: Does NOT include X-ray images, medical findings, predictions, Grad-CAM data, or sensitive medical content.
        """
        cfg = cls.get_smtp_config()
        subject = "New Patient Review Assigned — HC-XCDSS"

        portal_url = cfg["app_url"]

        text = (
            f"Dear {professional_name},\n\n"
            f"A new chest X-ray review consultation has been requested and assigned to you on HC-XCDSS.\n\n"
            f"Consultation Details:\n"
            f"• Patient: {patient_name}\n"
            f"• Review Reference: #{review_id[:8]}\n"
            f"• Analysis Reference: {analysis_id}\n\n"
            f"Please sign in to the HC-XCDSS Professional Portal to access the case workspace, "
            f"review the radiograph and AI inferences, and submit your clinical assessment.\n\n"
            f"Portal: {portal_url}\n\n"
            f"HC-XCDSS Clinical Network"
        )

        html = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px;">
          <div style="border-bottom: 2px solid #0284c7; padding-bottom: 12px; margin-bottom: 20px;">
            <h2 style="color: #0284c7; margin: 0; font-size: 20px;">New Case Review Assigned</h2>
            <p style="color: #64748b; margin: 4px 0 0 0; font-size: 13px;">HC-XCDSS Professional Portal</p>
          </div>
          <p>Dear {professional_name},</p>
          <p>A new chest X-ray review consultation has been requested and assigned to you on HC-XCDSS.</p>
          <table style="width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; background-color: #f8fafc; border-radius: 6px;">
            <tr><td style="padding: 10px; font-weight: bold; color: #475569; width: 40%; border-bottom: 1px solid #f1f5f9;">Patient</td><td style="padding: 10px; font-weight: 600; color: #0f172a; border-bottom: 1px solid #f1f5f9;">{patient_name}</td></tr>
            <tr><td style="padding: 10px; font-weight: bold; color: #475569; border-bottom: 1px solid #f1f5f9;">Review Reference</td><td style="padding: 10px; font-family: monospace; color: #0369a1; border-bottom: 1px solid #f1f5f9;">#{review_id[:8]}</td></tr>
            <tr><td style="padding: 10px; font-weight: bold; color: #475569;">Analysis Reference</td><td style="padding: 10px; font-family: monospace; color: #475569;">{analysis_id}</td></tr>
          </table>
          <p>Please log into your Professional Portal to review the case and complete your clinical assessment.</p>
          <div style="text-align: center; margin: 24px 0;">
            <a href="{portal_url}" style="background-color: #0284c7; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; display: inline-block;">Open Professional Case Workspace</a>
          </div>
          <p style="margin-top: 24px; font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 12px;">
            HC-XCDSS AI-Assisted Decision Support Platform
          </p>
        </div>
        """
        return cls.send_email(professional_email, subject, text, html)
