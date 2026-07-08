import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.collectors.calendar import CalendarCollector
from app.config import settings
from app.db.repositories import (
    ArticleRepository,
    SchedulePostRepository,
    SourceSettingRepository,
)
from app.db.session import AsyncSessionLocal
from app.logger import setup_logger
from app.parsers.calendar import parse_calendar_rsc_payload
from app.pipeline_runner import run_pipeline_once
from app.schemas.calendar import CalendarRoundItem

logger = setup_logger()
MSK_TZ = timezone(timedelta(hours=3))

MONTHS_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}

WEEKDAYS_RU = {
    0: "понедельник",
    1: "вторник",
    2: "среда",
    3: "четверг",
    4: "пятница",
    5: "суббота",
    6: "воскресенье",
}

SESSION_NAMES_RU = {
    "Practice 1": "Практика 1",
    "Practice 2": "Практика 2",
    "Practice 3": "Практика 3",
    "Sprint Qualifying": "Спринт-квалификация",
    "Sprint Shootout": "Спринт-квалификация",
    "Sprint": "Спринт",
    "Qualifying": "Квалификация",
    "Race": "Гонка",
}

COUNTRY_HASHTAGS = {
    "bahrain": "#Бахрейн",
    "australia": "#Австралия",
    "china": "#Китай",
    "japan": "#Япония",
    "saudi arabia": "#СаудовскаяАравия",
    "miami": "#Майами",
    "united states": "#США",
    "canada": "#Канада",
    "monaco": "#Монако",
    "spain": "#Испания",
    "austria": "#Австрия",
    "great britain": "#Великобритания",
    "belgium": "#Бельгия",
    "hungary": "#Венгрия",
    "netherlands": "#Нидерланды",
    "italy": "#Италия",
    "azerbaijan": "#Азербайджан",
    "singapore": "#Сингапур",
    "mexico": "#Мексика",
    "brazil": "#Бразилия",
    "qatar": "#Катар",
    "abu dhabi": "#АбуДаби",
    "las vegas": "#ЛасВегас",
}

COUNTRY_FLAGS = {
    "bahrain": "🇧🇭",
    "australia": "🇦🇺",
    "china": "🇨🇳",
    "japan": "🇯🇵",
    "saudi arabia": "🇸🇦",
    "miami": "🇺🇸",
    "united states": "🇺🇸",
    "canada": "🇨🇦",
    "monaco": "🇲🇨",
    "spain": "🇪🇸",
    "austria": "🇦🇹",
    "great britain": "🇬🇧",
    "belgium": "🇧🇪",
    "hungary": "🇭🇺",
    "netherlands": "🇳🇱",
    "italy": "🇮🇹",
    "azerbaijan": "🇦🇿",
    "singapore": "🇸🇬",
    "mexico": "🇲🇽",
    "brazil": "🇧🇷",
    "qatar": "🇶🇦",
    "abu dhabi": "🇦🇪",
    "las vegas": "🇺🇸",
}


def is_admin(update: Update) -> bool:
    chat_id = str(update.effective_chat.id).strip() if update.effective_chat else ""
    user_id = str(update.effective_user.id).strip() if update.effective_user else ""

    admin_chat_id = settings.telegram_admin_chat_id.strip()
    admin_user_id = settings.telegram_admin_user_id.strip()

    logger.info(
        "Admin check: chat_id=%s user_id=%s admin_chat_id=%s admin_user_id=%s",
        chat_id,
        user_id,
        admin_chat_id,
        admin_user_id,
    )

    if admin_chat_id and chat_id != admin_chat_id:
        return False

    if admin_user_id and user_id != admin_user_id:
        return False

    return True


