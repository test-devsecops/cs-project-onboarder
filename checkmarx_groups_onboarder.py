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
  get_client_id_endpoint = routes.get_client_id(tenant_name)

  api_actions = ApiActions(httpRequest)
  access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)

  # Step 1: Get list of groups to be created
  groups_list,groups_dict = HelperFunctions.get_groups_name_list(filename)

  # Step 2: Get the client ID to run the API for role-mapping to the group
  client_id = api_actions.get_client_id_by_client_name(access_token, tenant_iam_url, get_client_id_endpoint, 'ast-app')
  

  # Step 3: Get the role IDS for the composite roles created for the groups

  # Step 4: Create the groups
