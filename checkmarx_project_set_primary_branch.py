from utility.http_utility import HttpRequests
from utility.routes import Routes
from utility.config_utility import Config
from utility.csv_utility import Csv
from utility.api_actions import ApiActions
from utility.helper_functions import HelperFunctions
from utility.exception_handler import ExceptionHandler

import os
import sys
import argparse
import re
import time
import json

def main():

    httpRequest = HttpRequests()

    config = Config()
    token, tenant_name, tenant_iam_url, tenant_url = config.get_config()

    routes = Routes()
    get_access_token_endpoint = routes.get_access_token(tenant_name)
    get_checkmarx_projects_endpoint = routes.get_checkmarx_projects()

    api_actions = ApiActions(httpRequest)
    access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)

    cx_projects = api_actions.get_checkmarx_projects(access_token, tenant_url, get_checkmarx_projects_endpoint, empty_tag="false")

    # Tracking counters
    project_success_update_count = 0
    project_failed_update_count = 0

    failed_projects = []
    repos_missing_default_branch = []

    batch_size = 100
    batch_timeout = 60

    for i in range(0, len(cx_projects), batch_size):
        batch = cx_projects[i:i + batch_size]

        for cx_project in batch:
            
            try: 
                project_id = cx_project.get("id")
                project_name = cx_project.get("name")
                repo_id = cx_project.get("repoId")
                project_main_branch = cx_project.get("mainBranch")

                print(f"Updating the primary branch of project {project_name}...")

                # Get the repo branches that are available
                get_repo_branches_endpoint = routes.get_repo_branches(repo_id)
                available_repo_branches = api_actions.get_repo_branches(access_token, tenant_url, get_repo_branches_endpoint)

                # Default primary branch
                primary_branch = "main"

                # Check if the response is valid and contains the expected key
                if available_repo_branches and "branchWebDtoList" in available_repo_branches:
                    extracted_available_branches = set(branch["name"] for branch in available_repo_branches["branchWebDtoList"])

                    if "main" in extracted_available_branches:
                        primary_branch = "main"
                    elif "master" in extracted_available_branches:
                        primary_branch = "master"
                    else:
                        print("Neither 'main' nor 'master' branches were found in the repository.")
                        repos_missing_default_branch.append(project_name)
                        project_failed_update_count += 1
                        failed_projects.append(project_name)
                        continue
                else:
                    print("Failed to retrieve repository branches or unexpected response format.")
                    continue

                if primary_branch == project_main_branch:
                    print(f"Project {project_name}'s primary branch has already been configured to {primary_branch}.")
                    continue

                # Update the primary branch
                update_project_primary_branch_endpoint = routes.update_projects(project_id)
                api_actions.update_project_primary_branch(access_token, tenant_url, update_project_primary_branch_endpoint, cx_project, primary_branch)
                project_success_update_count += 1

                print(f"Project {project_name}'s primary branch has been set to {primary_branch}.")

            except Exception as e:
                print(f"Error processing {project_name}: {e}")

                failed_projects.append(project_name)
                project_failed_update_count += 1

        # Renew access token after processing a batch
        access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)
        print("Access token renewed.")

        if i + batch_size < len(cx_projects):  # Avoid sleeping after the last batch
            print(f"Processed {i + batch_size} projects. Waiting {batch_timeout} seconds before the next batch...")
            time.sleep(batch_timeout)  # Wait before processing the next batch

    print("Setting up Primary branch for the projects is completed.")
    print(f"Total Updated Projects: {project_success_update_count}")
    print(f"Total Project failed to update: {project_failed_update_count}")

    # Print repos withouth main or master branch
    if repos_missing_default_branch:
        print("Repositories skipped due to missing 'main' or 'master' branches:")
        for repo in repos_missing_default_branch:
            print(f" - {repo}")

if __name__ == "__main__":
    main()