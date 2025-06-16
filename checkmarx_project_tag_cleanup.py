from utility.http_utility import HttpRequests
from utility.routes import Routes
from utility.config_utility import Config
from utility.csv_utility import Csv
from utility.api_actions import ApiActions
from utility.helper_functions import HelperFunctions
from utility.exception_handler import ExceptionHandler
from utility.json_file_utility import JSONFile

import os
import sys
import argparse
import re
import time
import json

def main(filename):

    httpRequest = HttpRequests()

    config = Config()
    token, tenant_name, tenant_iam_url, tenant_url = config.get_config()

    routes = Routes()
    get_access_token_endpoint = routes.get_access_token(tenant_name)
    get_checkmarx_projects_endpoint = routes.get_checkmarx_projects()
    
    create_application_endpoint = routes.create_application()
    get_application_endpoint = routes.get_application()

    api_actions = ApiActions(httpRequest)
    access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)
    cx_projects = api_actions.get_checkmarx_projects(access_token, tenant_url, get_checkmarx_projects_endpoint, empty_tag="false")

    prucore_filepath = f"./csv_files/prucore/{filename}"

    project_codes = Csv.read_csv(prucore_filepath, column_index=0)
    user_defined_tags_data = JSONFile.read_json_file("user_defined_tags.json")
    user_defined_tags_list = user_defined_tags_data.get("valid_tags", [])

    project_codes_set = {code.upper() for code in project_codes}
    user_defined_tags_set = {t.upper() for t in user_defined_tags_list}

    project_tag_fixed = 0
    project_tag_failed = 0

    batch_size = 100
    batch_timeout = 60

    for i in range(0, len(cx_projects), batch_size):
        batch = cx_projects[i:i + batch_size]  # Get the next batch of batch_size

        for cx_project in batch:
            project_id = cx_project.get("id")
            project_name = cx_project.get("name")
            project_tags = cx_project.get("tags", {})
            project_criticality = cx_project.get("criticality")
            lbu_name = HelperFunctions.get_lbu_name_simple(project_name).upper()

            correct_project_tag_dict = {}
            project_using_user_defined_tag = False

            for code in project_codes_set:

                # Get the correct tags
                regex_pattern = r"^[\w\-\/]+\/([\w]+)-(" + code + r")-[\w\-]+"

                if re.match(regex_pattern, project_name, re.IGNORECASE):
                    print(f"{project_name} is regex matched! {code}")

                    correct_project_tag_dict[code] = ""
                    correct_project_tag_dict[lbu_name] = ""

            for code in user_defined_tags_set:
                if code in project_tags:
                    print(f"{project_name} user defined code is valid {code}")

                    correct_project_tag_dict[code] = ""
                    correct_project_tag_dict[lbu_name] = ""

                    project_using_user_defined_tag = True

            if not correct_project_tag_dict:
                print(f"Need to assign fallback code and LBU name tags to {project_name}")

                correct_project_tag_dict["PRU"] = ""
                correct_project_tag_dict[lbu_name] = ""

            try:
                print(f"Correct tags for {project_name}: {correct_project_tag_dict}")

                if project_tags != correct_project_tag_dict:

                    replace_project_tagsendpoint = routes.update_projects(project_id)
                    api_actions.replace_project_tags(access_token, tenant_url, replace_project_tagsendpoint, cx_project, correct_project_tag_dict)

                    print(f"Tags for {project_name} have been replaced with: {correct_project_tag_dict}")
                    project_tag_fixed += 1
                
                else:
                    print(f"Current project tags {project_name}:{project_tags} are equal to: {correct_project_tag_dict}")

            except Exception as e:
                print(f"Error tagging project {project_name}: {e}")
                project_tag_failed += 1
                
        # Renew access token after processing a batch
        access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)
        print("Access token renewed.")

        if i + batch_size < len(cx_projects):  # Avoid sleeping after the last batch
            print(f"Processed {i + batch_size} projects. Waiting {batch_timeout} seconds before the next batch...")
            time.sleep(batch_timeout)  # Wait before processing the next batch

    print("Project tag correction is complete.")
    print(f"Total project tag fixed: {project_tag_fixed}")
    print(f"Total project tag failed to fix: {project_tag_failed}")

if __name__ == "__main__":
    # Define command-line arguments
    parser = argparse.ArgumentParser(description='Clean project tags')
    parser.add_argument('-filename', help='filename of the prucore apps',required=True)

    # Parse the command-line arguments
    args = parser.parse_args()

    # Call the main function with the provided exlusions and LBU
    main(args.filename)