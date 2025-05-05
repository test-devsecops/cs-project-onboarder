import json

class JSONFile:

    @staticmethod
    def read_json_file(json_file):
        # Load JSON file
        with open(json_file, 'r') as file:
            data = json.load(file)
            return data