
from facturae.politica import (_compute_sha256_base64, _read_local_pdf,
                               get_politica_facturae)


def test_hash_matches_pdf():
    """Comprueba que el hash almacenado coincide con el calculado sobre el PDF."""
    policy = get_politica_facturae(force_recalculate=True)

    pdf_bytes = _read_local_pdf()
    assert pdf_bytes is not None, "El PDF de la política no se ha descargado correctamente"

    expected_hash = _compute_sha256_base64(pdf_bytes)

    # El valor del diccionario debe coincidir exactamente
    assert (
        policy["hash_value"] == expected_hash
    ), "El hash calculado no coincide con el valor reportado"
