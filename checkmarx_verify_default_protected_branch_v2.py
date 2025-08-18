from utility.http_utility import HttpRequests
from utility.routes import Routes
from utility.config_utility import Config
from utility.api_actions import ApiActions

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_repo(cx_project, access_token, tenant_url, routes, api_actions):
    project_id = cx_project.get("id")
    project_name = cx_project.get("name")
    repo_id = cx_project.get("repoId")
    
    if not repo_id:
        return project_name, "missing_repo_id", access_token

    try:
        get_project_repo_endpoint = routes.get_project_repo(repo_id)
        repo_info = api_actions.get_project_repo_info(access_token, tenant_url, get_project_repo_endpoint)

        get_repo_branches_endpoint = routes.get_repo_branches(repo_id)
        available_repo_branches = api_actions.get_repo_branches(access_token, tenant_url, get_repo_branches_endpoint)
        extracted_available_branches = set(branch["name"] for branch in available_repo_branches["branchWebDtoList"])

        # Determine preferred default branch
        preferred_default_branch = None
        if "main" in extracted_available_branches:
            preferred_default_branch = "main"
        elif "master" in extracted_available_branches:
            preferred_default_branch = "master"
        else:
            return project_name, "missing_default_branch", access_token

        protected_branch_names = set(branch["name"] for branch in repo_info.get("branches", []))
        
        # Skip if already protected
        if protected_branch_names & {"main", "master"}:
            return project_name, "already_protected", access_token

        # Update the repo to protect the preferred branch
        api_actions.update_project_repo_protected_branches(
            access_token, tenant_url, get_project_repo_endpoint, repo_info, project_id, [preferred_default_branch]
        )
        return project_name, "updated", access_token

    except Exception as e:
        # If unauthorized, renew token
        if hasattr(e, 'status_code') and e.status_code == 401:
            token, tenant_name, tenant_iam_url, _ = Config().get_config()
            access_token = api_actions.get_access_token(token, tenant_iam_url, routes.get_access_token(tenant_name))
            # Retry once
            return process_repo(cx_project, access_token, tenant_url, routes, api_actions)
        return project_name, "failed_update", access_token

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

    batch_size = 100
    batch_timeout = 1

    repo_updated_count = 0
    repo_failed_update_count = 0
    failed_repositories = []
    repos_missing_default_branch = []

    for i in range(0, len(cx_projects), batch_size):
        batch = cx_projects[i:i + batch_size]

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(process_repo, project, access_token, tenant_url, routes, api_actions)
                       for project in batch]

            for future in as_completed(futures):
                project_name, status, access_token = future.result()
                if status == "updated":
                    repo_updated_count += 1
                    print(f"Updated repository: {project_name}")
                elif status == "missing_repo_id":
                    repo_failed_update_count += 1
                    failed_repositories.append(project_name)
                    print(f"Missing repository ID for project: {project_name}")
                elif status == "missing_default_branch":
                    repo_failed_update_count += 1
                    failed_repositories.append(project_name)
                    repos_missing_default_branch.append(project_name)
                    print(f"No 'main' or 'master' branch for project: {project_name}")
                elif status == "already_protected":
                    print(f"Default branch already protected: {project_name}")
                else:  # failed_update
                    repo_failed_update_count += 1
                    failed_repositories.append(project_name)
                    print(f"Failed to update repository: {project_name}")

        if i + batch_size < len(cx_projects):
            print(f"Processed {i + batch_size} projects. Waiting {batch_timeout} seconds before next batch...")
            time.sleep(batch_timeout)

    # Final Summary
    # print("\nBatch processing complete.")
    # print(f"Total repositories updated: {repo_updated_count}")
    # print(f"Total repositories failed: {repo_failed_update_count}")
    # if failed_repositories:
    #     print("Failed Repositories:")
    #     for repo in failed_repositories:
    #         print(f" - {repo}")

    # if repos_missing_default_branch:
    #     print("\nRepositories skipped due to missing 'main' or 'master' branches:")
    #     for repo in repos_missing_default_branch:
    #         print(f" - {repo}")

    # Save summary to file
    with open("summary.txt", "w") as f:
        f.write("=== Summary ===\n")
        f.write(f"Total repositories updated: {repo_updated_count}\n")
        f.write(f"Total repositories failed: {repo_failed_update_count}\n")
        f.write(f"Failed Repositories: {failed_repositories}\n")
        if repos_missing_default_branch:
            f.write("Repositories missing 'main' or 'master':\n")
            for repo in repos_missing_default_branch:
                f.write(f" - {repo}\n")


if __name__ == "__main__":
    main()
