import discord
from discord import app_commands
from discord.ext import commands
import re
import mysql.connector

# List of course names
COURSE_CHOICES = ["C1 Inwards", "C1 Outwards", "New Belt (CCW)", "New Belt (CW)", "Shibuya/Shinjuku", "Ikebukuro/Yamate", "Wangan (East)", "Wangan (West)",
                  "Yokohane (Downwards)", "Yokohane (Upwards)", "Yaesu (Inwards)", "Yaesu (Outwards)", "Yokohama Minato Mirai (Inwards)",
                  "Yokohama Minato Mirai (Outwards)", "Nagoya", "Osaka Hanshin", "Kobe/Hanshin Expressway", "Hiroshima", "Fukuoka Expressway",
                  "Hakone Inwards", "Hakone Outwards", "Hakone Mt. Taikan (Upwards)", "Hakone Mt. Taikan (Downwards)", "Metro Highway Tokyo",
                  "Metro Highway Kanagawa"]

db = mysql.connector.connect(
    host="localhost",
    user="kurt",
    password="Kurteekurt123!",
    database="WMMT"
)
cursor = db.cursor()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Regex for times like 1:23.456 or 59.999 (milliseconds)
time_pattern = re.compile(r'^(?:(\d+):)?(\d{1,2})\.(\d{3})$')

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'✅ Logged in as {bot.user} and slash commands synced.')

def parse_time_string(time_str: str):
    match = time_pattern.match(time_str)
    if not match:
        return None
    minutes = int(match.group(1)) if match.group(1) else 0
    seconds = int(match.group(2))
    hundredths = int(match.group(3))
    return minutes * 60 + seconds + hundredths / 1000.0

@bot.tree.command(name="submit_time", description="Submit your best time for a course")
@app_commands.describe(
    user="The Discord user submitting the time",
    time="Your time in MM:SS.xxx or SS.xxx format",
    course="The name of the course (map/track)"
)
@app_commands.choices(course=[app_commands.Choice(name=c, value=c) for c in COURSE_CHOICES])
async def submit_time(interaction: discord.Interaction, user: discord.User, time: str, course: app_commands.Choice[str]):
    await interaction.response.defer()
    if not interaction.user.guild_permissions.administrator and not interaction.user.guild_permissions.manage_messages:
        await interaction.followup.send("❌ You don't have permission to use this command.", ephemeral=True)
        return
    course = course.value
    total_seconds = parse_time_string(time)
    if total_seconds is None:
        await interaction.followup.send(
            "❌ Invalid time format. Use MM:SS.xxx or SS.xxx", ephemeral=True
        )
        return

    course = course.strip().title()
    user_id = user.id
    display_name = user.display_name

    cursor.execute("""
        SELECT time_seconds FROM leaderboard
        WHERE discord_user_id = %s AND course_name = %s
    """, (user_id, course))
    result = cursor.fetchone()

    if result is None or total_seconds < result[0]:
        cursor.execute("""
            INSERT INTO leaderboard (discord_user_id, display_name, course_name, time_seconds)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE time_seconds = VALUES(time_seconds), display_name = VALUES(display_name)
        """, (user_id, display_name, course, total_seconds))
        db.commit()
        lines = [f"✅ {display_name} submitted **{time}** for **{course}**", f"🏁 **Leaderboard for {course}:**"]

        cursor.execute("""
            SELECT display_name, time_seconds FROM leaderboard
            WHERE course_name = %s
            ORDER BY time_seconds ASC
            LIMIT 10
        """, (course,))
        results = cursor.fetchall()

        for rank, (name, time_sec) in enumerate(results, 1):
            minutes = int(time_sec) // 60
            seconds = time_sec % 60
            formatted = f"{minutes}:{seconds:06.3f}" if minutes else f"{seconds:.3f}"
            lines.append(f"{rank}. {name} – {formatted}")

        await interaction.followup.send("\n".join(lines))
    else:
        existing_time = result[0]
        await interaction.followup.send(
            f"🕒 You already have a faster time for **{course}**: **{existing_time:.3f} seconds**",
            ephemeral=True
        )

@bot.tree.command(name="leaderboard", description="View the leaderboard for a course")
@app_commands.describe(course="The course name to view rankings for")
@app_commands.choices(course=[app_commands.Choice(name=c, value=c) for c in COURSE_CHOICES])
async def leaderboard(interaction: discord.Interaction, course: app_commands.Choice[str]):
    course = course.value
    course = course.strip().title()

    cursor.execute("""
        SELECT display_name, time_seconds FROM leaderboard
        WHERE course_name = %s
        ORDER BY time_seconds ASC
        LIMIT 10
    """, (course,))
    results = cursor.fetchall()

    if not results:
        await interaction.response.send_message(f"❌ No times submitted yet for **{course}**.")
        return

    lines = [f"🏁 **Leaderboard for {course}:**"]
    for rank, (name, time_sec) in enumerate(results, 1):
        minutes = int(time_sec) // 60
        seconds = time_sec % 60
        formatted = f"{minutes}:{seconds:06.3f}" if minutes else f"{seconds:.3f}"
        lines.append(f"{rank}. {name} – {formatted}")
    await interaction.response.send_message("\n".join(lines))

# Replace this with your real token (keep it secret!)
bot.run("YOUR_DISCORD_BOT_TOKEN")
