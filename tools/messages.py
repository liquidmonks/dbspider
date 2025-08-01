from discord import Embed
from discord.utils import get
from discord.ext import commands
import discord
from emoji import EMOJI_DATA  # Updated to new API
from copy import deepcopy
from pprint import pprint
from string import Template
import datetime
from collections import defaultdict
import re

class format_dict(dict):
    def __missing__(self, key):
        return "..."

class MessageHandler:
    def __init__(self, settings):
        self.settings = settings

    def get_emoji_from_name(self, guild, name):
        return get(guild.emojis, name=name)

    def emojify_text(guild, text):
        if not guild:
            return text

        potential_emojis = re.findall(r'\:(.*?)\:', text)

        for emoji in potential_emojis:
            if re.search(r'\s', emoji):
                continue

            emoji_obj = get(guild.emojis, name=emoji)

            if not emoji_obj:
                continue

            text = text.replace(f':{emoji}:', str(emoji_obj))

        return text

    def format_text(guild, msg, **kwargs):
        d = defaultdict(lambda: "...")
        d.update(**kwargs)
        return MessageHandler.emojify_text(guild, msg.format_map(d))

    def get_embed(self, setting, **kwargs):
        base_dict = {}

        if setting != "base_embed":
            try:
                base_dict = deepcopy(self.settings.get_config("base_embed"))
            except KeyError:
                pass

            if isinstance(self.settings, dict):
                if '.' in setting:
                    embed_dict = self.settings
                    for key in setting.split('.'):
                        embed_dict = embed_dict[key]
                else:
                    embed_dict = self.settings[setting]

                base_dict.update(deepcopy(embed_dict))
            else:
                base_dict.update(self.settings.get_config(setting))

            embed_dict = base_dict

            if 'prehook' in embed_dict:
                del embed_dict['prehook']

            if 'posthook' in embed_dict:
                del embed_dict['posthook']

            guild = kwargs.get('guild', None)

            if "author" in kwargs:
                embed_dict["author"] = {}
                embed_dict["author"]["name"] = str(kwargs["author"])
                embed_dict["author"]["icon_url"] = str(kwargs["author"].avatar)

                if not guild and isinstance(kwargs['author'], discord.Member):
                    guild = kwargs['author'].guild

            embed_dict['color'] = int(self.settings.get_config('embed_color'), 16)

            for field in embed_dict:
                if field == "title" or field == "description" or field == "url":
                    embed_dict[field] = MessageHandler.format_text(guild, embed_dict[field], **kwargs)
                elif field == "footer" or field == "thumbnail":
                    for footer_obj_name in embed_dict[field]:
                        embed_dict[field][footer_obj_name] = MessageHandler.format_text(guild, embed_dict[field][footer_obj_name], **kwargs)
                elif field == "fields":
                    for field_obj in embed_dict[field]:
                        field_obj["name"] = MessageHandler.format_text(guild, field_obj["name"], **kwargs)
                        field_obj["value"] = MessageHandler.format_text(guild, field_obj["value"], **kwargs)
                elif field == "timestamp":
                    if "timestamp" in kwargs:
                        embed_dict[field] = kwargs['timestamp']
                    else:
                        embed_dict[field] = datetime.datetime.utcnow().isoformat()

            return Embed.from_dict(embed_dict)

    async def send_message(self, place, setting, send_embed=True, template=None, custom_args=None, **kwargs):
        embed_settings = self.settings.get_config(setting)

        custom_args = {} if not custom_args else custom_args

        sent_msg = False

        if 'prehook' in embed_settings:
            await place.send(embed_settings['prehook'])

        if send_embed:
            embed = True if 'embed' in embed_settings else False

            if embed:
                embed = self.get_embed(setting, **kwargs)

                if template:
                    for template_data in kwargs.get('template_data', []):
                        add_embed = self.get_embed(setting, **kwargs)
                        for field in add_embed.fields:
                            embed.add_field(field.name, field.value, field.inline)

                sent_msg = await place.send(embed=embed, **custom_args)
            else:
                sent_msg = await place.send(MessageHandler.format_text(place.guild, embed_settings['description'], **kwargs), **custom_args)

        if 'posthook' in embed_settings:
            await place.send(embed_settings['posthook'], **custom_args)

        if sent_msg:
            return sent_msg

class Reactions:
    def get_reaction(guild, reaction):
        if reaction in EMOJI_DATA:  # Updated to new API
            return reaction

        emoji = get(guild.emojis, name=reaction[1:-1])

        if emoji:
            return emoji

        return reaction

class MessageContext(commands.Context):
    async def send(ctx, setting, *args, **kwargs):
        if not 'author' in kwargs:
            kwargs['author'] = ctx.author

        return await ctx.bot.message_handler.send_message(ctx.channel, setting, *args, **kwargs)