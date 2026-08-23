from pydantic import BaseModel, Field
from typing import List, Optional

class VoiceWebhookPayload(BaseModel):
    """Payload sent by the managed voice provider (Retell/Vapi).
    The exact fields may differ per provider – keep this generic.
    """
    call_sid: str = Field(..., description="Unique ID for the call from the provider")
    transcript: str = Field(..., description="Final transcript of the user's utterance")
    language: Optional[str] = Field(None, description="Detected language code (en/hi/te) or mixed")
    is_final: bool = Field(..., description="True when the user has finished speaking for this turn")


class LeadState(BaseModel):
    """Structured lead state – PRD section 8.
    Unknown fields stay None/empty; never invented.
    """
    business_type: Optional[str] = None
    product_or_service: Optional[str] = None
    product_count: Optional[int] = None
    features: List[str] = Field(default_factory=list)
    budget: Optional[str] = None
    timeline: Optional[str] = None
    decision_maker: Optional[str] = None
    pain_points: List[str] = Field(default_factory=list)
    barrier: Optional[str] = None


class Decision(BaseModel):
    """Outcome of the deterministic decision engine – PRD section 9."""
    intent: str                      # HOT | WARM | COLD
    confidence: float                # 0..0.95, grows with matched evidence
    signals: List[str] = Field(default_factory=list)
    barrier: Optional[str] = None
    next_action: str                 # send_whatsapp_mid_call | schedule_callback | persist_lead
    state: LeadState
