from pydantic import BaseModel, Field
from typing import Optional

class VoiceWebhookPayload(BaseModel):
    """Payload sent by the managed voice provider (Retell/Vapi).
    The exact fields may differ per provider – keep this generic.
    """
    call_sid: str = Field(..., description="Unique ID for the call from the provider")
    transcript: str = Field(..., description="Final transcript of the user's utterance")
    language: Optional[str] = Field(None, description="Detected language code (en/hi/te) or mixed")
    is_final: bool = Field(..., description="True when the user has finished speaking for this turn")
