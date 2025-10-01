from pathlib import Path
from typing import List

from cryptography.hazmat.primitives import serialization

from facturae.sign_facturae_xades import sign_with_xmlsec


def corregir_etiqueta_n_por_name(ruta_xml: str) -> None:
    """Compatibilidad con versiones anteriores: no aplica cambios."""
    return


def leer_contenido_xsig(ruta_xsig: str) -> str:
    with open(ruta_xsig, "rb") as f:
        return f.read().decode("utf-8", errors="ignore")


def _load_private_key(path: str, password: str | None) -> bytes:
    key_bytes = Path(path).read_bytes()
    password_bytes = password.encode("utf-8") if password else None
    private_key = serialization.load_pem_private_key(key_bytes, password=password_bytes)
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _split_pem_certificates(pem_bytes: bytes) -> List[bytes]:
    pem_text = pem_bytes.decode("utf-8")
    certificates: List[bytes] = []
    block = []
    inside = False
    for line in pem_text.splitlines():
        if "-----BEGIN CERTIFICATE-----" in line:
            inside = True
            block = [line]
        elif "-----END CERTIFICATE-----" in line and inside:
            block.append(line)
            certificates.append("\n".join(block).encode("utf-8") + b"\n")
            inside = False
            block = []
        elif inside:
            block.append(line)

    if not certificates and pem_bytes:
        certificates.append(pem_bytes)
    return certificates


def firmar_xml(
    ruta_xml: str,
    ruta_clave_privada: str,
    ruta_certificado_publico: str,
    password: str = "",
    alias: str | None = None,
    af_cli: str | None = None,
) -> bytes:
    """Firma un archivo XML Facturae y devuelve los bytes firmados (XAdES-BES)."""

    xml_bytes = Path(ruta_xml).read_bytes()
    key_pem = _load_private_key(ruta_clave_privada, password if password else None)

    cert_file_bytes = Path(ruta_certificado_publico).read_bytes()
    cert_chain = _split_pem_certificates(cert_file_bytes)

    if not cert_chain:
        raise ValueError("No se encontró ningún certificado en el archivo proporcionado")

    cert_pem = cert_chain[0]
    chain_pems = cert_chain[1:]

    signed_xml = sign_with_xmlsec(xml_bytes, key_pem, cert_pem, chain_pems)
    return signed_xml


def main():  # pragma: no cover - utilidad manual
    import argparse

    parser = argparse.ArgumentParser(description="Firmar Facturae con XAdES-BES usando xmlsec")
    parser.add_argument("--xml", required=True, help="Ruta al XML Facturae a firmar")
    parser.add_argument("--key", required=True, help="Ruta a la clave privada PEM")
    parser.add_argument("--cert", required=True, help="Ruta al certificado PEM")
    parser.add_argument("--password", default="", help="Contraseña de la clave privada si aplica")
    parser.add_argument("--out", required=True, help="Ruta de salida para el XML firmado")
    args = parser.parse_args()

    firmado = firmar_xml(args.xml, args.key, args.cert, password=args.password)
    Path(args.out).write_bytes(firmado)
    print(f"Firma generada en {args.out}")


if __name__ == "__main__":
    main()
