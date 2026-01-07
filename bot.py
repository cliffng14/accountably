import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ChatMemberHandler,
)
import sqlite3
import constants as consts
import challenge
import validate_completion
import utils
from datetime import datetime, time
import pytz

from dotenv import load_dotenv

load_dotenv()


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Replace with your bot token from @BotFather
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def upsert_user(user):

    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (user_id, username, display_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                display_name = excluded.display_name,
                updated_at = CURRENT_TIMESTAMP
        """, (user.id, user.username, user.first_name))

        conn.commit()

async def feedback_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward user feedback to admin."""
    ADMIN_USER_ID = os.getenv("ADMIN_TELEGRAM_USER_ID")  # Replace with your Telegram user ID
    
    # Get the feedback message (everything after /feedback)
    feedback = ' '.join(context.args)
    
    if not feedback:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please include your feedback after the command.\n\nExample: <code>/feedback I love this bot!</code>",
            parse_mode='HTML'
        )
        return
    
    # Get user info
    user = update.effective_user
    user_name = user.username or user.first_name
    
    # Send feedback to admin
    await context.bot.send_message(
        chat_id=ADMIN_USER_ID,
        text=(
            f"📬 <b>New Feedback</b>\n\n"
            f"<b>From:</b> @{user_name} (ID: {user.id})\n"
            f"<b>Message:</b> {feedback}"
        ),
        parse_mode='HTML'
    )
    
    # Confirm to user
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✅ Thanks for your feedback! It has been sent to the admin :)"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help information when the /help command is issued."""
    help_text = consts.INTRODUCTION_TEXT
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_text,
        parse_mode='HTML'
    )

