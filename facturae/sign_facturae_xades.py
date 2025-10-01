#!/usr/bin/env python3
"""Firma Facturae 3.2.2 con XAdES-BES usando únicamente lxml + cryptography."""

import argparse
import base64
import copy
import datetime
import hashlib
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from lxml import etree

from facturae.politica import get_politica_facturae

NS = {
    "fe": "http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "xades": "http://uri.etsi.org/01903/v1.3.2#",
}

C14N_ALGORITHM = "http://www.w3.org/2001/10/xml-exc-c14n#"
SIGNATURE_METHOD = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
DIGEST_METHOD = "http://www.w3.org/2001/04/xmlenc#sha256"
ENVELOPED_TRANSFORM = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
SIGNED_PROPS_TYPE = "http://uri.etsi.org/01903#SignedProperties"


def pfx_to_pem(pfx_path: Path, password: str):
    with pfx_path.open("rb") as f:
        pfx_data = f.read()

    password_bytes = password.encode("utf-8") if password else None
    private_key, cert, additional_certs = load_key_and_certificates(pfx_data, password_bytes)

    if private_key is None or cert is None:
        raise ValueError("No se pudo extraer clave/certificado del PFX. Verifica la contraseña y el archivo.")

    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)

    chain_pems = []
    if additional_certs:
        for c in additional_certs:
            chain_pems.append(c.public_bytes(serialization.Encoding.PEM))

    return key_pem, cert_pem, chain_pems


def canonicalize(element: etree._Element) -> bytes:
    return etree.tostring(element, method="c14n", exclusive=True, with_comments=False)


def pem_to_b64(pem_bytes: bytes) -> str:
    lines = [line.strip() for line in pem_bytes.decode("ascii").splitlines() if "---" not in line]
    return "".join(lines)


def build_xades_properties(signature_node: etree._Element, cert: x509.Certificate) -> etree._Element:
    sig_id = signature_node.get("Id")
    if not sig_id:
        sig_id = "Signature-" + datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        signature_node.set("Id", sig_id)

    qualifying = etree.SubElement(signature_node, etree.QName(NS["ds"], "Object"))
    qual_props = etree.SubElement(qualifying, etree.QName(NS["xades"], "QualifyingProperties"))
    qual_props.set("Target", f"#{sig_id}")

    signed_props = etree.SubElement(qual_props, etree.QName(NS["xades"], "SignedProperties"))
    signed_props_id = f"{sig_id}-SignedProperties"
    signed_props.set("Id", signed_props_id)

    ssp = etree.SubElement(signed_props, etree.QName(NS["xades"], "SignedSignatureProperties"))

    signing_time = etree.SubElement(ssp, etree.QName(NS["xades"], "SigningTime"))
    signing_time.text = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # SigningCertificateV2 con IssuerSerialV2 completo
    sc2 = etree.SubElement(ssp, etree.QName(NS["xades"], "SigningCertificateV2"))
    cert_el = etree.SubElement(sc2, etree.QName(NS["xades"], "Cert"))
    cert_digest = etree.SubElement(cert_el, etree.QName(NS["xades"], "CertDigest"))
    digest_method = etree.SubElement(cert_digest, etree.QName(NS["ds"], "DigestMethod"))
    digest_method.set("Algorithm", DIGEST_METHOD)
    digest_value = etree.SubElement(cert_digest, etree.QName(NS["ds"], "DigestValue"))
    digest_value.text = base64.b64encode(cert.fingerprint(hashes.SHA256())).decode("ascii")

    isv2 = etree.SubElement(cert_el, etree.QName(NS["xades"], "IssuerSerialV2"))
    issuer_name = cert.issuer.rfc4514_string()
    serial_number = str(cert.serial_number)
    etree.SubElement(isv2, etree.QName(NS["xades"], "X509IssuerName")).text = issuer_name
    etree.SubElement(isv2, etree.QName(NS["xades"], "X509SerialNumber")).text = serial_number

    policy = get_politica_facturae("3.2")
    sig_policy_identifier = etree.SubElement(ssp, etree.QName(NS["xades"], "SignaturePolicyIdentifier"))
    sig_policy_id = etree.SubElement(sig_policy_identifier, etree.QName(NS["xades"], "SignaturePolicyId"))
    sig_policy = etree.SubElement(sig_policy_id, etree.QName(NS["xades"], "SigPolicyId"))
    policy_identifier = etree.SubElement(sig_policy, etree.QName(NS["xades"], "Identifier"))
    policy_identifier.text = policy.get("identifier_url", policy["identifier"])

    sig_policy_hash = etree.SubElement(sig_policy_id, etree.QName(NS["xades"], "SigPolicyHash"))
    policy_digest_method = etree.SubElement(sig_policy_hash, etree.QName(NS["ds"], "DigestMethod"))
    policy_digest_method.set("Algorithm", policy["hash_algorithm"])
    policy_digest_value = etree.SubElement(sig_policy_hash, etree.QName(NS["ds"], "DigestValue"))
    policy_digest_value.text = policy["hash_value"]

    # Añadir calificador SPURI apuntando a la URL oficial (algunos validadores lo esperan)
    sig_policy_qualifiers = etree.SubElement(sig_policy_id, etree.QName(NS["xades"], "SigPolicyQualifiers"))
    spq = etree.SubElement(sig_policy_qualifiers, etree.QName(NS["xades"], "SigPolicyQualifier"))
    spuri = etree.SubElement(spq, etree.QName(NS["xades"], "SPURI"))
    spuri.text = policy.get("identifier_url", policy["identifier"])

    return signed_props


def compute_sha256_digest(element: etree._Element) -> str:
    data = canonicalize(element)
    return base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")


