import utils
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

async def validate_completion(context: ContextTypes.DEFAULT_TYPE):
    """
    Goes through all challenges that are marked as completed by the user and validates them against another member of the group.
    """

    unvalidated_challenges = utils.get_completed_unvalidated_challenges()

    if not unvalidated_challenges:
        return
    
    for challenge in unvalidated_challenges:
        challenge_response_id = challenge["challenge_response_id"]
        challenge_id = challenge["challenge_id"]
        completed_at = challenge["completed_at"]
        description = challenge["description"]
        goal_id = challenge["goal_id"]
        user_id = challenge["user_id"]
        challenge_text = challenge["description"]

        # Get group ID
        group_id = utils.get_group_id_by_goal_id(goal_id)

        # Get user handle
        username = utils.get_display_name_from_user_id(user_id)

        if not group_id:
            print("No group found for goal_id:", goal_id)
            return  # Goal does not belong to any group

        # Find partners to validate the challenge
        members = utils.get_members_in_goal(goal_id)

        # Drop partners who are the user themselves
        validators = [v for v in members if v["user_id"] != user_id]

        if not validators:
            await context.bot.send_message(
                chat_id = group_id,
                text = f"Hm... it seems there is no one available to validate your completed completed challenge... Okay, I'll just take your word for it this time...\n\n<b>Congratulations 🎉</b>, you have completed the following goal:\n{challenge_text}\n\nFind an accountability partner to join your quest soon... You have a higher chance of achieving your goal with a friend keeping you company!\n\n<i>Source: Me 😎</i>",
                parse_mode = 'HTML'
            )
            return  # No one to validate the challenge

        # Randomly select a validator
        selected_validator = random.choice(validators)

        # For simplicity, pick the first member to validate
        validator_user_id = selected_validator["user_id"]
        validator_name = selected_validator["name"]

        # Send validation request to the validator
        keyboard = [
            [
                InlineKeyboardButton("✅ Validate", callback_data=f"validate_{challenge_response_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{challenge_response_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=group_id,
            text=(
                f"👋 Hi {validator_name},\n\n"
                f"You've been selected to validate the completion of {username['name']}'s challenge! 🎯\n\n"
                f"🔍 *Challenge Details:*\n"
                f"• *Description:* {description}\n"
                f"• *Completed At:* {completed_at}\n\n"
                f"✅ *Your Role:*\n"
                f"Please confirm whether this challenge was completed successfully.\n\n"
                f"Your validation helps maintain accountability and ensures the integrity of the group goals."
            ),
            reply_markup=reply_markup,
        )

async def handle_validation_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    validator = query.from_user
    validator_display_name = f"@{validator.username}" if validator.username else validator.first_name

    await query.answer()

    data = query.data
    challenge_response_id = int(data.split("_")[1])

    challenger = utils.get_user_display_name_by_challenge_response_id(challenge_response_id)
    challenge_description = utils.get_challenge_from_challenge_response_id(challenge_response_id)['description']

    if data.startswith("validate_"):

        await utils.mark_challenge_as_validated(challenge_response_id)
        
        await query.answer(f"✅ Challenge validated successfully!")
        await query.edit_message_text(
            text = f"✅ You have validated the challenge completion for {challenger}. They have completed the following challenge:\n{challenge_description}\n\nThank you for your help!",
            reply_markup = None,
            parse_mode = 'HTML')
        await query.message.reply_text(f"✅ {challenger}'s challenge has been validated successfully by ! Great job!")

    elif data.startswith("reject_"):

        await utils.mark_challenge_as_rejected(challenge_response_id)

        await query.answer(f"❌ Challenge rejected.")
        await query.edit_message_text(
            text = f"❌ You have rejected the challenge completion for {challenger['display_name']}. They <b>did not</b> complete the following challenge:\n{challenge_description}",
            reply_markup = None,
            parse_mode = 'HTML')
        await query.reply_text(f"❌ Hey {challenger['display_name']}, {validator_display_name} does not think you did enough to complete the following challenge:\n{challenge_description}\n\n Prove them wrong tomorrow!")

