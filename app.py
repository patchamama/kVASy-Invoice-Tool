import json
import os
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_file
from flask_cors import CORS

import soap_client
from endpoints import ENDPOINTS

app = Flask(__name__)
CORS(app)

DOWNLOADS_DIR = Path(__file__).parent / 'downloads'
DOWNLOADS_DIR.mkdir(exist_ok=True)

_EP_MAP = {ep['id']: ep for ep in ENDPOINTS}


@app.get('/')
def index():
    return render_template('index.html')


@app.get('/api/endpoints')
def api_endpoints():
    return jsonify([
        {k: v for k, v in ep.items() if k != 'password'}
        for ep in ENDPOINTS
    ])


@app.post('/api/test-connection')
def api_test_connection():
    data = request.get_json(force=True)
    endpoint_id = data.get('endpoint_id', 'all')
    targets = ENDPOINTS if endpoint_id == 'all' else [_EP_MAP[endpoint_id]]

    results = []
    for ep in targets:
        t0 = datetime.now()
        result = soap_client.ping(ep)
        elapsed = round((datetime.now() - t0).total_seconds() * 1000)
        results.append({
            'id': ep['id'],
            'mandant': ep['mandant'],
            'division': ep['division'],
            'environment': ep['environment'],
            'url': ep['url'],
            'username': ep['username'],
            'ok': result['ok'],
            'error': result.get('error'),
            'latency_ms': elapsed,
        })

    return jsonify(results)


@app.get('/api/discover-companies/<endpoint_id>')
def api_discover_companies(endpoint_id):
    ep = _EP_MAP.get(endpoint_id)
    if not ep:
        return jsonify({'error': 'endpoint not found'}), 404
    try:
        companies = soap_client.discover_company_numbers(ep)
        return jsonify({'companies': companies})
    except Exception as e:
        msg = str(e)
        if '401' in msg:
            msg = ('401 Unauthorized on ias_creditor_w02 — '
                   'these credentials may not have access to the Creditor module. '
                   'Enter the company number manually instead.')
        return jsonify({'error': msg}), 500


@app.post('/api/list-invoices')
def api_list_invoices():
    data = request.get_json(force=True)
    ep = _EP_MAP.get(data.get('endpoint_id'))
    if not ep:
        return jsonify({'error': 'endpoint not found'}), 404
    company_number = data.get('company_number')
    if not company_number:
        return jsonify({'error': 'company_number required'}), 400
    try:
        invoices = soap_client.list_invoices(ep, company_number, data.get('beleg_nr') or None)
        return jsonify({'invoices': invoices, 'count': len(invoices)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.post('/api/get-invoice')
def api_get_invoice():
    data = request.get_json(force=True)
    ep = _EP_MAP.get(data.get('endpoint_id'))
    if not ep:
        return jsonify({'error': 'endpoint not found'}), 404
    try:
        invoice = soap_client.get_invoice(ep, data.get('document_number'), data.get('company_number'))
        return jsonify({'invoice': invoice})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.post('/api/download-invoice')
def api_download_invoice():
    data = request.get_json(force=True)
    ep = _EP_MAP.get(data.get('endpoint_id'))
    if not ep:
        return jsonify({'error': 'endpoint not found'}), 404

    document_number = data.get('document_number')
    company_number = data.get('company_number')
    fmt = data.get('format', 'json')

    try:
        invoice = soap_client.get_invoice(ep, document_number, company_number)
        if not invoice:
            return jsonify({'error': 'invoice not found'}), 404

        date_str = datetime.now().strftime('%Y-%m-%d')
        inv_nr = invoice.get('invoice_number') or invoice.get('rechnungNrLang') or document_number
        safe_nr = str(inv_nr).replace('/', '-').replace('\\', '-').replace(' ', '_')
        filename = f"{ep['mandant']}_{safe_nr}_{document_number}_{date_str}.{fmt}"
        filepath = DOWNLOADS_DIR / filename

        if fmt == 'json':
            filepath.write_text(json.dumps(invoice, indent=2, ensure_ascii=False), encoding='utf-8')
        else:
            filepath.write_text(_to_xml('invoice', invoice), encoding='utf-8')

        return jsonify({
            'filename': filename,
            'path': str(filepath),
            'size': filepath.stat().st_size,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _to_xml(tag, obj, depth=0):
    pad = '  ' * depth
    if isinstance(obj, dict):
        inner = '\n'.join(_to_xml(k, v, depth + 1) for k, v in obj.items() if v is not None)
        return f'{pad}<{tag}>\n{inner}\n{pad}</{tag}>'
    if isinstance(obj, list):
        return '\n'.join(_to_xml('item', v, depth) for v in obj)
    val = str(obj).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return f'{pad}<{tag}>{val}</{tag}>'


@app.get('/api/downloads')
def api_downloads():
    files = []
    for f in sorted(DOWNLOADS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.is_file():
            stat = f.stat()
            files.append({
                'filename': f.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    return jsonify({'files': files})


@app.get('/api/downloads/<path:filename>')
def api_download_file(filename):
    filepath = (DOWNLOADS_DIR / filename).resolve()
    if not str(filepath).startswith(str(DOWNLOADS_DIR.resolve())):
        abort(403)
    if not filepath.exists():
        abort(404)
    return send_file(filepath, as_attachment=True)


if __name__ == '__main__':
    port = int(os.environ.get('FLASK_RUN_PORT', 5224))
    app.run(debug=True, port=port)
