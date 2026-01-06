import os
import ast
import json
import sqlite3
from groq import Groq
from datetime import datetime, timedelta
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply

import utils
import constants as consts
import prompt_template as ptemplates

def get_users_for_goal(goal_id):
    """
    Fetch users working on a specific goal.

    Args:
        goal_id (int): The ID of the goal.

    Returns:
        list: A list of users working on the goal.
    """

    user_list = []

    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.user_id, 
                CASE 
                    WHEN u.username IS NOT NULL THEN '@' || u.username
                    ELSE u.display_name
                END AS name
            FROM users u
            JOIN goal_members gm ON u.user_id = gm.user_id
            WHERE gm.goal_id = ?
        """, (goal_id,))
        
        users = cursor.fetchall() # list of sqlite3.Row objects, each representing a user, can be accessed like a dict

        return users 
    
def get_goals_to_challenge(db_path):
    """
    Fetch goals from the database that should be challenged based on their frequency
    and last_challenged timestamp.

    Args:
        db_path (str): Path to the SQLite database file.

    Returns:
        list: A list of goals that need to be challenged.
    """

    # Connect to the database
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, group_id, goal, status
            FROM goals
            WHERE status = 'active'
        """)
        rows = cursor.fetchall()

    return rows

def generate_challenge(goal):
    """
    Generate a challenge message for a given goal.

    Args:
        goal (str): The goal text.

    Returns:
        str: A challenge message.
    """

    # Initialize the Groq client
    client = Groq(api_key=os.getenv("GROQ_TOKEN"))

    # Create a chat completion request to generate the challenge
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",  
        messages=[
            {"role": "system", "content": ptemplates.CHALLENGE_PROMPT_TEMPLATE},
            {"role": "user", "content": f"Generate a challenge for: {goal}"}
        ],
        max_tokens = 100,
        response_format = {'type': 'json_object'}
    )

    # Extract the generated challenge from the response
    generated_challenge = json.loads(response.choices[0].message.content)

    return generated_challenge

