from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import settings
from app.db.repositories import ArticleRepository
from app.db.session import AsyncSessionLocal
from app.logger import setup_logger

logger = setup_logger()


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
            logger.warning("No effective_chat in /status")
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
            logger.warning("No effective_chat in /queue")
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
            logger.warning("No effective_chat in /run_now")
            return

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Manual pipeline trigger is not connected yet. We will add it in the next step.",
        )

        logger.info("Replied to /run_now successfully.")

    except Exception as error:
        logger.exception("run_now_command failed: %s", error)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Telegram application error: %s", context.error)


def build_admin_application() -> Application:
    application = Application.builder().token(settings.telegram_bot_token).build()

    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("queue", queue_command))
    application.add_handler(CommandHandler("run_now", run_now_command))
    application.add_error_handler(error_handler)

    return application