import sqlite3
import constants as consts

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
            return user["display_name"]
        else:
            return None
        
def mark_challenge_as_validated(challenge_response_id):
    with sqlite3.connect(consts.GOALS_DB_SQLITE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE challenge_responses
            SET validated = 1, validated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (challenge_response_id,))
        conn.commit()

def mark_challenge_as_rejected(challenge_response_id):
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
    

