"""
Standalone connection diagnostic — run this when VPN is active:
    .venv/bin/python diagnose.py

Tests each step independently so you can see exactly where it fails.
"""
import socket
import sys
import time
import urllib.request
import urllib.error

try:
    import requests
    from requests.auth import HTTPBasicAuth
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from zeep import Client
    from zeep.transports import Transport
    HAS_ZEEP = True
except ImportError:
    HAS_ZEEP = False

from config import CREDENTIALS

HOST = 'evb.sivdc.systems'
PORT = 5004

PING_SOAP = '''<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:web="http://webservice.kvasy.siv.de/">
  <soapenv:Header/>
  <soapenv:Body>
    <web:ping/>
  </soapenv:Body>
</soapenv:Envelope>'''


def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


def ok(msg):    print(f"  ✓  {msg}")
def fail(msg):  print(f"  ✗  {msg}")
def info(msg):  print(f"  ·  {msg}")


# ── Step 1: DNS ───────────────────────────────────────────────────
section(f"Step 1 — DNS resolution: {HOST}")
try:
    ip = socket.gethostbyname(HOST)
    ok(f"Resolved to {ip}")
except socket.gaierror as e:
    fail(f"DNS failed: {e}")
    print("\n  → Make sure VPN is connected and resolves 'evb.sivdc.systems'")
    sys.exit(1)


# ── Step 2: TCP port ──────────────────────────────────────────────
section(f"Step 2 — TCP connect: {HOST}:{PORT}")
try:
    sock = socket.create_connection((HOST, PORT), timeout=10)
    sock.close()
    ok(f"TCP port {PORT} reachable")
except (OSError, socket.timeout) as e:
    fail(f"TCP connect failed: {e}")
    sys.exit(1)


# ── Step 3: Webservices listing (no auth) ────────────────────────
section("Step 3 — Webservices listing (shows available mandants/services)")
for ep_id, cred in list(CREDENTIALS.items())[:3]:   # first 3 only
    mandant = cred['url'].split('/ep/any/')[1].split('/')[0]
    listing_url = f"http://{HOST}:{PORT}/ep/any/{mandant}/webservices/"
    try:
        req = urllib.request.Request(listing_url)
        req.add_header('Authorization',
                       'Basic ' + __import__('base64').b64encode(
                           f"{cred['username']}:{cred['password']}".encode()).decode())
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read(500).decode('utf-8', errors='replace')
            ok(f"{mandant}: HTTP {r.status} — {len(body)} bytes")
    except urllib.error.HTTPError as e:
        fail(f"{mandant}: HTTP {e.code} — {e.reason}")
    except Exception as e:
        fail(f"{mandant}: {e}")


# ── Step 4: WSDL fetch (raw HTTP) ────────────────────────────────
section("Step 4 — WSDL fetch: ias_invoice_receipt_w01")
test_ep = None
for ep_id, cred in CREDENTIALS.items():
    if 'test1' in ep_id:
        test_ep = (ep_id, cred)
        break
if not test_ep:
    test_ep = list(CREDENTIALS.items())[0]

ep_id, cred = test_ep
mandant = cred['url'].split('/ep/any/')[1].split('/')[0]

# Confirmed working form from WSDL: ?wsdl (no /service suffix)
# /service?wsdl kept as fallback for compatibility
wsdl_variants = [
    f"http://{HOST}:{PORT}/ep/any/{mandant}/webservices/ias_invoice_receipt_w01?wsdl",
    f"http://{HOST}:{PORT}/ep/any/{mandant}/webservices/ias_invoice_receipt_w01/service?wsdl",
]

working_wsdl = None
for wsdl_url in wsdl_variants:
    try:
        if HAS_REQUESTS:
            r = requests.get(wsdl_url, auth=HTTPBasicAuth(cred['username'], cred['password']),
                             timeout=15)
            if r.status_code == 200 and 'wsdl' in r.text.lower():
                ok(f"WSDL OK [{r.status_code}]: {wsdl_url}")
                working_wsdl = wsdl_url
                # Show soap:address location from WSDL
                import re
                loc = re.search(r'location="([^"]+)"', r.text)
                if loc:
                    info(f"soap:address location in WSDL → {loc.group(1)}")
                break
            else:
                fail(f"HTTP {r.status_code}: {wsdl_url}")
        else:
            req = urllib.request.Request(wsdl_url)
            req.add_header('Authorization',
                           'Basic ' + __import__('base64').b64encode(
                               f"{cred['username']}:{cred['password']}".encode()).decode())
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read()
                if b'wsdl' in body.lower():
                    ok(f"WSDL OK [{resp.status}]: {wsdl_url}")
                    working_wsdl = wsdl_url
                    break
                else:
                    fail(f"Response not a WSDL: {wsdl_url}")
    except Exception as e:
        fail(f"{wsdl_url}\n      {e}")


# ── Step 5: Raw SOAP ping via curl-equivalent ────────────────────
section("Step 5 — Raw SOAP ping (no zeep)")
service_url = f"http://{HOST}:{PORT}/ep/any/{mandant}/webservices/ias_invoice_receipt_w01/service"
if HAS_REQUESTS:
    try:
        t0 = time.time()
        r = requests.post(
            service_url,
            data=PING_SOAP.encode('utf-8'),
            headers={'Content-Type': 'text/xml;charset=UTF-8',
                     'SOAPAction': '"ping"'},
            auth=HTTPBasicAuth(cred['username'], cred['password']),
            timeout=30,
        )
        elapsed = round((time.time() - t0) * 1000)
        if r.status_code == 200:
            ok(f"SOAP ping → HTTP 200 ({elapsed} ms)")
            if 'pingResponse' in r.text or 'ping' in r.text.lower():
                ok("Response contains ping/pingResponse — service is alive!")
            info(f"Response snippet: {r.text[:200]}")
        else:
            fail(f"SOAP ping → HTTP {r.status_code}")
            info(f"Body: {r.text[:400]}")
    except Exception as e:
        fail(f"SOAP ping failed: {e}")
else:
    info("requests not installed — skipping raw SOAP test")


# ── Step 6: zeep client ───────────────────────────────────────────
section("Step 6 — zeep client")
if not HAS_ZEEP:
    fail("zeep not installed")
elif not working_wsdl:
    fail("No working WSDL URL found in Step 4 — cannot test zeep")
else:
    try:
        session = __import__('requests').Session()
        session.auth = HTTPBasicAuth(cred['username'], cred['password'])
        transport = Transport(session=session, timeout=30)
        client = Client(working_wsdl, transport=transport)

        # Show bindings found in WSDL
        bindings = list(client.wsdl.bindings.keys())
        info(f"WSDL bindings: {bindings}")

        # Override endpoint URL
        if bindings:
            svc = client.create_service(bindings[0], service_url)
        else:
            svc = client.service

        t0 = time.time()
        svc.ping()
        elapsed = round((time.time() - t0) * 1000)
        ok(f"zeep ping() succeeded! ({elapsed} ms)")
        ok(f"Using endpoint: {ep_id} / {mandant}")
    except Exception as e:
        fail(f"zeep error: {e}")
        info("Check the soap:address location printed in Step 4 above")


# ── Summary ───────────────────────────────────────────────────────
section("Done")
print()
