import requests
import pandas as pd
import sys
import argparse
import os
from paramiko import SSHClient,AutoAddPolicy,RSAKey
import time

# User configuration section #
edgeApiUrl = "https://api-customer.pilot.bluec.at" # Make sure to have "api-" in the beginning of the URL
spApiUrl = "https://us.fleet.bluec.at" # PROD: 'us.fleet.bluec.at', PILOT: 'pilot.fleet.bluec.at'
edgeClientId = "abcd12234-1bc5-4a44-a016-12345678"
edgeClientSecret = "abcd12434-6959-453d-891f-12345678"
# ------------------------- #
sp_export_file = "sp_export.csv"
sp_results_file = "sp_hotfix_results.csv"
skip_disconnected = True
sp_ssh_private_key_file = "/Users/user/.ssh/ssh_private.key"
ssh_timeout = 5

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
            if sp['connectionStatus'] == "NOT_CONNECTED" and skip_disconnected is True:
                continue
            for service in sp['services']:
                if service['version'] == "3.10.0" and service['serviceName'] == 'dns-resolver-service' :
                    sp_export.append([sp['id'],sp['name'],sp['version'],sp['connectionStatus'],sp['ipv4CIDRAddress'].split("/")[0],service['version'],service['name'],False])
        df = pd.DataFrame(sp_export,columns=["sp_id","sp_name","sp_version","sp_connection_state","sp_ipv4_addr","drs_version","drs_name","hotfix_applied"])
        df = clean_sp_data(df)
        print(f"Exporting all SP ({len(sp_export)}) to file {sp_export_file}")
        df.to_csv(f"./{sp_export_file}", sep=',',index=False)

    else:
        print(f"Unable to get Edge API Token. HTTP/{response.status_code} - {response.text}")
        sys.exit(255)
    return True

        

def clean_sp_data(df_data):
    pd.set_option('display.max_rows', 100)
    pd.set_option('display.max_columns', 10)
    pd.set_option('display.width', 1500)
    print(df_data)
    return df_data


def runSSHcmd(sp_ip):
    client = SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(AutoAddPolicy())
    if not os.path.exists(sp_ssh_private_key_file):
        print(f"SSH Private key file ({sp_ssh_private_key_file}) not found. Exiting")
    sp_pkey = RSAKey.from_private_key_file(sp_ssh_private_key_file)
    try:
        client.connect(sp_ip,username="operations",pkey=sp_pkey,timeout=ssh_timeout)
        channel = client.invoke_shell()
        command = "sudo -S /opt/bluecat/bin/hotfix cert-renew;echo $? ignorethisline"
        success_message = "DRS Certificate renewal was completed successfully"
        break_message = ["Client certificate expiration"]
        channel.set_combine_stderr(True)
        cmd_stdout = ""
        channel.send(command + '\n')
        while cmd_stdout.find("ignorethisline") < 0:
            cmd_stdout += channel.recv(9999).decode('utf-8')
            string_found = False
            for line in cmd_stdout.split("\n"):
                for msg in break_message:
                    if not string_found:
                        if msg in line:
                            string_found = True
                            # print(f"Stopping command. Found ({msg})")
                            if any(y in line for y in ['2024','2025']):
                                print(f"\u2757 Timestamp likely old ({line}), continue")
                            elif any(y in line for y in ['2026','2027']):
                                print(f"\u2757 Timestamp new ({line.split(':')[1]}), skipping")
                                # send keyboard interrupt to stop script
                                channel.send(chr(3))
                                break
                            else:
                                print(f"unknown year. ({line})")
            time.sleep(0.5)
        client.close()
        if success_message in cmd_stdout:
            print(f"\u2705 DRS Certificates updated successfully.")
            return True
        else:
            print(f"\u274c DRS Certificates not updated.")
            # print(cmd_stdout)
            if string_found:
                return "SKIPPED"
            else:
                return False
    except Exception as err:
        print(f"\u274c Error connecting. {err}")
        return False


# Add CLI passing and parsing of flags
parser = argparse.ArgumentParser(description='Export a list of SPv4 instances and then run SSH command remotely')
changer = parser.add_mutually_exclusive_group()
changer.add_argument('--list',help=f"Lists all SP and exports them to file {sp_export_file}", action="store_true")
changer.add_argument('--run',help=f"Run SSH command on all SPs listed in {sp_export_file}", action="store_true")

args = parser.parse_args()
if not any([args.list,args.run]):
    print("No arguments specified. For help, please run the script with '-h' command.")
    sys.exit(0)

global edge_token
edge_token = login()
if edge_token:
    if args.list:
        if not dumpSP(edge_token):
            print("\u274c Unknown error occurred.")
    if args.run:
        if not os.path.exists(sp_export_file):
            print(f"\u274c Missing CSV file ({sp_export_file}) containing SPv4 list")
            sys.exit(255)
        else:
            sp_list = pd.read_csv(open(sp_export_file, newline=''))
            print(f"Read ({len(sp_list)}) lines from csv file")
            for sp in sp_list.values.tolist():
                if sp[7] == True:
                    print("Skipping SP ({sp[1]}), IPv4 Addr: ({sp[4]}). Hotfix applied flag is True")
                    continue
                hotfix_applied = False
                if sp[3] == 'CONNECTED':
                    print(f'#'*32)
                    print(f"Checking SP ({sp[1]}), IPv4 Addr: ({sp[4]})")
                    
                    hotfix_applied = runSSHcmd(sp[4])
                    
                else:
                    print(f"Skipping SP ({sp[1]}), IPv4 Addr: ({sp[4]}) because its in Disconnected state")

                sp_list.loc[sp_list['sp_id'] == sp[0], 'hotfix_applied'] = hotfix_applied
            df = clean_sp_data(sp_list)
            print(f"\u2705 Exporting report ({len(sp_list)}) to file {sp_results_file}")
            df.to_csv(f"./{sp_results_file}", sep=',',index=False)

    print('\u2705 Done.')


    


    