from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict

class SwapParticipant(BaseModel):
    pubkey: str
    alias: str
    rating_received: Optional[int]
    rating_given: Optional[int]

class LightningSwap(BaseModel):
    id: str
    web_url: str
    image_url: str
    capacity_sats: int
    duration_months: int
    participant_max_count: int
    status: str
    created_at: datetime
    starts: Optional[datetime]
    ends: Optional[datetime]
    participants: List[SwapParticipant]
    prime: bool
    private: bool
    platform: str

class SwapCreationRequest(BaseModel):
    capacity_sats: int = Field(..., ge=100000)
    duration_months: int = Field(..., ge=1, le=24)
    participant_max_count: int = Field(..., ge=2, le=5)
    description: Optional[str]
    private: bool = False
    platform: str = "any"

class NodeBadge(BaseModel):
    name: str
    description: str

class NodeMetrics(BaseModel):
    pubkey: str
    alias: str
    color_hex: str
    open_channels: int
    capacity: int
    hubness_rank: Optional[int]
    weighted_hubness_rank: Optional[int]
    hopness_rank: Optional[int]
    betweenness_rank: Optional[int]
    prime_status: bool
    positive_ratings: int
    negative_ratings: int
    badges: List[NodeBadge]
    profile_urls: Dict[str, str]

class RatingCreate(BaseModel):
    target_node_id: str
    is_positive: bool
    comment: Optional[str]
    swap_id: Optional[str]

class Rating(RatingCreate):
    id: str
    created_at: datetime
    from_node_id: str 