# kVASy Invoice Tool

A lightweight web-based tool for browsing and downloading invoices from a kVASy SOAP web service (`ias_invoice_receipt_w01`). Built with Python/Flask on the backend and plain HTML/JS (Tailwind) on the frontend. No database required.

---

## Features

- Test connectivity to all configured endpoints with a single click
- Auto-discover company numbers via `ias_creditor_w01`
- Browse, filter, and paginate incoming invoices
- Download invoices as JSON or XML
- Built-in CLI diagnostic script to troubleshoot network/SOAP issues step by step

---

## Requirements

- Python 3.11 or newer
- Network access to your kVASy host (VPN may be required — ask your administrator)
- Your SOAP credentials (URL, username, password per endpoint)

---

## Installation from scratch

### Windows (recommended — one-click installer)

1. Install Git if you don't have it — open PowerShell and run:
   ```powershell
   Invoke-WebRequest -Uri "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/Git-2.47.1-64-bit.exe" -OutFile "$env:TEMP\git-installer.exe"
   Start-Process "$env:TEMP\git-installer.exe" -ArgumentList "/SILENT" -Wait
   ```
   Then close and reopen the terminal so Git is available on PATH.
2. Open a terminal in the folder where you want to install the tool and clone the repo:
   ```cmd
   git clone https://github.com/patchamama/kVASy-Invoice-Tool.git
   cd kVASy-Invoice-Tool
   ```
3. Double-click **`install.bat`**

The installer will:
- Check if Python 3.11+ is installed; if not, download and install it automatically (via `winget` or direct download from python.org)
- Create a virtual environment in `.venv\`
- Install all Python dependencies
- Create `config.py` from the template if it doesn't exist yet
- Launch the app at `http://localhost:5224`

> After the first run, use **`start.bat`** to start the app — no need to run the installer again.

### Linux / macOS

```bash
git clone https://github.com/patchamama/kVASy-Invoice-Tool.git
cd kVASy-Invoice-Tool
cp config.example.py config.py
```

Then edit `config.py` and fill in your credentials (see [Configuration](#configuration) below).

---

## Configuration

`config.py` is the only file you need to edit. It is excluded from version control (`.gitignore`) and must never be committed.

Copy the template and fill in your values:

```bash
cp config.example.py config.py
```

Edit `config.py`:

```python
CREDENTIALS = {
    'netz_prod': {
        'url':      'http://your-host:5004/ep/any/your_mandant_prod/webservices/ias_invoice_receipt_w01/service',
        'username': 'your_username_prod',
        'password': 'your_password',
    },
    'netz_test1': {
        'url':      'http://your-host:5004/ep/any/your_mandant_test1/webservices/ias_invoice_receipt_w01/service',
        'username': 'your_username_test1',
        'password': 'your_password',
    },
    # Add as many endpoints as needed — one per mandant/environment combination.
    # Key format: {division}_{environment}  e.g. vertrieb_prod, seg_test2
}
```

**Key naming convention:** `{division}_{environment}` — for example `netz_prod`, `vertrieb_test1`, `seg_test2`. The tool uses these names to group results by division in the UI.

---

## Running on Windows

Double-click `start.bat` or run it from a terminal:

```cmd
start.bat
```

The script will:
1. Check that Python is installed and on `PATH`
2. Create a virtual environment in `.venv\` if it doesn't exist
3. Install all dependencies from `requirements.txt`
4. Show a menu — choose to run the diagnostic or start the web app

> **First run:** if `config.py` is missing, the script will warn you before launching.

---

## Running on Linux / macOS

```bash
chmod +x start.sh
./start.sh
```

The script creates `.venv/`, installs dependencies, and opens the app at `http://localhost:5224`.

---

## Running the diagnostic

The diagnostic script tests each connection layer independently — useful when you're not sure whether the problem is DNS, TCP, authentication, or the WSDL itself.

**Windows:**

```cmd
.venv\Scripts\python.exe diagnose.py
```

Or choose option `1` from `start.bat`.

**Linux / macOS:**

```bash
.venv/bin/python diagnose.py
```

### What the diagnostic checks

| Step | What it tests |
|------|--------------|
| 1 | DNS resolution of the kVASy host |
| 2 | TCP connection on port 5004 |
| 3 | HTTP webservices listing (authenticated) |
| 4 | WSDL fetch — tries both `?wsdl` and `/service?wsdl` URL forms |
| 5 | Raw SOAP `ping` call (no zeep, plain HTTP) |
| 6 | Full zeep client with WSDL + endpoint override |

If Step 1 fails, check that your VPN is connected and that DNS resolves the host name.

---

## Project structure

```
kVASy-Invoice-Tool/
├── app.py               # Flask backend — REST API for the frontend
├── soap_client.py       # zeep-based SOAP client (ping, list, get invoices)
├── endpoints.py         # Builds endpoint list from CREDENTIALS
├── diagnose.py          # Standalone connection diagnostic script
├── config.example.py    # Credentials template — copy to config.py
├── config.py            # Your credentials (gitignored, never commit)
├── requirements.txt     # Python dependencies
├── VERSION              # Current version string
├── start.sh             # Linux/macOS launcher
├── start.bat            # Windows launcher (menu: diagnostic / app)
├── install.bat          # Windows one-click installer (double-click to run)
├── install.ps1          # PowerShell installer script (called by install.bat)
├── templates/
│   └── index.html       # Single-page frontend (Tailwind CSS)
├── static/
│   └── app.js           # Frontend logic
└── downloads/           # Saved invoice files (gitignored)
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `flask` | Web framework / REST API |
| `flask-cors` | CORS headers for local development |
| `zeep` | SOAP client |
| `requests` | HTTP transport for zeep and diagnostic |
| `lxml` | XML parsing backend for zeep |

Install manually if needed:

```bash
pip install -r requirements.txt
```

---

## Troubleshooting

**DNS resolution fails (`[Errno -2] Name or service not known`)**
VPN is not connected, or WSL2 is not using the VPN's DNS server. Run the diagnostic from Windows PowerShell first to confirm whether the issue is Windows-level or WSL2-level.

**HTTP 401 on all endpoints**
Wrong username or password in `config.py`.

**WSDL fetch returns 404**
The mandant path in the URL is incorrect. Check the URL format with your kVASy administrator.

**zeep error: `No operations found`**
The WSDL loaded but the binding name doesn't match. The diagnostic Step 6 will print the available bindings for debugging.

---

## Version

See [`VERSION`](VERSION) for the current version number.
