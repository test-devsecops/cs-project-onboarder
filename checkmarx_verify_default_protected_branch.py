from utility.http_utility import HttpRequests
from utility.routes import Routes
from utility.config_utility import Config
from utility.csv_utility import Csv
from utility.api_actions import ApiActions

import os
import sys
import argparse
import re
import time

def main():

    httpRequest = HttpRequests()

    config = Config()
    token, tenant_name, tenant_iam_url, tenant_url = config.get_config()

    routes = Routes()
    get_access_token_endpoint = routes.get_access_token(tenant_name)
    get_checkmarx_projects_endpoint = routes.get_checkmarx_projects()

    api_actions = ApiActions(httpRequest)
    access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)
    cx_projects = api_actions.get_checkmarx_projects(access_token, tenant_url, get_checkmarx_projects_endpoint)
    
    # Batch configuration
    batch_size = 100
    batch_timeout = 3  # seconds
    sleep_time = 0 # seconds

    # Tracking counters
    repo_updated_count = 0
    repo_failed_update_count = 0

    failed_repositories = []
    repos_missing_default_branch = []

    for i in range(0, len(cx_projects), batch_size):
        batch = cx_projects[i:i + batch_size]

        for cx_project in batch:
            project_id = cx_project.get("id")
            project_name = cx_project.get("name")
            repo_id = cx_project.get("repoId")

            if not repo_id:
                print(f"Project {project_name} has no repository ID.")
                repo_failed_update_count += 1
                failed_repositories.append(project_name)
                continue

            print(f"Getting data of the project repo: {project_name}")
            get_project_repo_endpoint = routes.get_project_repo(repo_id)
            repo_info = api_actions.get_project_repo_info(access_token, tenant_url, get_project_repo_endpoint)

            try:
                # Get the repo branches that are available to be set as protected branches - these are not necessarily protected branches though they could be protected branches already.
                get_repo_branches_endpoint = routes.get_repo_branches(repo_id)
                available_repo_branches = api_actions.get_repo_branches(access_token, tenant_url, get_repo_branches_endpoint)
                extracted_available_branches = set(branch["name"] for branch in available_repo_branches["branchWebDtoList"])
            except Exception as e:
                print(f"Error processing {project_name}: {e}")
                print(f"Failed to get the available branches of {project_name}")
                
                failed_repositories.append(project_name)
                repo_failed_update_count += 1
            
            # Check for presence of main or master
            preferred_default_branch = None
            if "main" in extracted_available_branches:
                preferred_default_branch = "main"

            elif "master" in extracted_available_branches:
                preferred_default_branch = "master"

            else:
                print(f"Project '{project_name}' has neither 'main' nor 'master' branch. Skipping...")

                repos_missing_default_branch.append(project_name)
                repo_failed_update_count += 1
                failed_repositories.append(project_name)
                continue

            # Get currently protected branches from repo_info
            protected_branch_names = set(branch["name"] for branch in repo_info.get("branches", []))

            # Check if all preferred_default_branch are already protected branches
            if preferred_default_branch in protected_branch_names:
                print(f"The {preferred_default_branch} is already protected in repo: {project_name}. Skipping...")
                continue

            try:
                print(f"Updating protected branches of {project_name}... Adding the default branch: {preferred_default_branch}")

                api_actions.update_project_repo_protected_branches(access_token, tenant_url, get_project_repo_endpoint, repo_info, project_id, [preferred_default_branch])
                
                print(f"Updated the protected branches of {project_name} with the default branch: {preferred_default_branch}")
                print(f"Timeout: {sleep_time} seconds...")

                time.sleep(sleep_time)
                repo_updated_count += 1

            except Exception as e:

                print(f"Error processing {project_name}: {e}")
                print(f"Failed to add {preferred_default_branch} to {project_name}")
                
                failed_repositories.append(project_name)
                repo_failed_update_count += 1
            
        try:
            # Renew access token after processing a batch
            access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)
            print("Access token renewed.")
        except Exception as e:
            print(f"Failed to renew token after batch {i + 1}: {e}")
            break

        if i + batch_size < len(cx_projects):  # Avoid sleeping after the last batch
            print(f"Processed {i + batch_size} projects. Waiting {batch_timeout} seconds before the next batch...")
            time.sleep(batch_timeout)  # Wait before processing the next batch

    # Final Summary
    print("Batch processing complete.")
    print(f"Total repositories updated: {repo_updated_count}")
    print(f"Total repositories failed: {repo_failed_update_count}")
    print(f"Failed Repositories: {failed_repositories}")

    # Print repos withouth main or master branch
    if repos_missing_default_branch:
        print("Repositories skipped due to missing 'main' or 'master' branches:")
        for repo in repos_missing_default_branch:
            print(f" - {repo}")

if __name__ == "__main__":
    main()