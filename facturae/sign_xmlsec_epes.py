import argparse
from base64 import b64encode
from hashlib import sha256

import lxml.etree as ET
import xmlsec
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cryptography.hazmat.primitives.serialization import Encoding

# --- Constantes de política (FACE / Facturae 3.2) ---
POLICY_URL = (
    "https://www.facturae.gob.es/politica_de_firma_formato_facturae/"
    "politica_de_firma_formato_facturae_v3_2.pdf"
)
# SHA-256 del PDF en Base64 (oficial)
POLICY_DIGEST_B64 = "jWosQPfYzbWakrLwjPY6HmpPHX2MtcG1hyin2dLQ8Ng="

NSMAP = {
    "fe": "http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "xades": "http://uri.etsi.org/01903/v1.3.2#",
}


def ensure_root_id(doc: ET._ElementTree) -> str:
    """Asegura que el elemento raíz tiene atributo Id (necesario para referencia explícita).
    Devuelve el valor establecido.
    """
    root = doc.getroot()
    if root.get("Id") is None:
        root.set("Id", "Facturae-Root-1")
    return root.get("Id")


def x509_issuer_serial_from_p12(p12_path: str, password: str):
    data = open(p12_path, "rb").read()
    key, cert, _extra = load_key_and_certificates(data, password.encode() if password else None)
    if cert is None:
        raise ValueError("El PKCS#12 no contiene certificado")

    # Serial number
    serial_number = cert.serial_number

    # Issuer in RFC4514 string (similar a RFC2253)
    issuer_name = cert.issuer.rfc4514_string()

    # DER bytes for SHA-256 digest
    cert_der = cert.public_bytes(Encoding.DER)
    cert_digest_b64 = b64encode(sha256(cert_der).digest()).decode()

    return issuer_name, str(serial_number), cert_digest_b64


