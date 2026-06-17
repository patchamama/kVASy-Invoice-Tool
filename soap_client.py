from datetime import datetime, date
from decimal import Decimal

from zeep import Client
from zeep.transports import Transport
from zeep.helpers import serialize_object
from requests import Session
from requests.auth import HTTPBasicAuth

BASE_HOST = 'http://evb.sivdc.systems:5004/ep/any'

_NS = 'http://webservice.kvasy.siv.de/'

# Service version names used by this client. Bump here when the server exposes a newer version.
SVC_INVOICE_RECEIPT = 'ias_invoice_receipt_w02'
SVC_RECHNUNGSEINGANG = 'ias_rechnungseingang_w03'
SVC_CREDITOR = 'ias_creditor_w02'

# Binding names confirmed from each service WSDL — used to override the soap:address per mandant
_BINDINGS = {
    'ias_invoice_receipt_w01': f'{{{_NS}}}IAS_INVOICE_RECEIPT_W01WebservicePortBinding',
    'ias_invoice_receipt_w02': f'{{{_NS}}}IAS_INVOICE_RECEIPT_W02WebservicePortBinding',
    'ias_rechnungseingang_w03': f'{{{_NS}}}IAS_RECHNUNGSEINGANG_W03WebservicePortBinding',
    'ias_creditor_w02':        f'{{{_NS}}}IAS_CREDITOR_W02WebservicePortBinding',
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
        svc = _client(ep, SVC_INVOICE_RECEIPT)
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
    """IAS_RECHNUNGSEINGANG_W03.geteingangrechnungen — search incoming invoices.

    Per the WSDL the method takes a single record `pi_rechnungimp` (type
    rechnungsimport_rectype). `betriebNr` is mandatory, `belegNr` is optional.
    The result record `eingangRechngenResult_rectype` contains:
      - resultrec      → processing result / error message
      - rechnungimptab → table (list) of the found invoices
    """
    svc = _client(ep, SVC_RECHNUNGSEINGANG)
    rec = {'betriebNr': company_number}
    if beleg_nr:
        rec['belegNr'] = beleg_nr

    result = svc.geteingangrechnungen(pi_rechnungimp=rec)
    data = _to_json(result) or {}

    # Surface a server-side error message instead of returning silently empty
    res = (data.get('resultrec') or {}) if isinstance(data, dict) else {}
    if res and not _result_ok(res):
        raise RuntimeError(_result_message(res))

    invoices = data.get('rechnungimptab') if isinstance(data, dict) else None
    if invoices is None:
        return []
    return invoices if isinstance(invoices, list) else [invoices]


def get_invoice(ep, document_number, company_number):
    """IAS_INVOICE_RECEIPT_W02.get_incoming_invoices — single invoice by doc+company number."""
    svc = _client(ep, SVC_INVOICE_RECEIPT)
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


def _result_ok(res):
    """defaultresult_rectype carries a status/error. Treat missing error as OK."""
    for key in ('error', 'errorcode', 'error_code', 'fehler', 'fehlercode'):
        val = res.get(key)
        if val not in (None, '', 0, '0', False):
            return False
    return True


def _result_message(res):
    for key in ('message', 'errormessage', 'error_message', 'hinweis', 'meldung', 'text'):
        val = res.get(key)
        if val:
            return str(val)
    return 'Service returned an error result'
