import sqlite3
import logging
import constants as consts

logger = logging.getLogger(__name__)

async def upsert_user_and_group(user, group):
    """Insert or update user, group, and group membership information in the database."""
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        cursor = conn.cursor()

        # Insert or update user
        cursor.execute(
            """
            INSERT INTO users (user_id, username, display_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user.id, user.username, user.first_name)
        )

        # Insert or update group
        cursor.execute(
            """
            INSERT INTO groups (group_id, group_name)
            VALUES (?, ?)
            ON CONFLICT(group_id) DO NOTHING
            """,
            (group.id, group.title)
        )

        # Insert or update group membership
        cursor.execute(
            """
            INSERT INTO group_members (group_id, user_id)
            VALUES (?, ?)
            ON CONFLICT(group_id, user_id) DO NOTHING
            """,
            (group.id, user.id)
        )

        conn.commit()

def get_display_name_from_telegram_user(user):
    """
    Generate display name from Telegram user object.

    Args:
        user: Telegram user object with username and first_name attributes

    Returns:
        str: Display name in format "@username" or first_name
    """
    return f"@{user.username}" if user.username else user.first_name

def format_names_list(names):
    """
    Format a list of names into a grammatically correct string.

    Args:
        names: List of name strings

    Returns:
        str: Formatted string like "Alice", "Alice and Bob", or "Alice, Bob, and Charlie"

    Examples:
        [] -> ""
        ["Alice"] -> "Alice"
        ["Alice", "Bob"] -> "Alice and Bob"
        ["Alice", "Bob", "Charlie"] -> "Alice, Bob, and Charlie"
    """
    if not names:
        return ""
    elif len(names) == 1:
        return names[0]
    elif len(names) == 2:
        return f"{names[0]} and {names[1]}"
    else:
        return ", ".join(names[:-1]) + f", and {names[-1]}"

def get_active_participanting_goals(group_id, user_id):

    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.id, g.goal
            FROM goals g
            JOIN goal_members gm ON g.id = gm.goal_id
            WHERE g.group_id = ? AND gm.user_id = ? AND g.status = 'active'
        """, (group_id, user_id))
        goals = cursor.fetchall()
        return goals
    
def get_active_non_participanting_goal_ids(group_id, user_id):

    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.id, g.goal 
            FROM goals g
            WHERE g.group_id = ? 
            AND g.status = 'active'
            AND g.id NOT IN (
                SELECT goal_id FROM goal_members WHERE user_id = ?
            )
        """, (group_id, user_id))
        available_goals = cursor.fetchall()

        return available_goals
    
def get_pending_challenges(group_id, user_id):

    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.goal_id, c.description, c.due_date, c.created_at, c.rejected, cr.id as challenge_response_id
            FROM challenges c
            JOIN challenge_responses cr ON c.id = cr.challenge_id
            JOIN goals g on c.goal_id = g.id
            WHERE cr.user_id = ? AND cr.status = 'pending' AND c.rejected = 0 AND g.group_id = ?
        """, (user_id, group_id))

        pending_challenges = cursor.fetchall()

        return pending_challenges
    
def get_completed_unvalidated_challenges():

    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cr.id as challenge_response_id, cr.challenge_id, cr.completed_at, c.description, c.goal_id, cr.user_id
            FROM challenge_responses cr
            JOIN challenges c ON cr.challenge_id = c.id
            WHERE cr.status = 'completed' AND cr.validated = 0
        """)

        completed_challenges = cursor.fetchall()

        return completed_challenges
    
def get_challenge_from_challenge_response_id(challenge_response_id):

    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cr.id as challenge_response_id, cr.challenge_id, cr.completed_at, c.description, c.goal_id, cr.user_id
            FROM challenge_responses cr
            JOIN challenges c ON cr.challenge_id = c.id
            WHERE cr.id = ?
        """, (challenge_response_id,))

        completed_challenges = cursor.fetchone()

        return completed_challenges

def get_members_in_goal(goal_id):

    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.user_id, 
                CASE 
                    WHEN u.username IS NOT NULL THEN '@' || u.username
                    ELSE u.display_name
                END AS name,
                g.group_id    
            FROM users u
            JOIN goal_members gm ON u.user_id = gm.user_id
            JOIN goals g ON gm.goal_id = g.id
            WHERE gm.goal_id = ?
        """, (goal_id,))

        members = cursor.fetchall()

        return members
    
def get_group_id_by_goal_id(goal_id):
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT group_id
            FROM goals
            WHERE id = ?
        """, (goal_id,))

        goal = cursor.fetchone()

        if goal:
            return goal["group_id"]
        else:
            return None

def get_group_id_by_prize_fight_id(prize_fight_id):
    """Get group_id from a prizefight ID."""
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT group_id
            FROM prizefights
            WHERE id = ?
        """, (prize_fight_id,))

        prizefight = cursor.fetchone()

        if prizefight:
            return prizefight["group_id"]
        else:
            return None

def get_user_display_name_by_challenge_response_id(challenge_response_id):
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
            JOIN challenge_responses cr ON u.user_id = cr.user_id
            WHERE cr.id = ?
        """, (challenge_response_id,))

        user = cursor.fetchone()

        if user:
            return user["name"]
        else:
            return None
        
async def mark_challenge_as_validated(challenge_response_id):
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE challenge_responses
            SET validated = 1, validated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (challenge_response_id,))
        conn.commit()

async def mark_challenge_as_rejected(challenge_response_id):
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE challenge_responses
            SET status = 'rejected', validated = 0, validated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (challenge_response_id,))
        conn.commit()

