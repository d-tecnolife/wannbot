from .flight_alerts import FlightAlerts


async def setup(bot):
    await bot.add_cog(FlightAlerts(bot))
