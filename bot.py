import discord
import aiomysql
from discord.ext import commands
from tools import config, messages
import sys, traceback
from saveConfig.saveConfig import SaveConfig

async def command_prefix(bot, message):
	return "?"

class DiscordBot(commands.Bot):
	def __init__(self, *args, **kwargs):
		super(DiscordBot, self).__init__(*args, **kwargs)
		self.add_check(self.permissions_check)

		self.no_command = []

		self.config = config.Config()
		self.message_handler = messages.MessageHandler(self.config)

		self.saveConfig = SaveConfig()

	async def get_mysql_pool(self):
		try:
			if self.pool:
				await self.pool.close()
		except:
			False

		self.pool = await aiomysql.create_pool(
			host=self.config.get_config('mysql_host'),
			port=self.config.get_config('mysql_port'),
			user=self.config.get_config('mysql_username'),
			password=self.config.get_config('mysql_password'),
			db=self.config.get_config('mysql_database'),
			autocommit=True
		)

	async def setup_hook(self) -> None:
		self.pool = False
		await self.get_mysql_pool()

		for extension in extensions:
			await self.load_extension(extension)

	async def on_message(self, msg):
		ctx = await self.get_context(msg, cls=messages.MessageContext)
		await self.invoke(ctx)

	async def on_ready(self):
		print("[MAIN] User details: " + str(self.user))

	async def permissions_check(self, ctx):
		#print("Permissions check for: " + ctx.command.name)

		if ctx.guild is None:
			return True
		
		if ctx.author.guild_permissions.administrator:
			return True

		permissions = self.config.get_config('permissions')
		if not ctx.command.name in permissions:
			return True

		permissions = permissions[ctx.command.name]
		for permission in permissions:
			role_perm = discord.utils.get(ctx.author.roles, id=permission) if isinstance(permission, int) else discord.utils.get(ctx.author.roles, name=permission)
			if role_perm:
				return True
		
		#print("Failed")
		return False

	@commands.Cog.listener()
	async def on_command_error(self, ctx, error):
		if hasattr(ctx.command, 'on_error') and not hasattr(ctx, 'error_handle'):
			return

		cog = ctx.cog
		if cog:
			if cog._get_overridden_method(cog.cog_command_error) is not None:
				return

		ignored = (commands.CommandNotFound, commands.CheckFailure)

		error = getattr(error, 'original', error)

		if isinstance(error, ignored):
			return

		if isinstance(error, commands.errors.MissingRequiredArgument) or isinstance(error, commands.errors.BadArgument):
			if ctx.guild is None:
				return

			try:
				await ctx.send(f'{ctx.command.name}_usage', prefix=await self.settings.get_setting(ctx.guild, 'prefix'))
			except KeyError:
				pass
			return

		print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
		traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

	async def on_error(self, event_method, *args, **kwargs):
		raise

intents = discord.Intents.default()
intents.members = True
intents.invites = True
intents.message_content = True

bot = DiscordBot(command_prefix=command_prefix, intents=intents, help_command=None)

extensions = ['cogs.service_status', 'cogs.content', 'cogs.on_demand']

bot.run(bot.config.get_config('token'))