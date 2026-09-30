{
    'name': "Perú EDI SUNAT Beta (Python)",
    'summary': "Facturación electrónica SUNAT en Python puro: UBL 2.1, firma XMLDSig, "
               "envío SOAP y CDR. Factura, Boleta, Nota de Crédito y Débito. Ambiente Beta.",
    'description': """
Integración pura-Python (sin OSE/PSE ni PHP) para emitir comprobantes electrónicos a SUNAT:

* Factura (01), Boleta (03), Nota de Crédito (07), Nota de Débito (08).
* Genera XML UBL 2.1 y lo firma (XMLDSig enveloped, RSA-SHA1, C14N) dentro de UBLExtensions.
* Empaqueta en ZIP y envía por SOAP a billService (WS-Security UsernameToken, clave SOL).
* Recibe y guarda el CDR (Constancia de Recepción) con estado aceptado/rechazado.
* Solo IGV gravado (Catálogo 07 código 10). Ambiente por defecto: Beta (pruebas).

Requiere: signxml, lxml, cryptography, requests. Para pruebas usa certificado autofirmado
generado al vuelo y usuario SOL de Beta (MODDATOS / moddatos).
    """,
    'version': '18.0.1.0.0',
    'author': "Claude",
    'category': 'Accounting/Localizations/EDI',
    'license': 'LGPL-3',
    'depends': ['l10n_pe', 'account', 'l10n_latam_invoice_document'],
    'external_dependencies': {
        'python': ['signxml', 'lxml', 'cryptography', 'requests'],
    },
    'data': [
        'views/res_company_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
}
