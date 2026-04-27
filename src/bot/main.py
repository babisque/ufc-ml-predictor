import asyncio
import datetime
import discord
from discord.ext import commands, tasks

from src.core.config import settings
from src.core.logger import get_logger

from src.db import (
    save_prediction, 
    get_statistics, 
    get_event_predictions, 
    get_last_event_predictions
)

from src.ml.predict import predict_winner, get_fighter_profile

from src.scraper.events import get_event_fights, get_next_event
from scripts.auditor import audit_predictions
import pandas as pd

logger = get_logger(__name__)

TOKEN = settings.DISCORD_TOKEN
AUDIT_TIME = datetime.time(hour=15, minute=0)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info(f'Bot is ready. Logged in as {bot.user}')
    logger.info('Type !help for a list of commands.')

    if not weekly_audit.is_running():
        weekly_audit.start()
        logger.info("✅ Weekly audit task started.")

@bot.command(name='predict', help='Predict the outcome of a fight. Usage: !predict <Fighter 1> , <Fighter 2> , <Weight Class>')
async def predict_fight(ctx, *, args: str):
    """
    Example usage: !predict Conor McGregor , Dustin Poirier , Lightweight
    """
    try:
        parts = [part.strip() for part in args.split(',')]
        if len(parts) != 3:
            await ctx.send("Invalid format. Please use: !predict <Fighter 1> , <Fighter 2> , <Weight Class>")
            return
        
        fighter_1, fighter_2, weight_class = parts
        message_status = await ctx.send(f"Preparing prediction for: {fighter_1} vs {fighter_2} in {weight_class} category...")

        result = predict_winner(fighter_1, fighter_2, weight_class)

        if result:
            winner = result['winner']
            prop = result['confidence'] / 100.0

            save_prediction("Individual fight", fighter_1, fighter_2, weight_class, winner, prop)

            embed = discord.Embed(
                title=f"🥊 Fight Prediction: {fighter_1} vs {fighter_2} 🥊",
                description=f"**Weight Class:** {weight_class}",
                color=discord.Color.red()
            )
            embed.add_field(name="Predicted Winner", value=f"🏆 **{winner}**", inline=False)
            embed.add_field(name="AI Confidence", value=f"🤖 {prop:.2%}", inline=False)
            embed.set_footer(text="This prediction is based on historical data and machine learning. Not a guarantee of the actual fight outcome!")    

            await message_status.edit(content=None, embed=embed)
        else:
            await message_status.edit(content="Could not calculate prediction. Check if fighters exist in database.")

    except Exception as e:
        logger.error(f"Error in predict_fight: {e}")
        await ctx.send(f"An error occurred while processing the prediction: {e}")

async def _send_event_embeds(ctx, status_message, event_name, event_date, fields, from_cache=False):
    """Sends fight prediction fields across multiple embeds (max 25 fields each)."""
    FOOTER = "Predictions are based on historical data and machine learning. Not a guarantee of actual fight outcomes!"
    CHUNK_SIZE = 25
    chunks = [fields[i:i + CHUNK_SIZE] for i in range(0, len(fields), CHUNK_SIZE)]

    for idx, chunk in enumerate(chunks):
        cache_note = " (loaded from cache)" if from_cache else ""
        description = (
            f"📅 Date: {event_date}\n{len(fields)} fights analyzed{cache_note}."
            if idx == 0
            else f"_(continued — part {idx + 1} of {len(chunks)})_"
        )
        embed = discord.Embed(
            title=f"🔮 Predicted Next UFC Event: {event_name} 🔮",
            description=description,
            color=discord.Color.gold()
        )
        for name, value in chunk:
            embed.add_field(name=name, value=value, inline=False)
        if idx == len(chunks) - 1:
            embed.set_footer(text=FOOTER)

        if idx == 0:
            await status_message.edit(content=None, embed=embed)
        else:
            await ctx.send(embed=embed)

@bot.command(name='nextEvent', help='Predict the outcome of a fight. Usage: !nextEvent')
async def next_event(ctx):
    status_message = await ctx.send("Fetching the next UFC event...")

    event_info = get_next_event()

    if not event_info:
        await status_message.edit(content="No future events found.")
        return

    event_name = event_info['name']
    event_link = event_info['link']
    event_date = event_info['date']

    cached_predictions = get_event_predictions(event_name)

    if cached_predictions:
        await status_message.edit(content="Predictions found in database. Loading...")
        fields = [
            (
                f"{fighter_1} vs {fighter_2} ({weight_class})",
                f"Predicted Winner: **{winner}** with AI Confidence of {confiability:.2%}"
            )
            for fighter_1, fighter_2, weight_class, winner, confiability in cached_predictions
        ]
        await _send_event_embeds(ctx, status_message, event_name, event_date, fields, from_cache=True)
        return

    await status_message.edit(content="Fight event found. Fetching details...")

    fights = get_event_fights(event_link)

    if not fights:
        await status_message.edit(content=f"No fight details found for {event_name}.")
        return

    fields = []
    for fighter_1, fighter_2, weight_class in fights:
        
        result = predict_winner(fighter_1, fighter_2, weight_class)

        if result:
            winner = result['winner']
            confiability = result['confidence'] / 100.0

            save_prediction(event_name, fighter_1, fighter_2, weight_class, winner, confiability)

            fields.append((
                f"{fighter_1} vs {fighter_2} ({weight_class})",
                f"Predicted Winner: **{winner}** with AI Confidence of {confiability:.2%}"
            ))
        else:
            fields.append((
                f"{fighter_1} vs {fighter_2} ({weight_class})",
                "Could not retrieve profiles for one or both fighters. Skipping prediction."
            ))

    await _send_event_embeds(ctx, status_message, event_name, event_date, fields)

