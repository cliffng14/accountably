DEV_MODE = False

GOALS_DB_SQLITE = "./goals.db"

INTRODUCTION_TEXT = """
Hello everyone! 👋

I'm an accountability bot that generates daily challenges based on your goals. Research shows you're more likely to achieve your goals with an accountability partner — so don't go it alone!

<b>Goals vs Challenges:</b>
- <b>Goal</b> — Your long-term objective (e.g. "Get fit", "Learn Spanish")
- <b>Challenge</b> — A small daily task I generate to help you progress toward your goal

<b>How it works:</b>

1️⃣ Add a goal with /addgoal (e.g. <code>/addgoal Get fit</code>)
2️⃣ Invite your friends to join the goal
3️⃣ Every day at 10:45pm SGT, I'll generate a challenge for each goal
4️⃣ Accept and complete your challenge at your own pace
5️⃣ Mark it done with /complete before 10:30pm SGT
6️⃣ A fellow participant will verify your completion

<b>Commands:</b>
- /addgoal — Add a new goal
- /goals — View all goals in this group
- /complete — Mark your challenge as done
- /deletegoal — Remove a goal
- /feedback — Send feedback to the developer
- /help — Show this message again

<b>📌 Quick access tips:</b>
- <b>Pin this group</b> — Long press the group → Pin to keep it at the top
- <b>Add widget (iOS)</b> — Long press Telegram icon → Widgets → Add "Chats" widget
- <b>Add widget (Android)</b> — Long press home screen → Widgets → Telegram → Chats

<b>🔒 Privacy:</b>
I only read messages that start with a command (/) or when you interact with my buttons. I cannot see your regular group conversations.

Let's crush some goals together! 💪
"""