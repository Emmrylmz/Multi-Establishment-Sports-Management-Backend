import base64
from typing import Any, Dict
import yaml
import os

# print("Current working directory:", os.getcwd())


class Config:
    def __init__(self, config_path: str):
        self.config_data = self.load_config(config_path)

    def load_config(self, config_path: str) -> Dict[str, Any]:
        if not os.path.exists(config_path):
            print(f"file not found: {config_path}")
            return {'file not found:' : config_path}
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            print(f"Error loading: {e}")
            return {'Error loading:' : config_path}

    def get(self, key: str):
        # print(f"Current configuration data: {self.config_data.get('USERNAME')}")
        return self.config_data.get(key)

# Creating a config obj to import in main 
configure = Config('config.yaml')