@bot.command(name='stats', help='Show the official accuracy rate of the Oracle in the real world.')
async def show_stats(ctx):
    try:
        total_resolvidas, total_acertos, total_pendentes = get_statistics()

        if total_resolvidas == 0:
            await ctx.send("📊 I don't have enough **audited** fights yet to calculate my accuracy rate.\n(I made the predictions, but I'm waiting for next Sunday at 15:00 to confirm the official results!)")
            return

        accuracy = (total_acertos / total_resolvidas) * 100
        erros = total_resolvidas - total_acertos

        embed = discord.Embed(
            title="📊 Official Statistics of the UFC-AI Oracle",
            description="My prediction history in the real world validated by the database:",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Audited Fights", value=f"**{total_resolvidas}**", inline=True)
        embed.add_field(name="Correct Predictions", value=f"✅ **{total_acertos}**", inline=True)
        embed.add_field(name="Errors", value=f"❌ **{erros}**", inline=True)
        
        embed.add_field(name="🎯 Accuracy Rate", value=f"## {accuracy:.2f}%", inline=False)
        
        embed.add_field(name="⏳ Pending", value=f"I have **{total_pendentes}** predictions made waiting for the fight to happen.", inline=False)

        embed.set_footer(text="The results auditor runs automatically every Sunday at 15:00.")

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Error querying database for stats: {e}")
        await ctx.send(f"❌ Error querying the database: {str(e)}")

@bot.command(name='lastEvent', help='Show the predictions for the last UFC event that took place.')
async def last_event(ctx):
    try:
        event, total, correct, fights = get_last_event_predictions()

        if not event:
            await ctx.send("No predictions found for the last event.")
            return
        
        accuracy = (correct / total) * 100 if total > 0 else 0
        errors = total - correct

        color = discord.Color.green() if accuracy >= 50 else discord.Color.red()
        embed = discord.Embed(
            title=f"📊 Predictions for the Last UFC Event: {event}",
            description=f"**{event}**\nThe model achieved **{accuracy:.1f}%** accuracy.",
            color=color
        )

        embed.add_field(name="Hits", value=f"✅ **{correct}**", inline=True)
        embed.add_field(name="Errors", value=f"❌ **{errors}**", inline=True)

        fight_text = ""
        for f1, f2, predicted, real, correct, confidence in fights:
            icon = "✅" if correct == 1 else "❌"
            if correct is None:
                icon = "⏳"
                real = "Pending"

            details = f"{icon} **{f1}** vs **{f2}**\nPredicted: **{predicted}** ({confidence:.1%}) | Real: **{real}**\n\n"
            fight_text += details

        if fight_text:
            embed.add_field(name="Fight details", value=fight_text[:1024], inline=False)

        await ctx.send(embed=embed)
    
    except Exception as e:
        logger.error(f"Error querying database for lastEvent: {e}")
        await ctx.send(f"❌ Error querying the database: {str(e)}")

@bot.command(name='profile', help='Show the profile of a fighter. Usage: !profile <Fighter Name>')
async def fighter_profile(ctx, *, fighter_name: str):
    """
    Shows the profile of a specific fighter.
    """
    try:
        historical_df = pd.read_csv('data/processed/balanced_fights.csv')
        fighter_name = fighter_name.title()
        profile = get_fighter_profile(fighter_name, historical_df)

        if not profile:
            await ctx.send(f"Could not find a profile for **{fighter_name}**. Please check the name and try again.")
            return
        
        embed = discord.Embed(
            title=f"🥋 Fighter Profile: {profile['name']}",
            description="Statistics based on historical data.",
            color=discord.Color.dark_blue()
        )

        embed.add_field(name="Age", value=f"{int(profile['age'])} anos", inline=True)
        embed.add_field(name="Height", value=f"{profile['height']} cm", inline=True)
        embed.add_field(name="Reach", value=f"{profile['reach']} cm", inline=True)
        embed.add_field(name="Win Streak", value=f"{int(profile['f1_win_streak'])}", inline=True)
        embed.add_field(name="Strike Advantage", value=f"{profile.get('f1_strike_diff', 0):.2f}", inline=True)
        
        embed.set_footer(text="UFC-AI Data Analytics • Data evolves with every fight")
        
        await ctx.send(embed=embed)
    except Exception as e:
         await ctx.send(f"Error loading profile: {e}")

@tasks.loop(time=AUDIT_TIME)
async def weekly_audit():
    if datetime.datetime.today().weekday() == 6:
        logger.info("🕒 It's Sunday at 15:00! Starting weekly audit...")
        await asyncio.to_thread(audit_predictions)
        logger.info("✅ Audit completed on Sunday at 15:00!")

if __name__ == "__main__":
    if not TOKEN:
        logger.error("No DISCORD_TOKEN found. Cannot start the bot.")
        raise ValueError("No DISCORD_TOKEN found in environment variables.")
    bot.run(TOKEN)