def build_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Статус", callback_data="status")],
        [InlineKeyboardButton("Очереди", callback_data="queue")],
        [InlineKeyboardButton("Логи", callback_data="logs")],
        [InlineKeyboardButton("Ошибки", callback_data="errors")],
        [InlineKeyboardButton("Запустить pipeline", callback_data="run_now")],
        [InlineKeyboardButton("Расписание", callback_data="schedule_menu")],
        [InlineKeyboardButton("Источники", callback_data="sources_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_schedule_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Показать этапы", callback_data="schedule_list")],
        [InlineKeyboardButton("Назад", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_sources_menu(sources: list[tuple[str, bool]]) -> InlineKeyboardMarkup:
    keyboard = []

    for index, (source_name, is_enabled) in enumerate(sources):
        status = "ВКЛ" if is_enabled else "ВЫКЛ"
        keyboard.append([
            InlineKeyboardButton(
                f"{source_name} — {status}",
                callback_data=f"source_toggle_{index}",
            )
        ])

    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def build_schedule_preview_menu(schedule_post_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("Показать трассу", callback_data=f"schedule_track_{schedule_post_id}"),
            InlineKeyboardButton("Опубликовать трассу", callback_data=f"schedule_publish_track_{schedule_post_id}"),
        ],
        [
            InlineKeyboardButton("Опубликовать исходный", callback_data=f"schedule_publish_original_{schedule_post_id}"),
            InlineKeyboardButton("Опубликовать отредактированный", callback_data=f"schedule_publish_edited_{schedule_post_id}"),
        ],
        [
            InlineKeyboardButton("Редактировать", callback_data=f"schedule_edit_{schedule_post_id}"),
        ],
        [
            InlineKeyboardButton("Назад к этапам", callback_data="schedule_list"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def send_main_menu(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        chat_id=chat_id,
        text="Админ-панель бота",
        reply_markup=build_main_menu(),
    )


def translate_session_name(name: str) -> str:
    return SESSION_NAMES_RU.get(name, name)


def build_session_emoji(session_name: str) -> str:
    normalized = session_name.lower().strip()
    if "race" in normalized or normalized == "sprint":
        return "🏆"
    return "🏁"


def normalize_country_key(round_item: CalendarRoundItem) -> str:
    raw_values = [round_item.country, round_item.city, round_item.short_title]

    for raw_value in raw_values:
        lowered = raw_value.lower().strip()
        for key in COUNTRY_HASHTAGS:
            if key in lowered:
                return key

    return ""


def build_country_hashtag(round_item: CalendarRoundItem) -> str:
    key = normalize_country_key(round_item)
    return COUNTRY_HASHTAGS.get(key, "#ГранПри")


def build_country_flag(round_item: CalendarRoundItem) -> str:
    key = normalize_country_key(round_item)
    return COUNTRY_FLAGS.get(key, "🏁")


def build_round_key(round_item: CalendarRoundItem) -> str:
    return "|".join(
        [
            round_item.round_number.strip(),
            round_item.short_title.strip(),
            round_item.start_date.strip(),
        ]
    )


def format_datetime_msk(date_text: str) -> datetime:
    parsed = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
    return parsed.astimezone(MSK_TZ)


def format_date_label_ru(date_text: str) -> str:
    parsed = format_datetime_msk(date_text)
    return f"{parsed.day} {MONTHS_RU[parsed.month]}, {WEEKDAYS_RU[parsed.weekday()]}"


def format_time_ru(date_text: str) -> str:
    parsed = format_datetime_msk(date_text)
    return parsed.strftime("%H:%M")


def format_track_value(value: str) -> str:
    return value.replace("km", " km")


def build_schedule_post_text(round_item: CalendarRoundItem) -> str:
    flag = build_country_flag(round_item)
    hashtag = build_country_hashtag(round_item)
    title = html.escape(f"{flag} {round_item.short_title} {datetime.now().year}")
    circuit = html.escape(round_item.circuit_name)

    lines = [
        f"<b>{title}</b>",
        f"<b>{circuit}</b>",
        "",
    ]

    current_date = None
    for session in round_item.sessions:
        date_label = format_date_label_ru(session.start_date)
        if date_label != current_date:
            if current_date is not None:
                lines.append("")
            current_date = date_label
            lines.append(date_label)

        session_name = html.escape(translate_session_name(session.name))
        session_time = format_time_ru(session.start_date)
        session_emoji = build_session_emoji(session.name)
        lines.append(f"{session_emoji} {session_name} — {session_time} МСК")

    lines.append("")
    lines.append(f"#f1 #formula1 {hashtag}")

    return "\n".join(lines)


def translate_track_label(label: str) -> str:
    mapping = {
        "Circuit Length": "Длина трассы",
        "First Grand Prix": "Первый Гран-при",
        "Number of Laps": "Количество кругов",
        "Lap Record": "Рекорд круга",
        "Fastest lap time": "Рекорд круга",
        "Race Distance": "Дистанция гонки",
    }
    return mapping.get(label, label)


def build_track_info_text(round_item: CalendarRoundItem) -> str:
    flag = build_country_flag(round_item)
    circuit_name = html.escape(round_item.circuit_name)

    lines = [
        f"<b>{flag} Трасса: {circuit_name}</b>",
        "",
    ]

    for item in round_item.circuit.info:
        label = html.escape(translate_track_label(item.key))
        value = format_track_value(item.value.strip())

        if item.annotation:
            value = f"{value} — {item.annotation.strip()}"

        value = html.escape(value)
        lines.append(f"{label}: {value}")

    return "\n".join(lines)


def extract_map_url_from_schedule_post(schedule_post) -> str | None:
    if not schedule_post.source_payload_json:
        return None

    try:
        payload = json.loads(schedule_post.source_payload_json)
    except json.JSONDecodeError:
        return None

    circuit = payload.get("circuit")
    if not isinstance(circuit, dict):
        return None

    map_url = circuit.get("map_url")
    if isinstance(map_url, str) and map_url.strip():
        return map_url.strip()

    return None


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        "Received /status from chat_id=%s user_id=%s",
        update.effective_chat.id if update.effective_chat else None,
        update.effective_user.id if update.effective_user else None,
    )

    try:
        if not is_admin(update):
            logger.warning("Access denied for /status")
            return

        if update.effective_chat is None:
            return

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Bot is running. Admin panel is active.",
        )
        logger.info("Replied to /status successfully.")

    except Exception as error:
        logger.exception("status_command failed: %s", error)


async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        "Received /queue from chat_id=%s user_id=%s",
        update.effective_chat.id if update.effective_chat else None,
        update.effective_user.id if update.effective_user else None,
    )

    try:
        if not is_admin(update):
            logger.warning("Access denied for /queue")
            return

        if update.effective_chat is None:
            return

        async with AsyncSessionLocal() as session:
            repository = ArticleRepository(session)
            pending_ai = await repository.get_pending_ai_articles(limit=100)
            pending_tg = await repository.get_pending_telegram_articles(limit=100)
            failed_tg = await repository.get_failed_telegram_articles(limit=100)

            message = (
                "Queue status:\n\n"
                f"AI pending: {len(pending_ai)}\n"
                f"Telegram pending: {len(pending_tg)}\n"
                f"Telegram failed: {len(failed_tg)}"
            )

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
            )
        logger.info("Replied to /queue successfully.")

    except Exception as error:
        logger.exception("queue_command failed: %s", error)


