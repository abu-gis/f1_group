from dataclasses import dataclass


@dataclass
class ScheduleSession:
    date_label: str
    session_name: str
    session_time: str


@dataclass
class WeekendSchedule:
    country_flag: str
    round_name: str
    circuit_name: str
    sessions: list[ScheduleSession]


def build_schedule_text(schedule: WeekendSchedule) -> str:
    lines = [
        f"{schedule.country_flag} {schedule.round_name} ({schedule.circuit_name})",
        "",
    ]

    current_date = None

    for session in schedule.sessions:
        if session.date_label != current_date:
            if current_date is not None:
                lines.append("")

            current_date = session.date_label
            lines.append(f"🏆 {session.date_label}")

        lines.append(f"{session.session_name} - {session.session_time}")

    lines.append("")
    lines.append("#f1 #formula1")

    return "\n".join(lines)


def get_regular_weekend_schedule() -> WeekendSchedule:
    return WeekendSchedule(
        country_flag="🇦🇹",
        round_name="Расписание восьмого этапа Формулы-1 2026 Гран-при Австрии",
        circuit_name="Red Bull Ring",
        sessions=[
            ScheduleSession("26 июня (пятница)", "FP1", "14:30"),
            ScheduleSession("26 июня (пятница)", "FP2", "18:00"),
            ScheduleSession("27 июня (суббота)", "FP3", "13:30"),
            ScheduleSession("27 июня (суббота)", "Квалификация", "17:00"),
            ScheduleSession("28 июня (воскресенье)", "Гран-при Австрии", "16:00"),
        ],
    )


def get_sprint_weekend_schedule() -> WeekendSchedule:
    return WeekendSchedule(
        country_flag="🇦🇹",
        round_name="Расписание восьмого этапа Формулы-1 2026 Гран-при Австрии",
        circuit_name="Red Bull Ring",
        sessions=[
            ScheduleSession("26 июня (пятница)", "FP1", "14:30"),
            ScheduleSession("26 июня (пятница)", "Спринт-квалификация", "18:00"),
            ScheduleSession("27 июня (суббота)", "Спринт", "13:00"),
            ScheduleSession("27 июня (суббота)", "Квалификация", "17:00"),
            ScheduleSession("28 июня (воскресенье)", "Гран-при Австрии", "16:00"),
        ],
    )