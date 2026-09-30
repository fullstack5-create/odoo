"""Build SUNAT UBL 2.1 XML for Factura/Boleta (01/03), Nota Crédito (07) y Débito (08).

Pure function of a plain dict payload (no Odoo objects) so it is unit-testable.
Scope: IGV gravado (Catálogo 07 código 10) only; one tax scheme (IGV 1000/VAT).
Leaves an empty ext:ExtensionContent for the signature (see edi_sign).
"""
from lxml import etree

NS = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
    'ds': 'http://www.w3.org/2000/09/xmldsig#',
}
ROOT_NS = {
    '01': ('Invoice', 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'),
    '03': ('Invoice', 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'),
    '07': ('CreditNote', 'urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2'),
    '08': ('DebitNote', 'urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2'),
}
IGV_SCHEME = ('1000', 'IGV', 'VAT')  # id, name, taxTypeCode (Catálogo 05)


def _q(prefix, local):
    return '{%s}%s' % (NS[prefix], local)


def _sub(parent, qname, text=None, **attrs):
    el = etree.SubElement(parent, _q(*qname.split(':')), attrs)
    if text is not None:
        el.text = str(text)
    return el


def _money(parent, qname, amount, currency):
    return _sub(parent, qname, '%.2f' % float(amount), currencyID=currency)


def _party(parent, wrapper_tag, ruc_or_doc, doc_scheme, name, address=None):
    wrap = _sub(parent, wrapper_tag)
    party = _sub(wrap, 'cac:Party')
    ident = _sub(party, 'cac:PartyIdentification')
    _sub(ident, 'cbc:ID', ruc_or_doc, schemeID=doc_scheme,
         schemeName='Documento de Identidad', schemeAgencyName='PE:SUNAT',
         schemeURI='urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06')
    legal = _sub(party, 'cac:PartyLegalEntity')
    _sub(legal, 'cbc:RegistrationName', name)
    if address:
        addr = _sub(legal, 'cac:RegistrationAddress')
        if address.get('ubigeo'):
            _sub(addr, 'cbc:ID', address['ubigeo'])
        if address.get('line'):
            line = _sub(addr, 'cac:AddressLine')
            _sub(line, 'cbc:Line', address['line'])


def _tax_total(parent, taxable, igv, currency, percent):
    tt = _sub(parent, 'cac:TaxTotal')
    _money(tt, 'cbc:TaxAmount', igv, currency)
    sub = _sub(tt, 'cac:TaxSubtotal')
    _money(sub, 'cbc:TaxableAmount', taxable, currency)
    _money(sub, 'cbc:TaxAmount', igv, currency)
    cat = _sub(sub, 'cac:TaxCategory')
    _sub(cat, 'cbc:Percent', '%.2f' % float(percent))
    _sub(cat, 'cbc:TaxExemptionReasonCode', '10')  # Catálogo 07: Gravado - Op. Onerosa
    scheme = _sub(cat, 'cac:TaxScheme')
    _sub(scheme, 'cbc:ID', IGV_SCHEME[0])
    _sub(scheme, 'cbc:Name', IGV_SCHEME[1])
    _sub(scheme, 'cbc:TaxTypeCode', IGV_SCHEME[2])


def _line(parent, p, line, idx):
    qty_tag = {'CreditNote': 'cbc:CreditedQuantity',
               'DebitNote': 'cbc:DebitedQuantity'}.get(p['_root_tag'], 'cbc:InvoicedQuantity')
    line_tag = {'CreditNote': 'cac:CreditNoteLine',
                'DebitNote': 'cac:DebitNoteLine'}.get(p['_root_tag'], 'cac:InvoiceLine')
    el = _sub(parent, line_tag)
    _sub(el, 'cbc:ID', idx)
    _sub(el, qty_tag, '%.2f' % float(line['qty']), unitCode=line.get('unit_code', 'NIU'))
    _money(el, 'cbc:LineExtensionAmount', line['line_ext'], p['currency'])
    pref = _sub(el, 'cac:PricingReference')
    alt = _sub(pref, 'cac:AlternativeConditionPrice')
    _money(alt, 'cbc:PriceAmount', line['price_with_igv'], p['currency'])
    _sub(alt, 'cbc:PriceTypeCode', '01')  # precio unitario (incluye IGV)
    _tax_total(el, line['line_ext'], line['igv_amount'], p['currency'], line['tax_pct'])
    item = _sub(el, 'cac:Item')
    _sub(item, 'cbc:Description', line['desc'])
    price = _sub(el, 'cac:Price')
    _money(price, 'cbc:PriceAmount', line['unit_price_no_igv'], p['currency'])


def build(p):
    """p: payload dict. Returns lxml root Element with empty ExtensionContent."""
    root_tag, root_ns = ROOT_NS[p['doc_type']]
    p['_root_tag'] = root_tag
    nsmap = {None: root_ns, 'cac': NS['cac'], 'cbc': NS['cbc'],
             'ext': NS['ext'], 'ds': NS['ds']}
    root = etree.Element('{%s}%s' % (root_ns, root_tag), nsmap=nsmap)

    # UBLExtensions with empty ExtensionContent (signature slot)
    exts = _sub(root, 'ext:UBLExtensions')
    ext = _sub(exts, 'ext:UBLExtension')
    _sub(ext, 'ext:ExtensionContent')

    _sub(root, 'cbc:UBLVersionID', '2.1')
    _sub(root, 'cbc:CustomizationID', '2.0')
    _sub(root, 'cbc:ID', '%s-%s' % (p['serie'], p['numero']))
    _sub(root, 'cbc:IssueDate', p['issue_date'])
    _sub(root, 'cbc:IssueTime', p.get('issue_time', '00:00:00'))
    # monto en letras
    _sub(root, 'cbc:Note', p['legend'], languageLocaleID='1000')

    if root_tag == 'Invoice':
        _sub(root, 'cbc:InvoiceTypeCode', p['doc_type'], listID='0101',
             listAgencyName='PE:SUNAT', listName='Tipo de Documento',
             listURI='urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01')
    _sub(root, 'cbc:DocumentCurrencyCode', p['currency'])

    # nota de crédito/débito: motivo + referencia
    if root_tag in ('CreditNote', 'DebitNote'):
        disc = _sub(root, 'cac:DiscrepancyResponse')
        _sub(disc, 'cbc:ReferenceID', p['ref_serie_num'])
        _sub(disc, 'cbc:ResponseCode', p['note_code'])
        _sub(disc, 'cbc:Description', p['note_reason'])
        bill = _sub(root, 'cac:BillingReference')
        ref = _sub(bill, 'cac:InvoiceDocumentReference')
        _sub(ref, 'cbc:ID', p['ref_serie_num'])
        _sub(ref, 'cbc:DocumentTypeCode', p['ref_doc_type'])

    s = p['supplier']
    _party(root, 'cac:AccountingSupplierParty', s['ruc'], '6', s['name'], s.get('address'))
    c = p['customer']
    _party(root, 'cac:AccountingCustomerParty', c['doc_num'], c['doc_type'], c['name'],
           c.get('address'))

    t = p['totals']
    _tax_total(root, t['gravada'], t['igv'], p['currency'], p.get('tax_pct', 18))

    mon = _sub(root, 'cac:LegalMonetaryTotal')
    _money(mon, 'cbc:LineExtensionAmount', t['gravada'], p['currency'])
    _money(mon, 'cbc:TaxInclusiveAmount', t['total'], p['currency'])
    _money(mon, 'cbc:PayableAmount', t['total'], p['currency'])

    for i, line in enumerate(p['lines'], start=1):
        _line(root, p, line, i)

    return root
