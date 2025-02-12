import json, requests
from pprint import pprint as print
micetro_url = "http://10.3.135.95/mmws/api/v2"
micetro_user = ""
micetro_passwd = ""


micetro_custom_property_names = ["DNS_ENV","USER_ACCESS_GROUP","NETWORK_SPACE","USER_SEGMENT"]

def micetro_login():
    login_url = f"{micetro_url}/micetro/sessions"
    response = m_session.post(url=login_url,json={"loginName": micetro_user,"password": micetro_passwd})
    if response.status_code == 201:
        print(f"Logged into Micetro Central.")
        session_token = response.json()['result']['session']
        return session_token
    else:
        print(f"Login request failed\n{response.text}")
    return None

def build_tags_from_dns_servers():
    infra_env_tags = {}
    request_url = f"{micetro_url}/dnsServers"
    response = m_session.get(url=request_url)
    if response.status_code == 200:
        print("DNS Servers list retrieved")
        server_data = response.json()
        # proceed if there are any servers
        if server_data['result']['totalResults'] > 0:
            for server in server_data['result']['dnsServers']:
                # Check if custom properties exist
                if server['customProperties']:
                    # Check for existence of custom property on the server 
                    for tag in micetro_custom_property_names:
                        # If custom property found, build the map 
                        if server['customProperties'].get(tag):    
                            if not infra_env_tags.get(tag):
                                infra_env_tags[tag] = [{"value": server['customProperties'][tag], "servers": [server['name']]}]
                            else:
                                tag_updated = False
                                for tval in infra_env_tags[tag]:
                                    if tval['value'] == server['customProperties'].get(tag):
                                        tval['servers'].append(server['name'])
                                        tag_updated = True
                                        break
                                if not tag_updated:
                                    infra_env_tags[tag].extend([{"value": server['customProperties'][tag], "servers": [server['name']]}])
        return infra_env_tags

    else:
        print(f"Login request failed\n{response.text}")
    return None


def build_tags_from_dhcp_servers():
    infra_env_tags = {}
    request_url = f"{micetro_url}/dhcpServers"
    response = m_session.get(url=request_url)
    if response.status_code == 200:
        print("DHCP Servers list retrieved")
        server_data = response.json()
        # proceed if there are any servers
        if server_data['result']['totalResults'] > 0:
            for server in server_data['result']['dhcpServers']:
                # Check if custom properties exist
                if server['customProperties']:
                    # Check for existence of custom property on the server 
                    for tag in micetro_custom_property_names:
                        # If custom property found, build the map 
                        if server['customProperties'].get(tag):    
                            if not infra_env_tags.get(tag):
                                infra_env_tags[tag] = [{"value": server['customProperties'][tag], "servers": [server['name']]}]
                            else:
                                tag_updated = False
                                for tval in infra_env_tags[tag]:
                                    if tval['value'] == server['customProperties'].get(tag):
                                        tval['servers'].append(server['name'])
                                        tag_updated = True
                                        break
                                if not tag_updated:
                                    infra_env_tags[tag].extend([{"value": server['customProperties'][tag], "servers": [server['name']]}])
        return infra_env_tags

    else:
        print(f"Login request failed\n{response.text}")
    return None


global m_session
m_session = requests.Session()
session_token = micetro_login()
if session_token:
    service_map_dns = build_tags_from_dns_servers()
    print(service_map_dns)
    service_map_dhcp = build_tags_from_dhcp_servers()
    print(service_map_dhcp)