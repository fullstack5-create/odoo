"""Certificate loading and SUNAT XMLDSig signing.

SUNAT wants an enveloped signature living inside
ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent. We sign the whole
document (reference_uri="") then relocate the generated ds:Signature into
ExtensionContent; the enveloped transform excludes the Signature subtree
regardless of where it sits, so moving it after signing keeps digests valid.
"""
import datetime

from lxml import etree
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from cryptography.x509.oid import NameOID

from signxml import XMLSigner, methods

DS = 'http://www.w3.org/2000/09/xmldsig#'
EXT = 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2'
C14N = 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315'


def load_cert(pfx_bytes, password):
    """Return (key_pem, cert_pem) from a .pfx/.p12, both PEM bytes."""
    pwd = password.encode() if password else None
    key, cert, _ = pkcs12.load_key_and_certificates(pfx_bytes, pwd)
    key_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    cert_pem = cert.public_bytes(Encoding.PEM)
    return key_pem, cert_pem


def generate_self_signed(ruc='20000000001'):
    """Self-signed cert for SUNAT Beta testing. Returns (key_pem, cert_pem)."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, 'PE'),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'DEMO BETA'),
        x509.NameAttribute(NameOID.COMMON_NAME, ruc),
    ])
    now = datetime.datetime.utcnow()
    cert = (x509.CertificateBuilder()
            .subject_name(subject).issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=3650))
            .sign(key, hashes.SHA256()))
    key_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    cert_pem = cert.public_bytes(Encoding.PEM)
    return key_pem, cert_pem


def sign_document(root, key_pem, cert_pem):
    """Sign `root` (lxml Element) in place-style; return signed XML bytes.

    `root` must already contain an empty ExtensionContent placeholder.
    """
    # SUNAT accepts SHA-256; signxml blocks SHA-1 by default as insecure
    signer = XMLSigner(method=methods.enveloped,
                       signature_algorithm='rsa-sha256',
                       digest_algorithm='sha256',
                       c14n_algorithm=C14N)
    # keep only ds namespace prefix on the Signature
    signer.namespaces = {'ds': DS}
    # default enveloped reference is URI="" (whole document), which SUNAT expects
    signed_root = signer.sign(root, key=key_pem, cert=cert_pem)

    signature = signed_root.find('{%s}Signature' % DS)
    if signature is None:
        raise ValueError('signxml did not produce a Signature element')
    ext_content = signed_root.find('.//{%s}ExtensionContent' % EXT)
    if ext_content is None:
        raise ValueError('ExtensionContent placeholder missing in UBL')
    signed_root.remove(signature)
    ext_content.append(signature)
    return etree.tostring(signed_root, xml_declaration=True, encoding='ISO-8859-1', standalone=False)
