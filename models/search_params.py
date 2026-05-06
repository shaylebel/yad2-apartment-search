from pydantic import BaseModel
from typing import Optional


class SearchFilters(BaseModel):
    city: Optional[str] = None
    rooms_min: Optional[float] = None
    rooms_max: Optional[float] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    size_min: Optional[int] = None
    size_max: Optional[int] = None
    floor_min: Optional[int] = None
    floor_max: Optional[int] = None
    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_balcony: Optional[bool] = None
    has_ac: Optional[bool] = None
    is_furnished: Optional[bool] = None
    pets_allowed: Optional[bool] = None

    def to_url_params(self) -> dict[str, str]:
        params = {}
        if self.city:
            params["city"] = str(self.city)
        if self.rooms_min is not None or self.rooms_max is not None:
            r_min = self._format_rooms(self.rooms_min) if self.rooms_min is not None else ""
            r_max = self._format_rooms(self.rooms_max) if self.rooms_max is not None else ""
            params["rooms"] = f"{r_min}-{r_max}"
        if self.price_min is not None or self.price_max is not None:
            p_min = self.price_min if self.price_min is not None else ""
            p_max = self.price_max if self.price_max is not None else ""
            params["price"] = f"{p_min}-{p_max}"
        return params

    @staticmethod
    def _format_rooms(val: float) -> str:
        if val == int(val):
            return str(int(val))
        return str(val)
