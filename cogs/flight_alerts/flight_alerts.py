import discord
from discord.ext import commands, tasks

from config import ALERT_CHANNEL_ID

from . import gmail_handler


class FlightAlerts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_flights.start()

    @tasks.loop(minutes=30)
    async def check_flights(self):
        print("Checking for flight alerts...")

        gmail, flights = gmail_handler.check_flights()

        if not flights:
            print("No new flights found")
            return

        channel = self.bot.get_channel(ALERT_CHANNEL_ID)
        if not channel:
            print(f"Could not find channel {ALERT_CHANNEL_ID}")
            return

        for flight_data in flights:
            flight = flight_data["flight"]
            if flight["savings"] != "N/A":
                savings_num = int(flight["savings"].rstrip('%'))
                if savings_num >= 40:
                    color = discord.Color.gold()  # Great deal
                elif savings_num >= 20:
                    color = discord.Color.green()  # Good deal
                else:
                    color = discord.Color.blue()  # Decent deal
            else:
                color = discord.Color.blue()

            embed = discord.Embed(
                title=f"{flight["airline"]}",
                description=f"### **{flight["routes"]}**\n{flight["dates"]}\n",
                color=color,
            )

            embed.add_field(name="Price:", value=f"{flight["price"]}", inline=True)

            if flight["savings"] != "N/A":
                embed.add_field(
                    name="Save:", value=f"{flight["savings"]}%", inline=True
                )

            if flight["savings"] == "N/A":
                embed.add_field(name="\u200b", value="\u200b", inline=True)

            embed.add_field(
                name="Book now",
                value=f"[View on Google Flights]({flight["link"]})",
                inline=False,
            )
            embed.timestamp = discord.utils.utcnow()

            await channel.send(embed=embed)

            print(flight_data["email_id"])
            gmail_handler.mark_as_read(gmail, flight_data["email_id"]["id"])

        print(f"Posted {len(flights)} flight alerts")

    @check_flights.before_loop
    async def before_check_flights(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(FlightAlerts(bot))
