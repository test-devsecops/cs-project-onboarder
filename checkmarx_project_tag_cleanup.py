from utility.http_utility import HttpRequests
from utility.routes import Routes
from utility.config_utility import Config
from utility.csv_utility import Csv
from utility.api_actions import ApiActions
from utility.helper_functions import HelperFunctions
from utility.logger import Logger
from utility.exception_handler import ExceptionHandler
from utility.json_file_utility import JSONFile

import os
import sys
import argparse
import re
import time
import json

def fallback_tags(project_name, project_codes_set, logger):
    match = re.match(r"^[\w\-\/]+\/([\w]+)-([\w]+)-[\w\-]+", project_name, re.IGNORECASE)

    if match:
        fallback_tag = match.group(2).upper()
        if fallback_tag in project_codes_set:
            return fallback_tag
        else:
            return "PRU"
            print(f"No valid tag found in PruCore for project {project_name}")
            logger.error(f"No valid tag found in PruCore for project {project_name}")
    else:
        print(f"Regex did not match for project name: {project_name}")
        logger.error(f"Regex did not match for project name: {project_name}")

def main(filename):

    httpRequest = HttpRequests()

    config = Config()
    token, tenant_name, tenant_iam_url, tenant_url = config.get_config()

    logger = Logger("project_tag_cleanup")

    routes = Routes()
    get_access_token_endpoint = routes.get_access_token(tenant_name)
    get_checkmarx_projects_endpoint = routes.get_checkmarx_projects()
    
    create_application_endpoint = routes.create_application()
    get_application_endpoint = routes.get_application()

    api_actions = ApiActions(httpRequest)
    access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)
    cx_projects = api_actions.get_checkmarx_projects(access_token, tenant_url, get_checkmarx_projects_endpoint, empty_tag="false")

    project_codes = Csv.read_csv(filename, column_index=0)
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
            normalized_tags = {tag.upper(): tag for tag in project_tags}
            fallback_tag = fallback_tags(project_name, project_codes_set, logger)
            
            # Step 1: Check if the project tags list is empty
            if not normalized_tags:
                print(f"No tags found in {project_name}")
                logger.info(f"No tags found in {project_name}")
                
                if fallback_tag:
                    print(f"Fallback tag '{fallback_tag}' found and valid for {project_name}")
                    logger.info(f"Fallback tag '{fallback_tag}' found and valid for {project_name}")
                    correct_project_tag_dict[fallback_tag] = ""

            # Step 2: Check which of the current tags are valid
            for normalized_tag, original_tag in normalized_tags.items():

                regex_pattern = r"^[\w\-\/]+\/([\w]+)-(" + normalized_tag + r")-[\w\-]+"

                # Check: Validate the tag against the list of project codes from prucore
                if normalized_tag in project_codes_set:

                    # Check: Validate the tag based on the regex patterns in project name
                    if re.match(regex_pattern, project_name, re.IGNORECASE):
                        correct_project_tag_dict[normalized_tag] = ""
                        print(f"Tag '{normalized_tag}' matches pattern in project name.")
                        logger.info(f"Tag '{normalized_tag}' matches pattern in project name.")
                
                # Check: Validate against user_defined_tags_list
                elif normalized_tag in user_defined_tags_set:
                    correct_project_tag_dict[normalized_tag] = ""
                    print(f"Tag '{normalized_tag}' is found in user_defined_tags_list.")
                    logger.info(f"Tag '{normalized_tag}' is found in user_defined_tags_list.")

                # Check: Validate if the tag is an LBU name
                elif normalized_tag == lbu_name:
                    correct_project_tag_dict[normalized_tag] = ""
                    print(f"LBU Name: '{normalized_tag}'")
                    logger.info(f"LBU Name:  '{normalized_tag}'")

                else:
                    print(f"Tag '{normalized_tag}' is invalid tag")
                    logger.info(f"Tag '{normalized_tag}' is invalid tag")

            # Step 3: Always add LBU name if not already included
            if lbu_name not in correct_project_tag_dict:
                correct_project_tag_dict[lbu_name] = ""
                print(f"Added LBU name'{lbu_name}' to {project_name}")
                logger.info(f"Added LBU name'{lbu_name}' to {project_name}")

            # Step 4: Project code should be in project tags - fallback tag not empty, and project code (fallback_tag) should be present in the correct_project_tag_dict
            if fallback_tag:
                if fallback_tag not in correct_project_tag_dict:
                    print(f"No valid project code tag in {project_name}, attempting fallback.")
                    logger.info(f"No valid project code tag in {project_name}, attempting fallback.")

                    correct_project_tag_dict[fallback_tag] = ""
                    print(f"Fallback tag '{fallback_tag}' found and valid for {project_name}")
                    logger.info(f"Fallback tag '{fallback_tag}' found and valid for {project_name}")

            elif not correct_project_tag_dict:
                print(f"No valid project tags matched for {project_name} and no fallback tag was available.")
                logger.warning(f"No valid project tags matched for {project_name} and no fallback tag was available.")

            print(f"Correct tags for {project_name}: {correct_project_tag_dict}")
            logger.info(f"Correct tags for {project_name}: {correct_project_tag_dict}")
            
            # Step 5: Final check - if project_tags are present in correct_project_tag_dict, it means the tags are correct and can be skipped
            if set(project_tags.keys()) == set(correct_project_tag_dict.keys()):
                print(f"Project Tags in {project_name}: {project_tags} are equal to {correct_project_tag_dict}")
                logger.info(f"Project Tags in {project_name}: {project_tags} are equal to {correct_project_tag_dict}")

                print(f"Skipping {project_name}...")
                logger.info(f"Skipping {project_name}...")
                continue

            try:
                print(f"Correcting the tags for {project_name}: {correct_project_tag_dict}")
                logger.info(f"Correcting the tags for {project_name}: {correct_project_tag_dict}")

                replace_project_tagsendpoint = routes.update_projects(project_id)
                api_actions.replace_project_tags(access_token, tenant_url, replace_project_tagsendpoint, cx_project, correct_project_tag_dict)

                print(f"Tags for {project_name} have been replaced with: {correct_project_tag_dict}")
                logger.info(f"Tags for {project_name} have been replaced with: {correct_project_tag_dict}")
                project_tag_fixed += 1

            except Exception as e:
                print(f"Error tagging project {project_name}: {e}")
                logger.error(f"Error tagging project {project_name}: {e}")
                project_tag_failed += 1

        # Renew access token after processing a batch
        access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)
        print("Access token renewed.")

        if i + batch_size < len(cx_projects):  # Avoid sleeping after the last batch
            print(f"Processed {i + batch_size} projects. Waiting {batch_timeout} seconds before the next batch...")
            time.sleep(batch_timeout)  # Wait before processing the next batch
    
    logger.info("Project tag correction is complete.")
    logger.info(f"Total project tag fixed: {project_tag_fixed}")
    logger.info(f"Total project tag failed to fix: {project_tag_failed}")

    print("Project tag correction is complete.")
    print(f"Total project tag fixed: {project_tag_fixed}")
    print(f"Total project tag failed to fix: {project_tag_failed}")
    print(f"Logs available here {logger.get_log_file_path()}")

if __name__ == "__main__":
    # Define command-line arguments
    parser = argparse.ArgumentParser(description='Onboarding Prucore Apps')
    parser.add_argument('-filename', help='filename of the prucore apps',required=True)

    # Parse the command-line arguments
    args = parser.parse_args()

    # Call the main function with the provided exlusions and LBU
    main(args.filename)