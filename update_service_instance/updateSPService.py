import requests,json
import pandas as pd
import csv
import sys
import argparse
import os

# User configuration section #
edgeApiUrl = "https://api-demo.pilot.bluec.at" # Make sure to have "api-" in the beginning of the URL
spApiUrl = "https://pilot.fleet.bluec.at" # PROD: 'us.fleet.bluec.at', PILOT: 'pilot.fleet.bluec.at'
edgeClientId = "abcd1234-1bc5-1234-5678-6123456abcd"
edgeClientSecret = "abcd1234-abcd-1234-123345656"
drs_source_version = "3.11.0"
drs_target_version = "3.11.0"
drsUpdateFile = "drs-1.csv"
# ------------------------- #
spExportFile = "sp_drs_export.csv"


def login():
    url = f"{edgeApiUrl}/v1/api/authentication/token"
    payload = {
        "grantType": "ClientCredentials",
        "clientCredentials": {
            "clientId": edgeClientId,
            "clientSecret": edgeClientSecret
        }
    }
    headers = {
        "Content-Type": "application/json"
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    if response.status_code == 200:
        token = response.json()['accessToken']
    else:
        print(f"Unable to get Edge API Token. HTTP/{response.status_code} - {response.text}")
        sys.exit(255)
    return token


def dumpSP(token):
    sp_export = []

    url = f"{spApiUrl}/user/api/v1/servicePoints"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.request("GET", url, headers=headers)
    if response.status_code == 200:
        sp_data = response.json()
        print(f"Total SP: {len(sp_data['data'])}")   
        for sp in sp_data['data']:
            for service in sp['services']:
                if service['version'] == drs_source_version and service['serviceName'] == 'dns-resolver-service' :
                    sp_export.append([sp['id'],sp['name'],sp['version'],service['id'],service['name'],service['version']])
        df = pd.DataFrame(sp_export,columns=["sp_id","sp_name","sp_version","drs_instance_id","drs_name","drs_version"])
        df = clean_sp_data(df)
        print(f"Exporting all SP ({len(sp_export)}) with DRS running on ({drs_source_version}) to file {spExportFile}")
        df.to_csv(f"./{spExportFile}", sep=',',index=False)

    else:
        print(f"Unable to get Edge API Token. HTTP/{response.status_code} - {response.text}")
        sys.exit(255)
    return True

        

def clean_sp_data(df_data):
    pd.set_option('display.max_rows', 100)
    pd.set_option('display.max_columns', 10)
    pd.set_option('display.width', 1000)
    print(df_data)
    return df_data


def patch_drs_instance(token):
    drs_fo = csv.reader(open(drsUpdateFile))
    for drs in drs_fo:
        print(f"Updating DRS instance: {drs}")
        url = f"{spApiUrl}/user/api/v1/serviceInstances/{drs[3]}"
        newSIData = {
            "version": drs_target_version
            }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        response = requests.request("PATCH",url,data=json.dumps(newSIData),headers=headers)
        if response.status_code == 202:
            print(f"Service instance version change to ({drs_target_version}) started")
        else:
            print(f"Unable to change service instance version. {response.text}")

def check_drs_instance(token):
    drs_fo = csv.reader(open(drsUpdateFile))
    for drs in drs_fo:
        print(f"Checking DRS instance: {drs[4]}")
        url = f"{spApiUrl}/user/api/v1/serviceInstances/{drs[3]}"
        newSIData = {
            "version": drs_target_version
            }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        response = requests.request("GET",url,data=json.dumps(newSIData),headers=headers)
        if response.status_code == 200:
            drs_details = response.json()
            drs_version = drs_details['version']
            update_status = drs_details.get('updateStatus',None)
            if update_status:
                print(f"DRS Update Status: {update_status}, current version: ({drs_version}) ")
            else:
                print(f"Update operation completed. DRS version is now ({drs_version}) ")
    return

# Add CLI passing and parsing of flags
parser = argparse.ArgumentParser(description='Export a list of DRS instances and then upgrade or check upgrade status of DRS instances')
changer = parser.add_mutually_exclusive_group()
changer.add_argument('--list',help=f"Lists all SP and DRS instances and exports them to file {spExportFile}", action="store_true")
changer.add_argument('--check',help=f"Check DRS update status for DRS instances listed in {drsUpdateFile}", action="store_true")
changer.add_argument('--update',help=f"Start DRS (Up/Down)grade for DRS instances listed in {drsUpdateFile}", action="store_true")
args = parser.parse_args()
if not any([args.list,args.check,args.update]):
    print("No arguments specified. For help, please run the script with '-h' command.")
    sys.exit(0)

global edge_token
edge_token = login()
if edge_token:
    if args.list:
        if not dumpSP(edge_token):
            print("Unknown error occurred.")
    if args.check:
        if not os.path.exists(drsUpdateFile):
            print(f"Missing CSV file ({drsUpdateFile}) containing DRS instance details")
            sys.exit(255)
        else:
            check_drs_instance(edge_token)  
    if args.update:
        if not os.path.exists(drsUpdateFile):
            print(f"Missing CSV file ({drsUpdateFile}) containing DRS instance details")
            sys.exit(255)
        else:
            patch_drs_instance(edge_token)
    


    