"""Provider abstraction – voice calls and WhatsApp.

Mock implementations run the whole flow at zero cost for development and
CI. The real Retell / Twilio implementations activate automatically as
soon as their API keys appear in settings, so "switching on" the paid
stack later requires no code changes here.
"""
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from ..settings import settings


@dataclass
class ProviderResult:
    provider_call_id: str
    status: str                      # initiated | sent | failed | ...
    raw: dict | None = None


# ---------------------------------------------------------------------------
# Voice (outbound calling)
# ---------------------------------------------------------------------------

class VoiceProvider(ABC):
    @abstractmethod
    async def place_call(self, to_number: str, from_number: str | None = None) -> ProviderResult:
        ...


class MockVoiceProvider(VoiceProvider):
    """Zero-cost stand-in: no network, instant success."""

    async def place_call(self, to_number: str, from_number: str | None = None) -> ProviderResult:
        call_id = f"mock-call-{uuid.uuid4().hex[:12]}"
        return ProviderResult(call_id, "initiated", {"mock": True, "to": to_number})


class RetellVoiceProvider(VoiceProvider):
    """Retell AI outbound call – https://docs.retellai.com.

    Written against the published v2 API shape; will be verified against a
    live key before the first real call.
    """

    CREATE_CALL_URL = "https://api.retellai.com/v2/create-phone-call"

    def __init__(self, api_key: str, agent_id: str | None = None):
        self._api_key = api_key
        self._agent_id = agent_id

    async def place_call(self, to_number: str, from_number: str | None = None) -> ProviderResult:
        payload: dict = {
            "to_number": to_number,
            "from_number": from_number or settings.RETELL_FROM_NUMBER or None,
        }
        if self._agent_id:
            payload["override_agent_id"] = self._agent_id

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                self.CREATE_CALL_URL,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            if response.status_code >= 400:
                return ProviderResult("", "failed", {"status": response.status_code, "body": response.text})
            data = response.json()
            return ProviderResult(data.get("call_id", ""), "initiated", data)


def get_voice_provider() -> VoiceProvider:
    api_key = settings.RETELL_API_KEY.get_secret_value()
    if api_key:
        return RetellVoiceProvider(api_key, agent_id=settings.RETELL_AGENT_ID or None)
    return MockVoiceProvider()


# ---------------------------------------------------------------------------
# WhatsApp
# ---------------------------------------------------------------------------

class WhatsAppSender(ABC):
    @abstractmethod
    async def send(self, to_number: str, body: str, media_url: str | None = None) -> ProviderResult:
        ...


class MockWhatsAppSender(WhatsAppSender):
    async def send(self, to_number: str, body: str, media_url: str | None = None) -> ProviderResult:
        message_id = f"mock-wa-{uuid.uuid4().hex[:12]}"
        return ProviderResult(message_id, "sent", {"mock": True, "to": to_number, "body": body})


class TwilioWhatsAppSender(WhatsAppSender):
    """Twilio Messages API – works with the free Sandbox for testing."""

    API_URL = "https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self._auth = (account_sid, auth_token)
        # Sandbox number by default; swap for an approved sender in production.
        self._from = from_number or "whatsapp:+14155238886"

    async def send(self, to_number: str, body: str, media_url: str | None = None) -> ProviderResult:
        url = self.API_URL.format(account_sid=self._auth[0])
        to = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
        form = {"From": self._from, "To": to, "Body": body}
        if media_url:
            form["MediaUrl"] = media_url

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, data=form, auth=self._auth)
            if response.status_code >= 400:
                return ProviderResult("", "failed", {"status": response.status_code, "body": response.text})
            data = response.json()
            return ProviderResult(data.get("sid", ""), "sent", data)


class MetaWhatsAppSender(WhatsAppSender):
    """Official WhatsApp Cloud API (Meta Graph) – free test number, India-friendly.

    Free-form text requires an open 24h customer-service window (the recipient
    messaged us recently); template sends need a pre-approved template name.
    """

    API_URL = "https://graph.facebook.com/v21.0/{phone_number_id}/messages"

    def __init__(self, access_token: str, phone_number_id: str):
        self._token = access_token
        self._phone_number_id = phone_number_id

    async def send(self, to_number: str, body: str, media_url: str | None = None) -> ProviderResult:
        url = self.API_URL.format(phone_number_id=self._phone_number_id)
        to = to_number.lstrip("+").replace("whatsapp:", "")
        if media_url:
            payload: dict = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "document",
                "document": {"link": media_url, "caption": body},
            }
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": body},
            }

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {self._token}"},
            )
            if response.status_code >= 400:
                return ProviderResult("", "failed", {"status": response.status_code, "body": response.text})
            data = response.json()
            message_id = ""
            try:
                message_id = data["messages"][0]["id"]
            except (KeyError, IndexError, TypeError):
                pass
            return ProviderResult(message_id, "sent", data)


def get_whatsapp_sender() -> WhatsAppSender:
    # Meta Cloud API first – free test tier works for Indian numbers.
    meta_token = settings.META_WHATSAPP_TOKEN.get_secret_value()
    meta_phone_id = settings.META_WHATSAPP_PHONE_NUMBER_ID
    if meta_token and meta_phone_id:
        return MetaWhatsAppSender(meta_token, meta_phone_id)

    sid = settings.TWILIO_ACCOUNT_SID.get_secret_value()
    token = settings.TWILIO_AUTH_TOKEN.get_secret_value()
    if sid and not sid.startswith("ACxxx"):        # placeholder .env value guard
        return TwilioWhatsAppSender(sid, token, settings.TWILIO_WHATSAPP_FROM)
    return MockWhatsAppSender()
