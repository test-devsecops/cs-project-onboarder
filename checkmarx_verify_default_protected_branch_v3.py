from utility.http_utility import HttpRequests
from utility.routes import Routes
from utility.config_utility import Config
from utility.api_actions import ApiActions
from utility.logger import Logger
from utility.csv_utility import Csv

from concurrent.futures import ThreadPoolExecutor, as_completed


import time
import datetime
import os

def process_project(cx_project, token, tenant_name, tenant_iam_url, tenant_url, routes, api_actions, log, counters, project_timeout):
    project_id = cx_project.get("id")
    project_name = cx_project.get("name")
    repo_id = cx_project.get("repoId")

    if not repo_id:
        log.warning(f"Project {project_name} has no repository ID.")
        counters['repo_failed_update_count'] += 1
        counters['failed_repositories'].append(project_name)
        return

    log.info(f"Processing project: {project_name}")

    try:
        get_project_repo_endpoint = routes.get_project_repo(repo_id)
        valid_token = api_actions.get_valid_token(token, tenant_iam_url, routes.get_access_token(tenant_name))
        repo_info = api_actions.get_project_repo_info(valid_token, tenant_url, get_project_repo_endpoint)

        get_repo_branches_endpoint = routes.get_repo_branches(repo_id)
        valid_token = api_actions.get_valid_token(token, tenant_iam_url, routes.get_access_token(tenant_name))
        available_repo_branches = api_actions.get_repo_branches(valid_token, tenant_url, get_repo_branches_endpoint)

        extracted_available_branches = {branch["name"] for branch in available_repo_branches.get("branchWebDtoList", [])}
        time.sleep(project_timeout)

    except Exception as e:
        log.error(f"Error fetching repo data for {project_name}: {e}")
        counters['failed_repositories'].append(project_name)
        counters['repo_failed_update_count'] += 1
        return

    preferred_default_branch = None
    if "main" in extracted_available_branches:
        preferred_default_branch = "main"
    elif "master" in extracted_available_branches:
        preferred_default_branch = "master"

    if not preferred_default_branch:
        log.skipped(f"Project '{project_name}' has neither 'main' nor 'master' branch.")
        counters['repos_missing_default_branch'].append(project_name)
        counters['repo_failed_update_count'] += 1
        return

    protected_branch_names = {branch["name"] for branch in (repo_info or {}).get("branches", [])}
    if preferred_default_branch in protected_branch_names:
        log.skipped(f"{preferred_default_branch} is already protected in repo: {project_name}.")
        time.sleep(project_timeout)
        return

    try:
        get_project_repo_endpoint = routes.get_project_repo(repo_id)
        log.info(f"Updating protected branches of {project_name}... Adding: {preferred_default_branch}")
        valid_token = api_actions.get_valid_token(token, tenant_iam_url, routes.get_access_token(tenant_name))
        api_actions.update_project_repo_protected_branches(valid_token, tenant_url, get_project_repo_endpoint, repo_info, project_id, [preferred_default_branch])

        log.info(f"Updated {project_name} with {preferred_default_branch}")
        counters['repo_updated_count'] += 1
        time.sleep(project_timeout)

    except Exception as e:
        log.error(f"Error updating {project_name}: {e}")
        counters['failed_repositories'].append(project_name)
        counters['repo_failed_update_count'] += 1

def main():
    httpRequest = HttpRequests()
    config = Config()
    log = Logger("verify_default_protected_branch")
    token, tenant_name, tenant_iam_url, tenant_url = config.get_config()

    routes = Routes()
    get_access_token_endpoint = routes.get_access_token(tenant_name)
    get_checkmarx_projects_endpoint = routes.get_checkmarx_projects()

    api_actions = ApiActions(httpRequest, logger=log)
    valid_token = api_actions.get_valid_token(token, tenant_iam_url, get_access_token_endpoint)
    cx_projects = api_actions.get_checkmarx_projects(valid_token, tenant_url, get_checkmarx_projects_endpoint)

    # Batch configuration
    batch_size = 100
    batch_timeout = 1.6  # seconds
    project_timeout = 1.1

    # Thread max workers
    thread_workers = 3

    # Tracking counters
    counters = {
        "repo_updated_count": 0,
        "repo_failed_update_count": 0,
        "failed_repositories": [],
        "repos_missing_default_branch": []
    }
    
    for batch_num, i in enumerate(range(0, len(cx_projects), batch_size), start=1):
        batch = cx_projects[i:i + batch_size]
        log.info(f"Processing Batch {batch_num} with {len(batch)} projects...")

        with ThreadPoolExecutor(max_workers=thread_workers) as executor:
            futures = [
                executor.submit(
                    process_project,
                    cx_project, token, tenant_name, tenant_iam_url, tenant_url, routes, api_actions, log, counters, project_timeout
                )
                for cx_project in batch
            ]
            for future in as_completed(futures):
                pass  # All logging and error handling is inside `process_project`

        if i + batch_size < len(cx_projects):
            log.info(f"Processed {i + batch_size} projects. Waiting {batch_timeout} seconds...")
            time.sleep(batch_timeout)

    # --- Final Summary ---
    print("\n=== Summary ===")
    print(f"Total repositories updated: {counters['repo_updated_count']}")
    print(f"Total repositories failed: {counters['repo_failed_update_count']}")
    
    if counters['repos_missing_default_branch']:
        print("Failed Repositories:")
        for repo in counters['failed_repositories']:
            print(f" - {repo}")

    if counters['repos_missing_default_branch']:
        print("Repositories missing 'main' or 'master':")
        for repo in counters['repos_missing_default_branch']:
            print(f" - {repo}")
    
    # Write summary + CSV
    csv_data = []
    fieldnames = ["repo_name", "status"]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY", "summary.txt")

    with open(summary_file, "a") as f:
        f.write("### Checkmarx Protected Branch Verification Summary\n\n")
        f.write(f"Total repositories updated: {counters['repo_updated_count']}\n")
        f.write(f"Total repositories failed: {counters['repo_failed_update_count']}\n\n")

        if counters['failed_repositories']:
            f.write("**Failed Repositories:**\n")
            for repo in counters['failed_repositories']:
                f.write(f"{repo}\n")
                csv_data.append({"repo_name": repo, "status": "failed"})

        if counters['repos_missing_default_branch']:
            f.write("\n**Repositories missing 'main' or 'master':**\n")
            for repo in counters['repos_missing_default_branch']:
                f.write(f"{repo}\n")
                csv_data.append({"repo_name": repo, "status": "missing_default_branch"})

    # Export to CSV using your utility
    if csv_data:
        Csv.extract_to_csv(csv_data, fieldnames, directory="./csv_files/", filename=f"{timestamp}_repos_summary")

if __name__ == "__main__":
    main()