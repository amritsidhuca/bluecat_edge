import requests
import pandas as pd
import sys
import os
import json
import datetime as dt

# User configuration section #
edgeApiUrl = "https://api-customer.edge.bluec.at" # Make sure to have "api-" in the beginning of the URL
spApiUrl = "https://us.fleet.bluec.at" 
edge_creds_file = "~/Documents/care-ci-keys.json" 
# ------------------------- #
sp_export_file = "sp_export_1.csv"

def login():
    url = f"{edgeApiUrl}/v1/api/authentication/token"
    creds_data = json.load(open(os.path.abspath(os.path.expanduser(os.path.expandvars(edge_creds_file)))))
    payload = {
        "grantType": "ClientCredentials",
        "clientCredentials": {
            "clientId": creds_data['clientId'],
            "clientSecret": creds_data['clientSecret']
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
                if service['version'] in ['3.10.0','3.9.1','3.9.0','3.8.0'] and service['serviceName'] == 'dns-resolver-service' :
                    sp_export.append([sp['id'],sp['name'],sp['version'],sp['ipv4CIDRAddress'].split("/")[0],service['id']])
                    break
                if service['version'] in ['3.11.1','4.0.0'] and service['serviceName'] == 'dns-resolver-service' :
                    sp_export.append([sp['id'],sp['name'],sp['version'],sp['ipv4CIDRAddress'].split("/")[0],service['id']])
                    break


    else:
        print(f"Unable to get Edge API Token. HTTP/{response.status_code} - {response.text}")
        sys.exit(255)
    return sp_export


def checkDRS(drs_instance_id):
    # First get serviceinstance details and then get DRS details
    url = f"{spApiUrl}/user/api/v1/serviceInstances/{drs_instance_id}"

    headers = {
        "Authorization": f"Bearer {edge_token}",
        "Content-Type": "application/json"
    }

    response = requests.request("GET", url, headers=headers)
    if response.status_code == 200:
        for param in response.json()['parameters']:
            if param['name'] == 'DRSID':
                url = f"{edgeApiUrl}/v1/api/dnsResolverServices/{param['value']}"

                headers = {
                    "Authorization": f"Bearer {edge_token}",
                    "Content-Type": "application/json"
                }

                response = requests.request("GET", url, headers=headers)
                if response.status_code == 200:
                    drs_details =  response.json()
                    return [drs_details['name'],drs_details['version']]
                else:
                    print(f"Unable to get DRS details. HTTP/{response.status_code} - {response.text}")
                    return None,None
        return 
    else:
        print(f"Unable to get DRS details. HTTP/{response.status_code} - {response.text}")
        return None,None


def clean_sp_data(df_data):
    pd.set_option('display.max_rows', 100)
    pd.set_option('display.max_columns', 10)
    pd.set_option('display.width', 1500)
    print(df_data)
    return df_data


def check_drs_cert(sp_ip):
    print("Checking Certificate Timestamp")
    try:
        sp_diag = requests.get(f"http://{sp_ip}:2021/v2/diagnostics").json()
        for service in sp_diag['services']:
            if service['id'] == 'sp-controller-service':
                for resource in service['resources']:
                    if resource['type'] == 'certificates':
                        for cert_info in resource['info']:
                            if cert_info['name'] == 'clientCertificateExpiration':
                                return(dt.datetime.fromtimestamp(cert_info['value']/1000).strftime('%c'))
    except Exception as err:
        print(f"Unable to get DRS Diagnostics. {err}") 
    return "not_applicable"

global edge_token
print("logging into Edge")
edge_token = login()
if edge_token:
    print("Getting Service Points")
    sp_export = dumpSP(edge_token)
    if sp_export:
        print("Getting DRS details")
        for sp in sp_export:
            sp.extend(checkDRS(sp[4]))
            if sp[-1] == '3.10.0':
                sp.append(check_drs_cert(sp[3]))
            else:
                sp.append("not_applicable")
        df = pd.DataFrame(sp_export,columns=["sp_id","sp_name","sp_version","sp_ipv4_addr","drs_instance_id","drs_name","drs_version","drs_cert_expiry"])
        df = df.drop('drs_instance_id',axis=1)
        df = clean_sp_data(df)
        print(f"Exporting all SP ({len(sp_export)}) to file {sp_export_file}")
        df.to_csv(f"./{sp_export_file}", sep=',',index=False)
    

    print('\u2705 Done.')
