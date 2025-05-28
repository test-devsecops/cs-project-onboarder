from utility.http_utility import HttpRequests
from utility.routes import Routes
from utility.config_utility import Config
from utility.csv_utility import Csv
from utility.api_actions import ApiActions
from utility.helper_functions import HelperFunctions
from utility.logger import Logger
from utility.exception_handler import ExceptionHandler

import os
import sys
import argparse
import re
import time
import json

def generate_checkmarx_app_name(app_name, project_code):
    # Generates a Checkmarx application name in the format <LBU>-<Project Code>-<App Name>
    lbu_name = HelperFunctions.get_lbu_name_simple(app_name)
    formatted_app_name = clean_app_name(app_name)
    final_app_name = f"{lbu_name}-{project_code}-{formatted_app_name}"
    return final_app_name

def clean_app_name(app_name):

    # Remove all special characters except letters, numbers, spaces, and dashes
    cleanedName = re.sub(r'[^a-zA-Z0-9\s-]', '', app_name)

    # Replace multiple spaces and dashes with a single dash
    cleanedName = re.sub(r'[\s-]+', '-', cleanedName)

    # Remove any leading or trailing dashes
    cleanedName = cleanedName.strip('-')

    return cleanedName

def check_checkmarx_app_exists_by_name(cx_app):

    cx_app_name = ""
    if "applications" in cx_app and cx_app["applications"]:
        cx_app_name = cx_app["applications"][0].get("name", "")

    return cx_app_name if cx_app_name else None

def get_criticality_level(risk):

    criticalityMapping = {
        "none": 1,
        "low": 2,
        "medium": 3,
        "high": 4,
        "critical": 5
    }

    return criticalityMapping.get(risk.lower(), 3)

