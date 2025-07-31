import discord
from discord.ext import commands, tasks
import asyncio
import m3u8
import time
import aiohttp
import math

class OnDemandChannel:
	def __init__(self, stream_id):
		self.id = stream_id

	async def get_status(self, retry=0):
		if (retry == 2):
			#print(f'Status of channel ID {self.id}: False')
			return False

		#print(f'Getting status of channel ID {self.id}... RETRY: {retry}')

		try:
			load = m3u8.load(f'http://vision274.xyz:25461/live/test/cdgW26WarRjD9jsx/{self.id}.m3u8')
			#print(f'Status of channel ID {self.id}: {str(load.target_duration != None)}')
			return load.target_duration != None
		except Exception as e:
			await asyncio.sleep(5)
			return await self.get_status(retry + 1)

class OnDemand(commands.Cog):
	"""Handles on demand channels status."""

	def __init__(self, bot):
		self.bot = bot

		self.anti_spam = {}

	async def send_service_message(self, message : str):
		for channel in self.bot.config.get_config('service_status_channels'):
			channel = self.bot.get_channel(channel)
			if not channel:
				continue

			await channel.send(message)

	@commands.command()
	async def status(self, ctx, *, msg = ""):
		if not ctx.channel.id in self.bot.config.get_config('find_cmd_channels'):
			return

		if not self.bot.pool:
			await ctx.channel.send(f'{ctx.author.mention} The service is down. Please try again later.')
			return

		if ctx.author in self.anti_spam and ctx.author.id != self.bot.config.get_config('scoreboard_bot_id'):
			if time.time() - self.anti_spam[ctx.author] <= 5:
				time_left = math.ceil(5 - (time.time() - self.anti_spam[ctx.author]))
				await ctx.channel.send(f"{ctx.author.mention} Please wait **{time_left}** more seconds before using this command again.")
				return

		if msg == "":
			await ctx.channel.send(f"{ctx.author.mention} Command usage: **?status <on demand channel name>**")
			return

		msg_para = "%" + msg + "%"

		self.anti_spam[ctx.author] = time.time()

		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute("""
					SELECT 
						streams.id,
						streams.stream_display_name
					FROM
						streams,
						streams_servers
					WHERE
						streams.id = streams_servers.stream_id
						AND streams_servers.on_demand = 1
						AND streams.stream_display_name LIKE %s""", (msg_para, ))

				resp = await cur.fetchall()

				if len(resp) == 0:
					await ctx.channel.send(f"{ctx.author.mention} No on demand channel was found with the name '**{msg}**'.")
					return

				demand = OnDemandChannel(resp[0][0])

				status = await demand.get_status()

				if status:
					await ctx.channel.send(f"{ctx.author.mention} **{resp[0][1]}**'s status: **Up**")
				else:
					await ctx.channel.send(f"{ctx.author.mention} **{resp[0][1]}**'s status: **Down**")

	@commands.Cog.listener()
	async def on_ready(self):
		print("[OnDemand] Loaded cog.")

async def setup(bot):
	await bot.add_cog(OnDemand(bot))