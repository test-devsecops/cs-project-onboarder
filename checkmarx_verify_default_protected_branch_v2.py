from utility.http_utility import HttpRequests
from utility.routes import Routes
from utility.config_utility import Config
from utility.api_actions import ApiActions
from utility.access_token_manager import AccessTokenManager

from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def process_project(cx_project, token_manager, routes, tenant_url, api_actions, sleep_time, counters):
    project_id = cx_project.get("id")
    project_name = cx_project.get("name")
    repo_id = cx_project.get("repoId")

    if not repo_id:
        print(f"Project {project_name} has no repository ID.")
        counters["repo_failed_update_count"] += 1
        counters["failed_repositories"].append(project_name)
        return

    print(f"Getting data of the project repo: {project_name}")
    get_project_repo_endpoint = routes.get_project_repo(repo_id)

    try:
        # Get repo info
        repo_info = token_manager.request_with_retry(
            api_actions.get_project_repo_info, tenant_url, get_project_repo_endpoint
        )

        # Get available branches
        get_repo_branches_endpoint = routes.get_repo_branches(repo_id)
        available_repo_branches = token_manager.request_with_retry(
            api_actions.get_repo_branches, tenant_url, get_repo_branches_endpoint
        )
        extracted_available_branches = set(branch["name"] for branch in available_repo_branches["branchWebDtoList"])

    except Exception as e:
        print(f"Error processing {project_name}: {e}")
        print(f"Failed to get the available branches of {project_name}")
        counters["failed_repositories"].append(project_name)
        counters["repo_failed_update_count"] += 1
        return

    # Determine preferred default branch
    preferred_default_branch = None
    if "main" in extracted_available_branches:
        preferred_default_branch = "main"
    elif "master" in extracted_available_branches:
        preferred_default_branch = "master"
    else:
        print(f"Project '{project_name}' has neither 'main' nor 'master' branch. Skipping...")
        counters["repos_missing_default_branch"].append(project_name)
        counters["repo_failed_update_count"] += 1
        counters["failed_repositories"].append(project_name)
        return

    # Get currently protected branches
    protected_branch_names = set(branch["name"] for branch in repo_info.get("branches", []))

    if preferred_default_branch in protected_branch_names:
        print(f"The {preferred_default_branch} is already protected in repo: {project_name}. Skipping...")
        return

    try:
        print(f"Updating protected branches of {project_name}... Adding the default branch: {preferred_default_branch}")

        token_manager.request_with_retry(api_actions.update_project_repo_protected_branches,tenant_url,get_project_repo_endpoint,repo_info,project_id,[preferred_default_branch])

        print(f"Updated the protected branches of {project_name} with the default branch: {preferred_default_branch}")
        print(f"Timeout: {sleep_time} seconds...")
        time.sleep(sleep_time)
        counters["repo_updated_count"] += 1

    except Exception as e:
        print(f"Error processing {project_name}: {e}")
        print(f"Failed to add {preferred_default_branch} to {project_name}")
        counters["failed_repositories"].append(project_name)
        counters["repo_failed_update_count"] += 1


def main():
    httpRequest = HttpRequests()
    config = Config()
    token, tenant_name, tenant_iam_url, tenant_url = config.get_config()

    routes = Routes()
    api_actions = ApiActions(httpRequest)

    # Thread-safe AccessTokenManager
    token_manager = AccessTokenManager(
        api_actions, token, tenant_iam_url, routes.get_access_token(tenant_name)
    )

    cx_projects = token_manager.request_with_retry(
        api_actions.get_checkmarx_projects, tenant_url, routes.get_checkmarx_projects()
    )

    sleep_time = 0

    # Tracking counters
    counters = {
        "repo_updated_count": 0,
        "repo_failed_update_count": 0,
        "failed_repositories": [],
        "repos_missing_default_branch": []
    }

    max_threads = 5

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {
            executor.submit(process_project, cx_project, token_manager, routes, tenant_url, api_actions, sleep_time, counters): cx_project
            for cx_project in cx_projects
        }

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                cx_project = futures[future]
                print(f"Thread error for project {cx_project.get('name')}: {e}")

    with open("summary.txt", "w") as f:
        f.write("=== Summary ===\n")
        f.write(f"Total repositories updated: {counters['repo_updated_count']}\n")
        f.write(f"Total repositories failed: {counters['repo_failed_update_count']}\n")
        
        if counters['failed_repositories']:
            f.write("Failed Repositories:\n")
            for repo in counters['failed_repositories']:
                f.write(f" - {repo}\n")
        
        if counters['repos_missing_default_branch']:
            f.write("Repositories missing 'main' or 'master':\n")
            for repo in counters['repos_missing_default_branch']:
                f.write(f" - {repo}\n")

if __name__ == "__main__":
    main()
