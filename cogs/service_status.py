from discord.ext import commands, tasks
import aiohttp

class ServiceStatus(commands.Cog):
	"""Handles service status."""

	def __init__(self, bot):
		self.bot = bot

	async def check_status(self):
		try:
			async with aiohttp.ClientSession() as session:
				async with session.get("http://his.damnserver.com:8080/VisionTeam/") as resp:
					return resp.status == 200
		except Exception as e:
			return False

	async def send_service_message(self, message : str):
		for channel in self.bot.config.get_config('service_status_channels'):
			channel = self.bot.get_channel(channel)
			if not channel:
				continue

			await channel.send(message)

	@tasks.loop(seconds=300.0)
	async def status_checker(self):
		resp = await self.check_status()
		if resp and not self.bot.pool:
			await self.send_service_message(":boom:Current Service Status::boom: **Online**")
			
			await self.bot.get_mysql_pool()
		elif not resp and self.bot.pool:
			await self.send_service_message("Current Service Status: **Offline**")

			try:
				await self.bot.pool.close()
			except TypeError:
				pass

			self.bot.pool = False

	@commands.command()
	async def service(self, ctx):
		if not ctx.guild:
			return

		status = await self.check_status()
		if status:
			await ctx.channel.send(":boom:Current Service Status::boom: **Online**")
		else:
			await ctx.channel.send(":boom:Current Service Status::boom: **Offline**")

	@commands.Cog.listener()
	async def on_ready(self):
		if self.status_checker.is_running():
			return

		self.status_checker.start()
		print("[ServiceStatus] Loaded cog.")

async def setup(bot):
	await bot.add_cog(ServiceStatus(bot))