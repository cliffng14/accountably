import sqlite3
import constants as consts

# Connect (creates the file if it doesn't exist)
conn = sqlite3.connect(consts.GOALS_DB_SQLITE)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        display_name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        group_id INTEGER PRIMARY KEY,
        group_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS group_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        FOREIGN KEY (group_id) REFERENCES groups(group_id),
        UNIQUE(group_id, user_id)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    goal TEXT NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS goal_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT DEFAULT 'member' CHECK (role IN ('owner', 'member')),
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE,
        UNIQUE (goal_id, user_id)
    );
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_id INTEGER NOT NULL,
        description TEXT,
        due_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        rejected BOOLEAN DEFAULT 0,
        FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
    );
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS challenge_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challenge_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending' CHECK (status IN ('issued', 'pending', 'rejected', 'completed', 'failed')),
        validated BOOLEAN DEFAULT 0,
        completed_at TIMESTAMP,
        validated_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (challenge_id) REFERENCES challenges(id) ON DELETE CASCADE,
        UNIQUE (challenge_id, user_id)
    );
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS prizefights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        challenge TEXT NOT NULL,
        prize TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS prizefight_participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prizefight_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'verifying', 'completed', 'failed')),
        FOREIGN KEY (prizefight_id) REFERENCES prizefights(id) ON DELETE CASCADE,
        UNIQUE (prizefight_id, user_id)
    );
""")

# Look at current table
print('Users table contents:')
cursor.execute("SELECT * FROM users")
rows = cursor.fetchall()
for row in rows:
    print(row)

print('Groups table contents:')
cursor.execute("SELECT * FROM groups")
rows = cursor.fetchall()
for row in rows:
    print(row)

print('Group Members table contents:')
cursor.execute("SELECT * FROM group_members")
rows = cursor.fetchall()
for row in rows:
    print(row)

print('Goals table contents:')
cursor.execute("SELECT * FROM goals")
rows = cursor.fetchall()
for row in rows:
    print(row)

print('Goal Members table contents:')
cursor.execute("SELECT * FROM goal_members")
rows = cursor.fetchall()
for row in rows:
    print(row)

print('Challenges table contents:')
cursor.execute("SELECT * FROM challenges")
rows = cursor.fetchall()
for row in rows:
    print(row)

print('Challenge Response table contents:')
cursor.execute("SELECT * FROM challenge_responses")
rows = cursor.fetchall()
for row in rows:
    print(row)

print('Prizefights table contents:')
cursor.execute("SELECT * FROM prizefights")
rows = cursor.fetchall()
for row in rows:
    print(row)

conn.commit()
conn.close()