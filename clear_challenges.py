import os
from datetime import datetime, timedelta
import constants as consts
import utils
from telegram.error import Forbidden, BadRequest, TimedOut, NetworkError
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ChatMemberHandler,
)

async def fail_expiring_challenges(context: ContextTypes.DEFAULT_TYPE):
    """Mark challenges that have not been completed failed."""

    expiring_challenges = utils.get_expiring_challenges()

    if not expiring_challenges:
        await context.bot.send_message(
            chat_id=os.getenv("ADMIN_TELEGRAM_USER_ID"),
            text="No expiring challenges found, everyone completed their challenges today! 🎉"
        )
        return

    for challenge in expiring_challenges:
        challenge_response_id = challenge["id"]
        challenge_id = challenge["challenge_id"]
        goal_id = challenge["goal_id"]
        description = challenge["description"]
        user_id = challenge["user_id"]
        display_name = utils.get_display_name_from_user_id(user_id)

        # Get group ID
        group_id = utils.get_group_id_by_goal_id(goal_id)

        await context.bot.send_message(
            chat_id=group_id,
            text=f"{display_name} failed to complete challenge {description} on time. Try again tomorrow! 💪"
        )
    
    await context.bot.send_message(
        chat_id=os.getenv("ADMIN_TELEGRAM_USER_ID"),
        text=f"{len(expiring_challenges)} challenges were marked as failed today."
    )

    return

async def fail_prizefights(context: ContextTypes.DEFAULT_TYPE):
    """Mark prize fights that have not been completed failed."""

    expiring_prizefights = utils.get_pending_prizefights()

    if not expiring_prizefights:
        await context.bot.send_message(
            chat_id=os.getenv("ADMIN_TELEGRAM_USER_ID"),
            text="No expiring prize fights found, everyone completed their prize fights today! 🎉"
        )
        return

    for prizefight in expiring_prizefights:
        prizefight_participant_id = prizefight["id"]
        prize_fight_id = prizefight["prizefight_id"]
        challenge = prizefight["challenge"]
        prize = prizefight["prize"]
        user_id = prizefight["user_id"]
        group_id = prizefight["group_id"]
        display_name = utils.get_display_name_from_user_id(user_id)

        await context.bot.send_message(
            chat_id=group_id,
            text=f"{display_name} failed to complete the prize fight '{challenge}' for ${prize} on time. Try again tomorrow! 💪"
        )
    
    await context.bot.send_message(
        chat_id=os.getenv("ADMIN_TELEGRAM_USER_ID"),
        text=f"{len(expiring_prizefights)} prize fights were marked as failed today."
    )

    return