async def run_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        "Received /run_now from chat_id=%s user_id=%s",
        update.effective_chat.id if update.effective_chat else None,
        update.effective_user.id if update.effective_user else None,
    )

    try:
        if not is_admin(update):
            logger.warning("Access denied for /run_now")
            return

        if update.effective_chat is None:
            return

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Manual pipeline run started.",
        )
        await run_pipeline_once()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Manual pipeline run finished.",
        )
        logger.info("Replied to /run_now successfully.")

    except Exception as error:
        logger.exception("run_now_command failed: %s", error)


async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        "Received /logs from chat_id=%s user_id=%s",
        update.effective_chat.id if update.effective_chat else None,
        update.effective_user.id if update.effective_user else None,
    )

    try:
        if not is_admin(update):
            logger.warning("Access denied for /logs")
            return

        if update.effective_chat is None:
            return

        log_path = Path("logs/pipeline.log")
        if not log_path.exists():
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Log file not found.",
            )
            return

        lines = log_path.read_text(encoding="utf-8").splitlines()
        tail = lines[-20:] if lines else []
        message = "\n".join(tail) if tail else "Log file is empty."

        if len(message) > 4000:
            message = message[-4000:]

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
        )
        logger.info("Replied to /logs successfully.")

    except Exception as error:
        logger.exception("logs_command failed: %s", error)


