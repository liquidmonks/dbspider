from discord.ext import commands, tasks
import aiohttp
import discord
import pymysql
import time
import math
import datetime
import pytz
import json
from pprint import pprint

def get_formatted_date_from_epoch_est(epoch):
	new_datetime = datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc)
	timezone = pytz.timezone('America/New_York')
	given_date = new_datetime.astimezone(timezone)
	current_date = datetime.datetime.now(timezone)

	if given_date.day == current_date.day:
		return "Today at " + given_date.strftime('%I:%M %p **%Z**')
	elif given_date.day == (current_date.day + 1):
		return "Tomorrow at " + given_date.strftime('%I:%M %p **%Z**')
	return given_date.strftime('%m-%d-%y %I:%M %p **%Z**')

class ContentServices(commands.Cog):
	"""Handles content service status."""

	def __init__(self, bot):
		self.bot = bot

		self.event_cache = {}
		self.down_cache = []
		self.last_down_messages = []

		self.find_anti_spam = {}

		self.bouquet_channels = []

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

	def add_message(self, data, addition):
		current_index = len(data) - 1
		if len(data[current_index]) + len(addition) > 2000:
			data.append(addition)
		else:
			data[current_index] = data[current_index] + addition

	@tasks.loop(seconds=300.0)
	async def stream_down_checker(self):
		if not self.bot.pool:
			return False

		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor() as cur:
					await cur.execute("SELECT streams.stream_display_name FROM streams, streams_servers WHERE streams.id=streams_servers.stream_id AND streams_servers.stream_status=1")
					resp = await cur.fetchall()

				down_channels = []
				output = False

				for data in resp:
					if not data[0] in self.down_cache:
						output = True

					down_channels.append(data[0])

				self.down_cache = down_channels[:]

				if output and len(down_channels) > 0:
					stream_down_msg = ["**:boom:The following channels are currently offline for maintenance::boom:**\n\n"]
					for data in down_channels:
						self.add_message(stream_down_msg, f"**{data}**\n")

					for old_message in self.last_down_messages:
						try:
							await old_message.delete()
						except discord.errors.NotFound:
							pass

					self.last_down_messages.clear()
					storage_msgs  = {}

					for message in stream_down_msg:
						for channel in self.bot.config.get_config("down_stream_channels"):
							channel = self.bot.get_channel(channel)
							if not channel:
								continue

							msg = await channel.send(message)
							self.last_down_messages.append(msg)
							storage_msgs[msg.channel.id] = msg.id

					self.bot.saveConfig.set_setting("last_down_messages", storage_msgs)
		except pymysql.err.InternalError:
			await self.get_mysql_pool()
		except pymysql.err.OperationalError:
			await self.get_mysql_pool()

	@tasks.loop(seconds=120.0)
	async def event_checker(self):
		if not self.bot.pool:
			return False

		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor() as cur:
					#await cur.execute("SELECT id, stream_display_name FROM streams WHERE id IN (507, 509, 510, 511, 512, 513, 514, 515, 516, 1391, 2875, 4952)")
					await cur.execute("SELECT id, stream_display_name FROM streams WHERE stream_display_name LIKE 'EVENT%'")
					current_data = await cur.fetchall()

			changed_current_data = False
			upcoming_events = [f"@here :boom:LIVE & UPCOMING PPV/EVENTS::boom: "]

			for data in current_data:
				if data[0] >= 7893 and data[0] <= 7923:
					continue
				if not str(data[0]) in self.event_cache or self.event_cache[str(data[0])] != data[1]:
					newEvent = data[1].split(":", 1)[1].strip()
					self.event_cache[str(data[0])] = data[1]
					changed_current_data = True
					if newEvent != "":
						self.add_message(upcoming_events, f"{data[1]}\n")

			if changed_current_data:
				for channel in self.bot.config.get_config("event_update_channels"):
					channel = self.bot.get_channel(channel)
					if not channel:
						continue

					for message in upcoming_events:
						await channel.send(message)

				check_trigger_channel = self.bot.get_channel(self.bot.config.get_config("check_events_trigger_id"))
				if check_trigger_channel:
					await check_trigger_channel.send("?checkevents")

			self.bot.saveConfig.set_setting("event_cache", self.event_cache)
		except pymysql.err.InternalError:
			await self.get_mysql_pool()
		except pymysql.err.OperationalError:
			await self.get_mysql_pool()

	@commands.command()
	async def find(self, ctx, *args):
		if not ctx.channel.id in self.bot.config.get_config("find_cmd_channels"):
			return

		if not self.bot.pool:
			await ctx.channel.send(f"{ctx.author.mention} The service is down. Please try again later.")
			return

		if ctx.author in self.find_anti_spam:
			if time.time() - self.find_anti_spam[ctx.author] <= 5:
				time_left = math.ceil(5 - (time.time() - self.find_anti_spam[ctx.author]))
				await ctx.channel.send(f"{ctx.author.mention} Please wait **{time_left}** more seconds before using this command again.")
				return

		msg = " ".join(str(x) for x in args).lower()
		msg_para = "%" + msg + "%"
		if msg == "":
			await ctx.channel.send(f"{ctx.author.mention} Command usage: **?find <stream title>**")
			return

		self.find_anti_spam[ctx.author] = time.time()

		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute("""
					SELECT 
						start as start_date, 
						`end`, 
						streams.stream_display_name,
						title,
						epg_data.channel_id,
						streams.id
					FROM
						streams,
						epg_data
					WHERE
						streams.epg_id = epg_data.epg_id
						AND streams.channel_id = epg_data.channel_id
						AND LOWER(title) LIKE %s
					ORDER BY
						start_date ASC""", (msg_para, ))
				resp = await cur.fetchall()
				
				print(f"RESP: {len(resp)}")

				await cur.execute("""
					SELECT 
						streams.stream_display_name
					FROM 
						streams 
					WHERE 
						stream_display_name LIKE %s 
					AND 
						stream_display_name LIKE %s""", (msg_para, "EVENT%"))

				events_resp = await cur.fetchall()

				current_streams = []
				future_streams = []
				past_streams = []

				for data in resp:
					if data[5] in self.bouquet_channels:
						data_list = list(data)
						if isinstance(data_list[3], bytes):
							data_list[3] = data_list[3].decode("utf-8")
						if self.find_anti_spam[ctx.author] >= data[0] and self.find_anti_spam[ctx.author] <= data[1] and len(current_streams) < 5:
							current_streams.append(data_list)
						elif self.find_anti_spam[ctx.author] < data[0] and len(future_streams) < 5:
							future_streams.append(data_list)
						elif self.find_anti_spam[ctx.author] > data[1] and len(past_streams) < 5:
							past_streams.append(data_list)

				for data in events_resp:
					current_streams.append([data[0]])

				await conn.commit()

				sent_msg = False

				if len(current_streams) > 0:
					current_stream_str = [f"{ctx.author.mention} Current streams: \n\n"]

					for data in current_streams:
						if len(data) > 1:
							addition = f"**{data[3]}** on channel **{data[2]}**\n"
						else:
							addition = f"**{data[0]}**\n"

						self.add_message(current_stream_str, addition)

					for message in current_stream_str:
						await ctx.channel.send(message)

					sent_msg = True 

				if len(future_streams) > 0 and not sent_msg:
					future_stream_str = [f"{ctx.author.mention} No current streams found. This will stream later on: \n\n"]
					channels_completed = []

					for data in future_streams:
						if data[2] in channels_completed:
							continue
						channels_completed.append(data[2])

						date_str = get_formatted_date_from_epoch_est(data[0])
						self.add_message(future_stream_str, f"**{data[3]} ** on channel **{data[2]}** ({date_str})\n")

					for message in future_stream_str:
						await ctx.channel.send(message)

					return

				if len(past_streams) > 0:
					if sent_msg:
						past_stream_str = [""]
					else:
						past_stream_str = [ctx.author.mention + " No current streams found. This aired in the past: \n\n"]

					channels_completed = []

					for data in past_streams:
						if data[2] in channels_completed:
							continue
						channels_completed.append(data[4])
						hours = math.ceil((self.find_anti_spam[ctx.author] - data[1]) / 3600)
						if hours > 1:
							addition = f"**{data[3]}** on channel **{data[2]}** (Program Ended {hours} hours ago)\n"
						else:
							addition = f"**{data[3]}** on channel **{data[2]}** (Program Ended {hours} hour ago)\n"
						self.add_message(past_stream_str, addition)

					for message in past_stream_str:
						await ctx.channel.send(message)

					return

				if sent_msg:
					return

				await ctx.channel.send(f"{ctx.author.mention} No channel was found with this content.")
				return

	@commands.command()
	async def whatson(self, ctx, *args):
		if not ctx.channel.id in self.bot.config.get_config("find_cmd_channels"):
			return

		if not self.bot.pool:
			await ctx.channel.send(f"{ctx.author.mention} The service is down. Please try again later.")
			return

		if ctx.author in self.find_anti_spam:
			if time.time() - self.find_anti_spam[ctx.author] <= 5:
				time_left = math.ceil(5 - (time.time() - self.find_anti_spam[ctx.author]))
				await ctx.channel.send(f"{ctx.author.mention} Please wait **{time_left}** more seconds before using this command again.")
				return

		msg = " ".join(str(x) for x in args).lower()
		msg_para = "%" + msg + "%"
		if msg == "":
			await ctx.channel.send(f"{ctx.author.mention} Command usage: **?whatson <channel name>**")
			return

		self.find_anti_spam[ctx.author] = time.time()

		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute("""
					SELECT 
						start as start_date, 
						`end` as end_date,
						streams.stream_display_name,
						title,
						epg_data.channel_id,
						streams.id,
						streams.category_id
					FROM
						streams,
						epg_data
					WHERE
						streams.epg_id = epg_data.epg_id
						AND streams.channel_id = epg_data.channel_id
						AND streams.stream_display_name LIKE %s
					ORDER BY
						stream_display_name DESC,
						end_date ASC""", (msg_para, ))
				resp = await cur.fetchall()
				current_streams = {}

				for data in resp:
					if data[5] in self.bouquet_channels:
						data_list = list(data)
						if isinstance(data_list[3], bytes):
							data_list[3] = data_list[3].decode("utf-8")

						if self.find_anti_spam[ctx.author] <= data[1]:
							if not data[2] in current_streams:
								if len(current_streams) == 8 and not data[6] in (19, 7, 42, 20, 8, 21):
									continue
								current_streams[data[2]] = []
							current_streams[data[2]].append(data_list)

				await conn.commit()

				if len(current_streams) > 0:
					current_stream_str = [ctx.author.mention + "\n"]
					title_len = 0
					for stream_channel, stream_data_list in current_streams.items():
						self.add_message(current_stream_str, f"\n{stream_channel}\n")
						start_time_used = []
						number_additions = 0
						for data in stream_data_list:
							if number_additions == 5:
								break
							if data[0] in start_time_used:
								continue
							start_time_used.append(data[0])
							date_str = get_formatted_date_from_epoch_est(data[0])
							self.add_message(current_stream_str, f"**{data[3]}** - {date_str}\n")
							number_additions = number_additions + 1

					for message in current_stream_str:
						await ctx.channel.send(message)

					return

				await ctx.channel.send(f"{ctx.author.mention} No channels were found with that name.")
				return
	
	@commands.Cog.listener()
	async def on_ready(self):
		if self.stream_down_checker.is_running():
			return


		msg_id_list = self.bot.saveConfig.get_setting("last_down_messages")

		for channel_id, msg_id in msg_id_list.items():
			channel = self.bot.get_channel(int(channel_id))
			if not channel:
				continue

			try:
				msg = await channel.fetch_message(msg_id)
			except discord.errors.NotFound:
				continue

			await msg.delete()

		self.event_cache = self.bot.saveConfig.get_setting("event_cache")

		async with self.bot.pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute("SELECT bouquet_channels FROM bouquets;")
				resp = await cur.fetchall()

				for data in resp:
					self.bouquet_channels = self.bouquet_channels + json.loads(data[0])

				await conn.commit()
	
		self.stream_down_checker.start()
		self.event_checker.start()

		print("[ContentServices] Loaded cog.")

async def setup(bot):
	await bot.add_cog(ContentServices(bot))