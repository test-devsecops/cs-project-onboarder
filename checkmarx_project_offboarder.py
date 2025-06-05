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

def main(filename):

    httpRequest = HttpRequests()

    config = Config()
    token, tenant_name, tenant_iam_url, tenant_url = config.get_config()

    logger = Logger("project_offboarding")

    routes = Routes()
    get_access_token_endpoint = routes.get_access_token(tenant_name)
    get_checkmarx_projects_endpoint = routes.get_checkmarx_projects()

    api_actions = ApiActions(httpRequest)
    access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)

    # Step 1: Retrieve all on-boarded projects
    cx_projects = api_actions.get_checkmarx_projects(access_token, tenant_url, get_checkmarx_projects_endpoint, empty_tag="false")

    prucore_filepath = f"./csv_files/project_offboarding/{filename}"
    project_names_to_delete = Csv.read_csv(prucore_filepath, column_index=0)

    # Tracking counters
    project_deleted_count = 0
    project_failed_delete_count = 0

    failed_projects = []

    for project_name_to_delete in project_names_to_delete:

        try: 
            cx_projects = api_actions.get_checkmarx_projects(access_token, tenant_url, get_checkmarx_projects_endpoint, project_name=project_name_to_delete)

            if not cx_projects:
                logger.error(f"No Checkmarx project found for {project_name_to_delete}")
                project_failed_delete_count += 1
                failed_projects.append(project_name_to_delete)
                continue

            cx_project = cx_projects[0]
            project_id = cx_project.get("id")

            if not project_id:
                logger.error(f"Project {project_name_to_delete} has no project ID.")
                project_failed_delete_count += 1
                failed_projects.append(project_name_to_delete)
                continue

            print(f"Removing project {project_name_to_delete}...")
            logger.info(f"Removing project {project_name_to_delete}...")

            delete_checkmarx_project_endpoint = routes.delete_project(project_id)
            delete_project_response = api_actions.delete_checkmarx_project(access_token, tenant_url, delete_checkmarx_project_endpoint)
            project_deleted_count += 1

            print(f"Project {project_name_to_delete} removed.")
            logger.info(f"Project {project_name_to_delete} removed.")

        except Exception as e:
            logger.error(f"Error processing {project_name_to_delete}: {e}")
            logger.error(f"Failed to remove {project_name_to_delete}")

            print(f"Error processing {project_name_to_delete}: {e}")
            print(f"Failed to remove {project_name_to_delete}")
            
            failed_projects.append(project_name_to_delete)
            project_failed_delete_count += 1

    logger.info("Offboarding projects is completed.")
    logger.info(f"Total Offboarded Projects: {project_deleted_count}")
    logger.info(f"Total Project failed to remove: {project_failed_delete_count}")

    print("Offboarding projects is completed.")
    print(f"Total Offboarded Projects: {project_deleted_count}")
    print(f"Total Project failed to remove: {project_failed_delete_count}")

    print(f"Logs available here {logger.get_log_file_path()}")

if __name__ == "__main__":
    # Define command-line arguments
    parser = argparse.ArgumentParser(description='Offboarding CX project ')
    parser.add_argument('-filename', help='filename of the CX projects to be deleted',required=True)

    # Parse the command-line arguments
    args = parser.parse_args()

    # Call the main function with the provided exlusions and LBU
    main(args.filename)