import os
from html import escape
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.schemas.expense import ManagerAuditReport


class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "localhost")
        self.smtp_port = int(os.getenv("SMTP_PORT", "1025"))
        self.manager_email = os.getenv("MANAGER_EMAIL", "manager@company.com")

    def send_audit_report(self, report: ManagerAuditReport):
        subject = f"[ACTION REQUIRED] Expense Audit: {"[DEMO DATA] " if report.trip_or_purpose.startswith("DEMO DATA:") else ""}{report.employee_name} (${report.total_requested:.2f})"
        html_content = self._build_html_email(report)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = "audit-agent@company.com"
        msg["To"] = self.manager_email

        msg.attach(MIMEText(report.summary_for_manager, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
            server.sendmail("audit-agent@company.com", [self.manager_email], msg.as_string())

        print(f"Audit report email successfully sent to {self.manager_email} via SMTP ({self.smtp_host}:{self.smtp_port}).")

    def _build_html_email(self, report: ManagerAuditReport) -> str:
        items_html = ""
        for audit in report.itemized_audit:
            icon = "✓" if audit.is_compliant else "✕"
            violation_text = (
                f"<div style='color: #dc2626; font-size: 12px; margin-top: 4px;'>Violation: {escape('; '.join(audit.violations))}</div>"
                if audit.violations
                else ""
            )

            items_html += f"""
            <div style="border-left: 4px solid {'#16a34a' if audit.is_compliant else '#dc2626'}; padding: 10px; margin-bottom: 8px; background-color: {'#f0fdf4' if audit.is_compliant else '#fef2f2'}; border-radius: 0 6px 6px 0;">
                <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 14px;">
                    <span>{icon} {escape(audit.item.description)} ({audit.item.category.value.title()})</span>
                    <span>${audit.item.amount:.2f}</span>
                </div>
                {violation_text}
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f6f8fc; padding: 20px;">
            <div style="background: #ffffff; max-width: 650px; margin: 0 auto; border-radius: 8px; padding: 24px; border: 1px solid #e0e0e0;">
                <h2 style="color: #1e293b; margin-top: 0;">Expense Audit Report (POL-2026-EXP)</h2>
                <div style="background-color: #fef3c7; color: #92400e; padding: 6px 12px; border-radius: 4px; font-weight: bold; display: inline-block; margin-bottom: 16px;">
                    STATUS: {report.overall_status.value}
                </div>

                <table style="width: 100%; text-align: center; background: #f8fafc; border-radius: 6px; padding: 12px; margin-bottom: 20px;">
                    <tr>
                        <td><strong>Employee:</strong><br>{escape(report.employee_name)}</td>
                        <td><strong>Requested:</strong><br>${report.total_requested:.2f}</td>
                        <td><strong>Compliant Amount:</strong><br><span style="color: #16a34a; font-weight: bold;">${report.total_compliant:.2f}</span></td>
                    </tr>
                </table>

                <h3 style="color: #475569; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px;">Itemized Breakdown</h3>
                {items_html}

                <div style="background: #f1f5f9; padding: 14px; border-radius: 6px; margin-top: 20px;">
                    <strong style="color: #334155;">RECOMMENDED ACTION FOR MANAGER:</strong>
                    <ol style="margin-top: 8px;">
                        <li><strong>Approve Compliant Amount Only (${report.total_compliant:.2f})</strong> [Default]</li>
                        <li>Reject Entire Submission (${report.total_requested:.2f})</li>
                        <li>Approve Full Amount (${report.total_requested:.2f}) [Requires Exception Override]</li>
                    </ol>
                    <p style="font-size: 12px; color: #475569;">Reply processing is not implemented yet. Planned commands: <code>"APPROVE COMPLIANT"</code> | <code>"REJECT"</code> | <code>"APPROVE ALL"</code></p>
                </div>
            </div>
        </body>
        </html>
        """
