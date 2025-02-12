import sys,requests

# User configuration section #
edgeApiUrl = "https://api-demo.pilot.bluec.at" # Make sure to have "api-" in the beginning of the URL
spApiUrl = "https://pilot.fleet.bluec.at" # PROD: 'us.fleet.bluec.at', PILOT: 'pilot.fleet.bluec.at'
edgeClientId = "61ef57d5-1bc5-1234-5678-6123456abcd"
edgeClientSecret = "965f7584-abcd-1234-123345656"
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
