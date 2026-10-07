import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Alert, Score

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.settings = get_settings()

    async def send_email_alert(
        self,
        score: Score,
        tx: Dict[str, Any],
        reasons: List[str]
    ) -> bool:
        """Sends an HTML alert email via MailHog / SMTP."""
        try:
            subject = f"🚨 [ExpenseGuard] HIGH Risk Expense Detected - ₹{float(tx.get('amount', 0)):,.2f}"
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.settings.SMTP_FROM
            msg["To"] = "auditors@expenseguard.local"

            reasons_html = "".join([f"<li>{r}</li>" for r in reasons])
            html_content = f"""
            <html>
                <body style="font-family: Inter, sans-serif; background-color: #F4F7FE; padding: 20px;">
                    <div style="background-color: #FFFFFF; border-radius: 16px; padding: 24px; max-width: 600px; margin: 0 auto; box-shadow: 0 4px 16px rgba(0,0,0,0.06);">
                        <div style="display: flex; align-items: center; margin-bottom: 16px;">
                            <span style="background-color: #FEE2E2; color: #DC2626; padding: 4px 12px; border-radius: 9999px; font-weight: bold; font-size: 14px;">HIGH RISK TIER</span>
                            <span style="margin-left: 12px; color: #1B2559; font-weight: bold; font-size: 18px;">Risk Score: {score.risk_score}/100</span>
                        </div>
                        <h2 style="color: #1B2559; margin-top: 0;">₹{float(tx.get('amount', 0)):,.2f} at {tx.get('vendor', 'Unknown')}</h2>
                        <p style="color: #6B7280; font-size: 14px;"><strong>Category:</strong> {tx.get('category')} | <strong>Date:</strong> {tx.get('date')}</p>
                        <h4 style="color: #1B2559; margin-bottom: 8px;">Triggered Anomaly Signals:</h4>
                        <ul style="color: #4B5563; font-size: 14px; line-height: 1.5;">
                            {reasons_html}
                        </ul>
                        <div style="margin-top: 24px;">
                            <a href="http://localhost:3000" style="background-color: #4318FF; color: white; padding: 10px 20px; border-radius: 10px; text-decoration: none; font-weight: bold; display: inline-block;">Open Review Queue</a>
                        </div>
                    </div>
                </body>
            </html>
            """
            msg.attach(MIMEText(html_content, "html"))

            # Connect to SMTP (run in thread pool to avoid blocking async loop)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_smtp_sync, msg)
            return True
        except Exception as exc:
            logger.warning(f"Could not send email alert to {self.settings.SMTP_HOST}:{self.settings.SMTP_PORT}: {exc}")
            return False

    def _send_smtp_sync(self, msg: MIMEMultipart):
        with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT, timeout=5) as server:
            server.send_message(msg)

    async def send_slack_alert(
        self,
        score: Score,
        tx: Dict[str, Any],
        reasons: List[str]
    ) -> bool:
        """Sends an alert notification via Slack Webhook if configured."""
        if not self.settings.SLACK_WEBHOOK_URL:
            return False

        try:
            payload = {
                "text": f"🚨 *ExpenseGuard High Risk Alert*\n*Amount:* ₹{float(tx.get('amount', 0)):,.2f}\n*Vendor:* {tx.get('vendor')}\n*Risk:* {score.risk_score}/100 (HIGH)\n*Signals:* {'; '.join(reasons)}"
            }
            async with httpx.AsyncClient(timeout=5) as client:
                res = await client.post(self.settings.SLACK_WEBHOOK_URL, json=payload)
                return res.status_code == 200
        except Exception as exc:
            logger.warning(f"Could not dispatch Slack alert: {exc}")
            return False

    async def dispatch_alert(
        self,
        score: Score,
        tx: Dict[str, Any],
        reasons: List[str]
    ):
        """Dispatches alerts across active channels and logs them in alerts table."""
        email_ok = await self.send_email_alert(score, tx, reasons)
        if self.db:
            try:
                alert_rec = Alert(
                    score_id=score.id,
                    channel="email",
                    destination=self.settings.SMTP_FROM,
                    status="sent" if email_ok else "failed"
                )
                self.db.add(alert_rec)
                await self.db.commit()
            except Exception as exc:
                logger.warning(f"Could not record alert log: {exc}")

        if self.settings.SLACK_WEBHOOK_URL:
            slack_ok = await self.send_slack_alert(score, tx, reasons)
            if self.db:
                try:
                    slack_rec = Alert(
                        score_id=score.id,
                        channel="slack",
                        destination=self.settings.SLACK_WEBHOOK_URL[:30] + "...",
                        status="sent" if slack_ok else "failed"
                    )
                    self.db.add(slack_rec)
                    await self.db.commit()
                except Exception:
                    pass
