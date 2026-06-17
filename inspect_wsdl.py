"""
Print the exact operation signatures of a kVASy SOAP service from the live WSDL.

Use this to confirm the precise element/field names (and casing) that zeep
expects — SOAP is case-sensitive and the generated HTML docs are not reliable
for casing.

Usage (VPN active):
    .venv/bin/python inspect_wsdl.py                      # default service
    .venv/bin/python inspect_wsdl.py ias_rechnungseingang_w03
    .venv/bin/python inspect_wsdl.py ias_rechnungseingang_w03 geteingangrechnungen
"""
import sys

from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client
from zeep.transports import Transport

from config import CREDENTIALS

BASE_HOST = 'http://evb.sivdc.systems:5004/ep/any'


def main():
    service = sys.argv[1] if len(sys.argv) > 1 else 'ias_rechnungseingang_w03'
    only_op = sys.argv[2] if len(sys.argv) > 2 else None

    # Pick the first test endpoint, else the first available
    ep_id = next((k for k in CREDENTIALS if 'test1' in k), next(iter(CREDENTIALS)))
    cred = CREDENTIALS[ep_id]
    mandant = cred['url'].split('/ep/any/')[1].split('/')[0]

    wsdl = f"{BASE_HOST}/{mandant}/webservices/{service}?wsdl"
    print(f"Endpoint : {ep_id}  (mandant: {mandant})")
    print(f"WSDL     : {wsdl}\n")

    session = Session()
    session.auth = HTTPBasicAuth(cred['username'], cred['password'])
    client = Client(wsdl, transport=Transport(session=session, timeout=30))

    for svc in client.wsdl.services.values():
        for port in svc.ports.values():
            ops = port.binding._operations
            for name, op in sorted(ops.items()):
                if only_op and name != only_op:
                    continue
                print(f"── {name}")
                try:
                    print(f"   input : {op.input.signature()}")
                except Exception as e:
                    print(f"   input : <{e}>")
                try:
                    print(f"   output: {op.output.signature()}")
                except Exception as e:
                    print(f"   output: <{e}>")
                print()


if __name__ == '__main__':
    main()
