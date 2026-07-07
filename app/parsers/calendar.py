import json

from app.schemas.calendar import (
    CalendarCircuitItem,
    CalendarRoundItem,
    CalendarSessionItem,
    CalendarTrackInfoItem,
)


def parse_calendar_rsc_payload(payload: str) -> list[CalendarRoundItem]:
    decoder = json.JSONDecoder()
    items: list[CalendarRoundItem] = []
    seen_keys: set[str] = set()

    start_marker = '{"title":"'
    start_index = 0

    while True:
        index = payload.find(start_marker, start_index)
        if index == -1:
            break

        try:
            item_data, end_index = decoder.raw_decode(payload[index:])
        except json.JSONDecodeError:
            start_index = index + len(start_marker)
            continue

        start_index = index + end_index

        if not isinstance(item_data, dict):
            continue

        if "title" not in item_data or "sessions" not in item_data or "circuit" not in item_data:
            continue

        circuit_data = item_data.get("circuit")
        sessions_data = item_data.get("sessions")

        if not isinstance(circuit_data, dict):
            continue

        if not isinstance(sessions_data, list):
            continue

        round_value = str(item_data.get("round", "")).strip()
        name = str(item_data.get("name", "")).strip()
        title = str(item_data.get("title", "")).strip()

        unique_key = f"{round_value}|{name}|{title}"
        if unique_key in seen_keys:
            continue
        seen_keys.add(unique_key)

        track_info: list[CalendarTrackInfoItem] = []
        raw_info = circuit_data.get("info", [])
        if isinstance(raw_info, list):
            for info_item in raw_info:
                if not isinstance(info_item, dict):
                    continue

                track_info.append(
                    CalendarTrackInfoItem(
                        key=str(info_item.get("key", "")).strip(),
                        value=str(info_item.get("value", "")).strip(),
                        annotation=info_item.get("annotation"),
                    )
                )

        sessions: list[CalendarSessionItem] = []
        for session_item in sessions_data:
            if not isinstance(session_item, dict):
                continue

            sessions.append(
                CalendarSessionItem(
                    name=str(session_item.get("name", "")).strip(),
                    start_date=str(session_item.get("start_date", "")).strip(),
                    end_date=str(session_item.get("end_date", "")).strip(),
                    gmt_offset=str(session_item.get("gmt_offset", "")).strip(),
                )
            )

        circuit = CalendarCircuitItem(
            name=str(circuit_data.get("name", "")).strip(),
            track_url=circuit_data.get("track_url") if isinstance(circuit_data.get("track_url"), str) else None,
            map_url=circuit_data.get("map_url") if isinstance(circuit_data.get("map_url"), str) else None,
            info=track_info,
        )

        items.append(
            CalendarRoundItem(
                round_number=round_value,
                grand_prix_title=title,
                short_title=name,
                country=str(item_data.get("country", "")).strip(),
                city=str(item_data.get("city", "")).strip(),
                circuit_name=circuit.name,
                country_flag_image_url=item_data.get("country_flag_image_url")
                if isinstance(item_data.get("country_flag_image_url"), str)
                else None,
                start_date=str(item_data.get("start_date", "")).strip(),
                end_date=str(item_data.get("end_date", "")).strip(),
                gmt_offset=str(item_data.get("gmt_offset", "")).strip(),
                circuit=circuit,
                sessions=sessions,
            )
        )

    return items