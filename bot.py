import discord
import os
import datetime
import asyncio

from discord.ext import commands
from dotenv import load_dotenv
from database import save_prediction, get_statistics
from discord.ext import tasks
from predict import get_fighter_profile, prepare_data_prevision, historical_df, model
from src.scraper.events import get_event_fights, get_next_event
from src.scraper.events import get_next_event
from auditor import audit_predictions

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
AUDIT_TIME = datetime.time(hour=15, minute=0)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')
    print('Type !help for a list of commands.')

    if not weekly_audit.is_running():
        weekly_audit.start()
        print("✅ Weekly audit task started.")

@bot.command(name='predict', help='Predict the outcome of a fight. Usage: !predict <Fighter 1> vs <Fighter 2> in <Weight Class>')
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

        f1 = get_fighter_profile(fighter_1, historical_df)
        f2 = get_fighter_profile(fighter_2, historical_df)

        if not f1 or not f2:
            await message_status.edit(content="Could not find profiles for one or both fighters. Please check the names and try again.")
            return
        
        X_new = prepare_data_prevision(f1, f2, weight_class)

        if X_new is not None:
            prediction = model.predict(X_new)
            probability = model.predict_proba(X_new)

            winner = fighter_1 if prediction[0] == 1 else fighter_2
            prop = float(probability[0][1] if prediction[0] == 1 else probability[0][0])

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
            await message_status.edit(content="Error preparing data for the model. Please try again later.")

    except Exception as e:
        await ctx.send(f"An error occurred while processing the prediction: {e}")

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

    await status_message.edit(content=f"Fight event found. Fetching details...")

    fights = get_event_fights(event_link)

    if not fights:
        await status_message.edit(content=f"No fight details found for {event_name}.")
        return
    
    embed = discord.Embed(
        title=f"🔮 Predicted Next UFC Event: {event_name} 🔮",
        description=f"📅 Date: {event_date}\nThe model analyzed {len(fights)} fights.",
        color=discord.Color.gold()
    )

    for fighter_1, fighter_2, weight_class in fights:
        f1 = get_fighter_profile(fighter_1, historical_df)
        f2 = get_fighter_profile(fighter_2, historical_df)

        if not f1 or not f2:
            embed.add_field(
                name=f"{fighter_1} vs {fighter_2} ({weight_class})",
                value="Could not retrieve profiles for one or both fighters. Skipping prediction.",
                inline=False
            )
            continue

        X_new = prepare_data_prevision(f1, f2, weight_class)

        if X_new is not None:
            prediction = model.predict(X_new)
            probability = model.predict_proba(X_new)

            winner = fighter_1 if prediction[0] == 1 else fighter_2
            confiability = probability[0][1] if prediction[0] == 1 else probability[0][0]

            save_prediction(event_name, fighter_1, fighter_2, weight_class, winner, confiability)

            embed.add_field(
                name=f"{fighter_1} vs {fighter_2} ({weight_class})",
                value=f"Predicted Winner: **{winner}** with AI Confidence of {confiability:.2%}",
                inline=False
            )

    embed.set_footer(text="Predictions are based on historical data and machine learning. Not a guarantee of actual fight outcomes!")
    await status_message.edit(content=None, embed=embed)

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
        await ctx.send(f"❌ Error querying the database: {str(e)}")

@tasks.loop(time=AUDIT_TIME)
async def weekly_audit():
    if datetime.datetime.today().weekday() == 6:
        print("🕒 It's Sunday at 15:00! Starting weekly audit...")
        await asyncio.to_thread(audit_predictions)
        print("✅ Audit completed on Sunday at 15:00!")
        
bot.run(TOKEN)