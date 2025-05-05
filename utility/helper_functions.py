from utility.json_file_utility import JSONFile

import string
import re

class HelperFunctions:
    
    @staticmethod
    def get_lbu_name(app_name, json_file="lbu.json"):

        # Read JSON file and extract the LBU list
        lbu_data = JSONFile.read_json_file(json_file)
        lbu_list = lbu_data.get("lbu", [])

        # Search for LBU in project name
        for lbu in lbu_list:
            if lbu.lower() in app_name.lower():
                return lbu 
        
        return "Pru"
    
    @staticmethod
    def get_lbu_name_v2(app_name, json_file="lbu.json"):
        lbu_data = JSONFile.read_json_file(json_file)
        lbu_list = lbu_data.get("lbu", [])

        # Extract the segment right after "pru-"
        match = re.search(r'^pru-([\w]+)', app_name, re.IGNORECASE)
        if match:
            lbu_candidate = match.group(1).upper()
            if lbu_candidate in [l.upper() for l in lbu_list]:
                return lbu_candidate

        # If not found using prefix, fallback to whole-word matching
        for lbu in lbu_list:
            pattern = r'(?i)(?:^|[-/_])' + re.escape(lbu) + r'(?:$|[-/_])'
            if re.search(pattern, app_name):
                return lbu

        return "Pru"

    @staticmethod
    def get_lbu_name_simple(app_name):
        """
        Extracts the LBU name directly after 'pru-' in the given app_name.
        Does not validate against any JSON list.
        """
        match = re.search(r'^pru-([\w]+)', app_name, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        
        return "Pru"

    @staticmethod
    def is_readable(text):
        # Check if all characters in a string are readable (printable)
        if all(char in string.printable for char in text):
            return True
        return False