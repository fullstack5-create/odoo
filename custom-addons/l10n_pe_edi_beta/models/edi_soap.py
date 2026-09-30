"""ZIP packaging, SOAP sendBill to SUNAT, and CDR parsing. Uses requests only."""
import base64
import io
import zipfile

import requests
from lxml import etree

BETA_URL = 'https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService'
PROD_URL = 'https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService'

SOAP_NS = 'http://schemas.xmlsoap.org/soap/envelope/'
SER_NS = 'http://service.sunat.gob.pe'
WSSE = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd'
CBC = 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'

_ENVELOPE = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{soap}" xmlns:ser="{ser}" xmlns:wsse="{wsse}">
  <soapenv:Header>
    <wsse:Security>
      <wsse:UsernameToken>
        <wsse:Username>{user}</wsse:Username>
        <wsse:Password>{password}</wsse:Password>
      </wsse:UsernameToken>
    </wsse:Security>
  </soapenv:Header>
  <soapenv:Body>
    <ser:sendBill>
      <fileName>{filename}</fileName>
      <contentFile>{content}</contentFile>
    </ser:sendBill>
  </soapenv:Body>
</soapenv:Envelope>"""


def zip_document(xml_bytes, base_name):
    """Return zip bytes with <base_name>.xml at the archive root."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('%s.xml' % base_name, xml_bytes)
    return buf.getvalue()


def send_bill(zip_bytes, base_name, sol_user, sol_pass, production=False):
    """POST sendBill. Returns dict with accepted/code/description/cdr_zip/raw."""
    envelope = _ENVELOPE.format(
        soap=SOAP_NS, ser=SER_NS, wsse=WSSE,
        user=sol_user, password=sol_pass,
        filename='%s.zip' % base_name,
        content=base64.b64encode(zip_bytes).decode(),
    )
    url = PROD_URL if production else BETA_URL
    resp = requests.post(
        url, data=envelope.encode('utf-8'),
        headers={'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': ''},
        timeout=60,
    )
    return _parse_response(resp.status_code, resp.content)


def _parse_response(status, content):
    out = {'http_status': status, 'raw': content, 'accepted': False,
           'code': None, 'description': None, 'cdr_zip': None}
    try:
        root = etree.fromstring(content)
    except Exception as e:
        out['description'] = 'Respuesta no XML: %s' % e
        return out

    fault = root.find('.//{%s}Fault' % SOAP_NS)
    if fault is not None:
        code = fault.findtext('faultcode') or ''
        msg = fault.findtext('faultstring') or ''
        out['code'] = code.strip()
        out['description'] = msg.strip()
        return out

    app_resp = root.find('.//applicationResponse')
    if app_resp is None or not (app_resp.text or '').strip():
        out['description'] = 'Sin applicationResponse en la respuesta'
        return out

    cdr_zip = base64.b64decode(app_resp.text)
    out['cdr_zip'] = cdr_zip
    with zipfile.ZipFile(io.BytesIO(cdr_zip)) as zf:
        name = next((n for n in zf.namelist() if n.lower().endswith('.xml')), None)
        cdr_xml = zf.read(name) if name else b''
    cdr = etree.fromstring(cdr_xml)
    out['code'] = (cdr.findtext('.//{%s}ResponseCode' % CBC) or '').strip()
    out['description'] = (cdr.findtext('.//{%s}Description' % CBC) or '').strip()
    out['accepted'] = out['code'] == '0'
    return out
