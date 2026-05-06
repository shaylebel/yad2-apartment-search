from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ApartmentListing(BaseModel):
    listing_id: str
    url: str

    price: Optional[int] = None
    rooms: Optional[float] = None
    size_sqm: Optional[int] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None

    city: Optional[str] = None
    neighborhood: Optional[str] = None
    street: Optional[str] = None
    address_full: Optional[str] = None

    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_balcony: Optional[bool] = None
    has_ac: Optional[bool] = None
    is_furnished: Optional[bool] = None
    pets_allowed: Optional[bool] = None
    has_mamad: Optional[bool] = None
    has_bars: Optional[bool] = None

    image_urls: list[str] = Field(default_factory=list)
    thumbnail_url: Optional[str] = None

    date_published: Optional[str] = None
    date_updated: Optional[str] = None
    date_scraped: datetime = Field(default_factory=datetime.now)
    description: Optional[str] = None
    contact_name: Optional[str] = None

    raw_text: Optional[str] = None
