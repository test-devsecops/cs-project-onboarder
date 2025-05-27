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
    get_idps_endpoint = routes.get_idps(tenant_name)
    get_group_endpoint = routes.get_group(tenant_name)

    api_actions = ApiActions(httpRequest)
    access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)

    groups_file_path = f"./csv_files/groups/{filename}"

    # Step 1: retrieve IdPs configured in CX, there should only be one integrated with the main AD
    print(f"Retrieving IdP from CX...")
    logger.info(f"Retrieving IdP from CX...")
    get_idps_response = api_actions.get_identity_providers(access_token, tenant_iam_url, get_idps_endpoint)
    results = get_idps_response
    if not len(results):
        print(f"No IdP found in Checkmarx")
        logger.info(f"No IdP found in Checkmarx")
        return
    idp_alias = results[0].get("alias")

    # Step 2: Create Mappers in CX IdP
    create_mapper_endpoint = routes.create_mapper(tenant_name, idp_alias)
    groups_list, groups_dict = HelperFunctions.get_groups_name_list(groups_file_path)
    for group_name in groups_list:
        print(f"Checking if {group_name} exists in CX...")
        logger.info(f"Checking if {group_name} exists in CX...")
        group_response = api_actions.get_group(access_token, tenant_iam_url, get_group_endpoint, group_name)
        results = group_response
        if not len(results):
            print(f"{group_name} not found in CX! Skipping mapper creation for group.")
            logger.info(f"{group_name} not found in CX! Skipping mapper creation for group.")
            continue
        print(f"{group_name} found! Creating Mapper on {idp_alias}")
        logger.info(f"{group_name} found! Creating Mapper on {idp_alias}")
        create_mapper_response = api_actions.create_mapper(access_token, tenant_iam_url, create_mapper_endpoint, group_name, idp_alias)

if __name__ == "__main__":
    # Define command-line arguments
    parser = argparse.ArgumentParser(description='Onboarding Groups')
    parser.add_argument('-filename', help='filename of the prucore apps',required=True)
    
    # Parse the command-line arguments
    args = parser.parse_args()
    
    # Call the main function with the provided exlusions and LBU
    main(args.filename)