async def goals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show a list of available goals in the group and allow users to join."""
    group = update.effective_chat
    user = update.effective_user
    user_id = user.id

    # Insert or update the user in the database
    await upsert_user(user)

    # Fetch active goals the user has already joined
    joined_goals = utils.get_active_participanting_goals(group.id, user_id)

    # Fetch active goals the user has not joined
    available_goals = utils.get_active_non_participanting_goal_ids(group.id, user_id)

    # Build the message
    message_parts = []

    if joined_goals:
        joined_list = "\n".join(f"• {goal}" for _, goal in joined_goals)
        message_parts.append(f"Your current goals:\n{joined_list}")
    else:
        message_parts.append("You have not joined any goals yet. Join an available goal below or create one using /addgoal.")

    if available_goals:
        message_parts.append("\nAvailable goals to join:")
        keyboard = [
            [InlineKeyboardButton(goal, callback_data=f"join_goal_from_goals_command:{goal_id}")]
            for goal_id, goal in available_goals
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        message_parts.append("\nNo other goals available to join. Create one using /addgoal.")
        reply_markup = None

    await update.message.reply_text(
        "\n".join(message_parts),
        reply_markup=reply_markup
    )

async def join_goals_from_goals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    group_id = query.message.chat.id
    goal_id = query.data.split(":")[1]  # Extract the goal ID (e.g., "42")
    display_name = f"@{user.username}" if user.username else user.first_name

    # Insert the user into the database
    try:
        conn = sqlite3.connect(consts.GOALS_DB_SQLITE)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO goal_members (goal_id, user_id, role) VALUES (?, ?, ?)",
            (goal_id, user_id, "member")
        )
        conn.commit()
        conn.close()

    except sqlite3.Error as e:
        await update.message.reply_text("An error occurred while joining goal. Please try again.")
        logger.error(f"Database error: {e}")
        return
    
    # Send confirmation messages
    await query.answer(f"{display_name} joined the goal!")
    await query.message.reply_text(f"{display_name} joined the goal!")

    # Update the original message to reflect the change
    new_message_parts = []

    new_joined_goals = utils.get_active_participanting_goals(group_id, user_id)
    new_available_goals = utils.get_active_non_participanting_goal_ids(group_id, user_id)

    if new_joined_goals:
        new_joined_list = "\n".join(f"• {goal}" for _, goal in new_joined_goals)
        new_message_parts.append(f"Your current goals:\n{new_joined_list}")
    else:
        new_message_parts.append("You have not joined any goals yet. Join an available goal below or create one using /addgoal.")

    if new_available_goals:
        new_message_parts.append("\nAvailable goals to join:")
        keyboard = [
            [InlineKeyboardButton(goal, callback_data=f"join_goal_from_goals_command:{goal_id}")]
            for goal_id, goal in new_available_goals
        ]
        new_reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        new_message_parts.append("\nNo other goals available to join. Create one using /addgoal.")
        new_reply_markup = None

    await query.edit_message_text(
        text="\n".join(new_message_parts),
        reply_markup=new_reply_markup,
        parse_mode="HTML"
    )
    await query.edit_message_text(f"")

async def add_goal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group = update.effective_chat
    user = update.effective_user
    display_name = f"@{user.username}" if user.username else user.first_name

    # Insert or update the user in the database
    await upsert_user(user)

    full_text = update.message.text

    # Extract the goal text from the command
    if " " in full_text:
        message = full_text.split(" ", 1)[1]
    else:
        await update.message.reply_text("Please provide a goal after the command, e.g., /addgoal Learn Python.")
        return

    # Insert the goal into the database
    try:
        with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO goals (group_id, goal, status) VALUES (?, ?, ?)",
                (group.id, message, "active")
            )

            cursor.execute(
                "INSERT INTO goal_members (goal_id, user_id, role) VALUES (?, ?, ?)",
                (cursor.lastrowid, user.id, "owner")
            )
            conn.commit()
            goal_id = cursor.lastrowid # Get the auto-incremented goal ID

        # Save the goal temporarily in the context for later use
        context.chat_data[f"goal_id_{goal_id}"] = {"goal": message, "creator_id": user.id, "participants":[user.id]}

        await update.message.reply_text(f"Goal added: '{message}' by {display_name}.")
    except sqlite3.Error as e:
        await update.message.reply_text("An error occurred while adding the goal. Please try again.")
        logger.error(f"Database error: {e}")
        return

    # Callback for encouraging others to join the goal
    keyboard = [
        InlineKeyboardButton("Join Goal", callback_data=f"join_goal_from_creation:{goal_id}")
    ]
    reply_markup = InlineKeyboardMarkup([keyboard])

    await update.message.reply_text(
        f"{display_name} has started a new goal: '{message}'. Do you want to join?",
        reply_markup=reply_markup
    )

async def join_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    # Get information from the callback data
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    group_id = query.message.chat.id
    goal_id = query.data.split(":")[1]
    display_name = f"@{user.username}" if user.username else user.first_name

    # Adding user to goal in chat_data
    try:
        context.chat_data.get(f"goal_id_{goal_id}")['participants'].append(user_id)
        await query.answer(f"@{display_name} joined the goal.", show_alert=True)
    except KeyError:
        await query.answer("Error in adding participant into group context", show_alert=True)
        return

    # Insert the user into the database
    try:
        conn = sqlite3.connect(consts.GOALS_DB_SQLITE)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO goal_members (goal_id, user_id, role) VALUES (?, ?, ?)",
            (goal_id, user_id, "member")
        )
        conn.commit()
        conn.close()

    except sqlite3.Error as e:
        await query.message.reply_text("An error occurred while joining goal. Please try again.")
        logger.error(f"Database error: {e}")
        return
    
    # Send confirmation messages
    await query.answer(f"{display_name} joined the goal!")
    await query.message.reply_text(f"{display_name} joined the goal!")

async def join_goal_from_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    goal_id = query.data.split(":")[1]

    new_goal = context.chat_data.get(f"goal_id_{goal_id}")

    await upsert_user(user)

    if not new_goal:
        await query.answer("Something went wrong.", show_alert=True)
        return

    # Track who has joined
    if "participants" not in new_goal:
        query.answer("No participants list found.", show_alert=True)
        return

    if user_id in new_goal["participants"]:
        await query.answer("You already joined!", show_alert=True)
        return

    # Add user to goal
    try:
        await join_goal(update, context)
    except Exception as e:
        await query.answer("An error occurred while joining the goal.", show_alert=True)
        logger.error(f"Error in join_goal_from_creation: {e}")
        return

async def delete_goal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:   
    """Delete a goal for the user."""
    await update.message.reply_text("Thinking of giving up? Oops... delete goal functionality coming soon... maybe next year...")

async def complete_challenge_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mark a challenge as completed."""

    group = update.effective_chat
    user = update.effective_user
    user_id = user.id
    display_name = f"@{user.username}" if user.username else user.first_name

    # Insert or update the user in the database
    await upsert_user(user)

    # Fetch active challenges the user has already joined
    pending_challenges = utils.get_pending_challenges(group.id, user_id)

    if not pending_challenges:
        await update.message.reply_text("You have no pending challenges to complete.")
        return
    
    # Craft the message listing pending challenges
    message = f"{display_name} is completing a challenge! Pending challenges are listed below. Choose one to mark as completed and I will validate it with another group member:"

    keyboard = [
            [InlineKeyboardButton(challenges['description'], callback_data=f"mark_challenge_complete:{challenges['challenge_response_id']}")]
            for challenges in pending_challenges
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        message,
        reply_markup=reply_markup
    )

