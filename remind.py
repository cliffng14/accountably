import os
import logging
import utils
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

async def send_morning_reminder(context: ContextTypes.DEFAULT_TYPE):

    challenges_issued_yesterday = utils.get_challenges_issued_yesterday()

    for challenge in challenges_issued_yesterday:
        challenge_id = challenge["id"]
        goal_id = challenge["goal_id"]
        challenge_text = challenge["description"]

        # Get group ID
        group_id = utils.get_group_id_by_goal_id(goal_id)

        # Get users participating in the challenge
        participants = utils.get_challenge_accepted_participants(challenge_id)
        participants_list = [p["name"] for p in participants]
        participants_str = utils.format_names_list(participants_list)

        if not group_id:
            logger.error(f"No group found for goal_id: {goal_id}")
            return  # Goal does not belong to any group

        try:
            await context.bot.send_message(
                chat_id=group_id,
                text=f"🌅 Good morning {participants_str}! A reminder on your goal today:\n\n🎯 <b>Challenge:</b> {challenge_text}\n\nDon't forget to complete it today and mark it as done! Let's keep pushing towards our goals together! 💪",
                parse_mode='HTML'
            )
        except Exception as e:
            await context.bot.send_message(
            chat_id=os.getenv("ADMIN_TELEGRAM_USER_ID"),
            text=f"Failed to send morning reminder to group {group_id}\n\nChallenge ID: {challenge_id}\nChallenge: {challenge_text}\nError: {e}",
            parse_mode='HTML'
            )

async def send_evening_reminder(context: ContextTypes.DEFAULT_TYPE):
    
    challenges_issued_yesterday = utils.get_challenges_issued_yesterday()

    for challenge in challenges_issued_yesterday:
        challenge_id = challenge["id"]
        goal_id = challenge["goal_id"]
        challenge_text = challenge["description"]

        # Get group ID
        group_id = utils.get_group_id_by_goal_id(goal_id)

        # Get users participating in the challenge
        participants = utils.get_challenge_accepted_participants(challenge_id)
        participants_list = [p["name"] for p in participants]
        participants_str = utils.format_names_list(participants_list)

        if not group_id:
            logger.error(f"No group found for goal_id: {goal_id}")
            return  # Goal does not belong to any group

        try:
            await context.bot.send_message(
                chat_id=group_id,
                text=f"🌆 Good evening {participants_str}! Just a friendly reminder to complete your challenge for today:\n\n🎯 <b>Challenge:</b> {challenge_text}\n\nMake sure to mark it as done before the deadline! Let's finish strong! 💪",
                parse_mode='HTML'
            )
        except Exception as e:
            await context.bot.send_message(
            chat_id=os.getenv("ADMIN_TELEGRAM_USER_ID"),
            text=f"Failed to send evening reminder to group {group_id}\n\nChallenge ID: {challenge_id}\nChallenge: {challenge_text}\nError: {e}",
            parse_mode='HTML'
            )
