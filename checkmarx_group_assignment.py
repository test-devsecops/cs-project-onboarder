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

def assign_groups_to_resource(tenant_url, tenant_iam_url, groups, resource_id, resource_type, resource_name):
    
    # Get route endpoints
    get_access_token_endpoint = routes.get_access_token(tenant_name)
    assign_group_to_resource_endpoint = routes.assign_group_to_resource()
    
    access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)

    for groupId in groups:
        print(f"Creating Assignment for Group {groupId} for {resource_type} {resource_id} {resource_name}")
        logger.info(f"Creating Assignment for Group {groupId} for {resource_type} {resource_id} {resource_name}")
        access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)
        assign_group_to_resource_response = api_actions.assign_group_to_resource(access_token, tenant_url, groupId, resource_id, resource_type)

def assign_group_by_tag(tenant_name, tenant_iam_url, tenant_url, groups_list, groups_dict, routes, api_actions):

    tag_groups = {}

    # Get route endpoints
    get_access_token_endpoint = routes.get_access_token(tenant_name)
    get_groups_endpoint = routes.get_groups(tenant_name)
    get_application_endpoint = routes.get_application()
    get_projects_endpoint = routes.get_projects()

    for group in groups_list:
        print(f"Retrieving Id for Group {group}...")
        logger.info(f"Retrieving Id for Group {group}...")
        access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)
        
        get_group_response = api_actions.get_group(access_token, tenant_iam_url, get_group_endpoint, group)
        results = get_group_response
        if not len(results):
            print(f"{group} not found in Checkmarx! Skipping group assignment for {group}")
            logger.info(f"{group} not found in Checkmarx! Skipping group assignment for {group}")
            continue
        group_id = results[0].get('id', '')
        tag = groups_dict[group].get("tag")
        print(f"{group} found! Adding {group} id {group_id} to tag group {tag}")
        logger.info(f"{group} found! Adding {group} id {group_id} to tag group {tag}")
        if tag not in tag_groups:
            tag_groups[tag] = []
        tag_groups[tag].append(group_id)

    access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)
    for thistag, groups in tag_groups.items():
        print(f"Retrieving Application with {thistag} tag")
        logger.info(f"Retrieving Application with {thistag} tag")
        get_application_response = api_actions.get_application_by_tag(access_token, tenant_url, get_application_endpoint, thistag)
        results = get_application_response
        if not len(results):
            print(f"No Application found for {thistag}")
            logger.info(f"No Application found for {thistag}")
            continue
        app_id = results[0].get("id")
        app_name = results[0].get("name")
        assign_groups_to_resource(tenant_url, tenant_iam_url, groups, app_id, 'application', app_name, routes, api_actions)

    for thistag, groups in tag_groups.items():
        print(f"Retrieving Projects with {thistag} tag")
        logger.info(f"Retrieving Projects with {thistag} tag")
        offset = 0
        limit = 100
        get_projects_by_tags_response = api_actions.get_projects_by_tags(access_token, tenant_url, get_projects_endpoint, thistag, offset, limit)
        results = get_projects_by_tags_response
        projects_count = results.get("filteredTotalCount", 0)
        if not projects_count:
            print(f"No projects found for tag {thistag}. Skipping ahead.")
            logger.info(f"No projects found for tag {thistag}. Skipping ahead.")
            continue
        projects = results.get("projects", [])
        count = 1
        while projects_count > 0:
            for project in projects:
                # print(count, project["id"], project["name"])
                count += 1
                assign_groups_to_resource(tenant_url, tenant_iam_url, groups, project["id"], "project", project["name"], routes, api_actions)
            projects_count -= limit
            offset += 100
            get_projects_by_tags_response = api_actions.get_projects_by_tags(access_token, tenant_url, get_projects_endpoint, thistag, offset, limit)
            results = get_projects_by_tags_response
            projects = results.get("projects", [])