async def mark_challenge_complete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    display_name = f"@{user.username}" if user.username else user.first_name

    challenge_response_id = query.data.split(":")[1]  # Extract the challenge response ID

    # Update the challenge response status to 'completed'
    try:
        with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE challenge_responses SET status = 'completed', completed_at = ? WHERE id = ? AND user_id = ?",
                (datetime.now().isoformat(), challenge_response_id, user_id)
            )
            conn.commit()
    except sqlite3.Error as e:
        await query.answer("An error occurred while marking the challenge as completed. Please try again.")
        logger.error(f"Database error: {e}")
        return

    await query.answer(f"🎉 {display_name}, your challenge has been marked as completed! Great job!")
    await query.edit_message_text(
        text = f"🎉 {display_name} has marked a challenge as completed! Great job!",
        reply_markup = None, 
        parse_mode = 'HTML')
    
async def bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if the bot was added (status changed to "member" or "administrator")
    result = update.my_chat_member
    
    if result.new_chat_member.status in ["member", "administrator"]:
        await context.bot.send_message(
            chat_id=result.chat.id,
            text=consts.INTRODUCTION_TEXT,
            parse_mode='HTML'
        )

async def private_chat_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to private messages with a standard message."""
    if update.effective_chat.type == "private":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="👋 Hi! I only work in group chats.\n\nAdd me to your chatgroup to get started! Don't worry, I don't have access to the regular messages sent in your groupchat, just the ones directed at me :)",
        )

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Set timezone for scheduling
    sgt = pytz.timezone('Asia/Singapore')

    # application.job_queue.run_repeating(challenge.schedule_challenges, interval=3600, first=10)
    # application.job_queue.run_repeating(validate_completion.validate_completion, interval=3600, first=30)

    # Generate and issue challenges for the next day at 9:30 PM SGT daily
    application.job_queue.run_daily(challenge.schedule_challenges, time=time(hour=22, minute=45, tzinfo=sgt))

    # Validate completed challenges at 10:00 PM SGT daily
    application.job_queue.run_daily(validate_completion.validate_completion, time=time(hour=22, minute=30, tzinfo=sgt))


    # Add command handlers
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("goals", goals_command))
    application.add_handler(CommandHandler("addgoal", add_goal_command))
    application.add_handler(CommandHandler("feedback", feedback_to_admin))
    application.add_handler(CommandHandler("deletegoal", delete_goal_command))
    application.add_handler(CommandHandler("complete", complete_challenge_command))

    # application.add_handler(CommandHandler("buttons", buttons))

    # Add callback handler for inline buttons
    application.add_handler(CallbackQueryHandler(join_goal_from_creation, pattern=r"^join_goal_from_creation:"))
    application.add_handler(CallbackQueryHandler(join_goals_from_goals_command, pattern=r"^join_goal_from_goals_command:"))
    application.add_handler(CallbackQueryHandler(challenge.accept_challenge, pattern=r"^accept_challenge_"))
    application.add_handler(CallbackQueryHandler(challenge.handle_suggest_challenge, pattern=r"^suggest_challenge_"))
    application.add_handler(CallbackQueryHandler(mark_challenge_complete_handler, pattern=r"^mark_challenge_complete:"))
    application.add_handler(CallbackQueryHandler(validate_completion.handle_validation_response, pattern=r"^validate_"))
    application.add_handler(CallbackQueryHandler(validate_completion.handle_validation_response, pattern=r"^reject_"))
    application.add_handler(MessageHandler(filters.TEXT & filters.REPLY & ~filters.COMMAND, challenge.handle_suggestion_reply))
    application.add_handler(ChatMemberHandler(bot_added_to_group, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE, private_chat_reply))



    # Add message handler for regular text messages
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Add error handler
    # application.add_error_handler(error_handler)

    # Start the bot
    print("Bot is starting...")
    application.run_polling(allowed_updates=["message", "callback_query", "my_chat_member"])


if __name__ == "__main__":
    main()