def goal_id_from_challenge_response_id_and_user_id(challenge_response_id, user_id):
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.goal_id
            FROM challenges c
            JOIN challenge_responses cr ON c.id = cr.challenge_id
            WHERE cr.id = ? AND cr.user_id = ?
        """, (challenge_response_id, user_id))

        result = cursor.fetchone()

    if result:
        return result["goal_id"]
    else:
        return None
        
def get_goal_id_from_challenge_id(challenge_id):
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.goal_id
            FROM challenges c
            WHERE c.id = ?
        """, (challenge_id,))

        result = cursor.fetchone()

    if result:
            return result["goal_id"]
    else:
        return None
        
def get_display_name_from_user_id(user_id):
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
            WHERE u.user_id = ?
        """, (user_id,))

        result = cursor.fetchone()

        if result:
            return result
        else:
            return None
        
def get_user_id_from_display_name(display_name):
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.user_id
            FROM users u
            WHERE (u.username = ? OR u.display_name = ?)
        """, (display_name.lstrip('@'), display_name))

        result = cursor.fetchone()

        if result:
            return result
        else:
            return None
        
def get_username_from_user_id(user_id):
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *
            FROM users u
            WHERE u.user_id = ?
        """, (user_id,))

        result = cursor.fetchone()

        if result:
            return result
        else:
            return None
        
def get_challenge_accepted_participants(challenge_id):
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cr.*,
                CASE 
                    WHEN u.username IS NOT NULL THEN '@' || u.username
                    ELSE u.display_name
                END AS name
            FROM challenge_responses cr
            JOIN users u ON cr.user_id = u.user_id
            WHERE cr.challenge_id = ? AND cr.status = 'issued'
        """, (challenge_id,))

        result = cursor.fetchall()

    return result

def get_goal_starting_date(goal_id):
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT created_at
            FROM goals 
            WHERE id = ?
        """, (goal_id,))

        result = cursor.fetchone()

    return result

def get_past_challenges(goal_id, limit = 7):
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *
            FROM challenges 
            WHERE goal_id = ? AND rejected = 0
            ORDER BY created_at DESC
            LIMIT ? 
        """, (goal_id, limit))

        result = cursor.fetchall()

    return result

def get_challenges_issued_yesterday():

    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *
            FROM challenges 
            WHERE DATE(created_at) >= DATE('now', '-1 day')
        """)

        result = cursor.fetchall()

    return result

def insert_into_prizefights(challenge, prize, group_id):

    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO prizefights (challenge, prize, group_id)
            VALUES (?, ?, ?)
        """, (challenge, prize, group_id))
        conn.commit()
    return cursor.lastrowid

def insert_into_prizefight_participants(prizefight_id, user_id):

    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO prizefight_participants (prizefight_id, user_id)
            VALUES (?, ?)
        """, (prizefight_id, user_id))
        conn.commit()

def get_prize_fight_for_user_id(user_id, group_id):
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
                """
                SELECT pf.id, pf.challenge, pf.prize
                FROM prizefights pf
                JOIN prizefight_participants pfp ON pf.id = pfp.prizefight_id
                WHERE pfp.user_id = ? AND pf.group_id = ? AND pfp.status = 'pending'
                """,
                (user_id, group_id)
            )
        return cursor.fetchall()

def edit_prize_fight_status(prize_fight_id, user_id, status):
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE prizefight_participants
            SET status = ?
            WHERE prizefight_id = ? AND user_id = ?
        """, (status, prize_fight_id, user_id))
        conn.commit()

def get_prize_fight_details(prize_fight_id):
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *
            FROM prizefights
            WHERE id = ?
        """, (prize_fight_id,))

        prize_fight = cursor.fetchone()

        return prize_fight
    
def get_prize_fight_participants(prize_fight_id, exclude_user_id=None):
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if exclude_user_id:
            cursor.execute("""
                SELECT u.user_id, u.username, u.display_name
                FROM prizefight_participants pfp
                JOIN users u ON pfp.user_id = u.user_id
                WHERE pfp.prizefight_id = ? AND pfp.user_id != ?
            """, (prize_fight_id, exclude_user_id))
        else:
            cursor.execute("""
                SELECT u.user_id, u.username, u.display_name
                FROM prizefight_participants pfp
                JOIN users u ON pfp.user_id = u.user_id
                WHERE pfp.prizefight_id = ?
            """, (prize_fight_id,))
        participants = cursor.fetchall()
        return participants
    
def get_expiring_challenges():
    """
    Get all challenges that are still pending with full challenge details
    """
    try:
        with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT cr.id, cr.challenge_id, cr.user_id, c.description, c.goal_id
                FROM challenge_responses cr
                JOIN challenges c ON cr.challenge_id = c.id
                WHERE cr.status = 'pending'
                """
            )
            return cursor.fetchall()

    except sqlite3.Error as e:
        logger.error(f"Database error in get_expiring_challenges: {e}")
        return []
    
def get_pending_prizefights():
    """
    Get all prize fights that are still pending with full details
    """
    try:
        with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT pfp.id, pfp.prizefight_id, pfp.user_id, pf.challenge, pf.prize, pf.group_id
                FROM prizefight_participants pfp
                JOIN prizefights pf ON pfp.prizefight_id = pf.id
                WHERE pfp.status = 'pending'
                """
            )
            return cursor.fetchall()

    except sqlite3.Error as e:
        logger.error(f"Database error in get_pending_prizefights: {e}")
        return []