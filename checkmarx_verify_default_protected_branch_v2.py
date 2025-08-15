from utility.http_utility import HttpRequests
from utility.routes import Routes
from utility.config_utility import Config
from utility.api_actions import ApiActions

from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading

# === Configurable settings ===
MAX_WORKERS = 20            # How many projects to process in parallel
MAX_REQUESTS_PER_SECOND = 8 # API rate limit safety
TOKEN_EXPIRY_BUFFER = 3500  # Seconds before we refresh token

# === Rate limiting control ===
last_request_times = []
rate_lock = threading.Lock()

def rate_limited():
    """Ensure we don't exceed MAX_REQUESTS_PER_SECOND."""
    with rate_lock:
        now = time.time()
        last_request_times.append(now)

        # Keep only requests in the last second
        while last_request_times and last_request_times[0] < now - 1:
            last_request_times.pop(0)

        if len(last_request_times) > MAX_REQUESTS_PER_SECOND:
            sleep_time = 1 - (now - last_request_times[0])
            time.sleep(max(0, sleep_time))


def main():
    httpRequest = HttpRequests()
    config = Config()
    token, tenant_name, tenant_iam_url, tenant_url = config.get_config()

    routes = Routes()
    get_access_token_endpoint = routes.get_access_token(tenant_name)
    get_checkmarx_projects_endpoint = routes.get_checkmarx_projects()

    api_actions = ApiActions(httpRequest)

    # Initial token fetch
    print("[INFO] Getting initial access token...")
    access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)
    token_expiry_time = time.time() + TOKEN_EXPIRY_BUFFER

    print("[INFO] Fetching project list...")
    cx_projects = api_actions.get_checkmarx_projects(access_token, tenant_url, get_checkmarx_projects_endpoint)
    print(f"[INFO] Found {len(cx_projects)} projects.")

    repo_updated_count = 0
    repo_failed_update_count = 0
    failed_repositories = []
    repos_missing_default_branch = []

    # Lock for token refresh
    token_lock = threading.Lock()

    def refresh_token_if_needed():
        nonlocal access_token, token_expiry_time
        if time.time() >= token_expiry_time:
            with token_lock:
                if time.time() >= token_expiry_time:
                    print("[INFO] Refreshing access token...")
                    rate_limited()
                    access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)
                    token_expiry_time = time.time() + TOKEN_EXPIRY_BUFFER

    def process_project(cx_project):
        nonlocal repo_updated_count, repo_failed_update_count

        project_id = cx_project.get("id")
        project_name = cx_project.get("name")
        repo_id = cx_project.get("repoId")

        if not repo_id:
            repo_failed_update_count += 1
            failed_repositories.append(project_name)
            return f"[SKIP] {project_name} - No repo ID"

        try:
            refresh_token_if_needed()
            rate_limited()
            available_repo_branches = api_actions.get_repo_branches(
                access_token, tenant_url, routes.get_repo_branches(repo_id)
            )
            extracted_available_branches = {b["name"] for b in available_repo_branches["branchWebDtoList"]}
        except Exception as e:
            repo_failed_update_count += 1
            failed_repositories.append(project_name)
            return f"[ERROR] {project_name} - Cannot fetch branches: {e}"

        preferred_branch = None
        if "main" in extracted_available_branches:
            preferred_branch = "main"
        elif "master" in extracted_available_branches:
            preferred_branch = "master"
        else:
            repos_missing_default_branch.append(project_name)
            repo_failed_update_count += 1
            failed_repositories.append(project_name)
            return f"[SKIP] {project_name} - No main/master branch"

        try:
            refresh_token_if_needed()
            rate_limited()
            repo_info = api_actions.get_project_repo_info(
                access_token, tenant_url, routes.get_project_repo(repo_id)
            )
            protected_branch_names = {b["name"] for b in repo_info.get("branches", [])}

            if preferred_branch in protected_branch_names:
                return f"[SKIP] {project_name} - Already protected"

            rate_limited()
            api_actions.update_project_repo_protected_branches(
                access_token, tenant_url, routes.get_project_repo(repo_id),
                repo_info, project_id, [preferred_branch]
            )
            repo_updated_count += 1
            return f"[OK] {project_name} - Protected branch set to {preferred_branch}"

        except Exception as e:
            repo_failed_update_count += 1
            failed_repositories.append(project_name)
            return f"[ERROR] {project_name} - Update failed: {e}"

    # Process in parallel
    print("[INFO] Starting parallel processing...")
    results = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_project, p) for p in cx_projects]
        for future in as_completed(futures):
            results.append(future.result())

    # Print per-project results
    for r in results:
        print(r)

    elapsed = time.time() - start_time
    print("\n=== Summary ===")
    print(f"Total repositories updated: {repo_updated_count}")
    print(f"Total repositories failed: {repo_failed_update_count}")
    print(f"Failed Repositories: {failed_repositories}")
    if repos_missing_default_branch:
        print("Repositories missing 'main' or 'master':")
        for repo in repos_missing_default_branch:
            print(f" - {repo}")
    print(f"Total runtime: {elapsed:.2f} seconds")


if __name__ == "__main__":
    main()