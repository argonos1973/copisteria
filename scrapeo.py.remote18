#!/var/www/html/venv/bin/python

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from db_utils import get_db_connection

# Registrar inicio del script
print("=== scrapeo.py iniciado ===")

# ==== Modo simplificado: Importar gastos desde un Excel y terminar ====

def importar_desde_excel(ruta_excel: str):
    """Importa los movimientos bancarios desde un fichero Excel a la tabla 'gastos'.
    Solo inserta los registros que aún no existen (por fecha_operacion, concepto, importe_eur)."""


    # Conexión a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener registros existentes para evitar duplicados. Se usa la combinación
    # (fecha_operacion, concepto, importe_eur, ejercicio) como clave única.
    cursor.execute("SELECT fecha_operacion, concepto, importe_eur, ejercicio FROM gastos")
    raw_registros = cursor.fetchall()

    def _normalize(fecha, concepto, importe, ejercicio):
        """Normaliza los valores para poder comparar de forma fiable"""
        # Normalizar fecha -> YYYY-MM-DD (cadena)
        if fecha is None:
            fecha_str = ""
        else:
            try:
                # Si viene como string, intentar parsear los dos formatos más comunes
                if isinstance(fecha, str):
                    # nos quedamos con la parte anterior al espacio si lleva HH:MM:SS
                    fecha_txt = fecha.split()[0]
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                        try:
                            fecha_dt = datetime.strptime(fecha_txt, fmt)
                            break
                        except Exception:
                            fecha_dt = None
                    fecha_str = fecha_dt.strftime("%Y-%m-%d") if fecha_dt else fecha_txt
                else:
                    # Timestamp o datetime
                    fecha_str = fecha.strftime("%Y-%m-%d")
            except Exception:
                fecha_str = str(fecha)

        # Normalizar concepto (mayúsculas + sin espacios extremos + espacios múltiples a uno solo)
        import re
        concepto_norm = re.sub(r'\s+', ' ', str(concepto).strip().upper())

        # Normalizar importe redondeando a 2 decimales
        try:
            importe_norm = round(float(importe), 2)
        except Exception:
            importe_norm = float(str(importe).replace(',', '.')) if importe is not None else 0.0
        # Normalizar ejercicio
        try:
            ejercicio_norm = int(ejercicio) if ejercicio is not None else 0
        except Exception:
            try:
                ejercicio_norm = int(str(ejercicio).strip())
            except Exception:
                ejercicio_norm = 0

        return (fecha_str, concepto_norm, importe_norm, ejercicio_norm)

    registros_existentes = set(_normalize(f, c, i, e) for f, c, i, e in raw_registros)

    # Leer el Excel detectando automáticamente la fila de encabezado para no perder registros
    ext = os.path.splitext(ruta_excel)[1].lower()

    # Cargar provisionalmente sin encabezado para encontrar la fila donde empieza la tabla
    df_raw = pd.read_excel(
        ruta_excel,
        header=None,
        engine=("xlrd" if ext == ".xls" else None)
    )
    header_row_idx = None
    for idx, val in df_raw.iloc[:, 0].items():
        if isinstance(val, str) and val.strip().upper() == "FECHA OPERACIÓN":
            header_row_idx = idx
            break

    if header_row_idx is None:
        raise ValueError("No se encontró la fila de encabezado en el Excel ('FECHA OPERACIÓN')")

    # Volver a leer el Excel usando la fila detectada como encabezado
    df = pd.read_excel(
        ruta_excel,
        header=header_row_idx,
        engine=("xlrd" if ext == ".xls" else None)
    )

    # Eliminar filas completamente vacías
    df = df.dropna(how="all")

    required_cols = ['FECHA OPERACIÓN', 'FECHA VALOR', 'CONCEPTO', 'IMPORTE EUR', 'SALDO']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Falta la columna requerida: {col}")

    df = df.rename(columns={
        'FECHA OPERACIÓN': 'fecha_operacion',
        'FECHA VALOR': 'fecha_valor',
        'CONCEPTO': 'concepto',
        'IMPORTE EUR': 'importe_eur',
        'SALDO': 'saldo'
    })

    # Asegurar que existe la columna saldo
    if 'saldo' not in df.columns:
        df['saldo'] = None

    # Añadir metadatos
    ahora = datetime.now()
    df['ejercicio'] = ahora.year
    df['TS'] = ahora.isoformat()

    # Reordenar columnas
    df = df[['fecha_operacion', 'fecha_valor', 'concepto', 'importe_eur', 'saldo', 'ejercicio', 'TS']]

    # Filtrar registros que ya existen para evitar duplicados
    # Preprocesar columnas para la comparación
    import re
    df['concepto_cmp'] = df['concepto'].astype(str).str.strip().str.upper().apply(lambda x: re.sub(r'\s+', ' ', x))
    # Asegurar tipo fecha en pandas para poder formatear; los valores no nulos se convierten a string YYYY-MM-DD
    df['fecha_cmp'] = pd.to_datetime(df['fecha_operacion'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
    df['importe_cmp'] = df['importe_eur'].apply(lambda x: round(float(x), 2))
    df['ejercicio_cmp'] = df['ejercicio'].astype(int)

    mask_nuevos = ~df.apply(lambda row: (row['fecha_cmp'], row['concepto_cmp'], row['importe_cmp'], row['ejercicio_cmp']) in registros_existentes, axis=1)
    nuevos_registros = df[mask_nuevos].drop(columns=['fecha_cmp', 'concepto_cmp', 'importe_cmp', 'ejercicio_cmp'])

    inserted = 0
    if not nuevos_registros.empty:
        # Inserción robusta respetando la clave única con INSERT OR IGNORE
        columnas = ['fecha_operacion', 'fecha_valor', 'concepto', 'importe_eur', 'saldo', 'ejercicio', 'TS']
        data = [
            (
                row['fecha_operacion'],
                row['fecha_valor'],
                row['concepto'],
                float(row['importe_eur']) if row['importe_eur'] is not None else None,
                row['saldo'],
                int(row['ejercicio']) if row['ejercicio'] is not None else None,
                row['TS'],
            )
            for _, row in nuevos_registros[columnas].iterrows()
        ]

        antes = conn.total_changes
        cursor.executemany(
            """
            INSERT OR IGNORE INTO gastos
            (fecha_operacion, fecha_valor, concepto, importe_eur, saldo, ejercicio, TS)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            data,
        )
        conn.commit()
        despues = conn.total_changes
        inserted = max(despues - antes, 0)
        logging.info("%d registros nuevos insertados en 'gastos'", inserted)
        print(f"Registros insertados: {inserted}")
    else:
        logging.info("No se encontraron registros nuevos para insertar en 'gastos'")
        print("No hay registros nuevos para insertar (evitados duplicados)")

    conn.close()
    logging.info("Importación de gastos completada desde Excel '%s'", ruta_excel)
    print(f"Importación completada OK desde: {ruta_excel}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Importar gastos desde un fichero Excel, eliminando previamente toda la tabla 'gastos'."
    )
    parser.add_argument(
        "excel",
        nargs="?",
        default=None,
        help="Ruta al fichero Excel a importar (por defecto: /tmp/descarga.xlsx)"
    )
    args = parser.parse_args()

    # Verificar primero si se proporcionó una ruta específica
    if args.excel is not None:
        excel_path = Path(args.excel)
    else:
        # Buscar el archivo en /tmp con el nombre descarga
        excel_path = Path("/tmp/descarga.xlsx")
        # Si no existe con extensión .xlsx, buscar sin extensión
        if not excel_path.exists():
            excel_path = Path("/tmp/descarga")
    
    # Si aún no existe, mostrar error
    if not excel_path.exists():
        print(f"ERROR: No se encontró el fichero {excel_path}")
        sys.exit(1)

    importar_desde_excel(str(excel_path))
    sys.exit(0)
# ==== Fin modo simplificado ====

