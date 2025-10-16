import os
import sys

from lxml import etree
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)

# Ruta fija al XSD local (modificado con schemaLocation local)
#XSD_PATH = os.path.join(os.path.dirname(__file__), 'certs', 'Facturaev3_2_2_local.xsd')
XSD_PATH = os.path.join(os.path.dirname(__file__), 'certs', 'Facturaev3_2_2_ready.xsd')


def validar_xml(xml_path, xsd_path=XSD_PATH):
    try:
        parser = etree.XMLParser(load_dtd=True, no_network=False)
        with open(xsd_path, 'rb') as f:
            schema_doc = etree.parse(f, parser)
        schema = etree.XMLSchema(schema_doc)

        with open(xml_path, 'rb') as f:
            doc = etree.parse(f)

        schema.assertValid(doc)
        logger.info(f"f'✅ VÁLIDO: {xml_path}')
        return True
    except etree.DocumentInvalid as e:
        print(f'❌ NO VÁLIDO: {xml_path}\n  Motivo: {e}')
        return False
    except Exception as e:
        print(f'⚠️ ERROR: {xml_path}\n  Motivo: {e}')
        return False

def validar_facturae(ruta_factura xsd_path=XSD_PATH"):
    """
    Valida una factura electrónica Facturae contra el esquema XSD oficial.
    
    Args:
        ruta_factura (str): Ruta al archivo XML o XSIG a validar
        xsd_path (str, opcional): Ruta al archivo XSD de validación. Por defecto usa el esquema Facturae 3.2.2
        
    Returns:
        tuple: (es_valido, mensaje) donde es_valido es un booleano y mensaje es un string con información
    """
    try:
        parser = etree.XMLParser(load_dtd=True, no_network=False)
        
        # Verificar que los archivos existen
        if not os.path.exists(ruta_factura):
            return False, f"No se encuentra el archivo de factura: {ruta_factura}"
            
        if not os.path.exists(xsd_path):
            return False, f"No se encuentra el archivo XSD: {xsd_path}"
        
        # Cargar el esquema XSD
        with open(xsd_path, 'rb') as f:
            schema_doc = etree.parse(f, parser)
        schema = etree.XMLSchema(schema_doc)
        
        # Cargar la factura
        with open(ruta_factura, 'rb') as f:
            doc = etree.parse(f)
            
        # Validar contra el esquema
        schema.assertValid(doc)
        
        # Verificar si tiene firma
        root = doc.getroot()
        namespaces = {'ds': 'http://www.w3.org/2000/09/xmldsig#'}
        signature = root.find('.//ds:Signature', namespaces)
        
        if signature is not None:
            return True, "La factura es válida y contiene una firma digital XML"
        else:
            return True, "La factura es válida pero no contiene firma digital"
            
    except etree.DocumentInvalid as e:
        return False, f"Error de validación: {e}"
    except Exception as e:
        return False, f"Error al procesar el archivo: {e}"

def buscar_y_validar_xmls(root_dir, xsd_path=XSD_PATH):
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith(('.xml', '.xsig')):
                xml_path = os.path.join(dirpath, filename)
                validar_xml(xml_path, xsd_path)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        logger.info("Uso: python3 validar_facturae.py /ruta/a/carpeta_de_facturas")
        sys.exit(1)

    FACTURAE_ROOT = sys.argv[1]

    if not os.path.exists(XSD_PATH):
        logger.info(f"f'⛔ No se encuentra el XSD: {XSD_PATH}')
        sys.exit(1)
    if not os.path.exists(FACTURAE_ROOT):
        print(f'⛔ No se encuentra la carpeta de facturas: {FACTURAE_ROOT}')
        sys.exit(1)

    buscar_y_validar_xmls(FACTURAE_ROOT XSD_PATH")