async def schedule_challenges(context: ContextTypes.DEFAULT_TYPE):
    """
    Schedule challenges for goals based on their frequency and last challenged timestamp.
    This function fetches goals that need to be challenged and generates challenges for them.
    """

    # Fetch goals that need to be challenged
    goals_to_challenge = get_goals_to_challenge(consts.GOALS_DB_SQLITE)

    for goal in goals_to_challenge:

        # Generate a challenge for the goal
        challenge_message = generate_challenge(goal["goal"]).get("challenge")

        # Get users working on this goal
        users = get_users_for_goal(goal["id"])

        # Store the challenge in the database        
        with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO challenges (goal_id, description, due_date) VALUES (?, ?, ?)", (goal['id'], challenge_message, (datetime.now() + timedelta(days=1)).isoformat())
            )

            challenge_id = cursor.lastrowid

            for i in users:
                cursor.execute(
                    "INSERT INTO challenge_responses (challenge_id, user_id, status) VALUES (?, ?, ?)", 
                    (challenge_id, i['user_id'], 'issued')
                )

            conn.commit()

        # Format user list to string for message
        if len(users) == 0:
            username_string = ""
        elif len(users) == 1:
            username_string = users[0]['name']
        elif len(users) == 2:
            username_string = f"{users[0]['name']} and {users[1]['name']}"
        else:
            username_string = ", ".join(users[:-1]['name']) + f", and {users[-1]['name']}"
        
        # Create message
        message = f"{username_string}\n\n<b>🎯 Challenge for tomorrow:</b>\n <tg-spoiler>{challenge_message}</tg-spoiler>\n\nAll the best and stay locked in!"

        # Create inline keyboard for accepting or suggesting a challenge
        keyboard = [
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"acpt_chlng_{challenge_id}_{[u['name'] for u in users]}"),
                InlineKeyboardButton("💡 Suggest my own", callback_data=f"suggest_challenge_{goal['id']}_{challenge_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send messsage to the group
        await context.bot.send_message(
                chat_id = goal["group_id"],
                text = message,
                reply_markup=reply_markup,
                parse_mode = 'HTML'
            )

async def accept_challenge(update, context):
    """
    Updatees the challenge response status to 'accepted from 'issued' when a user accepts a challenge.
    """

    try:
        query = update.callback_query
        user = query.from_user
        user_id = user.id
        display_name = utils.get_display_name_from_user_id(user_id)
        

        # Extract challenge ID from callback data
        challenge_id = query.data.split("_")[-2]
        users = query.data.split("_")[-1]
        users = ast.literal_eval(users)
        if display_name['name'] in users:
            users.remove(display_name['name'])

        # Format user list to string for message
        if len(users) == 0:
            username_string = ""
        elif len(users) == 1:
            username_string = users[0]['name']
        elif len(users) == 2:
            username_string = f"{users[0]['name']} and {users[1]['name']}"
        else:
            username_string = ", ".join(u['name'] for u in users[:-1]) + f", and {users[-1]['name']}"

        # Add challenge response to the database
        with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Check current status first
            cursor.execute(
                "SELECT status FROM challenge_responses WHERE challenge_id = ? AND user_id = ?",
                (challenge_id, user_id)
            )
            row = cursor.fetchone()
            
            if not row:
                await query.answer("You're not part of this challenge! Use /goals to join this goal and be part of the challenge", show_alert=True)
                return
            
            if row["status"] == "pending":
                await query.answer("Love the enthusiasm, but you've already accepted this challenge!", show_alert=True)
                return

            cursor.execute(
                "UPDATE challenge_responses SET status = ? WHERE challenge_id = ? AND user_id = ?", 
                ('pending', challenge_id, user_id)
            )
            conn.commit()

        

        await query.answer("✅ Challenge accepted!")
        await query.message.reply_text(f"{username_string}\n\n{display_name['name']} has accepted the challenge, don't be left behind!")

    except Exception as e:
        print(f"Error accepting challenge: {e}")
        await query.answer("❌ There was an error accepting the challenge. Please try again later.")

async def handle_suggest_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    goal_id = query.data.split("_")[-2]
    challenge_id = query.data.split("_")[-1]
    
    await query.answer()
    
    sent_message = await query.message.reply_text(
        "What challenge would you like to suggest? Reply to this message with your challenge idea.",
        reply_markup=ForceReply(selective=True)
    )
    
    # Only store goal_id, keyed by message_id
    if "suggestion_prompts" not in context.chat_data:
        context.chat_data["suggestion_prompts"] = {}
    
    context.chat_data["suggestion_prompts"][sent_message.message_id] = (goal_id, challenge_id)

async def handle_suggestion_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    # Check if this message is a reply to another message
    # If user just sent a normal message (not a reply), ignore it
    if not update.message.reply_to_message:
        return
    
    # Get the ID of the message the user replied to
    reply_to_id = update.message.reply_to_message.message_id
    
    # Get our stored prompts (or empty dict if none exist)
    # This contains {message_id: goal_id} pairs
    prompts = context.chat_data.get("suggestion_prompts", {})
    
    # Check if the message they replied to is one of our prompts
    # If they replied to some random message, ignore it
    if reply_to_id not in prompts:
        return
    
    # We found a match! Get the goal_id we stored earlier
    goal_id, old_challenge_id = prompts[reply_to_id]
    
    # Get the user's suggestion text
    suggestion = update.message.text
    
    # Clean up - remove this prompt since it's been used
    del context.chat_data["suggestion_prompts"][reply_to_id]

    users = get_users_for_goal(goal_id)

    # Store the challenge in the database        
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO challenges (goal_id, description, due_date) VALUES (?, ?, ?)", (goal_id, suggestion, (datetime.now() + timedelta(days=1)).isoformat())
        )

        cursor.execute(
            "UPDATE challenges SET rejected = 1 WHERE challenge_id = ?",
            (old_challenge_id,)
        )

        cursor.execute(
            "UPDATE challenge_responses SET status = 'rejected' WHERE challenge_id = ?",
            (old_challenge_id,)
        )

        challenge_id = cursor.lastrowid

        for i in users:
            cursor.execute(
                "INSERT INTO challenge_responses (challenge_id, user_id, status) VALUES (?, ?, ?)", 
                (challenge_id, i['user_id'], 'issued')
            )

            if cursor.rowcount == 0:
                # No matching row found
                print(f"{i} not in challenge {challenge_id}")

        conn.commit()

    # Confirm to the user
    keyboard = [
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"accept_challenge_{challenge_id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    display_name = f"@{update.effective_user.username}" or update.effective_user.first_name

    await update.message.reply_text(
        f"🎯 <b>New Challenge Suggested by {display_name}:</b>\n<tg-spoiler>{suggestion}</tg-spoiler>\n\n<u><i>They don't think you can do it. Show them.</i></u>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )




# def get_challenges_to_poll(db_path):
#     """
#     Fetch open challenges that need to be polled for results.

#     Args:
#         db_path (str): Path to the SQLite database file.

#     Returns:
#         list: A list of open challenges to poll.
#     """

#     conn = sqlite3.connect(db_path)
#     cursor = conn.cursor()

#     # Query open challenges that are pending and past their due date
#     cursor.execute("""
#         SELECT *
#         FROM open_challenges_issued
#         WHERE status = 'pending' AND due_at <= ? AND polled_at IS NULL
#     """, (datetime.now().isoformat(),))

#     challenges_to_poll = []
#     for row in cursor.fetchall():
#         challenges_to_poll.append({
#             "id": row[0],
#             "goal_id": row[1],
#             "group_id": row[2],
#             "challenge_text": row[3],
#             "issued_at": row[4],
#             "due_at": row[5]
#         })

#     conn.close()
#     return challenges_to_poll

# async def challenge_result_poll(db_path, context: ContextTypes.DEFAULT_TYPE):

#     challenges_to_poll = get_challenges_to_poll(db_path)

#     for challenge in challenges_to_poll:
        
#         # Here you would send the challenge_message to the appropriate group/user
#         await context.bot.send_message(
#             chat_id = challenge["group_id"],
#             text = f"⏳ Time to check in! Did you complete the challenge: {challenge['challenge_text']}? Please reply with 'yes' or 'no'."
#             )