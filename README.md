# bluecat_edge
Collection of Random API Scripts for BlueCat Edge and Edge Service Points
- **delete_sp_v4.py**: Delete Edge Service Points running version v4.4.1+. The script takes 3 user parameters:
   - `edge_access_keys`: JSON file containing user API keys for Edge
   - `sp_id_file`: Text file containing Service Point IDs, one id per line
   - `edge_url`: The API URL for Edge CI
