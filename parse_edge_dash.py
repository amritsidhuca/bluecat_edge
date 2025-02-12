import json
from pprint import pprint

jsond = json.load(open("bluecat_edge/edgedashdata.json"))
for customer in jsond['customers']:
    customer_found = False
    try:
        for daysdata in customer['queries']['days']:
            for day in daysdata['namespaces']:
                if 'opendns' in day['key'].lower():
                    print(customer['customer'])
                    customer_found=True
                    break
            if customer_found:
                break
    except TypeError:
        continue
    except KeyError:
        continue
