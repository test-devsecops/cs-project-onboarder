from utility.http_utility import HttpRequests
from utility.routes import Routes
from utility.config_utility import Config
from utility.csv_utility import Csv
from utility.api_actions import ApiActions
from utility.helper_functions import HelperFunctions
from utility.logger import Logger
from utility.exception_handler import ExceptionHandler

import os
import sys
import argparse
import re
import time
import json

def main(filename):
  httpRequest = HttpRequests()

  config = Config()
  token, tenant_name, tenant_iam_url, tenant_url = config.get_config()

  logger = Logger("project_and_app_onboarding")

  routes = Routes()
  get_access_token_endpoint = routes.get_access_token(tenant_name)
  get_client_id_endpoint = routes.get_client(tenant_name)

  api_actions = ApiActions(httpRequest)
  access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)

  # Step 1: Get list of groups to be created
  print("Extracting list of group names from file")
  logger.info("Extracting list of group names from file")
  groups_file_path = f"./csv_files/groups/{filename}"
  groups_list, groups_dict = HelperFunctions.get_groups_name_list(groups_file_path)

  # Step 2: Get the client ID to run the API for role-mapping to the group
  print("Retrieving Client Id for ast-app client for role-mapping purposes...")
  logger.info("Retrieving Client Id for ast-app client for role-mapping purposes...")
  client_id_response = api_actions.get_client_by_client_name(access_token, tenant_iam_url, get_client_id_endpoint, 'ast-app')
  client_id = client_id_response[0].get('id')

  # Step 3: Get the role IDS for the composite roles created for the groups
  get_role_id_endpoint = routes.get_role(tenant_name, client_id)
  roleids_dict = {}
  for role in ["Contributors", "Viewers", "Managers"]:
    print(f"Retrieving Role ID for {role}")
    logger.info(f"Retrieving Role ID for {role}")
    roles_id_response = api_actions.get_role(access_token, tenant_iam_url, get_role_id_endpoint, role)
    role_id = roles_id_response.get('id')
    roleids_dict[role] = role_id

  # Step 4: Create the groups
  # Step 4a: Check if group exist
  get_group_endpoint = routes.get_group(tenant_name)
  for count, group in enumerate(groups_list):
    print(f"Checking if {group} exists...")
    logger.info(f"Checking if {group} exists...")
    group_response = api_actions.get_group(access_token, tenant_iam_url, get_group_endpoint, group)
    results = group_response
    group_id = ""
    if len(results):
      group_id = results[0].get("id")
      print(f"{group} already exists! Group ID: {group_id}")
      logger.info(f"{group} already exists! Group ID: {group_id}")
    else:
  # Step 4b: Create groups if they do not exist yet
      create_group_endpoint = routes.create_group(tenant_name)
      print(f"{group} not found! Proceeding to create group...")
      logger.info(f"{group} not found! Proceeding to create group...")
      group_creation_response = api_actions.create_group(access_token, tenant_iam_url, create_group_endpoint, group)
      print(group_creation_response)
      print(group_creation_response.headers)
      group_id = group_creation_response.headers['Location'].split('/')[-1]
      print(f"{group} created with id: {group_id}")
      logger.info(f"{group} created with id: {group_id}")

  # Step 4c: Perform role mapping to group
    role = groups_dict[group].get("role", "")
    role_id = roleids_dict[role]
    assign_group_role_endpoint = routes.assign_group_role(tenant_name, group_id, client_id)
    print(f"Performing role-mapping to {group}")
    logger.info(f"Performing role-mapping to {group}")
    print(f"https://{tenant_iam_url}{assign_group_role_endpoint}")
    assign_group_role_response = api_actions.assign_group_role(access_token, tenant_iam_url, assign_group_role_endpoint, role_id, role) 

if __name__ == "__main__":
  # Define command-line arguments
  parser = argparse.ArgumentParser(description='Onboarding Groups')
  parser.add_argument('-filename', help='filename of the groups',required=True)

  # Parse the command-line arguments
  args = parser.parse_args()

  # Call the main function with the provided exlusions and LBU
  main(args.filename)
