from urllib.parse import urlencode
import requests
import base64
import sys
import json
from utility.exception_handler import ExceptionHandler

class ApiActions:

    def __init__(self, httpRequest):
        self.httpRequest = httpRequest

    @ExceptionHandler.handle_exception
    def get_access_token(self, token, base_url, endpoint):

        url = f"https://{base_url}{endpoint}"

        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "refresh_token",
            "client_id": "ast-app",
            "refresh_token": token
        }

        encoded_data = urlencode(data)

        response = self.httpRequest.post_api_request(url, headers, encoded_data)
        print("Successfully generated a token")

        return response.get("access_token")

    @ExceptionHandler.handle_exception
    def get_checkmarx_projects(self, token, base_url, endpoint, empty_tag="false", project_name=None):

        url = f"https://{base_url}{endpoint}"

        headers = {
            "accept": "application/json; version=1.0",
            "authorization": f"Bearer {token}",
            "Content-Type": "application/json; version=1.0"
        }

        limit = 100  
        offset = 0   
        all_projects = []

        while True:
            params = {
                "limit": limit,
                "offset": offset,
                "empty-tags": empty_tag
            }

            if project_name is not None:
                params["name-regex"] = f"(?i)^{project_name}$"

            response = self.httpRequest.get_api_request(url, headers=headers, params=params)

            if not response or "projects" not in response or not isinstance(response["projects"], list):
                print("Error: 'projects' key missing or not a list in API response")
                return None

            all_projects.extend(response["projects"])

            if len(response["projects"]) < limit:
                break  

            offset += limit

        return all_projects
    
    @ExceptionHandler.handle_exception
    def delete_checkmarx_project(self, token, base_url, endpoint):

        url = f"https://{base_url}{endpoint}"

        headers = {
            "accept": "application/json; version=1.0",
            "authorization": f"Bearer {token}",
            "Content-Type": "application/json; version=1.0"
        }

        response = self.httpRequest.delete_api_request(url, headers=headers)

        return response
    
    @ExceptionHandler.handle_exception
    def update_project_repo_protected_branches(self, token, base_url, endpoint, repo_info, project_id, new_branches):
        
        url = f"https://{base_url}{endpoint}"

        headers = {
            "accept": "application/json; version=1.0",
            "authorization": f"Bearer {token}",
            "Content-Type": "application/json; version=1.0"
        }

        params = {
            "projectId": project_id
        }

        payload = {
            "apiSecScannerEnabled": repo_info.get("apiSecScannerEnabled"),
            "branches": repo_info.get("branches"),
            "containerScannerEnabled": repo_info.get("containerScannerEnabled"),
            "isRepoAdmin": repo_info.get("isRepoAdmin"),
            "kicsScannerEnabled": repo_info.get("kicsScannerEnabled"),
            "ossfSecoreCardScannerEnabled": repo_info.get("ossfSecoreCardScannerEnabled"),
            "prDecorationEnabled": repo_info.get("prDecorationEnabled"),
            "sastIncrementalScan": repo_info.get("sastIncrementalScan"),
            "sastScannerEnabled": repo_info.get("sastScannerEnabled"),
            "scaAutoPrEnabled": repo_info.get("scaAutoPrEnabled"),
            "scaScannerEnabled": repo_info.get("scaScannerEnabled"),
            "secretsDerectionScannerEnabled": repo_info.get("secretsDerectionScannerEnabled"),
            "sshRepoUrl": repo_info.get("sshRepoUrl"),
            "sshState": "SKIPPED",
            "url": repo_info.get("url"),
            "webhookEnabled": repo_info.get("webhookEnabled"),
            "webhookId": repo_info.get("webhookId")
        }

        # Ensure branches list exists
        if "branches" not in payload:
            payload["branches"] = []

        # Convert existing branch names to a set for quick lookup
        existing_branch_names = {branch["name"] for branch in payload["branches"]}

        # Add new branches only if they are not already in the list
        for branch in new_branches:
            if branch not in existing_branch_names:
                payload["branches"].append({
                    "name": branch,
                    "isDefaultBranch": False
                })

        # Send updated repo configuration
        response = self.httpRequest.put_api_request(url, headers=headers, json=payload, params=params)
        return response

    @ExceptionHandler.handle_exception
    def get_repo_branches(self, token, base_url, endpoint):
        """
        Retrieve all available branches (including paginated results) for a repo.
        """

        url = f"https://{base_url}{endpoint}"

        headers = {
            "accept": "application/json; version=1.0",
            "authorization": f"Bearer {token}",
            "Content-Type": "application/json; version=1.0"
        }

        all_branches = []
        page = 1
        next_page = 1

        while True:
            params = {
                "page": page,
                "nextPageLink": next_page
            }

            response = self.httpRequest.get_api_request(url, headers=headers, params=params)

            if not response or "branchWebDtoList" not in response:
                break

            current_branches = response["branchWebDtoList"]
            all_branches.extend(current_branches)

            if not current_branches:
                break  # No more branches returned

            page += 1
            next_page += 1

        return {"branchWebDtoList": all_branches}
    
    @ExceptionHandler.handle_exception
    def get_project_repo_info(self, token, base_url, endpoint):
        # Use this function if you want to retrieve the list of protected branches
        
        url = f"https://{base_url}{endpoint}"

        headers = {
            "accept": "application/json; version=1.0",
            "authorization": f"Bearer {token}",
            "Content-Type": "application/json; version=1.0"
        }

        response = self.httpRequest.get_api_request(url, headers=headers)
        return response

    @ExceptionHandler.handle_exception
    def get_projects_by_tags(self, token, base_url, endpoint, tag, offset=0, limit=100):

        url = f"https://{base_url}{endpoint}"

        headers = {
            "accept": "application/json; version=1.0",
            "authorization": f"Bearer {token}",
            "Content-Type": "application/json; version=1.0"
        }

        params = {
            "tags-keys": tag,
            "limit": limit,
            "offset": offset
        }

        response = self.httpRequest.get_api_request(url, headers=headers, params=params)
        return response

    @ExceptionHandler.handle_exception
    def get_projects_through_searchbar(self, token, base_url, endpoint, search_term, offset=0, limit=100):

        url = f"https://{base_url}{endpoint}"

        headers = {
            'Authorization': f"Bearer {token}",
            'Accept': "application/json; version=1.0",
            'Content-Type': "application/json; version=1.0",
            'User-Agent': "python-requests/2.32.3"
        }

        params = {
            "search": search_term,
            "limit": limit,
            "offset": offset,
            "sort": "+last-scan-date"
        }

        response = self.httpRequest.get_api_request(url, headers=headers, params=params)
        return response

    @ExceptionHandler.handle_exception
    def replace_project_tags(self, token, base_url, endpoint, project, tags_dict):
        
        url = f"https://{base_url}{endpoint}"

        headers = {
            "accept": "application/json; version=1.0",
            "authorization": f"Bearer {token}",
            "Content-Type": "application/json; version=1.0"
        }

        project_tags = tags_dict

        payload = {
            "tags": project_tags
        }

        response = self.httpRequest.put_api_request(url, headers=headers, json=payload)
        return response

    @ExceptionHandler.handle_exception
    def update_project_tags_and_criticality(self, token, base_url, endpoint, project, criticality, tags_dict):
        
        url = f"https://{base_url}{endpoint}"

        headers = {
            "accept": "application/json; version=1.0",
            "authorization": f"Bearer {token}",
            "Content-Type": "application/json; version=1.0"
        }

        project_tags = project["tags"]
        project_tags.update(tags_dict)

        payload = {
            "name": project["name"],
            "tags": project_tags,
            "groups": project["groups"],
            "criticality": project["criticality"] if not criticality else criticality,
            "repoUrl": project["repoUrl"],
            "mainBranch": project["mainBranch"]
        }

        response = self.httpRequest.put_api_request(url, headers=headers, json=payload)
        return response
    
    def update_application_tags_and_criticality(self, token, base_url, endpoint, criticality, tags_dict):
        
        url = f"https://{base_url}{endpoint}"

        headers = {
            "accept": "application/json; version=1.0",
            "authorization": f"Bearer {token}",
            "Content-Type": "application/json; version=1.0"
        }

        payload = {
            "criticality": criticality,
            "tags": tags_dict
        }

        response = self.httpRequest.put_api_request(url, headers=headers, json=payload)
        return response

    @ExceptionHandler.handle_exception
    def create_application(self, token, base_url, endpoint, app_name, tags_dict, criticality):

        url = f"https://{base_url}{endpoint}"

        headers = {
            "accept": "application/json; version=1.0",
            "authorization": f"Bearer {token}",
            "Content-Type": "application/json; version=1.0"
        }

        payload = {
            "name": app_name,
            "criticality": criticality,
            "tags": tags_dict
        }

        response = self.httpRequest.post_api_request(url, headers=headers, json=payload)
        return response

    @ExceptionHandler.handle_exception
    def add_projects_to_application(self, token, base_url, endpoint, project_ids):

        url = f"https://{base_url}{endpoint}"

        headers = {
            "accept": "application/json; version=1.0",
            "authorization": f"Bearer {token}",
            "Content-Type": "application/json; version=1.0"
        }

        payload = {
            "projectIds": project_ids
        }

        response = self.httpRequest.post_api_request(url, headers=headers, json=payload)
        return response

    @ExceptionHandler.handle_exception_with_retries()
    def get_application_by_name(self, token, base_url, endpoint, app_name):
        
        url = f"https://{base_url}{endpoint}"

        headers = {
            "accept": "application/json; version=1.0",
            "authorization": f"Bearer {token}",
            "Content-Type": "application/json; version=1.0"
        }

        params = {
            "name": app_name
        }

        response = self.httpRequest.get_api_request(url, headers=headers, params=params)
        return response

    @ExceptionHandler.handle_exception
    def get_application_by_id(self, token, base_url, endpoint):
        
        url = f"https://{base_url}{endpoint}"

        headers = {
            "accept": "application/json; version=1.0",
            "authorization": f"Bearer {token}",
            "Content-Type": "application/json; version=1.0"
        }

        response = self.httpRequest.get_api_request(url, headers=headers)
        return response

    @ExceptionHandler.handle_exception
    def get_application_by_tag(self, token, base_url, endpoint, tag):

        url = f"https://{base_url}{endpoint}"

        headers = {
            "accept": "application/json; version=1.0",
            "authorization": f"Bearer {token}",
            "Content-Type": "application/json; version=1.0"
        }

        params = {
            "tags-keys": tag
        }

        response = self.httpRequest.get_api_request(url, headers=headers, params=params)
        return response

    @ExceptionHandler.handle_exception
    def get_client_by_client_name(self, token, base_url, endpoint, client_name):
        
        url = f"https://{base_url}{endpoint}"

        headers = {
            'Authorization': f"Bearer {token}",
            'Accept': "application/json; version=1.0",
            'Content-Type': "application/json; version=1.0",
            'User-Agent': "python-requests/2.32.3"
        }

        params = {
            'clientId': client_name
        }

        response = self.httpRequest.get_api_request(url, headers=headers, params=params)
        return response

    @ExceptionHandler.handle_exception
    def get_role(self, token, base_url, endpoint, role):

        url = f"https://{base_url}{endpoint}{role}"

        headers = {
            'Authorization': f"Bearer {token}",
            'Accept': "application/json; version=1.0",
            'Content-Type': "application/json; version=1.0",
            'User-Agent': "python-requests/2.32.3"
        }

        response = self.httpRequest.get_api_request(url, headers=headers)
        return response

    @ExceptionHandler.handle_exception
    def get_group(self, token, base_url, endpoint, group=None):

        url = f"https://{base_url}{endpoint}"

        headers = {
            'Authorization': f"Bearer {token}",
            'Accept': "application/json; version=1.0",
            'Content-Type': "application/json; version=1.0",
            'User-Agent': "python-requests/2.32.3"
        }

        params = None

        if group:
            params = {
                'exact': 'true',
                'search': group
            }

        response =  self.httpRequest.get_api_request(url, headers=headers, params=params)
        return response
    
    @ExceptionHandler.handle_exception
    def create_group(self, token, base_url, endpoint, group):

        url = f"https://{base_url}{endpoint}"

        headers = {
            'Authorization': f"Bearer {token}",
            'Accept': "application/json; version=1.0",
            'Content-Type': "application/json; version=1.0",
            'User-Agent': "python-requests/2.32.3"
        }

        payload = {
            'name': group
        }

        response = requests.post(url, headers=headers, json=payload)
        return response

    @ExceptionHandler.handle_exception
    def assign_group_role(self, token, base_url, endpoint, role_id, role):
        
        url = f"https://{base_url}{endpoint}"

        headers = {
            'Authorization': f"Bearer {token}",
            'Accept': "application/json; version=1.0",
            'Content-Type': "application/json; version=1.0",
            'User-Agent': "python-requests/2.32.3"
        }

        payload = [{
            'id': role_id,
            'name': role
        }]

        response = self.httpRequest.post_api_request(url, headers=headers, json=payload)
        return response

    @ExceptionHandler.handle_exception
    def assign_group_to_resource(self, token, base_url, endpoint, group_id, resource_id, resource_type):

        url = f"https://{base_url}{endpoint}"

        headers = {
            'Authorization': f"Bearer {token}",
            'Accept': "application/json; version=1.0",
            'Content-Type': "application/json; version=1.0",
            'User-Agent': "python-requests/2.32.3"
        }

        payload = {
            'entityID': group_id,
            'entityType': 'group',
            'resourceID': resource_id,
            'resourceType': resource_type
        }

        response = self.httpRequest.post_api_request(url, headers=headers, json=payload)
        return response

    @ExceptionHandler.handle_exception
    def get_identity_providers(self, token, base_url, endpoint):

        url = f"https://{base_url}{endpoint}"

        headers = {
            'Authorization': f"Bearer {token}",
            'Accept': "application/json; version=1.0",
            'Content-Type': "application/json; version=1.0",
            'User-Agent': "python-requests/2.32.3"
        }

        response =  self.httpRequest.get_api_request(url, headers=headers)
        return response

    @ExceptionHandler.handle_exception
    def create_mapper(self, token, base_url, endpoint, group_name, idp_alias):

        url = f"https://{base_url}{endpoint}"

        headers = {
            'Authorization': f"Bearer {token}",
            'Accept': "application/json; version=1.0",
            'Content-Type': "application/json; version=1.0",
            'User-Agent': "python-requests/2.32.3"
        }
        
        payload = {
            "name": group_name,
            "identityProviderAlias": idp_alias,
            "identityProviderMapper": "saml-groups-idp-mapper",
            "config": {
                "attribute.groups": "/" + group_name,
                "attribute.name": "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
                "attribute.value": group_name,
                "syncMode": "INHERIT",
                "attribute.groups.creation": "",
                "override.user.groups": False
            }
        }

        response = self.httpRequest.post_api_request(url, headers=headers, json=payload)
        return response
