import yaml


# def load_yaml(filepath):
#     with open(filepath, "r") as file:
#         return yaml.safe_load(file)
def load_yaml(config_path):
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading api config: {e}")
        return {}