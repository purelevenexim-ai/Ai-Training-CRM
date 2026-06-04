"""
Wabis API Client - Send messages and manage conversations

Supports:
- Sending template messages (existing)
- Sending freeform text messages (new - for AI replies)
- Conversation management
"""

import os
import logging
import json
from typing import Any, Optional
import urllib.request
import urllib.error
import urllib.parse

logger = logging.getLogger(__name__)

# Configuration
WABIS_API_TOKEN = os.getenv("WABIS_API_TOKEN") or os.getenv("WABIS_API_KEY", "")
WABIS_PHONE_ID = os.getenv("WABIS_PHONE_ID") or os.getenv("WABIS_PHONE_NUMBER_ID", "252036884661683")
WABIS_BASE_URL = os.getenv("WABIS_BASE_URL", "https://bot.wabis.in/api/v1/whatsapp")


class WabisAPIClient:
    """Client for Wabis WhatsApp API"""
    
    @staticmethod
    def send_text_message(
        phone_number: str,
        message_text: str,
        conversation_id: str = "",
    ) -> dict[str, Any]:
        """
        Send a freeform text message via Wabis WhatsApp.
        
        Args:
            phone_number: Recipient phone number (with or without country code)
            message_text: Text message to send
            conversation_id: Optional Wabis conversation ID
            
        Returns:
            {
                "success": bool,
                "message_id": "...",
                "wabis_response": {...}
            }
        """
        if not WABIS_API_TOKEN:
            logger.error("WABIS_API_TOKEN not configured")
            return {"success": False, "error": "WABIS_API_TOKEN not configured"}
        
        try:
            # Normalize phone number (remove non-digits)
            normalized_phone = "".join(c for c in phone_number if c.isdigit())
            
            # Prepare request body
            send_params = {
                "apiToken": WABIS_API_TOKEN,
                "phone_number_id": WABIS_PHONE_ID,
                "phone_number": normalized_phone,
                "message": message_text,
            }
            
            if conversation_id:
                send_params["conversation_id"] = conversation_id
            
            form_data = urllib.parse.urlencode(send_params).encode()
            
            # Wabis free text message endpoint (session/24h window)
            url = f"{WABIS_BASE_URL}/send"
            
            req = urllib.request.Request(
                url,
                data=form_data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "User-Agent": "PureLeven-AI-Engine/1.0",
                },
                method="POST",
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
            
            # Check if send was successful
            success = str(result.get("status", "0")) == "1"
            
            if success:
                logger.info(f"Wabis text message sent to {normalized_phone}: {result}")
                return {
                    "success": True,
                    "message_id": result.get("message_id"),
                    "wabis_response": result,
                }
            else:
                error_msg = result.get("message", "Unknown error")
                logger.warning(f"Wabis send failed for {normalized_phone}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "wabis_response": result,
                }
                
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="ignore")
            logger.error(f"Wabis HTTP error {exc.code}: {err_body}")
            return {
                "success": False,
                "error": f"HTTP {exc.code}: {err_body}",
            }
        except Exception as exc:
            logger.error(f"Wabis send error: {exc}")
            return {
                "success": False,
                "error": str(exc),
            }
    
    @staticmethod
    def send_template_message(
        phone_number: str,
        template_id: int,
        params: Optional[list[str]] = None,
        header_image_url: str = "",
    ) -> dict[str, Any]:
        """Send a template message via Wabis (existing implementation)"""
        if not WABIS_API_TOKEN:
            return {"success": False, "error": "WABIS_API_TOKEN not configured"}
        
        try:
            normalized_phone = "".join(c for c in phone_number if c.isdigit())
            
            send_params = {
                "apiToken": WABIS_API_TOKEN,
                "phone_number_id": WABIS_PHONE_ID,
                "phone_number": normalized_phone,
                "template_id": str(template_id),
            }
            
            if params:
                send_params["params"] = json.dumps(params)
            
            if header_image_url:
                send_params["header_content"] = header_image_url
            
            form_data = urllib.parse.urlencode(send_params).encode()
            
            req = urllib.request.Request(
                f"{WABIS_BASE_URL}/send/template",
                data=form_data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "User-Agent": "PureLeven-AI-Engine/1.0",
                },
                method="POST",
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
            
            success = str(result.get("status", "0")) == "1"
            
            return {
                "success": success,
                "message_id": result.get("message_id") if success else None,
                "wabis_response": result,
            }
            
        except Exception as exc:
            logger.error(f"Wabis template send error: {exc}")
            return {
                "success": False,
                "error": str(exc),
            }
    
    @staticmethod
    def get_conversation(conversation_id: str) -> dict[str, Any]:
        """Fetch conversation details from Wabis"""
        if not WABIS_API_TOKEN:
            return {"success": False, "error": "WABIS_API_TOKEN not configured"}
        
        try:
            params = urllib.parse.urlencode({
                "apiToken": WABIS_API_TOKEN,
                "phone_number_id": WABIS_PHONE_ID,
                "conversation_id": conversation_id,
            })
            
            url = f"{WABIS_BASE_URL}/conversation/get?{params}"
            
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "PureLeven-AI-Engine/1.0",
                },
                method="GET",
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
            
            return {
                "success": True,
                "conversation": result,
            }
            
        except Exception as exc:
            logger.error(f"Wabis get conversation error: {exc}")
            return {
                "success": False,
                "error": str(exc),
            }
