from pydantic import BaseModel


class CalendarSessionItem(BaseModel):
    name: str
    start_date: str
    end_date: str
    gmt_offset: str = ""


class CalendarTrackInfoItem(BaseModel):
    key: str
    value: str
    annotation: str | None = None


class CalendarCircuitItem(BaseModel):
    name: str
    track_url: str | None = None
    map_url: str | None = None
    info: list[CalendarTrackInfoItem] = []


class CalendarRoundItem(BaseModel):
    round_number: str
    grand_prix_title: str
    short_title: str
    country: str
    city: str
    circuit_name: str
    country_flag_image_url: str | None = None
    start_date: str
    end_date: str
    gmt_offset: str = ""
    circuit: CalendarCircuitItem
    sessions: list[CalendarSessionItem] = []