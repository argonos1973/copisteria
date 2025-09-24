import logging
import os
import shutil
import subprocess
import tempfile


def sign_with_autofirma_pem(
    input_xml: str,
    output_xsig: str,
    cert_pem: str,
    key_pem: str,
    pem_password: str = "",
    af_cli: str = "/usr/bin/autofirma",
    alias: str = None,
    cert_filter: str = None
):
    """
    Firma un XML usando AutoFirma CLI con certificados PEM.

    El .xsig resultante se deja en la ruta que se pase en output_xsig.
    """
    # Verificar CLI
    if not (os.path.isfile(af_cli) and os.access(af_cli, os.X_OK)):
        raise FileNotFoundError(f"No encuentro o no es ejecutable: '{af_cli}'")

    # Crear PKCS#12 temporal
    with tempfile.NamedTemporaryFile(suffix=".p12", delete=False) as tmp_p12:
        p12_path = tmp_p12.name
    try:
        # Exportar PEM -> P12
        openssl_cmd = [
            "openssl", "pkcs12", "-export",
            "-in", cert_pem,
            "-inkey", key_pem,
            "-out", p12_path,
            "-passout", f"pass:{pem_password}"
        ]
        if alias:
            openssl_cmd += ["-name", alias]
        proc = subprocess.run(openssl_cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Error generando P12 (código {proc.returncode}): STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}")

        # Crear HOME para logs en temporal
        log_home = tempfile.mkdtemp()
        env = os.environ.copy()
        env['HOME'] = log_home

        # Llamar a AutoFirma
        cmd = [
            af_cli, "sign",
            "-i", input_xml,
            "-o", output_xsig,
            "-format", "facturae",
            "-store", f"pkcs12:{p12_path}",
            "-password", pem_password
        ]
        if alias:
            cmd += ["-alias", alias]
        elif cert_filter:
            cmd += ["-filter", cert_filter]
        # Si no se proporciona ni alias ni filtro, AutoFirma utilizará el primer
        # certificado disponible en el almacén PKCS#12.


        proc2 = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if proc2.returncode != 0:
            raise RuntimeError(f"AutoFirma falló (código {proc2.returncode}): STDOUT: {proc2.stdout}\nSTDERR: {proc2.stderr}")

        print(f"✅ Firma generada → {output_xsig}")
    finally:
        # Limpieza
        if os.path.exists(p12_path):
            os.unlink(p12_path)
        if 'log_home' in locals() and os.path.isdir(log_home):
            shutil.rmtree(log_home)


# -----------------------------------------------------------------------------
# Wrapper de alto nivel compatible con el resto de módulos
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Funciones de utilidad requeridas por otros módulos (stubs básicos)
# -----------------------------------------------------------------------------

def corregir_etiqueta_n_por_name(ruta_xml: str) -> None:
    """Corrige, si es necesario, etiquetas <N> por <Name> en el XML.

    En esta implementación mínima no se realiza modificación alguna para no
    interferir con XML ya válido. Se mantiene por compatibilidad.
    """
    # Implementación real pendiente
    return


def leer_contenido_xsig(ruta_xsig: str) -> str:
    """Devuelve el contenido (texto) de un archivo XSIG.

    Args:
        ruta_xsig: Ruta al archivo .xsig.

    Returns:
        str: Contenido en texto (utf-8, errores ignorados si los hay).
    """
    with open(ruta_xsig, "rb") as f:
        return f.read().decode("utf-8", errors="ignore")


# -----------------------------------------------------------------------------
# Wrapper de alto nivel compatible con el resto de módulos
# -----------------------------------------------------------------------------

def firmar_xml(
    ruta_xml: str,
    ruta_clave_privada: str,
    ruta_certificado_publico: str,
    password: str = "",
    alias: str | None = None,
    af_cli: str = "/usr/bin/autofirma",
) -> bytes:
    """Firma un archivo XML Facturae y devuelve el contenido firmado (bytes).

    Este wrapper existe para mantener compatibilidad con módulos que esperan
    la función ``firmar_xml``. Internamente delega en
    :func:`sign_with_autofirma_pem` que utiliza AutoFirma CLI.

    Args:
        ruta_xml: Ruta al XML de entrada.
        ruta_clave_privada: Ruta a la clave privada PEM.
        ruta_certificado_publico: Ruta al certificado público PEM.
        password: Contraseña del almacén (si existe).
        alias: Alias del certificado dentro del PKCS#12 temporal (opcional).
        af_cli: Ruta al ejecutable de AutoFirma CLI.

    Returns:
        bytes: Contenido del fichero .xsig firmado.
    """
    import os
    import tempfile

    # Crear ruta temporal para el .xsig
    with tempfile.NamedTemporaryFile(suffix=".xsig", delete=False) as tmp_out:
        ruta_xsig_tmp = tmp_out.name

    try:
        sign_with_autofirma_pem(
            input_xml=ruta_xml,
            output_xsig=ruta_xsig_tmp,
            cert_pem=ruta_certificado_publico,
            key_pem=ruta_clave_privada,
            pem_password=password,
            af_cli=af_cli,
            alias=alias,
        )

        # Leer bytes firmados y devolverlos
        with open(ruta_xsig_tmp, "rb") as f:
            firmado_bytes = f.read()
        return firmado_bytes

    finally:
        # Limpiar temporal
        if os.path.exists(ruta_xsig_tmp):
            os.unlink(ruta_xsig_tmp)


def main():
    logging.basicConfig(level=logging.DEBUG)
    # Ruta fija de entrada y salida
    input_xml = "/media/sami/copia500/F250948.xml"
    output_xsig = input_xml.replace(".xml", ".xsig")
    cert_pem    = "/media/sami/copia500/cert_real.pem"
    key_pem     = "/media/sami/copia500/clave_real.pem"
    pem_password = ""  # si hay contraseña, ponerla aquí
    alias       = "certificadora_sami"

    try:
        sign_with_autofirma_pem(
            input_xml=input_xml,
            output_xsig=output_xsig,
            cert_pem=cert_pem,
            key_pem=key_pem,
            pem_password=pem_password,
            alias=alias
        )
    except Exception as e:
        logging.error(f"AutoFirma falló: {e}")
        raise


if __name__ == "__main__":
    main()