async def errors_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        "Received /errors from chat_id=%s user_id=%s",
        update.effective_chat.id if update.effective_chat else None,
        update.effective_user.id if update.effective_user else None,
    )

    try:
        if not is_admin(update):
            logger.warning("Access denied for /errors")
            return

        if update.effective_chat is None:
            return

        log_path = Path("logs/pipeline.log")
        if not log_path.exists():
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Log file not found.",
            )
            return

        lines = log_path.read_text(encoding="utf-8").splitlines()
        filtered = [
            line for line in lines
            if "ERROR" in line or "failed" in line.lower() or "crashed" in line.lower()
        ]
        tail = filtered[-20:] if filtered else []
        message = "\n".join(tail) if tail else "No recent errors found."

        if len(message) > 4000:
            message = message[-4000:]

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
        )
        logger.info("Replied to /errors successfully.")

    except Exception as error:
        logger.exception("errors_command failed: %s", error)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update) or update.effective_chat is None:
        return
    await send_main_menu(update.effective_chat.id, context)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update) or update.effective_chat is None:
        return
    await send_main_menu(update.effective_chat.id, context)


async def schedule_edit_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not is_admin(update):
            return
        if not context.user_data.get("schedule_edit_mode"):
            return
        if update.effective_chat is None or update.message is None:
            return

        edited_text = update.message.text.strip()
        schedule_post_id = context.user_data.get("schedule_post_id")

        if not schedule_post_id:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Не найдена запись расписания для редактирования.",
            )
            context.user_data["schedule_edit_mode"] = False
            return

        async with AsyncSessionLocal() as session:
            repository = SchedulePostRepository(session)
            schedule_post = await repository.get_by_id(schedule_post_id)

            if schedule_post is None:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Запись расписания не найдена в базе.",
                )
                context.user_data["schedule_edit_mode"] = False
                return

            await repository.save_edited_text(schedule_post, edited_text)

        context.user_data["schedule_edit_mode"] = False

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Черновик обновлён:\n\n" + edited_text,
            reply_markup=build_schedule_preview_menu(schedule_post_id),
            parse_mode="HTML",
        )

    except Exception as error:
        logger.exception("schedule_edit_text_handler failed: %s", error)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    if not is_admin(update):
        return

    try:
        if query.data == "status":
            await query.message.reply_text("Bot is running. Admin panel is active.")
            return

        if query.data == "queue":
            async with AsyncSessionLocal() as session:
                repository = ArticleRepository(session)
                pending_ai = await repository.get_pending_ai_articles(limit=100)
                pending_tg = await repository.get_pending_telegram_articles(limit=100)
                failed_tg = await repository.get_failed_telegram_articles(limit=100)

                message = (
                    "Queue status:\n\n"
                    f"AI pending: {len(pending_ai)}\n"
                    f"Telegram pending: {len(pending_tg)}\n"
                    f"Telegram failed: {len(failed_tg)}"
                )
                await query.message.reply_text(message)
            return

        if query.data == "logs":
            log_path = Path("logs/pipeline.log")
            if not log_path.exists():
                await query.message.reply_text("Log file not found.")
                return

            lines = log_path.read_text(encoding="utf-8").splitlines()
            message = "\n".join(lines[-20:]) if lines else "Log file is empty."
            if len(message) > 4000:
                message = message[-4000:]
            await query.message.reply_text(message)
            return

        if query.data == "errors":
            log_path = Path("logs/pipeline.log")
            if not log_path.exists():
                await query.message.reply_text("Log file not found.")
                return

            lines = log_path.read_text(encoding="utf-8").splitlines()
            filtered = [
                line for line in lines
                if "ERROR" in line or "failed" in line.lower() or "crashed" in line.lower()
            ]
            message = "\n".join(filtered[-20:]) if filtered else "No recent errors found."
            if len(message) > 4000:
                message = message[-4000:]
            await query.message.reply_text(message)
            return

        if query.data == "run_now":
            await query.message.reply_text("Manual pipeline run started.")
            await run_pipeline_once()
            await query.message.reply_text("Manual pipeline run finished.")
            return

        if query.data == "schedule_menu":
            await query.message.reply_text(
                "Меню расписания этапов",
                reply_markup=build_schedule_menu(),
            )
            return

        if query.data == "sources_menu":
            async with AsyncSessionLocal() as session:
                repository = SourceSettingRepository(session)
                sources = await repository.list_sources_with_status()

            if not sources:
                await query.message.reply_text("Источники пока не найдены.")
                return

            context.application.bot_data["source_settings_list"] = sources

            await query.message.reply_text(
                "Управление источниками:",
                reply_markup=build_sources_menu(sources),
            )
            return

        if query.data.startswith("source_toggle_"):
            index = int(query.data.replace("source_toggle_", ""))
            sources = context.application.bot_data.get("source_settings_list", [])

            if index >= len(sources):
                await query.message.reply_text("Источник не найден.")
                return

            source_name, _ = sources[index]

            async with AsyncSessionLocal() as session:
                repository = SourceSettingRepository(session)
                await repository.toggle_source(source_name)
                updated_sources = await repository.list_sources_with_status()

            context.application.bot_data["source_settings_list"] = updated_sources

            await query.message.reply_text(
                f"Источник обновлён: {source_name}",
                reply_markup=build_sources_menu(updated_sources),
            )
            return

        if query.data == "schedule_list":
            collector = CalendarCollector()
            payload = await collector.fetch_calendar_rsc()
            rounds = parse_calendar_rsc_payload(payload)

            if not rounds:
                await query.message.reply_text(
                    "Не удалось получить список этапов. Проверь RSC-запрос и парсер."
                )
                return

            context.application.bot_data["calendar_rounds"] = rounds

            keyboard = []
            for index, item in enumerate(rounds, start=0):
                round_label = item.round_number.strip() or "-"
                keyboard.append([
                    InlineKeyboardButton(
                        f"{round_label}. {item.short_title}",
                        callback_data=f"schedule_preview_{index}",
                    )
                ])

            keyboard.append([InlineKeyboardButton("Назад", callback_data="back_main")])

            await query.message.reply_text(
                "Выберите этап:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        if query.data.startswith("schedule_preview_"):
            index = int(query.data.replace("schedule_preview_", ""))
            rounds = context.application.bot_data.get("calendar_rounds", [])

            if index >= len(rounds):
                await query.message.reply_text("Этап не найден.")
                return

            selected_round = rounds[index]
            draft_text = build_schedule_post_text(selected_round)
            track_text = build_track_info_text(selected_round)
            round_key = build_round_key(selected_round)

            async with AsyncSessionLocal() as session:
                repository = SchedulePostRepository(session)
                schedule_post = await repository.create_or_update(
                    round_key=round_key,
                    round_number=selected_round.round_number,
                    grand_prix_title=selected_round.short_title,
                    country=selected_round.country,
                    city=selected_round.city,
                    circuit_name=selected_round.circuit_name,
                    start_date=selected_round.start_date,
                    end_date=selected_round.end_date,
                    original_text=draft_text,
                    track_text=track_text,
                    source_payload_json=json.dumps(selected_round.model_dump(), ensure_ascii=False),
                )

            context.user_data["schedule_post_id"] = schedule_post.id
            context.user_data["schedule_edit_mode"] = False

            await query.message.reply_text(
                schedule_post.original_text,
                reply_markup=build_schedule_preview_menu(schedule_post.id),
                parse_mode="HTML",
            )
            return

        if query.data.startswith("schedule_track_"):
            schedule_post_id = int(query.data.replace("schedule_track_", ""))

            async with AsyncSessionLocal() as session:
                repository = SchedulePostRepository(session)
                schedule_post = await repository.get_by_id(schedule_post_id)

                if schedule_post is None:
                    await query.message.reply_text("Информация о трассе не найдена.")
                    return

                map_url = extract_map_url_from_schedule_post(schedule_post)

                if map_url:
                    await context.bot.send_photo(
                        chat_id=query.message.chat.id,
                        photo=map_url,
                        caption=schedule_post.track_text,
                        parse_mode="HTML",
                    )
                else:
                    await query.message.reply_text(
                        schedule_post.track_text,
                        parse_mode="HTML",
                    )
            return

        if query.data.startswith("schedule_publish_track_"):
            schedule_post_id = int(query.data.replace("schedule_publish_track_", ""))

            async with AsyncSessionLocal() as session:
                repository = SchedulePostRepository(session)
                schedule_post = await repository.get_by_id(schedule_post_id)

                if schedule_post is None:
                    await query.message.reply_text("Информация о трассе не найдена.")
                    return

                map_url = extract_map_url_from_schedule_post(schedule_post)

                if map_url:
                    await context.bot.send_photo(
                        chat_id=settings.telegram_chat_id,
                        photo=map_url,
                        caption=schedule_post.track_text,
                        parse_mode="HTML",
                    )
                else:
                    await context.bot.send_message(
                        chat_id=settings.telegram_chat_id,
                        text=schedule_post.track_text,
                        parse_mode="HTML",
                    )

            await query.message.reply_text("Информация о трассе опубликована.")
            return

        if query.data.startswith("schedule_edit_"):
            schedule_post_id = int(query.data.replace("schedule_edit_", ""))
            context.user_data["schedule_post_id"] = schedule_post_id
            context.user_data["schedule_edit_mode"] = True

            await query.message.reply_text("Пришлите новый текст поста одним сообщением.")
            return

        if query.data.startswith("schedule_publish_original_"):
            schedule_post_id = int(query.data.replace("schedule_publish_original_", ""))

            async with AsyncSessionLocal() as session:
                repository = SchedulePostRepository(session)
                schedule_post = await repository.get_by_id(schedule_post_id)

                if schedule_post is None:
                    await query.message.reply_text("Исходный текст не найден.")
                    return

                await context.bot.send_message(
                    chat_id=settings.telegram_chat_id,
                    text=schedule_post.original_text,
                    parse_mode="HTML",
                )
                await repository.mark_original_sent(schedule_post)

            await query.message.reply_text("Исходное расписание опубликовано.")
            return

        if query.data.startswith("schedule_publish_edited_"):
            schedule_post_id = int(query.data.replace("schedule_publish_edited_", ""))

            async with AsyncSessionLocal() as session:
                repository = SchedulePostRepository(session)
                schedule_post = await repository.get_by_id(schedule_post_id)

                if schedule_post is None:
                    await query.message.reply_text("Отредактированный текст не найден.")
                    return

                if not schedule_post.edited_text:
                    await query.message.reply_text("Отредактированный текст пока не сохранён.")
                    return

                await context.bot.send_message(
                    chat_id=settings.telegram_chat_id,
                    text=schedule_post.edited_text,
                    parse_mode="HTML",
                )
                await repository.mark_edited_sent(schedule_post)

            await query.message.reply_text("Отредактированное расписание опубликовано.")
            return

        if query.data == "back_main":
            await query.message.reply_text(
                "Главное меню",
                reply_markup=build_main_menu(),
            )
            return

    except Exception as error:
        logger.exception("button_handler failed: %s", error)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Telegram application error: %s", context.error)


def build_admin_application() -> Application:
    application = Application.builder().token(settings.telegram_bot_token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("queue", queue_command))
    application.add_handler(CommandHandler("run_now", run_now_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("errors", errors_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, schedule_edit_text_handler))
    application.add_error_handler(error_handler)

    return application