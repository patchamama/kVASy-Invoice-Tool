from datetime import datetime, date
from decimal import Decimal

from zeep import Client
from zeep.transports import Transport
from zeep.helpers import serialize_object
from requests import Session
from requests.auth import HTTPBasicAuth

BASE_HOST = 'http://evb.sivdc.systems:5004/ep/any'

# Binding names confirmed from WSDL — used to override the soap:address per mandant
_BINDINGS = {
    'ias_invoice_receipt_w01': '{http://webservice.kvasy.siv.de/}IAS_INVOICE_RECEIPT_W01WebservicePortBinding',
    'ias_creditor_w02':        '{http://webservice.kvasy.siv.de/}IAS_CREDITOR_W02WebservicePortBinding',
}


def _client(ep, service_name):
    session = Session()
    session.auth = HTTPBasicAuth(ep['username'], ep['password'])
    transport = Transport(session=session, timeout=30)

    mandant = ep['mandant']
    base = f"{BASE_HOST}/{mandant}/webservices/{service_name}"

    # Confirmed WSDL URL form: .../webservices/{service}?wsdl  (no /service suffix)
    wsdl_url = f"{base}?wsdl"
    # Actual SOAP endpoint
    endpoint_url = f"{base}/service"

    client = Client(wsdl_url, transport=transport)

    # Override soap:address so all calls go to the correct mandant URL at port 5004
    binding_name = _BINDINGS.get(service_name) or list(client.wsdl.bindings.keys())[0]
    try:
        return client.create_service(binding_name, endpoint_url)
    except Exception:
        return client.service


def _clean(obj):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def _to_json(obj):
    if obj is None:
        return None
    return _clean(serialize_object(obj, target_cls=dict))


def ping(ep):
    try:
        svc = _client(ep, 'ias_invoice_receipt_w01')
        svc.ping()
        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def discover_company_numbers(ep):
    """IAS_CREDITOR_W02.get_cred_own_customer_no() — no args → all company_numbers."""
    svc = _client(ep, 'ias_creditor_w02')
    result = svc.get_cred_own_customer_no()
    seen, out = set(), []
    for rec in (result or []):
        cn = getattr(rec, 'company_number', None)
        if cn and cn not in seen:
            seen.add(cn)
            out.append({
                'company_number': cn,
                'company_id': getattr(rec, 'company_id', None),
            })
    return out


def list_invoices(ep, company_number, beleg_nr=None):
    """IAS_RECHNUNGSEINGANG_W03.geteingangrechnungen — betriebNr mandatory, belegNr optional."""
    svc = _client(ep, 'ias_rechnungseingang_w03')
    kwargs = {'betriebNr': company_number}
    if beleg_nr:
        kwargs['belegNr'] = beleg_nr
    result = svc.geteingangrechnungen(**kwargs)
    return _to_json(result) or []


def get_invoice(ep, document_number, company_number):
    """IAS_INVOICE_RECEIPT_W01.get_incoming_invoices — single invoice by doc+company number."""
    svc = _client(ep, 'ias_invoice_receipt_w01')
    result = svc.get_incoming_invoices(
        pi_incoming_invoice_rec={
            'document_number': document_number,
            'company_number': company_number,
        }
    )
    data = _to_json(result)
    if isinstance(data, list):
        return data[0] if data else None
    return data
