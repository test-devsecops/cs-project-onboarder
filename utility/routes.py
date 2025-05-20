class Routes:

    def get_access_token(self, tenant_name):
        endpoint = f"/auth/realms/{tenant_name}/protocol/openid-connect/token"
        return endpoint

    def get_checkmarx_projects(self):
        endpoint = "/api/projects/"
        return endpoint

    def get_project_last_scan(self):
        endpoint = "/api/projects/last-scan"
        return endpoint
    
    def start_scans(self):
        endpoint = "/api/scans/"
        return endpoint

    def get_scans(self):
        endpoint = "/api/scans/"
        return endpoint

    def get_scan_details(self, scan_id):
        endpoint = f"/api/scans/{scan_id}"
        return endpoint

    # Use this route/endpint if you want to retrieve the list of protected branches.
    def get_project_repo(self, repo_id):
        endpoint = f"/api/repos-manager/repo/{repo_id}"
        return endpoint

    # Use this route/endpint if you want to retrieve the list of scanned branches.
    def get_project_branches(self):
        endpoint = "/api/projects/branches"
        return endpoint

    # Use this route/endpint if you want to retrieve the list of branches available to be set as protected branches.
    def get_repo_branches(self, repo_id):
        endpoint = f"/api/repos-manager/repos/{repo_id}/branches"
        return endpoint

    def get_repos_by_project_id(self, project_id):
        endpoint = f"/api/insights/project/{project_id}"
        return endpoint

    def get_repo_insights(self):
        endpoint = "/api/insights/repository"
        return endpoint

    def get_project(self, project_id):
        endpoint = f"/api/projects/{project_id}"
        return endpoint

    def delete_project(self, project_id):
        endpoint = f"/api/projects/{project_id}"
        return endpoint
    
    def update_projects(self, project_id):
        endpoint = f"/api/projects/{project_id}"
        return endpoint

    def create_application(self):
        endpoint = "/api/applications/"
        return endpoint

    def get_application(self):
        endpoint = "/api/applications/"
        return endpoint

    def get_application_by_id(self, application_id):
        endpoint = f"/api/applications/{application_id}"
        return endpoint
    
    def update_application(self, application_id):
        endpoint = f"/api/applications/{application_id}"
        return endpoint

    def create_app_rule(self, application_id):
        endpoint = f"/api/applications/{application_id}/projects"
        return endpoint

    def get_client(self, tenant_name):
        endpoint = f"/auth/admin/realms/{tenant_name}/clients"
        return endpoint

    def get_role(self, tenant_name, client_id):
        endpoint = f"/auth/admin/realms/{tenant_name}/clients/{client_id}/roles/"
        return endpoint

    def get_group(self, tenant_name):
        endpoint = f"/auth/admin/realms/{tenant_name}/groups"
        return endpoint
    
    def create_group(self, tenant_name):
        endpoint = f"/auth/admin/realms/{tenant_name}/groups"
        return endpoint

    def assign_group_role(self, tenant_name, group_id, client_id):
        endpoint = f"/auth/admin/realms/{tenant_name}/groups/{group_id}/role-mappings/clients/{client_id}"
        return endpoint

    def assign_group_to_resource(self):
        endpoint = "/api/access-management/"
        return endpoint
