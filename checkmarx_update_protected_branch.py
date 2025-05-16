from utility.http_utility import HttpRequests
from utility.routes import Routes
from utility.config_utility import Config
from utility.csv_utility import Csv
from utility.api_actions import ApiActions
from utility.logger import Logger

from collections import defaultdict
from itertools import islice
from datetime import datetime

import os
import sys
import argparse
import re
import time

def batch_dict(d, batch_size):
    it = iter(d.items())
    while True:
        batch = dict(islice(it, batch_size))
        if not batch:
            break
        yield batch

def export_failed_repos_to_csv(failed_repos):

    if not failed_repos:
        print("No failed repositories to export.")
        return

    fieldnames = ["repository"]
    data_list = [{"repository": repo} for repo in failed_repos]

    Csv.extract_to_csv(data_list, fieldnames, directory="./csv_files/protected_branches/error/", filename="failed_repositories")

def generate_protected_branches_list(repo_names, branches, in_scope_values):
    """Generates a list of dictionaries for protected branches using separate column data."""
    
    branch_list = []
    
    # Ensure all lists have the same length
    for i in range(len(repo_names)):
        repo_name = repo_names[i].strip()
        branch = branches[i].strip()
        in_scope = in_scope_values[i].strip() if i < len(in_scope_values) else "NO"  # Default to "NO" if missing
        
        branch_list.append({
            "repo_name": repo_name,
            "branch": branch,
            "in_scope": in_scope
        })
    
    return branch_list

def group_protected_branches(protected_branches):
    """Groups branches by repo_name, keeping only branches marked as in_scope = 'YES'."""
    
    grouped_repos = defaultdict(list)
    
    for entry in protected_branches:
        repo_name = entry["repo_name"]
        branch = entry["branch"]
        in_scope = entry["in_scope"].upper()

        if in_scope == "YES":  # Only add branches marked as 'YES'
            grouped_repos[repo_name].append(branch)

    return dict(grouped_repos)  # Convert defaultdict to normal dict

def main(filename):

    httpRequest = HttpRequests()

    config = Config()
    token, tenant_name, tenant_iam_url, tenant_url = config.get_config()

    routes = Routes()
    get_access_token_endpoint = routes.get_access_token(tenant_name)
    get_checkmarx_projects_endpoint = routes.get_checkmarx_projects()

    api_actions = ApiActions(httpRequest)
    access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)

    logger = Logger(filename)
    
    protected_branches_file_path = f"./csv_files/protected_branches/{filename}"

    repo_names = Csv.read_csv(protected_branches_file_path, column_index=0)
    branches = Csv.read_csv(protected_branches_file_path, column_index=1)
    in_scope_values = Csv.read_csv(protected_branches_file_path, column_index=2)

    protected_branches = generate_protected_branches_list(repo_names, branches, in_scope_values)
    grouped_repos = group_protected_branches(protected_branches)

    # Batch configuration
    batch_size = 100
    batch_timeout = 60  # seconds
    batches = list(batch_dict(grouped_repos, batch_size))
    total_batches = len(batches)

    # Tracking counters
    repo_updated_count = 0
    repo_failed_update_count = 0

    failed_repositories = []

    # Process each batch
    for idx, batch in enumerate(batches):
        logger.info(f"Processing batch {idx + 1}/{total_batches} at {datetime.now()}")

        for repo_name, branch_list in batch.items():
            try:
                cx_projects = api_actions.get_checkmarx_projects(access_token, tenant_url, get_checkmarx_projects_endpoint, project_name=repo_name)

                if not cx_projects:
                    logger.error(f"No Checkmarx project found for {repo_name}")
                    repo_failed_update_count += 1
                    failed_repositories.append(repo_name)
                    continue

                cx_project = cx_projects[0]
                project_id = cx_project.get("id")
                project_name = cx_project.get("name")
                repo_id = cx_project.get("repoId")

                if not repo_id:
                    logger.error(f"Project {project_name} has no repository ID.")
                    repo_failed_update_count += 1
                    failed_repositories.append(repo_name)
                    continue

                print(f"Getting data of the project repo: {project_name}")
                get_project_repo_endpoint = routes.get_project_repo(repo_id)
                repo_info = api_actions.get_project_repo_info(access_token, tenant_url, get_project_repo_endpoint)

                # Get the repo branches that are available to be set as protected branches - these are not necessarily protected branches though they could be protected branches already.
                get_repo_branches_endpoint = routes.get_repo_branches(repo_id)
                available_repo_branches = api_actions.get_repo_branches(access_token, tenant_url, get_repo_branches_endpoint)
                extracted_available_branches = set(branch["name"] for branch in available_repo_branches["branchWebDtoList"])
                
                # Identify branches that ARE in the extracted_available_branches list
                new_branches = [branch for branch in branch_list if branch in extracted_available_branches]

                # Get currently protected branches from repo_info
                protected_branch_names = set(branch["name"] for branch in repo_info.get("branches", []))

                if not new_branches:
                    print(f"No new branches specified for repo: {project_name}. Skipping...")
                    logger.info(f"No new branches specified for repo: {project_name}. Skipping...")
                    continue
                
                # Check if all new_branches are already protected branches
                if set(new_branches).issubset(protected_branch_names):
                    print(f"All branches in {new_branches} are already protected in repo: {project_name}. Skipping...")
                    logger.info(f"All branches in {new_branches} are already protected in repo: {project_name}. Skipping...")
                    continue

                print(f"Updating protected branches of {project_name}... Adding new branches: {new_branches}")
                logger.info(f"Updating protected branches of {project_name}... Adding new branches: {new_branches}")

                api_actions.update_project_repo_protected_branches(access_token, tenant_url, get_project_repo_endpoint, repo_info, project_id, new_branches)
                
                print(f"Updated the protected branches of {project_name} with new branches: {new_branches}")
                logger.info(f"Updated the protected branches of {project_name} with new branches: {new_branches}")

                print("Timeout: 3 seconds...")
                time.sleep(3)
                repo_updated_count += 1
                
            except Exception as e:
                logger.error(f"Error processing {repo_name}: {e}")
                logger.error(f"Failed to add {new_branches} to {repo_name}")

                print(f"Error processing {repo_name}: {e}")
                print(f"Failed to add {new_branches} to {repo_name}")
                
                failed_repositories.append(repo_name)
                repo_failed_update_count += 1

        try:
            access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)
        except Exception as e:
            logger.error(f"Failed to renew token after batch {idx + 1}: {e}")
            print(f"Failed to renew token after batch {idx + 1}: {e}")
            break

        if idx + 1 < total_batches:
            logger.info(f"Sleeping for {batch_timeout} seconds before next batch...")
            print(f"Sleeping for {batch_timeout} seconds before next batch...")
            time.sleep(batch_timeout)

    # Final Summary
    logger.info("Batch processing complete.")
    logger.info(f"Total repositories updated: {repo_updated_count}")
    logger.info(f"Total repositories failed: {repo_failed_update_count}")

    print("Batch processing complete.")
    print(f"Total repositories updated: {repo_updated_count}")
    print(f"Total repositories failed: {repo_failed_update_count}")
    print(f"Logs available here {logger.get_log_file_path()}")

    export_failed_repos_to_csv(failed_repositories)

if __name__ == "__main__":
    # Define command-line arguments
    parser = argparse.ArgumentParser(description='Update protected branches')
    parser.add_argument('-filename', help='filename of the protected branches',required=True)

    # Parse the command-line arguments
    args = parser.parse_args()

    # Call the main function with the provided exlusions and LBU
    main(args.filename)