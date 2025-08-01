import json
import os

class SaveConfig:
    def __init__(self):
        self.config_path = os.getenv('SAVECONFIG_PATH') or os.path.join(os.path.dirname(__file__), 'config.json')  # Use env or relative path
        try:
            with open(self.config_path, "r") as file:
                self.config = json.load(file)
        except FileNotFoundError:
            self.config = {}  # Default to empty if file missing
            print(f"Config file not found at {self.config_path}; using empty config.")

    def get_setting(self, key):
        return self.config.get(key)

    def set_setting(self, key, value):
        self.config[key] = value
        with open(self.config_path, "w") as file:
            json.dump(self.config, file, indent=4)