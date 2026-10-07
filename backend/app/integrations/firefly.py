import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)


class FireflyClient:
    """
    Async HTTP client for interacting with the unmodified Firefly III core API (/api/v1).
    Provides retries with exponential backoff, pagination, and error recovery.
    """

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        settings = get_settings()
        self.base_url = (base_url or settings.FIREFLY_SITE_URL).rstrip("/")
        self.token = token or settings.FIREFLY_API_TOKEN
        self.headers = {
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/json",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=15.0,
            verify=False
        )

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        url = path if path.startswith("/") else f"/{path}"
        backoff = 0.5

        for attempt in range(max_retries):
            try:
                async with self._get_client() as client:
                    response = await client.request(method, url, params=params, json=json)
                    if response.status_code in [200, 201, 204]:
                        if response.status_code == 204 or not response.content:
                            return {}
                        return response.json()
                    elif response.status_code == 404:
                        logger.warning(f"Firefly resource not found: {path}")
                        return None
                    else:
                        logger.warning(
                            f"Firefly request error {method} {path}: {response.status_code} - {response.text}"
                        )
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                logger.warning(f"Firefly connection error (attempt {attempt + 1}/{max_retries}): {exc}")
                if attempt == max_retries - 1:
                    logger.error(f"Firefly unreachable at {self.base_url}{path}")
                    return None
            await asyncio.sleep(backoff)
            backoff *= 2
        return None

    async def check_health(self) -> Dict[str, Any]:
        """Verify reachability and API status of Firefly III."""
        try:
            data = await self._request("GET", "/api/v1/about")
            if data and "data" in data:
                return {
                    "reachable": True,
                    "version": data["data"].get("attributes", {}).get("version", "unknown"),
                    "os": data["data"].get("attributes", {}).get("os", "unknown")
                }
            return {"reachable": False, "reason": "Invalid response"}
        except Exception as exc:
            return {"reachable": False, "error": str(exc)}

    async def get_transaction(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Fetch single transaction group by ID."""
        return await self._request("GET", f"/api/v1/transactions/{group_id}")

    async def get_transactions(
        self,
        page: int = 1,
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        txn_type: str = "withdrawal"
    ) -> List[Dict[str, Any]]:
        """Retrieve paginated transactions list from Firefly III."""
        params: Dict[str, Any] = {
            "page": page,
            "limit": limit,
            "type": txn_type
        }
        if start_date:
            params["start"] = start_date
        if end_date:
            params["end"] = end_date

        res = await self._request("GET", "/api/v1/transactions", params=params)
        if res and "data" in res:
            return res["data"]
        return []

    async def tag_and_annotate_transaction(
        self,
        group_id: str,
        journal_id: Optional[int],
        tier: str,
        risk_score: float,
        reasons: List[str],
        bridge_score_id: str,
        existing_tags: Optional[List[str]] = None
    ) -> bool:
        """
        Merge tier tags and append audit notes to a Firefly transaction without overwriting existing tags.
        """
        tags = set(existing_tags or [])
        # Remove previous tier tags if any
        tags.discard("tier:LOW")
        tags.discard("tier:MEDIUM")
        tags.discard("tier:HIGH")
        tags.add(f"tier:{tier.upper()}")
        tags.add("expenseguard:scored")

        reason_text = "; ".join(reasons) if reasons else "No anomalous signals detected"
        audit_note = (
            f"[ExpenseGuard Audit]\n"
            f"Risk Score: {int(risk_score)}/100 ({tier.upper()})\n"
            f"Signals: {reason_text}\n"
            f"Bridge Ref: {bridge_score_id}"
        )

        split_payload: Dict[str, Any] = {
            "tags": list(tags),
            "notes": audit_note
        }
        if journal_id:
            split_payload["transaction_journal_id"] = str(journal_id)

        update_payload = {
            "apply_rules": False,
            "fire_webhooks": False,  # Prevent infinite webhook re-triggering
            "transactions": [split_payload]
        }

        res = await self._request("PUT", f"/api/v1/transactions/{group_id}", json=update_payload)
        return res is not None

    async def create_transaction(
        self,
        description: str,
        amount: float,
        date_str: str,
        source_id: int,
        destination_name: str,
        category_name: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new expense withdrawal transaction in Firefly III."""
        payload = {
            "error_if_duplicate_hash": False,
            "apply_rules": True,
            "fire_webhooks": True,
            "transactions": [
                {
                    "type": "withdrawal",
                    "description": description,
                    "date": date_str,
                    "amount": f"{amount:.2f}",
                    "source_id": str(source_id),
                    "destination_name": destination_name,
                    "category_name": category_name or "General",
                    "notes": notes or ""
                }
            ]
        }
        res = await self._request("POST", "/api/v1/transactions", json=payload)
        if res and "data" in res:
            return res["data"]
        return None

    async def ensure_webhook_registered(self, webhook_url: str, secret: str) -> bool:
        """Register the ExpenseGuard STORE_TRANSACTION webhook in Firefly III if not already registered."""
        try:
            webhooks_res = await self._request("GET", "/api/v1/webhooks")
            if webhooks_res and "data" in webhooks_res:
                for wh in webhooks_res["data"]:
                    attrs = wh.get("attributes", {})
                    if attrs.get("url") == webhook_url:
                        logger.info(f"Webhook already registered with ID {wh.get('id')}")
                        return True

            # Register new webhook
            payload = {
                "title": "ExpenseGuard Webhook Bridge",
                "trigger": "STORE_TRANSACTION",
                "response": "TRANSACTIONS",
                "delivery": "JSON",
                "url": webhook_url,
                "active": True
            }
            create_res = await self._request("POST", "/api/v1/webhooks", json=payload)
            if create_res and "data" in create_res:
                logger.info(f"Successfully registered webhook with Firefly III: {create_res['data']['id']}")
                return True
            return False
        except Exception as exc:
            logger.warning(f"Could not auto-register webhook with Firefly III: {exc}")
            return False

    async def get_accounts(self, account_type: str = "asset") -> List[Dict[str, Any]]:
        """Get accounts of specified type."""
        res = await self._request("GET", "/api/v1/accounts", params={"type": account_type})
        if res and "data" in res:
            return res["data"]
        return []

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all categories."""
        res = await self._request("GET", "/api/v1/categories")
        if res and "data" in res:
            return res["data"]
        return []
