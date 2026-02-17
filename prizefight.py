import random
import logging

import utils
import constants as consts


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

logger = logging.getLogger(__name__)

def parse_prizefight_message(message_html):
    """
    Parse prize fight details from formatted message HTML.

    Args:
        message_html (str): HTML-formatted prize fight message

    Returns:
        dict: Dictionary with 'challenge', 'prize', 'challenger_name' keys

    Raises:
        ValueError: If message format is invalid
    """
    try:
        challenge = message_html.split("<b>Challenge:</b> ")[1].split("\n")[0]
        prize = message_html.split("<b>Prize:</b> $")[1].split("\n")[0]
        challenger_name = message_html.split("💰<b>PRIZE FIGHT</b> - ")[1].split(" vs ")[0]

        return {
            'challenge': challenge,
            'prize': prize,
            'challenger_name': challenger_name
        }
    except (IndexError, KeyError) as e:
        raise ValueError(f"Invalid prize fight message format: {e}")

async def prize_fight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a prize fight between two users."""
    group = update.effective_chat
    user = update.effective_user
    display_name = utils.get_display_name_from_telegram_user(user)

    await utils.upsert_user_and_group(user, group)

    try:
        # Check if the message is a reply to a prize fight suggestion
        if update.message.text.strip().startswith("/prizefight"):
            full_text = update.message.text.replace("/prizefight", "").strip() # /prizefight <challenge> <prize> <participant>
            if " " in full_text:
                challenge, prize, participant = full_text.rsplit(" ", 2)
        elif not update.message.reply_to_message or "What would you like to suggest for the prize fight?" not in update.message.reply_to_message.text:
            return
        elif update.message.reply_to_message and "What would you like to suggest for the prize fight?" in update.message.reply_to_message.text:
            full_text = update.message.text.strip() # [challenge]<space>[prize]<space>[@participant]
            if " " in full_text:
                challenge, prize, participant = full_text.rsplit(" ", 2)
        else:
            full_text = update.message.text.replace("/prizefight", "").strip() # /prizefight <challenge> <prize> <participant>
            if " " in full_text:
                challenge, prize, participant = full_text.rsplit(" ", 2)

        message = f"💰<b>PRIZE FIGHT</b> - {display_name} vs {participant}\n\n*********************\n<b>Challenge:</b> {challenge}\n<b>Prize:</b> ${prize}\n*********************\n\nParty that completes that challenge receives payment from the other party. If the both of you completes/fails the challenge, keep trying until one of you wins!\n\nAccept or Suggest another Prize Fight!"

        keyboard = [
            InlineKeyboardButton("Accept Prize Fight", callback_data=f"accept_prizefight:{challenge}:{prize}"),
            InlineKeyboardButton("Suggest another challenge", callback_data="suggest_prizefight")
        ]
        reply_markup = InlineKeyboardMarkup([keyboard])

        await update.message.reply_text(
            message,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Prize fight error: {e}")
        await update.message.reply_text(
            "Format your prize fight suggestion like this: /prizefight <challenge> <prize> <participant>.\n\nExample: /prizefight Do 50 pushups 10 @john_doe"
        )
        return

async def handle_prize_fight_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    display_name = utils.get_display_name_from_telegram_user(user)
    group_id = query.message.chat_id

    await query.answer()
    await utils.upsert_user_and_group(user, query.message.chat)

    try:
        parsed = parse_prizefight_message(query.message.text_html)
        challenge = parsed['challenge']
        prize = parsed['prize']
        challenger_name = parsed['challenger_name']
        challenger_user_id = utils.get_user_id_from_display_name(challenger_name)
    except ValueError as e:
        await query.answer("Error parsing prize fight details.", show_alert=True)
        logger.error(f"Parse error in handle_prize_fight_response: {e}")
        return

    data_parts = query.data
    if "accept_prizefight" in data_parts and challenger_user_id is not None:
        try:
            prize_fight_id = utils.insert_into_prizefights(challenge, prize, group_id)
            utils.insert_into_prizefight_participants(prize_fight_id, challenger_user_id['user_id'])
            utils.insert_into_prizefight_participants(prize_fight_id, user_id)

            await query.edit_message_reply_markup(reply_markup=None)
        except Exception as e:
            logger.error(f"Database error inserting prize fight: {e}")

        message = f"🏆 {display_name} accepted the prize fight!\n<b>Challenge:</b> {challenge}\n<b>Prize:</b> ${prize}!\n\nSend your proof of completion here for all to see! Challenge begins now! May the best win!"

        # User accepted the prize fight
        await query.message.reply_text(
            text=message,
            parse_mode='HTML')
    else:
        await query.message.reply_text(
            "What would you like to suggest for the prize fight? Reply to this message with your challenge idea in this format - [challenge]<space>[prize]<space>[@participant].",
            reply_markup=ForceReply(selective=True)
            )
        await query.edit_message_reply_markup(reply_markup=None)
        return
    
    # Send confirmation messages
    await query.answer(f"You joined the prize fight!")

async def complete_prize_fight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_id = user.id
    group_id = update.message.chat.id
    display_name = utils.get_display_name_from_telegram_user(user)

    # Query for all active prize fights the user is participating in within the group

    active_prize_fights = utils.get_prize_fight_for_user_id(user_id, group_id)

    if not active_prize_fights:
        await update.message.reply_text("You have no active prize fights to complete in this group.")
        return

    # Build the message and buttons for active prize fights
    keyboard = [
        InlineKeyboardButton(f"{pf['challenge']} - ${pf['prize']}", callback_data=f"complete_prizefight:{pf['id']}")
        for pf in active_prize_fights
    ]

    reply_markup = InlineKeyboardMarkup([keyboard])

    await update.message.reply_text(
        f"Completing your prize fight already? Send in your <u><b>convincing proof of completion</b></u> and select the prize fight you wish to complete:",
        reply_markup=reply_markup,
        parse_mode='HTML'
        )

async def complete_selected_prize_fight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    group_id = query.message.chat.id
    display_name = utils.get_display_name_from_telegram_user(user)

    prize_fight_id = query.data.split(":")[1]  # Extract the prize fight ID

    # Get prize fight details
    prize_fight = utils.get_prize_fight_details(prize_fight_id)
    if not prize_fight:
        await query.answer("Something went wrong while fetching prize fight details. Please try again.")
        return

    # Get other challengers of the prize fight
    challengers = utils.get_prize_fight_participants(prize_fight_id, exclude_user_id=user_id)
    
    if not challengers:
        await query.answer("Something went wrong, please restart the prize fight.")

    # Randomly choose a challenger to validate the completion
    validator = random.choice(challengers)
    validator_user_id = validator['user_id']
    validator_display_name = f"@{validator['username']}" if validator['username'] else validator['display_name']

    keyboard = [
        InlineKeyboardButton("Yes!", callback_data=f"prizefight_validate:{prize_fight_id}:{user_id}:accept"),
        InlineKeyboardButton("Nope!", callback_data=f"prizefight_validate:{prize_fight_id}:{user_id}:reject")
    ]
    reply_markup = InlineKeyboardMarkup([keyboard])

    # Notify the validator
    await query.message.reply_text(
        f"Hey {validator_display_name}, {display_name} has completed prize fight <b>{prize_fight['challenge']}</b>. Are you convinced?",
        reply_markup=reply_markup,
        parse_mode='HTML'
        )
    
async def handle_prize_fight_validation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    display_name = utils.get_display_name_from_telegram_user(user)

    await query.answer()
    await utils.upsert_user_and_group(user, query.message.chat)

    data_parts = query.data.split(":")
    prize_fight_id = data_parts[1]
    challenger_user_id = data_parts[2]
    action = data_parts[3]

    challenger = utils.get_display_name_from_user_id(int(challenger_user_id))

    if action == "accept":
        # Validator accepted the completion
        utils.edit_prize_fight_status(int(prize_fight_id), int(challenger_user_id), "completed")

        await query.message.reply_text(
            text=f"🏆 Congratulations {challenger['name']}! Your prize fight completion has been validated by {display_name}. You have officially completed the challenge!"
            )
    elif action == "reject":
        # Validator rejected the completion
        utils.edit_prize_fight_status(int(prize_fight_id), int(challenger_user_id), "failed")

        await query.message.reply_text(
            text=f"❌ Hey {challenger['name']}, {display_name} does not think you did enough to complete the prize fight challenge. Issue a new prize fight and prove them wrong!"
            )