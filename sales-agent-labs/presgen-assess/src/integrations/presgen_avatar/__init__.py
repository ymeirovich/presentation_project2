"""PresGen-Avatar integration package."""

from .client import PresGenAvatarClient
from .schemas import (
    AvatarGenerationRequest,
    AvatarGenerationResponse,
    AvatarJobStatus,
    VoiceConfig,
)

__all__ = [
    "PresGenAvatarClient",
    "AvatarGenerationRequest",
    "AvatarGenerationResponse",
    "AvatarJobStatus",
    "VoiceConfig",
]