def main(filename):

    httpRequest = HttpRequests()

    config = Config()
    token, tenant_name, tenant_iam_url, tenant_url = config.get_config()

    logger = Logger("project_and_app_onboarding")

    routes = Routes()
    get_access_token_endpoint = routes.get_access_token(tenant_name)
    get_checkmarx_projects_endpoint = routes.get_checkmarx_projects()
    
    create_application_endpoint = routes.create_application()
    get_application_endpoint = routes.get_application()

    api_actions = ApiActions(httpRequest)
    access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)

    # Step 1: Retrieve all on-board projects and tag them accordingly
    cx_projects = api_actions.get_checkmarx_projects(access_token, tenant_url, get_checkmarx_projects_endpoint, empty_tag="false")

    prucore_filepath = f"./csv_files/prucore/{filename}"

    project_codes = Csv.read_csv(prucore_filepath, column_index=0)
    app_names = Csv.read_csv(prucore_filepath, column_index=1)
    criticality = Csv.read_csv(prucore_filepath, column_index=2)

    project_exists = False

    newly_tagged_project_count = 0
    newly_tagged_application_count = 0
    newly_created_application_count = 0

    # Step 2: Create Applications and Tag projects in Checkmarx
    for idx, app in enumerate(app_names):

        # NOTE: app_name is equal to Project Name in PruCore
        app_name, tag, crit = app_names[idx], project_codes[idx], criticality[idx]
        criticality_level = get_criticality_level(crit)

        # regex_pattern = r"^[\w\/\-\@]+(\-" + tag + r"\-)[\w]+"
        regex_pattern = r"^[\w\-\/]+\/([\w]+)-(" + tag + r")-[\w\-]+"
        for project in cx_projects:
            project_name = project.get("name")
            project_id = project.get("id")
            
            try:
                # NOTE: If existing CX project does not have a tag on its name, it will not be tagged
                if re.match(regex_pattern, project_name, re.IGNORECASE):
                    print(f"{project_name} is regex matched!")
                    logger.info(f"{project_name} is regex matched!")
                    tags = project.get("tags")

                    if not tags:

                        lbu_name_tag = HelperFunctions.get_lbu_name_simple(project_name)

                        # Combine tags in a dict
                        new_tags = {
                            tag: "",
                            lbu_name_tag: ""
                        }

                        # Tagging the exisiting CX Project. This includes updating the criticality level of the project.
                        print(f"Tagging project {project_name}")
                        logger.info(f"Tagging project {project_name}")

                        update_project_tags_and_criticality_endpoint = routes.update_projects(project_id)
                        api_actions.update_project_tags_and_criticality(access_token, tenant_url, update_project_tags_and_criticality_endpoint, project, criticality_level, new_tags)
                        
                        print(f"Tagged project {project_name}: {tag}")
                        logger.info(f"Tagged project {project_name}: {tag}")
                        newly_tagged_project_count += 1

                    else:
                        print(f"Project {project_name} is already tagged.")
                        logger.info(f"Project {project_name} is already tagged.")

                    project_exists = True

            except Exception as e:
                print(f"Error tagging project {project_name}: {e}")
                logger.error(f"Error tagging project {project_name}: {e}")
            
        if project_exists:

            '''Step 2b: Create Application on Checkmarx. Only those existing projects in CX with tag on its 
            name will be created with the equivalent application.'''

            generated_app_name = generate_checkmarx_app_name(app_name, tag)
            cx_app = api_actions.get_application_by_name(access_token, tenant_url, get_application_endpoint, generated_app_name)

            if not cx_app:
                print(f"No response received for application: {generated_app_name}")
                logger.error(f"No response received for application: {generated_app_name}")
                continue

            cx_app_exists = check_checkmarx_app_exists_by_name(cx_app)

            if not cx_app_exists:

                try:
                    api_actions.create_application(access_token, tenant_url, create_application_endpoint, 
                    generated_app_name, tag, criticality_level)
                    cx_app_id = app_created['id']

                    # Direct Association: Add Project IDs to the Application
                    add_projects_to_application_endpoint = routes.add_projects_to_application(cx_app_id)
                    api_actions.add_projects_to_application(access_token, tenant_url, add_projects_to_application_endpoint, project_ids_grouped_by_tag)

                    print(f"Sucessfully created application {generated_app_name}")
                    logger.info(f"Sucessfully created application {generated_app_name}")
                    newly_created_application_count += 1

                except Exception as e:
                    print(f"Error creating application {generated_app_name}: {e}")
                    logger.error(f"Error creating application {generated_app_name}: {e}")

            else:
                try:
                    cx_app_id = cx_app.get("applications", [{}])[0].get("id", "")
                    cx_app_name = cx_app.get("applications", [{}])[0].get("name", "")

                    print(f"Application {cx_app_name} exists")
                    logger.info(f"Application {cx_app_name} exists")

                    # Updating the application with the new project tag
                    print(f"Tagging application {cx_app_name} with the new project tag...")
                    logger.info(f"Tagging application {cx_app_name} with the new project tag...")

                    update_application_tags_and_criticality_endpoint = routes.update_application(cx_app_id)
                    api_actions.update_application_tags_and_criticality(
                        access_token, tenant_url, update_application_tags_and_criticality_endpoint, criticality_level, tag)

                    # Direct Association: Add Project IDs to the Application
                    add_projects_to_application_endpoint = routes.add_projects_to_application(cx_app_id)
                    api_actions.add_projects_to_application(access_token, tenant_url, add_projects_to_application_endpoint, project_ids_grouped_by_tag)

                    print(f"Tagged application {cx_app_name} with the new project tag: {tag}")
                    logger.info(f"Tagged application {cx_app_name} with the new project tag:  {tag}")
                    newly_tagged_application_count += 1

                    project_exists = False

                except Exception as e:
                    print(f"Error tagging application {cx_app_name}: {e}")
                    logger.error(f"Error tagging application {cx_app_name}: {e}")

    logger.info("Onboarding pru core apps is complete.")
    logger.info(f"Total Newly Tagged Projects: {newly_tagged_project_count}")
    logger.info(f"Total Tagged Applications: {newly_tagged_application_count}")
    logger.info(f"Total Newly Created Applications: {newly_created_application_count}")

    print("Onboarding pru core apps is complete.")
    print(f"Total Newly Tagged Projects: {newly_tagged_project_count}")
    print(f"Total Tagged Applications: {newly_tagged_application_count}")
    print(f"Total Newly Created Applications: {newly_created_application_count}")
    print(f"Logs available here {logger.get_log_file_path()}")

if __name__ == "__main__":
    # Define command-line arguments
    parser = argparse.ArgumentParser(description='Onboarding Prucore Apps')
    parser.add_argument('-filename', help='filename of the prucore apps',required=True)

    # Parse the command-line arguments
    args = parser.parse_args()

    # Call the main function with the provided exlusions and LBU
    main(args.filename)