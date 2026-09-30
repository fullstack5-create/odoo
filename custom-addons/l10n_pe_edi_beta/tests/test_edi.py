"""Offline checks for the SUNAT EDI pipeline (no network to SUNAT)."""
from lxml import etree
from signxml import XMLVerifier

from odoo.tests import TransactionCase, tagged
from odoo.addons.l10n_pe_edi_beta.models import edi_ubl, edi_sign
from odoo.addons.l10n_pe_edi_beta.models.edi_num2words import amount_to_words

DS = 'http://www.w3.org/2000/09/xmldsig#'
EXT = 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2'
CAC = 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'

_PAYLOAD = {
    'doc_type': '01', 'serie': 'F001', 'numero': '00000001',
    'issue_date': '2026-09-30', 'issue_time': '00:00:00', 'currency': 'PEN',
    'supplier': {'ruc': '20000000001', 'name': 'DEMO SAC', 'address': {'line': 'AV 1'}},
    'customer': {'doc_type': '6', 'doc_num': '20100070970', 'name': 'CLIENTE SAC',
                 'address': {'line': 'AV 2'}},
    'lines': [{'desc': 'Serv', 'qty': 2, 'unit_code': 'ZZ', 'line_ext': 2000.0,
               'igv_amount': 360.0, 'unit_price_no_igv': 1000.0,
               'price_with_igv': 1180.0, 'tax_pct': 18}],
    'totals': {'gravada': 2000.0, 'igv': 360.0, 'total': 2360.0},
    'tax_pct': 18, 'legend': amount_to_words(2360.0),
}


@tagged('post_install', '-at_install')
class TestSunatEdi(TransactionCase):

    def test_amount_to_words(self):
        self.assertEqual(amount_to_words(2360.0),
                         'DOS MIL TRESCIENTOS SESENTA CON 00/100 SOLES')
        self.assertEqual(amount_to_words(100.5), 'CIEN CON 50/100 SOLES')

    def test_invoice_signs_and_verifies(self):
        root = edi_ubl.build(dict(_PAYLOAD))
        key, cert = edi_sign.generate_self_signed('20000000001')
        signed = edi_sign.sign_document(root, key, cert)
        tree = etree.fromstring(signed)
        sig = tree.find('.//{%s}ExtensionContent/{%s}Signature' % (EXT, DS))
        self.assertIsNotNone(sig, 'signature must sit inside ExtensionContent')
        # raises if invalid
        XMLVerifier().verify(tree, x509_cert=cert, expect_references=1)

    def test_credit_note_structure(self):
        p = dict(_PAYLOAD, doc_type='07', ref_serie_num='F001-00000001',
                 ref_doc_type='01', note_code='01', note_reason='Anulacion')
        root = edi_ubl.build(p)
        self.assertTrue(root.tag.endswith('CreditNote'))
        self.assertIsNotNone(root.find('.//{%s}CreditNoteLine' % CAC))
        self.assertIsNotNone(root.find('.//{%s}DiscrepancyResponse' % CAC))
