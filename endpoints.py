from urllib.parse import urlparse

try:
    from config import CREDENTIALS
except ImportError:
    CREDENTIALS = {}
    import warnings
    warnings.warn("config.py not found — copy config.example.py to config.py and fill in passwords")

_DIVISION_MAP = {
    'netz':     'Netz',
    'vertrieb': 'Vertrieb',
    'seg':      'SEG',
}


def _mandant(url: str) -> str:
    """Extract mandant from URL: .../ep/any/{mandant}/webservices/..."""
    parts = urlparse(url).path.split('/')
    try:
        return parts[parts.index('any') + 1]
    except (ValueError, IndexError):
        return ''


def _parse_id(ep_id: str) -> tuple[str, str]:
    """'netz_prod' → ('netz', 'prod')  |  'vertrieb_test1' → ('vertrieb', 'test1')"""
    parts = ep_id.rsplit('_', 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (ep_id, '')


ENDPOINTS: list[dict] = []
for _id, _cred in CREDENTIALS.items():
    _div_key, _env = _parse_id(_id)
    ENDPOINTS.append({
        'id':          _id,
        'mandant':     _mandant(_cred['url']),
        'division':    _DIVISION_MAP.get(_div_key, _div_key.title()),
        'environment': _env,
        'url':         _cred['url'],
        'username':    _cred['username'],
        'password':    _cred['password'],
    })
