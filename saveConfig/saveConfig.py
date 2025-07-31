import json

class SaveConfig:
	def __init__(self):
		with open("/home/relerx/stream-bot-new/saveConfig/config.json", "r") as file:
			self.data = json.load(file)

	def get_setting(self, config):
		if config in self.data:
			return self.data[config]
		return None

	def set_setting(self, config, value):
		self.data[config] = value

		with open("/home/relerx/stream-bot-new/saveConfig/config.json", "w") as file:
			json.dump(self.data, file, indent=4)