def build_xades_epes(doc: ET._ElementTree, signature_node: ET._Element, root_id: str,
                      issuer_name: str, serial_number: str, cert_digest_b64: str) -> None:
    # ds:KeyInfo con X509
    key_info = xmlsec.template.ensure_key_info(signature_node)
    xmlsec.template.add_x509_data(key_info)

    # Referencia al documento raíz (enveloped + c14n exclusiva)
    ref_doc = xmlsec.template.add_reference(signature_node, xmlsec.Transform.SHA256, uri=f"#{root_id}")
    xmlsec.template.add_transform(ref_doc, xmlsec.Transform.ENVELOPED)
    xmlsec.template.add_transform(ref_doc, xmlsec.Transform.EXCL_C14N)

    # Estructura QualifyingProperties
    qp = ET.SubElement(signature_node, ET.QName(NSMAP["xades"], "QualifyingProperties"), nsmap=NSMAP)
    sig_id = signature_node.get("Id") or "Signature-1"
    signature_node.set("Id", sig_id)
    qp.set("Target", f"#{sig_id}")

    sp = ET.SubElement(qp, ET.QName(NSMAP["xades"], "SignedProperties"), Id=f"{sig_id}-SignedProperties")
    ssp = ET.SubElement(sp, ET.QName(NSMAP["xades"], "SignedSignatureProperties"))

    # SigningTime
    from datetime import datetime, timezone

    ET.SubElement(ssp, ET.QName(NSMAP["xades"], "SigningTime")).text = (
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    # SigningCertificateV2
    sc2 = ET.SubElement(ssp, ET.QName(NSMAP["xades"], "SigningCertificateV2"))
    cert_el = ET.SubElement(sc2, ET.QName(NSMAP["xades"], "Cert"))
    cert_digest = ET.SubElement(cert_el, ET.QName(NSMAP["xades"], "CertDigest"))
    dm = ET.SubElement(cert_digest, ET.QName(NSMAP["ds"], "DigestMethod"))
    dm.set("Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
    ET.SubElement(cert_digest, ET.QName(NSMAP["ds"], "DigestValue")).text = cert_digest_b64

    iser = ET.SubElement(cert_el, ET.QName(NSMAP["xades"], "IssuerSerialV2"))
    ET.SubElement(iser, ET.QName(NSMAP["xades"], "X509IssuerName")).text = issuer_name
    ET.SubElement(iser, ET.QName(NSMAP["xades"], "X509SerialNumber")).text = serial_number

    # Política de firma (EPES)
    spi = ET.SubElement(ssp, ET.QName(NSMAP["xades"], "SignaturePolicyIdentifier"))
    spid = ET.SubElement(spi, ET.QName(NSMAP["xades"], "SignaturePolicyId"))
    spid_id = ET.SubElement(spid, ET.QName(NSMAP["xades"], "SigPolicyId"))
    ET.SubElement(spid_id, ET.QName(NSMAP["xades"], "Identifier")).text = POLICY_URL

    sph = ET.SubElement(spid, ET.QName(NSMAP["xades"], "SigPolicyHash"))
    sph_dm = ET.SubElement(sph, ET.QName(NSMAP["ds"], "DigestMethod"))
    sph_dm.set("Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
    ET.SubElement(sph, ET.QName(NSMAP["ds"], "DigestValue")).text = POLICY_DIGEST_B64

    spq = ET.SubElement(spid, ET.QName(NSMAP["xades"], "SigPolicyQualifiers"))
    spq1 = ET.SubElement(spq, ET.QName(NSMAP["xades"], "SigPolicyQualifier"))
    ET.SubElement(spq1, ET.QName(NSMAP["xades"], "SPURI")).text = POLICY_URL

    # Referencia a SignedProperties (c14n exclusiva)
    ref_sp = xmlsec.template.add_reference(
        signature_node, xmlsec.Transform.SHA256, uri=f"#{sp.get('Id')}"
    )
    xmlsec.template.add_transform(ref_sp, xmlsec.Transform.EXCL_C14N)

def _x509_info_from_pem(cert_pem_path: str):
    data = open(cert_pem_path, "rb").read()
    cert = x509.load_pem_x509_certificate(data)
    serial_number = cert.serial_number
    issuer_name = cert.issuer.rfc4514_string()
    cert_der = cert.public_bytes(Encoding.DER)
    cert_digest_b64 = b64encode(sha256(cert_der).digest()).decode()
    return issuer_name, str(serial_number), cert_digest_b64


def sign_facturae(input_xml: str, output_xml: str, p12_path: str | None, p12_pass: str | None,
                  key_pem_path: str | None, cert_pem_path: str | None) -> None:
    parser = ET.XMLParser(remove_blank_text=True)
    doc = ET.parse(input_xml, parser)
    root_id = ensure_root_id(doc)

    # Crear plantilla Signature
    sign_node = xmlsec.template.create(
        doc,
        c14n_method=xmlsec.Transform.EXCL_C14N,
        sign_method=xmlsec.Transform.RSA_SHA256,
    )
    # Insertar al inicio del documento firmado (enveloped)
    doc.getroot().insert(0, sign_node)
    sign_node.set("Id", "Signature-1")

    # Construir XAdES-EPES (datos del certificado)
    if cert_pem_path:
        issuer_name, serial_number, cert_digest_b64 = _x509_info_from_pem(cert_pem_path)
    else:
        issuer_name, serial_number, cert_digest_b64 = x509_issuer_serial_from_p12(p12_path, p12_pass)
    build_xades_epes(doc, sign_node, root_id, issuer_name, serial_number, cert_digest_b64)

    # Cargar clave
    ctx = xmlsec.SignatureContext()
    if key_pem_path:
        key = xmlsec.Key.from_file(key_pem_path, xmlsec.KeyFormat.PEM)
        if cert_pem_path:
            key.load_cert_from_file(cert_pem_path, xmlsec.KeyFormat.CERT_PEM)
        ctx.key = key
    else:
        # Fallback a PKCS#12 si se proporciona (puede no estar soportado en este entorno)
        raise RuntimeError("Uso PEM requerido: proporcione --key y --crt")

    # Firmar
    ctx.sign(sign_node)

    with open(output_xml, "wb") as f:
        f.write(ET.tostring(doc, pretty_print=True, xml_declaration=True, encoding="utf-8"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Firmar Facturae 3.2.2 en XAdES-EPES (política FACE correcta)")
    ap.add_argument("--in", dest="inp", required=True, help="Facturae XML sin firma")
    ap.add_argument("--out", dest="out", required=True, help="Salida .xsig")
    ap.add_argument("--p12", dest="p12", help="Ruta al .p12/.pfx (opcional si usa PEM)")
    ap.add_argument("--pass", dest="pwd", default="", help="Password del .p12 (opcional)")
    ap.add_argument("--key", dest="key", help="Ruta clave privada PEM (recomendado)")
    ap.add_argument("--crt", dest="crt", help="Ruta certificado PEM (recomendado)")
    args = ap.parse_args()
    sign_facturae(args.inp, args.out, args.p12, args.pwd, args.key, args.crt)
