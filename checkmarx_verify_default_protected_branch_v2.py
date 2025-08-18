from utility.http_utility import HttpRequests
from utility.routes import Routes
from utility.config_utility import Config
from utility.api_actions import ApiActions

import time
import requests

def safe_api_call(func, retries=3, backoff=2, *args, **kwargs):
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code >= 500:
                print(f"Server error, retrying... attempt {attempt+1}/{retries}")
                time.sleep(backoff * (attempt + 1))
            else:
                raise
    raise Exception("Max retries reached")

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

    project_success_update_count = 0
    project_failed_update_count = 0

    failed_projects = []
    repos_missing_default_branch = []

    # Optimized batch config
    batch_size = 200
    batch_timeout = 10

    repo_branches_cache = {}

    for i in range(0, len(cx_projects), batch_size):
        batch = cx_projects[i:i + batch_size]

        for cx_project in batch:
            try:
                project_id = cx_project.get("id")
                project_name = cx_project.get("name")
                repo_id = cx_project.get("repoId")
                project_main_branch = cx_project.get("mainBranch")

                # Skip if already main/master
                if project_main_branch in ("main", "master"):
                    continue

                # Get branches (with caching + retry)
                if repo_id in repo_branches_cache:
                    available_repo_branches = repo_branches_cache[repo_id]
                else:
                    get_repo_branches_endpoint = routes.get_repo_branches(repo_id)
                    available_repo_branches = safe_api_call(
                        api_actions.get_repo_branches, 3, 2, access_token, tenant_url, get_repo_branches_endpoint
                    )
                    repo_branches_cache[repo_id] = available_repo_branches

                # Default primary branch
                primary_branch = "main"

                if available_repo_branches and "branchWebDtoList" in available_repo_branches:
                    extracted_available_branches = set(branch["name"] for branch in available_repo_branches["branchWebDtoList"])

                    if "main" in extracted_available_branches:
                        primary_branch = "main"
                    elif "master" in extracted_available_branches:
                        primary_branch = "master"
                    else:
                        repos_missing_default_branch.append(project_name)
                        project_failed_update_count += 1
                        failed_projects.append(project_name)
                        continue
                else:
                    continue

                # Update only if needed
                if primary_branch == project_main_branch:
                    continue

                update_project_primary_branch_endpoint = routes.update_projects(project_id)
                safe_api_call(
                    api_actions.update_project_primary_branch, 3, 2,
                    access_token, tenant_url, update_project_primary_branch_endpoint, cx_project, primary_branch
                )
                project_success_update_count += 1

            except Exception as e:
                failed_projects.append(project_name)
                project_failed_update_count += 1

        # Renew token only if older than 55 min (instead of every batch)
        if (i // batch_size) % 55 == 0:
            access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)

        if i + batch_size < len(cx_projects):
            time.sleep(batch_timeout)

    print("Completed.")
    print(f"Total Updated Projects: {project_success_update_count}")
    print(f"Total Project failed to update: {project_failed_update_count}")
    
    if repos_missing_default_branch:
        print("Repositories skipped due to missing 'main' or 'master' branches:")
        for repo in repos_missing_default_branch:
            print(f" - {repo}")

if __name__ == "__main__":
    main()
