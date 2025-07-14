import discord
from discord import app_commands
from discord.ext import commands
import re

# List of course names
COURSE_CHOICES = ["C1 Inwards", "C1 Outwards", "New Belt (CCW)", "New Belt (CW)", "Shibuya/Shinjuku", "Ikebukuro/Yamate", "Wangan (East)", "Wangan (West)",
                  "Yokohane (Downwards)", "Yokohane (Upwards)", "Yaesu (Inwards)", "Yaesu (Outwards)", "Yokohama Minato Mirai (Inwards)",
                  "Yokohama Minato Mirai (Outwards)", "Nagoya", "Osaka Hanshin", "Kobe/Hanshin Expressway", "Hiroshima", "Fukuoka Expressway",
                  "Hakone Inwards", "Hakone Outwards", "Hakone Mt. Taikan (Upwards)", "Hakone Mt. Taikan (Downwards)", "Metro Highway Tokyo",
                  "Metro Highway Kanagawa"]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# { course_name: { user_id: (best_time_seconds, display_name) } }
leaderboards = {}

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
    time="Your time in MM:SS.xxx or SS.xxx format",
    course="The name of the course (map/track)"
)
@app_commands.choices(course=[app_commands.Choice(name=c, value=c) for c in COURSE_CHOICES])
async def submit_time(interaction: discord.Interaction, time: str, course: app_commands.Choice[str]):
    await interaction.response.defer()
    course = course.value
    total_seconds = parse_time_string(time)
    if total_seconds is None:
        await interaction.followup.send(
            "❌ Invalid time format. Use MM:SS.xxx or SS.xxx", ephemeral=True
        )
        return

    course = course.strip().title()
    user_id = interaction.user.id
    display_name = interaction.user.display_name

    if course not in leaderboards:
        leaderboards[course] = {}

    if user_id not in leaderboards[course] or total_seconds < leaderboards[course][user_id][0]:
        leaderboards[course][user_id] = (total_seconds, display_name)
        lines = [f"✅ Time submitted for **{course}**: **{time}**", f"🏁 **Leaderboard for {course}:**"]
        sorted_times = sorted(leaderboards[course].items(), key=lambda x: x[1][0])
        for rank, (user_id, (time_sec, name)) in enumerate(sorted_times, 1):
            minutes = int(time_sec) // 60
            seconds = time_sec % 60
            formatted = f"{minutes}:{seconds:06.3f}" if minutes else f"{seconds:.3f}"
            lines.append(f"{rank}. {name} – {formatted}")

        await interaction.followup.send("\n".join(lines))
    else:
        existing_time = leaderboards[course][user_id][0]
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
    if course not in leaderboards or not leaderboards[course]:
        await interaction.response.send_message(f"❌ No times submitted yet for **{course}**.")
        return

    sorted_times = sorted(leaderboards[course].items(), key=lambda x: x[1][0])
    lines = [f"🏁 **Leaderboard for {course}:**"]
    for rank, (user_id, (time_sec, name)) in enumerate(sorted_times, 1):
        minutes = int(time_sec) // 60
        seconds = time_sec % 60
        formatted = f"{minutes}:{seconds:06.3f}" if minutes else f"{seconds:.3f}"
        lines.append(f"{rank}. {name} – {formatted}")

    await interaction.response.send_message("\n".join(lines))

# Replace this with your real token (keep it secret!)
bot.run("MTM5NDIyNjM0NDg5MTY1MDA4MA.GC3gBO.__xhvXI5WsMYh9sOVUE43D4Z3odPr_3ffuD_vs")
