import toml
import copy
import hashlib
from pathlib import Path
from dotenv import load_dotenv
import os

CONFIG_FILE_PATH = Path(__file__).parent / '../data/'


class Config:
    def checksum(self, filename, hash_factory=hashlib.md5, chunk_num_blocks=128):
        h = hash_factory()
        with open(filename, 'rb') as f:
            while chunk := f.read(chunk_num_blocks * h.block_size):
                h.update(chunk)
        return h.digest()

    def reload_file(self, file):
        file_hash = self.checksum(file)

        if file in self.files_to_hash and self.files_to_hash[file] == file_hash:
            return

        self.files_to_hash[file] = file_hash

        config_settings = toml.load(file)
        self.toml_data.update(config_settings)

        for config_setting in config_settings:
            self.config_to_file[config_setting] = file

    def reload_files(self):
        for config_file in Path(CONFIG_FILE_PATH).iterdir():
            if not config_file.is_file():
                continue

            config_str = str(config_file)

            if 'settings' in config_str:
                if self.dev:
                    if 'prod' in config_str:
                        continue
                else:
                    if not 'prod' in config_str:
                        continue

            self.reload_file(config_str)

    def __init__(self, dev=False):
        self.toml_data = {}
        self.files_to_hash = {}
        self.config_to_file = {}

        self.dev = dev

        load_dotenv()  # Load .env file for environment variables

        self.reload_files()

    def get_config(self, config):
        # First, try to get from environment variables (transform dot-separated to UPPER_WITH_UNDERSCORES)
        env_key = config.upper().replace('.', '_')
        env_value = os.getenv(env_key)
        if env_value is not None:
            # Attempt to parse env value if it's a simple type (str, int, etc.)
            try:
                return int(env_value)
            except ValueError:
                try:
                    return float(env_value)
                except ValueError:
                    if env_value.lower() in ['true', 'false']:
                        return env_value.lower() == 'true'
                    return env_value  # Return as string by default

        # Fallback to TOML if not in env
        config_data = self.toml_data
        config_keys = config.split('.')
        self.reload_file(self.config_to_file[config_keys[0]])

        for key in config_keys:
            try:
                config_data = config_data[key]
            except TypeError:
                config_data = config_data[int(key)]

        config_type = type(config_data)

        if config_type == list or config_type == dict:
            return copy.deepcopy(config_data)

        return config_data