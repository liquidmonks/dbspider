import json
import os

class Settings:
    def __init__(self):
        self.data = {}
        try:
            with open('settings.json', 'r') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            print("settings.json not found; falling back to env vars or defaults.")
            # Load from env as fallback
            self.guild_id = os.getenv('GUILD_ID')
            self.service_status_channels = os.getenv('SERVICE_STATUS_CHANNELS', '').split(',')
            self.down_stream_channels = os.getenv('DOWN_STREAM_CHANNELS', '').split(',')
            self.event_update_channels = os.getenv('EVENT_UPDATE_CHANNELS', '').split(',')
            self.find_cmd_channels = os.getenv('FIND_CMD_CHANNELS', '').split(',')
            self.scoreboard_bot_id = os.getenv('SCOREBOARD_BOT_ID')
            # Add more as needed from your original Settings
        else:
            # Load from JSON if file exists
            self.guild_id = self.data.get('guild_id')
            self.service_status_channels = self.data.get('service_status_channels', [])
            self.down_stream_channels = self.data.get('down_stream_channels', [])
            self.event_update_channels = self.data.get('event_update_channels', [])
            self.find_cmd_channels = self.data.get('find_cmd_channels', [])
            self.scoreboard_bot_id = self.data.get('other_settings', {}).get('scoreboard_bot_id')
            # Add more keys from your JSON example