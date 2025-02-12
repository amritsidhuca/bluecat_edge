import datetime
import requests, json

# User configurable credentials
edge_access_keys = "edge-keys-prod.json"
sp_id_file = "sp_id.txt"
edge_url = "https://api-xxx.edge.bluec.at"  # without trailing /

# Do not change unless the Edge endpoint changes for SPv4
edge_sp_url = "https://us.fleet.bluec.at/user/api"

# Read text file containing Service Point IDs
try:
    print(f'Loading SP IDs file: {sp_id_file}')
    fc = open(sp_id_file, 'r').readlines()
except Exception as err:
    print(f'Unable to read SP ID file. {err}')
    exit(255)


# Login Edge using User API keys
def edge_login():
    # Load credentials File
    print(f'Loading credentials file: {edge_access_keys}')
    edge_creds = None
    auth_token = None
    try:
        edge_creds = json.load(open(edge_access_keys))
        if any(key for key in ['clientId', 'clientSecret'] if key in edge_creds):
            pass
        else:
            print('Invalid credentials file.')
    except Exception as err:
        print(f'Unable to read Edge credentials file {edge_access_keys}. {err}')
        exit(255)

    # Login and get a token
    if edge_creds:
        print(f'Logging into Edge CI: {edge_url}')
        token_start_time = datetime.datetime.now()
        res = requests.post(f'{edge_url}/v1/api/authentication/token', json={
            "grantType": "ClientCredentials",
            "clientCredentials": {
                "clientId": edge_creds['clientId'],
                "clientSecret": edge_creds['clientSecret']
            }
        })
        if res.status_code == 200:
            auth_token = res.json()['accessToken']
            print(f'Token valid until {token_start_time + datetime.timedelta(seconds=res.json()["expiresIn"])}')
        else:
            print(f'Unable to login to Edge {edge_url}. {res.text}')
            exit(255)

    return auth_token


# Delete Service Points
def delete_sp_with_id():
    for sp_id in fc:
        sp_id = sp_id.strip()
        print('-----------------------------------------------------')
        print(f'Getting details on SP: ({sp_id})')
        try:
            res = requests.get(f'{edge_sp_url}/v1/servicePoints/{sp_id}',headers=headers)
            if res.status_code == 200:
                sp_details = res.json()
                print(f'| SP ID\t\t\t\t\t\t\t\t\t'
                      f'| SP Name\t\t\t'
                      f'| SP Primary Addresses\t'
                      f'| SP Conn Status\t'
                      f'| SP Services Count\t'
                      f'| SP Platform')
                print(f'| {sp_details["id"]}\t'
                      f'| {sp_details["name"]}\t'
                      f'| {[ip["ipAddress"] for ip in sp_details["addresses"] if ip["type"] == "PRIMARY"]}\t\t'
                      f'| {sp_details["connectionStatus"]}\t\t\t'
                      f'| {len(sp_details["services"])}\t\t\t\t\t'
                      f'| {sp_details["platform"]}')
                # print(f'Edge SP ({sp_details["name"]}) is deployed in {sp_details["platform"]}\nwith address ({[ip["ipAddress"] for ip in sp_details["addresses"] if ip["type"] == "PRIMARY"]})')
                print(f'## WARNING: This Service Point is currently in {sp_details["connectionStatus"]} state.\n'
                      f'## Please confirm with (y/n) if you would like to continue...')
                if len(sp_details['services']) == 0:
                    print('No services found on this SP, continuing')
                else:
                    if sp_details['connectionStatus'] == 'CONNECTED':
                        print(f'This Service Point is currently in CONNECTED state and has one or more services enabled.\n'
                              f'Please remove services before deleting the Service Point.')
                        continue
                    else:
                        print('## CAUTION: This Service Point is in DISCONNECTED state and has one or more services enabled on it.\n'
                              'Continuing to delete this SP will also delete services from your Edge CI.')
                while True:
                    user_res = input("\n## Delete? (y/n):")
                    if user_res.strip().lower() == 'y':
                        print(f'User responded with "y", continuing with deletion')
                        print(f'Deleting SP {sp_details["name"]} with id: {sp_details["id"]}')
                        break
                    elif user_res.strip().lower() == 'n':
                        print(f'Service Point deletion not confirmed, skipping')
                        break
                    else:
                        continue
            else:
                print(f'Unable to get details on SP: ({sp_id}). Edge SP endpoint responded with {res.status_code}. {res.text}')
        except Exception as err:
            print(f'Error getting SP details.{err}')
    print('-----------------------------------------------------')
    print(f'Reached end of file {sp_id_file}.')
    return


# End
def edge_logout():
    res = requests.post(f'{edge_url}/v1/api/authentication/logout', headers=headers)
    if res.status_code == 204:
        print('Logged out.')
    else:
        print(f'Error logging out. {res.status_code}: {res.text}')


if __name__ == "__main__":
    token = edge_login()
    headers = { 'Authorization': f'Bearer {token}' }
    if token:
        delete_sp_with_id()
        edge_logout()
