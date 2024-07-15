#!/usr/bin/env python3

import argparse
import re
import time
from datetime import datetime, timezone

import requests
from dateutil import parser

arg_parser = argparse.ArgumentParser(
    prog="gitlab_artifact_cleaner",
    description="Clean gitlab artifacts of groups or projects recursively",
)
arg_parser.add_argument(
    "-s",
    "--server",
    help="Gitlab server address. Examples https://mygitlab.com.",
    required=True,
)
arg_parser.add_argument(
    "-t",
    "--token",
    help="Token for Gitlab",
    required=True,
)

arg_parser.add_argument(
    "--ignore-expire",
    help="Enforce artifact deletion even if not expired",
    default=False,
    action=argparse.BooleanOptionalAction,
)

arg_parser.add_argument(
    "--ignore-mr",
    help="Ignore existing MRs",
    default=False,
    action=argparse.BooleanOptionalAction,
)

group = arg_parser.add_mutually_exclusive_group(required=True)
group.add_argument(
    "--group-id",
    help="The group to start from",
)
group.add_argument(
    "--project-id",
    help="The project to clean",
)

args = arg_parser.parse_args()
# print(args)

server = args.server
token = args.token
group_id = args.group_id
arg_project = args.project_id
ignore_expiry = args.ignore_expire
ignore_mr = args.ignore_mr

now = datetime.now(timezone.utc)

if ignore_expiry:
    print("Executed with ignoring expiry date.")
if ignore_mr:
    print("Executed with ignoring existing MRs.")


# Function to get all projects in a group, including subgroups
def get_all_projects_in_group(group_id):
    projects_url = f"{server}/api/v4/groups/{group_id}/projects?include_subgroups=true&per_page=500"
    response = requests.get(
        projects_url,
        headers={
            "private-token": token,
        },
    )
    response.raise_for_status()
    return response.json()


if arg_project:
    project_ids = [arg_project]
else:
    # Get all projects in the group and its subgroups
    response_json = get_all_projects_in_group(group_id)

    project_ids = [project["id"] for project in response_json]


print(f"Number of projects found: {len(project_ids)}")

overall_space_savings = 0
for project_id in project_ids:
    print(f"Processing project {project_id}:")

    merge_request_url = f"{server}/api/v4/projects/{project_id}/merge_requests?scope=all&per_page=100&page=1"
    merge_requests = {}
    while merge_request_url:
        response = requests.get(
            merge_request_url,
            headers={
                "private-token": token,
            },
        )

        if response.status_code in [500, 429]:
            print(f"Status {response.status_code}, retrying.")
            time.sleep(10)
            continue

        response.raise_for_status()
        response_json = response.json()

        for merge_request in response_json:
            iid = merge_request.get("iid", None)
            if iid:
                merge_requests[int(iid)] = merge_request["state"]

        merge_request_url = response.links.get("next", {}).get("url", None)

    branch_url = (
        f"{server}/api/v4/projects/{project_id}/repository/branches?per_page=100&page=1"
    )
    unmerged_branches = []
    while branch_url:
        response = requests.get(
            branch_url,
            headers={
                "private-token": token,
            },
        )

        if response.status_code in [500, 429]:
            print(f"Status {response.status_code}, retrying.")
            time.sleep(10)
            continue

        response.raise_for_status()
        response_json = response.json()

        for branch in response_json:
            is_merged = branch["merged"]
            if not is_merged:
                unmerged_branches.append(branch["name"])

        branch_url = response.links.get("next", {}).get("url", None)

    url = f"{server}/api/v4/projects/{project_id}/jobs?per_page=100&page=1"

    job_count = 0
    artifact_count = 0
    artifact_size = 0
    deleted_artifact_count = 0
    deleted_artifact_size = 0
    while url:
        response = requests.get(
            url,
            headers={
                "private-token": token,
            },
        )

        if response.status_code in [500, 429]:
            print(f"Status {response.status_code}, retrying.")
            time.sleep(10)
            continue

        response.raise_for_status()
        response_json = response.json()
        for job in response_json:
            job_count += 1

            artifacts = job.get("artifacts", None)
            artifacts_expire_at_string = job.get("artifacts_expire_at", None)
            artifacts_expire_at = None
            if artifacts_expire_at_string:
                artifacts_expire_at = parser.parse(artifacts_expire_at_string)

            has_expired_artifacts = False
            deleted_job_artifact_count = 0
            deleted_job_artifact_size = 0
            if artifacts:
                for artifact in artifacts:
                    if artifact["filename"] != "job.log":
                        size = artifact["size"]

                        artifact_count += 1
                        artifact_size += size

                        if (
                            not artifacts_expire_at or artifacts_expire_at < now
                        ) or ignore_expiry:
                            has_expired_artifacts = True
                            deleted_job_artifact_count += 1
                            deleted_job_artifact_size += size

            delete_artifacts = has_expired_artifacts

            if delete_artifacts and not ignore_mr:
                ref = job["ref"]
                merge_request_iid_match = re.search(
                    r"refs\/merge-requests\/(\d+)\/head", ref
                )
                if merge_request_iid_match:
                    merge_request_iid = merge_request_iid_match.group(1)
                    if merge_request_iid:
                        merge_request_status = merge_requests.get(
                            int(merge_request_iid)
                        )
                        if merge_request_status in ["merged", "closed", None]:
                            delete_artifacts = True
                            deleted_artifact_count += deleted_job_artifact_count
                            deleted_job_artifact_size += deleted_job_artifact_size

                elif ref not in unmerged_branches:
                    delete_artifacts = True
                    deleted_artifact_count += deleted_job_artifact_count
                    deleted_job_artifact_size += deleted_job_artifact_size

            if delete_artifacts:
                job_id = job["id"]
                print(f"Processing job ID: {job_id}", end="")
                delete_response = requests.delete(
                    f"{server}/api/v4/projects/{project_id}/jobs/{job_id}/artifacts",
                    headers={
                        "private-token": token,
                    },
                )
                print(f" - status: {delete_response.status_code}\033[K", end="\r")

        print(f"Processed page {url}.\033[K", end="\r")

        url = response.links.get("next", {}).get("url", None)

    overall_space_savings += deleted_artifact_size

    print()
    print(f"Jobs analysed: {job_count}")
    print(f"Pre artifact count: {artifact_count}")
    print(f"Pre artifact size [MB]: {artifact_size / (1024 * 1024)}")
    print(f"Post artifact count: {artifact_count - deleted_artifact_count}")
    print(
        f"Post artifact size [MB]: {(artifact_size - deleted_artifact_size) / (1024 * 1024)}"
    )
    print()

print(f"Overall savings [MB]: {overall_space_savings / (1024 * 1024)}")