def compute_document_digest(root: etree._Element) -> str:
    # Calcula el digest del elemento raíz (referenciado por Id) aplicando enveloped + c14n exclusiva
    doc_copy = copy.deepcopy(root)
    # eliminar ds:Signature (enveloped)
    for sig in doc_copy.xpath(".//ds:Signature", namespaces=NS):
        parent = sig.getparent()
        if parent is not None:
            parent.remove(sig)
    data = canonicalize(doc_copy)
    return base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")


def sign_with_xmlsec(xml_bytes: bytes, key_pem: bytes, cert_pem: bytes, chain_pems: list[bytes]) -> bytes:
    parser = etree.XMLParser(remove_blank_text=False)
    root = etree.fromstring(xml_bytes, parser=parser)
    tree = root.getroottree()

    placeholder = root.find("./ds:Signature[@Id='SignaturePlaceholder']", namespaces=NS)
    if placeholder is not None:
        placeholder.getparent().remove(placeholder)

    sig_id = "Signature-" + datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    signature_node = etree.Element(etree.QName(NS["ds"], "Signature"))
    signature_node.set("Id", sig_id)

    signed_info = etree.SubElement(signature_node, etree.QName(NS["ds"], "SignedInfo"))
    canon_method = etree.SubElement(signed_info, etree.QName(NS["ds"], "CanonicalizationMethod"))
    canon_method.set("Algorithm", C14N_ALGORITHM)

    sig_method = etree.SubElement(signed_info, etree.QName(NS["ds"], "SignatureMethod"))
    sig_method.set("Algorithm", SIGNATURE_METHOD)

    # Referencia al documento completo (URI vacía) con transforms
    ref_doc = etree.SubElement(signed_info, etree.QName(NS["ds"], "Reference"))
    ref_doc.set("URI", "")
    transforms = etree.SubElement(ref_doc, etree.QName(NS["ds"], "Transforms"))
    t_env = etree.SubElement(transforms, etree.QName(NS["ds"], "Transform"))
    t_env.set("Algorithm", ENVELOPED_TRANSFORM)
    t_c14n = etree.SubElement(transforms, etree.QName(NS["ds"], "Transform"))
    t_c14n.set("Algorithm", C14N_ALGORITHM)
    dm_doc = etree.SubElement(ref_doc, etree.QName(NS["ds"], "DigestMethod"))
    dm_doc.set("Algorithm", DIGEST_METHOD)
    dv_doc = etree.SubElement(ref_doc, etree.QName(NS["ds"], "DigestValue"))

    ref_props = etree.SubElement(signed_info, etree.QName(NS["ds"], "Reference"))
    ref_props.set("Type", SIGNED_PROPS_TYPE)
    ref_props.set("URI", f"#{sig_id}-SignedProperties")
    # Añadir Transforms con c14n exclusiva para SignedProperties (requisito XAdES)
    transforms_props = etree.SubElement(ref_props, etree.QName(NS["ds"], "Transforms"))
    t_props_c14n = etree.SubElement(transforms_props, etree.QName(NS["ds"], "Transform"))
    t_props_c14n.set("Algorithm", C14N_ALGORITHM)
    dm_props = etree.SubElement(ref_props, etree.QName(NS["ds"], "DigestMethod"))
    dm_props.set("Algorithm", DIGEST_METHOD)
    dv_props = etree.SubElement(ref_props, etree.QName(NS["ds"], "DigestValue"))

    signature_value_el = etree.SubElement(signature_node, etree.QName(NS["ds"], "SignatureValue"))

    key_info = etree.SubElement(signature_node, etree.QName(NS["ds"], "KeyInfo"))
    x509_data = etree.SubElement(key_info, etree.QName(NS["ds"], "X509Data"))
    primary_cert_el = etree.SubElement(x509_data, etree.QName(NS["ds"], "X509Certificate"))
    primary_cert_el.text = pem_to_b64(cert_pem)

    for cpem in chain_pems or []:
        extra_cert_el = etree.SubElement(x509_data, etree.QName(NS["ds"], "X509Certificate"))
        extra_cert_el.text = pem_to_b64(cpem)

    cert = x509.load_pem_x509_certificate(cert_pem)
    signed_props = build_xades_properties(signature_node, cert)

    # Importante: anexar la firma al árbol ANTES de calcular los digests,
    # para que la c14n tenga el mismo contexto de namespaces que tendrá al verificar.
    root.append(signature_node)

    # Ahora calcular los digests
    dv_doc.text = compute_document_digest(root)
    dv_props.text = compute_sha256_digest(signed_props)

    signed_info_c14n = canonicalize(signed_info)

    private_key = serialization.load_pem_private_key(key_pem, password=None)
    signature_bytes = private_key.sign(
        signed_info_c14n,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    signature_value_el.text = base64.b64encode(signature_bytes).decode("ascii")

    return etree.tostring(root.getroottree(), encoding="UTF-8", xml_declaration=True, pretty_print=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", required=True, help="Ruta al Facturae 3.2.2 XML sin firmar")
    parser.add_argument("--pfx", required=True, help="Ruta al fichero .p12/.pfx con clave y certificado")
    parser.add_argument("--password", required=True, help="Contraseña del .p12/.pfx")
    parser.add_argument("--out", required=True, help="Ruta de salida del XML firmado")
    args = parser.parse_args()

    xml_path = Path(args.xml)
    pfx_path = Path(args.pfx)
    out_path = Path(args.out)

    xml_bytes = xml_path.read_bytes()
    key_pem, cert_pem, chain_pems = pfx_to_pem(pfx_path, args.password)

    signed_xml = sign_with_xmlsec(xml_bytes, key_pem, cert_pem, chain_pems)

    out_path.write_bytes(signed_xml)
    print(f"OK: firmado XAdES-BES -> {out_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"ERROR: {exc}\n")
        sys.exit(1)
