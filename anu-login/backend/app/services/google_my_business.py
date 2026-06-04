"""
Google Business Profile (GMB) automation service.

Behavior:
- Always records requested posts in local DB (audit trail)
- Attempts immediate publish to Google when credentials are configured
- Falls back to pending status when publish is not possible
"""

from __future__ import annotations

import json
import logging
import ssl
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.config import settings
from app.storage import get_db_connection

logger = logging.getLogger(__name__)


@dataclass
class GMBPost:
    title: str
    content: str
    image_url: Optional[str] = None
    call_to_action_url: Optional[str] = None
    post_type: str = "OFFER"
    created_at: str | None = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


class GoogleMyBusinessService:
    BUSINESS_NAME = "PureLeven"

    @staticmethod
    def _is_publish_configured() -> bool:
        return bool(settings.gmb_access_token and settings.gmb_location_name)

    @staticmethod
    def _map_topic(post_type: str) -> str:
        mapping = {
            "OFFER": "OFFER",
            "EVENT": "EVENT",
            "PRODUCT": "STANDARD",
            "MEDIA": "STANDARD",
            "REVIEW": "STANDARD",
        }
        return mapping.get((post_type or "").upper(), "STANDARD")

    @staticmethod
    def _build_google_payload(post: GMBPost) -> dict:
        payload: dict[str, object] = {
            "languageCode": "en",
            "summary": post.content[:1500],
            "topicType": GoogleMyBusinessService._map_topic(post.post_type),
        }

        if post.call_to_action_url:
            payload["callToAction"] = {
                "actionType": "LEARN_MORE",
                "url": post.call_to_action_url,
            }

        if post.image_url:
            payload["media"] = [
                {
                    "mediaFormat": "PHOTO",
                    "sourceUrl": post.image_url,
                }
            ]

        return payload

    @staticmethod
    def _publish_to_google(post: GMBPost) -> dict:
        if not GoogleMyBusinessService._is_publish_configured():
            return {
                "success": False,
                "queued": True,
                "error": "GMB credentials not configured",
                "message": "Post queued locally (credentials missing).",
            }

        endpoint = f"https://mybusiness.googleapis.com/v4/{settings.gmb_location_name}/localPosts"
        payload = GoogleMyBusinessService._build_google_payload(post)
        body = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {settings.gmb_access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
                return {
                    "success": True,
                    "queued": False,
                    "provider_id": data.get("name"),
                    "raw": data,
                }
        except urllib.error.HTTPError as exc:
            msg = exc.read().decode("utf-8", errors="ignore")[:1200]
            logger.warning("GMB publish HTTPError %s: %s", exc.code, msg)
            return {
                "success": False,
                "queued": True,
                "error": f"HTTP {exc.code}",
                "message": msg or "Google API HTTP error",
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("GMB publish failed: %s", exc)
            return {
                "success": False,
                "queued": True,
                "error": str(exc),
                "message": "Failed to publish to Google API",
            }

    @staticmethod
    def _insert_local_post(
        post: GMBPost,
        customer_id: str | None = None,
        discount_percent: int | None = None,
        expiry_date: str | None = None,
        price: float | None = None,
    ) -> str:
        post_id = f"gmb-{uuid.uuid4().hex[:12]}"
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO gmb_posts
                (id, business_id, post_type, title, content, image_url, customer_id,
                 offer_discount, offer_expiry, product_price, call_to_action_url,
                 published, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    post_id,
                    settings.gmb_location_name or None,
                    post.post_type,
                    post.title,
                    post.content,
                    post.image_url,
                    customer_id,
                    discount_percent,
                    expiry_date,
                    price,
                    post.call_to_action_url,
                    post.created_at,
                    post.created_at,
                ),
            )
            conn.commit()
        return post_id

    @staticmethod
    def _mark_published(post_id: str, provider_id: str | None) -> None:
        now = datetime.utcnow().isoformat()
        with get_db_connection() as conn:
            conn.execute(
                """
                UPDATE gmb_posts
                SET published = 1,
                    published_at = ?,
                    updated_at = ?,
                    business_id = COALESCE(?, business_id)
                WHERE id = ?
                """,
                (now, now, provider_id, post_id),
            )
            conn.commit()

    @staticmethod
    def post_customer_review_to_gmb(customer_id: str, review_text: str, rating: int = 5) -> dict:
        post = GMBPost(
            title=f"{rating} Star Customer Review",
            content=review_text[:500],
            post_type="REVIEW",
        )

        post_id = GoogleMyBusinessService._insert_local_post(post=post, customer_id=customer_id)
        publish = GoogleMyBusinessService._publish_to_google(post)
        if publish.get("success"):
            GoogleMyBusinessService._mark_published(post_id, publish.get("provider_id"))

        return {
            "success": True,
            "post_id": post_id,
            "published": bool(publish.get("success")),
            "queued": bool(publish.get("queued")),
            "message": "Review saved and publish attempted",
            "provider": publish,
        }

    @staticmethod
    def post_offer_to_gmb(offer_title: str, offer_description: str, discount_percent: int = 0, expiry_date: str | None = None) -> dict:
        post = GMBPost(
            title=offer_title,
            content=offer_description[:500],
            post_type="OFFER",
            call_to_action_url="https://pureleven.com/products",
        )

        post_id = GoogleMyBusinessService._insert_local_post(
            post=post,
            discount_percent=discount_percent,
            expiry_date=expiry_date,
        )
        publish = GoogleMyBusinessService._publish_to_google(post)
        if publish.get("success"):
            GoogleMyBusinessService._mark_published(post_id, publish.get("provider_id"))

        return {
            "success": True,
            "post_id": post_id,
            "published": bool(publish.get("success")),
            "queued": bool(publish.get("queued")),
            "message": "Offer saved and publish attempted",
            "provider": publish,
        }

    @staticmethod
    def post_product_update_to_gmb(product_name: str, description: str, price: float, image_url: str | None = None) -> dict:
        post = GMBPost(
            title=f"New: {product_name}",
            content=description[:500],
            image_url=image_url,
            post_type="PRODUCT",
            call_to_action_url="https://pureleven.com/products",
        )

        post_id = GoogleMyBusinessService._insert_local_post(
            post=post,
            price=price,
        )
        publish = GoogleMyBusinessService._publish_to_google(post)
        if publish.get("success"):
            GoogleMyBusinessService._mark_published(post_id, publish.get("provider_id"))

        return {
            "success": True,
            "post_id": post_id,
            "published": bool(publish.get("success")),
            "queued": bool(publish.get("queued")),
            "message": "Product update saved and publish attempted",
            "provider": publish,
        }

    @staticmethod
    def auto_post_top_reviews() -> dict:
        with get_db_connection() as conn:
            reviews = conn.execute(
                """
                SELECT jce.customer_id, jce.metadata_json
                FROM journey_engagement_events jce
                WHERE jce.event_type = 'review'
                AND jce.created_at >= datetime('now', '-7 days')
                ORDER BY jce.created_at DESC
                LIMIT 5
                """
            ).fetchall()

        results: list[dict] = []
        for review in reviews:
            try:
                metadata = json.loads(review['metadata_json'] or '{}')
                review_text = metadata.get('review_text', '')
                rating = int(metadata.get('rating', 5) or 5)
                if review_text:
                    results.append(
                        GoogleMyBusinessService.post_customer_review_to_gmb(
                            review['customer_id'],
                            review_text,
                            rating,
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                results.append({
                    'success': False,
                    'error': str(exc),
                    'message': 'Error posting review',
                })

        return {
            'success': True,
            'action': 'auto_post_top_reviews',
            'posts_created': len([r for r in results if r.get('success')]),
            'posts_failed': len([r for r in results if not r.get('success')]),
            'results': results,
        }

    @staticmethod
    def auto_post_daily_offer() -> dict:
        expiry = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
        return GoogleMyBusinessService.post_offer_to_gmb(
            offer_title='Daily Deal: 15% Off Organic Turmeric',
            offer_description='Get 15% off our bestselling organic turmeric powder today only.',
            discount_percent=15,
            expiry_date=expiry,
        )

    @staticmethod
    def get_pending_posts() -> list[dict]:
        with get_db_connection() as conn:
            posts = conn.execute(
                """
                SELECT id, business_id, post_type, title, content, published, created_at
                FROM gmb_posts
                WHERE published = 0
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [dict(p) for p in posts]

    @staticmethod
    def publish_post(post_id: str) -> dict:
        with get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT id, title, content, image_url, post_type, call_to_action_url
                FROM gmb_posts
                WHERE id = ?
                """,
                (post_id,),
            ).fetchone()

        if not row:
            return {'success': False, 'message': 'Post not found'}

        post = GMBPost(
            title=row['title'],
            content=row['content'],
            image_url=row['image_url'],
            post_type=row['post_type'],
            call_to_action_url=row['call_to_action_url'],
        )
        publish = GoogleMyBusinessService._publish_to_google(post)
        if publish.get('success'):
            GoogleMyBusinessService._mark_published(post_id, publish.get('provider_id'))
            return {'success': True, 'post_id': post_id, 'published': True, 'provider': publish}

        return {
            'success': False,
            'post_id': post_id,
            'published': False,
            'queued': True,
            'message': publish.get('message', 'Failed to publish post'),
            'provider': publish,
        }

    @staticmethod
    def get_gmb_analytics() -> dict:
        with get_db_connection() as conn:
            stats = conn.execute(
                """
                SELECT
                    COUNT(*) as total_posts,
                    SUM(CASE WHEN published = 1 THEN 1 ELSE 0 END) as published_posts,
                    SUM(CASE WHEN post_type = 'REVIEW' THEN 1 ELSE 0 END) as review_posts,
                    SUM(CASE WHEN post_type = 'OFFER' THEN 1 ELSE 0 END) as offer_posts,
                    SUM(CASE WHEN post_type = 'PRODUCT' THEN 1 ELSE 0 END) as product_posts
                FROM gmb_posts
                """
            ).fetchone()

        return dict(stats)
