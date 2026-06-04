"""
Abandoned Customer Campaign Service with AI-driven warm/cold scoring

Campaign Logic:
- 15-day intervals: Send campaigns 1-6 over 90 days
- Warm (score ≥ 40): Click/Open tracked → Continue sequence
- Cold (score < 40): No engagement → Pause after 2 attempts, resume after 90 days
- Recurring: If warm, cycle back to campaign 1 after campaign 6
"""

from datetime import datetime, timedelta
import os
from app.storage import get_db_connection
from app.abandoned_customer_templates import build_abandoned_email


class AbandonedCampaignService:
    """Manages abandoned customer email campaigns with warm/cold segmentation"""
    
    # Campaign schedule: days since lead creation
    CAMPAIGN_SCHEDULE = {
        1: 0,      # Immediate
        2: 15,     # Day 15
        3: 30,     # Day 30 (exclusive offer)
        4: 45,     # Day 45 (urgency)
        5: 60,     # Day 60 (testimonial)
        6: 75,     # Day 75 (final winback)
    }
    
    # After campaign 6, if warm: restart at campaign 1 after 90 days
    # If cold for > 2 months: don't send until 90 days from last send
    
    @staticmethod
    def should_send_campaign(lead_id):
        """
        Determine if a campaign should be sent now
        
        Returns: (should_send: bool, next_campaign_num: int, reason: str)
        """
        with get_db_connection() as conn:
            lead = conn.execute(
                "SELECT * FROM abandoned_leads WHERE id = ?",
                (lead_id,)
            ).fetchone()
            
            if not lead:
                return False, None, "Lead not found"
            
            lead = dict(lead)
            
            # Check if unsubscribed
            if lead.get("do_not_email"):
                return False, None, "Lead unsubscribed"
            
            # Get last campaign sent
            last_campaign = conn.execute(
                """
                SELECT campaign_num, created_at, opened_at, clicked_at 
                FROM abandoned_campaigns 
                WHERE lead_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
                """,
                (lead_id,)
            ).fetchone()
            
            engagement_score = lead.get("engagement_score", 0)
            is_warm = engagement_score >= 40
            
            # Determine next campaign
            if not last_campaign:
                # First campaign ever
                return True, 1, "First campaign"
            
            last_campaign = dict(last_campaign)
            last_num = last_campaign["campaign_num"]
            last_created = datetime.fromisoformat(last_campaign["created_at"])
            last_opened = last_campaign["opened_at"]
            last_clicked = last_campaign["clicked_at"]
            
            # Check if engaged with last campaign
            was_engaged = bool(last_opened or last_clicked)
            
            # Determine next campaign
            if last_num < 6:
                next_num = last_num + 1
                next_days = AbandonedCampaignService.CAMPAIGN_SCHEDULE[next_num]
                first_created = datetime.fromisoformat(lead["created_at"])
                next_send_time = first_created + timedelta(days=next_days)
                
                now = datetime.utcnow()
                if now >= next_send_time:
                    # Check cold logic
                    if not is_warm and last_num >= 2:
                        # Cold lead + 2 campaigns sent
                        # Pause until 90 days from lead creation
                        cutoff = first_created + timedelta(days=90)
                        if now >= cutoff:
                            return True, 1, "Cold lead, reactivating after 90 days"
                        else:
                            days_remaining = (cutoff - now).days
                            return False, None, f"Cold lead, paused until {days_remaining}d"
                    
                    return True, next_num, f"Campaign {next_num} scheduled"
                else:
                    hours_remaining = ((next_send_time - now).total_seconds() / 3600)
                    return False, None, f"Campaign {next_num} scheduled in {hours_remaining:.1f}h"
            
            else:
                # Completed campaign 6
                if is_warm:
                    # Restart sequence after 90 days
                    cutoff = last_created + timedelta(days=90)
                    now = datetime.utcnow()
                    if now >= cutoff:
                        return True, 1, "Warm lead, restarting sequence after 90d"
                    else:
                        days_remaining = (cutoff - now).days
                        return False, None, f"Warm lead, waiting to restart in {days_remaining}d"
                else:
                    # Cold lead + no more campaigns
                    # Pause until 90 days from first send
                    first_send = conn.execute(
                        "SELECT created_at FROM abandoned_campaigns WHERE lead_id = ? ORDER BY created_at LIMIT 1",
                        (lead_id,)
                    ).fetchone()
                    
                    if first_send:
                        first_send_time = datetime.fromisoformat(first_send["created_at"])
                        cutoff = first_send_time + timedelta(days=90)
                        now = datetime.utcnow()
                        if now >= cutoff:
                            return True, 1, "Cold lead, reactivating after 90d pause"
                        else:
                            days_remaining = (cutoff - now).days
                            return False, None, f"Cold lead, paused until {days_remaining}d"
                    
                    return False, None, "Cold lead, no scheduled send"
    
    @staticmethod
    def send_campaign(lead_id):
        """
        Send next campaign for lead
        
        Returns: result dict with success, campaign_num, sent_at, to_email
        """
        from app.services.email_service import _send_raw, EmailResult
        
        should_send, campaign_num, reason = AbandonedCampaignService.should_send_campaign(lead_id)
        
        if not should_send:
            return {
                "success": False,
                "lead_id": lead_id,
                "campaign_num": None,
                "reason": reason,
            }
        
        with get_db_connection() as conn:
            lead = conn.execute(
                "SELECT * FROM abandoned_leads WHERE id = ?",
                (lead_id,)
            ).fetchone()
            
            if not lead:
                return {
                    "success": False,
                    "lead_id": lead_id,
                    "campaign_num": campaign_num,
                    "reason": "Lead not found",
                }
            
            lead = dict(lead)
            
            # ── Generate AI context for personalization ───────────────────────
            ai_context = lead.get("ai_context", "") or ""
            interest_category = lead.get("interest_category", "general")

            # Generate fresh AI context if not already stored
            if not ai_context:
                try:
                    from app.services.ai_enhancement_service import AIEnhancementService
                    first_campaign = conn.execute(
                        "SELECT created_at FROM abandoned_campaigns WHERE lead_id = ? ORDER BY created_at LIMIT 1",
                        (lead_id,)
                    ).fetchone()
                    days_abandoned = 0
                    if first_campaign:
                        from datetime import datetime as _dt
                        days_abandoned = (datetime.utcnow() - _dt.fromisoformat(first_campaign["created_at"])).days

                    ai_context = AIEnhancementService.generate_abandoned_context(
                        lead_id=str(lead.get("id", lead_id)),
                        interest_product=str(lead.get("interest_product", "organic products")),
                        interest_category=interest_category,
                        days_abandoned=days_abandoned,
                        engagement_score=float(lead.get("engagement_score", 0)),
                        campaign_number=campaign_num,
                    )

                    # Store generated context + personalization score for tracking
                    if ai_context:
                        conn.execute(
                            "UPDATE abandoned_leads SET ai_context = ? WHERE id = ?",
                            (ai_context, lead_id),
                        )
                except Exception as exc:
                    import logging as _logging
                    _logging.getLogger(__name__).warning("AI context generation failed: %s", exc)
            
            subject, html_body, text_body = build_abandoned_email(
                lead,
                campaign_num,
                interest_category=interest_category,
                ai_context=ai_context
            )
            
            # Send email
            try:
                result = _send_raw(
                    lead["email"],
                    subject,
                    html_body,
                    text_body
                )
                
                # Log campaign with AI context tracking
                conn.execute(
                    """
                    INSERT INTO abandoned_campaigns 
                    (lead_id, campaign_num, subject, email_to, opened_at, clicked_at,
                     ai_context_used, created_at, updated_at)
                    VALUES (?, ?, ?, ?, NULL, NULL, ?, ?, ?)
                    """,
                    (
                        lead_id,
                        campaign_num,
                        subject,
                        lead["email"],
                        ai_context or None,
                        datetime.utcnow().isoformat(),
                        datetime.utcnow().isoformat(),
                    )
                )
                
                conn.commit()
                
                return {
                    "success": True,
                    "lead_id": lead_id,
                    "campaign_num": campaign_num,
                    "sent_at": datetime.utcnow().isoformat(),
                    "to_email": lead["email"],
                    "subject": subject,
                    "reason": reason,
                }
            
            except Exception as e:
                return {
                    "success": False,
                    "lead_id": lead_id,
                    "campaign_num": campaign_num,
                    "error": str(e),
                    "reason": reason,
                }
    
    @staticmethod
    def track_engagement(lead_id, event_type="opened"):
        """
        Track open/click event for lead
        
        event_type: "opened" or "clicked"
        """
        if event_type not in ["opened", "clicked"]:
            return False
        
        with get_db_connection() as conn:
            # Get last campaign
            campaign = conn.execute(
                "SELECT id FROM abandoned_campaigns WHERE lead_id = ? ORDER BY created_at DESC LIMIT 1",
                (lead_id,)
            ).fetchone()
            
            if not campaign:
                return False
            
            # Update campaign
            now = datetime.utcnow().isoformat()
            if event_type == "opened":
                conn.execute(
                    "UPDATE abandoned_campaigns SET opened_at = ? WHERE id = ?",
                    (now, campaign["id"])
                )
            else:  # clicked
                conn.execute(
                    "UPDATE abandoned_campaigns SET clicked_at = ? WHERE id = ?",
                    (now, campaign["id"])
                )
            
            # Update lead engagement score
            # Opening: +3 points, Clicking: +10 points
            points = 3 if event_type == "opened" else 10
            conn.execute(
                """
                UPDATE abandoned_leads 
                SET engagement_score = engagement_score + ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (points, now, lead_id)
            )
            
            conn.commit()
            return True
