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

async def handle_validation_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    validator = query.from_user
    validator_display_name = utils.get_display_name_from_telegram_user(validator)

    await query.answer()

    data = query.data
    challenge_response_id = int(data.split("_")[1])

    challenger = utils.get_user_display_name_by_challenge_response_id(challenge_response_id)
    challenge_description = utils.get_challenge_from_challenge_response_id(challenge_response_id)['description']

    if data.endswith("_yes"):

        await utils.mark_challenge_as_validated(challenge_response_id)
        
        await query.answer(f"✅ Challenge validated successfully!")
        await query.edit_message_text(
            text = f"✅ You have validated the challenge completion for {challenger}.\n\nChallenge:\n{challenge_description}\n\nThank you for your help!",
            reply_markup = None,
            parse_mode = 'HTML')
        await query.message.reply_text(f"✅ {challenger}'s challenge has been validated successfully by {validator_display_name}! Great job!")

    elif data.endswith("_no"):

        await utils.mark_challenge_as_rejected(challenge_response_id)

        await query.answer(f"❌ Challenge rejected.")
        await query.edit_message_text(
            text = f"❌ You have rejected the challenge completion for {challenger}. They <b>did not</b> complete the following challenge:\n{challenge_description}",
            reply_markup = None,
            parse_mode = 'HTML')
        await query.message.reply_text(f"❌ Hey {challenger}, {validator_display_name} does not think you did enough to complete the following challenge:\n{challenge_description}\n\n Prove them wrong tomorrow!")


async def validate(update: Update, context: ContextTypes.DEFAULT_TYPE, challenge_response_id, user_id) -> None:

    challenge = utils.get_challenge_from_challenge_response_id(challenge_response_id)

    challenge_description = challenge['description']

    goal_id = utils.get_goal_id_from_challenge_id(challenge['challenge_id'])

    group_id = utils.get_group_id_by_goal_id(goal_id)

    # Select validator at random from group members
    members = utils.get_members_in_goal(goal_id)

    # Drop partners who are the user themselves
    validators = [v for v in members if v["user_id"] != user_id]

    # Username of challenger
    challenger = utils.get_display_name_from_user_id(user_id)

    if not validators:
        await context.bot.send_message(
            chat_id = group_id,
            text = f"You're alone in this goal, I'll just take your word for it this time...\n\n<b>Congratulations 🎉</b>, you have completed the following goal:\n{challenge_description}\n\nFind an accountability partner to join your quest soon... You have a higher chance of achieving your goal with a friend keeping you company!\n\n<i>Source: Me 😎</i>",
            parse_mode = 'HTML'
        )
        return  # No one to validate the challenge

    # Randomly select a validator
    selected_validator = random.choice(validators)

    await context.bot.send_message(
        chat_id=group_id,
        text=(
                f"{selected_validator['name']}, you have been chosen to validate the completion of {challenger['name']}'s challenge! 🎯\n\n<b>Challenge Description:</b>\n{challenge_description}\n\nDo you think they completed their challenge?"
            ),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Yes, they did!", callback_data=f"validate_{challenge_response_id}_yes"),
            InlineKeyboardButton("No, they didn't.", callback_data=f"validate_{challenge_response_id}_no")
        ]]),
        parse_mode='HTML'
    )

