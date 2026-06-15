# Template — copy this file to config.py and fill in your credentials.
# config.py is listed in .gitignore and must never be committed.
#
# Structure:
#   Each key is a logical endpoint ID: {division}_{environment}
#   Typical pattern: netz_prod, netz_test1, vertrieb_prod, seg_test2, …
#
#   url      — full SOAP service URL provided by your kVASy administrator
#   username — the account username for that endpoint
#   password — the account password (leave empty here, fill in config.py)

CREDENTIALS = {
    'division_prod':  {'url': 'http://your-host:5004/ep/any/your_mandant_prod/webservices/ias_invoice_receipt_w01/service',  'username': 'your_username_prod',  'password': ''},
    'division_test1': {'url': 'http://your-host:5004/ep/any/your_mandant_test1/webservices/ias_invoice_receipt_w01/service', 'username': 'your_username_test1', 'password': ''},
    'division_test2': {'url': 'http://your-host:5004/ep/any/your_mandant_test2/webservices/ias_invoice_receipt_w01/service', 'username': 'your_username_test2', 'password': ''},
}