def assign_group_by_GHOrg(tenant_name, tenant_iam_url, tenant_url, groups_list, groups_dict, routes, api_actions):

    ghorg_groups = {}
    
    # Get route endpoints
    get_access_token_endpoint = routes.get_access_token(tenant_name)
    get_groups_endpoint = routes.get_groups(tenant_name)
    # get_application_endpoint = routes.get_application()
    get_projects_endpoint = routes.get_projects()
    get_projects_through_searchbar_endpoint = routes.get_projects_through_searchbar()

    for group in groups_list:
        print(f"Retrieving Id for Group {group}...")
        logger.info(f"Retrieving Id for Group {group}...")
        access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)
        
        get_group_response = api_actions.get_group(access_token, tenant_iam_url, get_group_endpoint, group)
        results = get_group_response
        if not len(results):
            print(f"{group} not found in Checkmarx! Skipping group assignment for {group}")
            logger.info(f"{group} not found in Checkmarx! Skipping group assignment for {group}")
            continue
        group_id = results[0].get('id', '')
        ghorg = groups_dict[group].get("tag")
        print(f"{group} found! Adding {group} id {group_id} to tag group {tag}")
        logger.info(f"{group} found! Adding {group} id {group_id} to tag group {tag}")
        if ghorg not in ghorg_groups:
            ghorg_groups[ghorg] = []
        ghorg_groups[ghorg].append(group_id)

    access_token = api_actions.get_access_token(token, tenant_iam_url, get_access_token_endpoint)
    for thisghorg, groups in ghorg_groups.items():
        print(f"Retrieving Projects with {thisghorg} ghorg")
        logger.info(f"Retrieving Projects with {thisghorg} ghorg")
        offset = 0
        limit = 100
        get_projects_through_searchbar_response = api_actions.get_projects_through_searchbar(access_token, tenant_url, get_projects_through_searchbar_endpoint, thisghorg, offset, limit)
        results = get_projects_through_searchbar_response
        projects_count = results.get("filteredTotalCount", 0)
        if not projects_count:
            print(f"No projects found for tag {thisghorg}. Skipping ahead.")
            logger.info(f"No projects found for tag {thisghorg}. Skipping ahead.")
            continue
        projects = results.get("projects", [])
        count = 1
        while projects_count > 0:
            for project in projects:
                # print(count, project["projectId"], project["projectName"])
                count += 1
                assign_groups_to_resource(tenant_url, tenant_iam_url, groups, project["id"], "project", project["name"], routes, api_actions)
            projects_count -= limit
            offset += 100
            get_projects_through_searchbar_response = api_actions.get_projects_through_searchbar(access_token, tenant_url, get_projects_through_searchbar_endpoint, thisghorg, offset, limit)
            results = get_projects_through_searchbar_response.json()
            projects = results.get("projects", [])

def main(filename, mode):
    
    httpRequest = HttpRequests()

    config = Config()
    token, tenant_name, tenant_iam_url, tenant_url = config.get_config()

    logger = Logger("project_and_app_onboarding")

    routes = Routes()

    api_actions = ApiActions(httpRequest)

    groups_file_path = f"./csv_files/groups/{filename}"

    # Step 1: Get list of groups to be created
    print("Extracting list of group names from file")
    logger.info("Extracting list of group names from file")
    groups_list, groups_dict = HelperFunctions.get_groups_name_list(groups_file_path)

    # Step 2: Assign groups to projects and applications
    if mode == "tag":
        assign_group_by_tag(tenant_name, tenant_iam_url, tenant_url, groups_list, groups_dict, routes, api_actions)
    elif mode == "GHOrg":
        assign_group_by_GHOrg(tenant_name, tenant_iam_url, tenant_url, groups_list, groups_dict, routes, api_actions)
    else:
        print(f"{mode} is not a valid argument")
        logger.error(f"{mode} is not a valid argument")

if __name__ == "__main__":
    # Define command-line arguments
    parser = argparse.ArgumentParser(description='Onboarding Prucore Apps')
    parser.add_argument('-filename', help='filename of the prucore apps',required=True)
    parser.add_argument('-mode', help='assignment mode by tag or by lbu',required=True)

    # Parse the command-line arguments
    args = parser.parse_args()

    # Call the main function with the provided exlusions and LBU
    main(args.filename, args.mode)
