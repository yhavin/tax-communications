"""
Authentication functions to access Microsoft API.

Author: Yakir Havin
"""


import msal
import boto3


def get_msal_credentials():
    ssm = boto3.client("ssm")
    parent_path = "/tax-communications/azure"

    client_id = ssm.get_parameter(Name=f"{parent_path}/client-id", WithDecryption=True)["Parameter"]["Value"]
    client_secret = ssm.get_parameter(Name=f"{parent_path}/client-secret", WithDecryption=True)["Parameter"]["Value"]
    tenant_id = ssm.get_parameter(Name=f"{parent_path}/tenant-id", WithDecryption=True)["Parameter"]["Value"]

    return client_id, client_secret, tenant_id


def get_msal_access_token(client_id, client_secret, tenant_id):
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    scope = ["https://graph.microsoft.com/.default"]

    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        authority=authority,
        client_credential=client_secret
    )

    access_token_response = app.acquire_token_for_client(scopes=scope)
    access_token = access_token_response["access_token"]
    return access_token