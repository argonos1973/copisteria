#!/usr/bin/env python3
import os
import sys

from lxml import etree

sys.path.append('/var/www/html')
from validar_facturae import validar_facturae
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)


def analizar_xsig(ruta_xsig_file):
    """
    Analiza un archivo .xsig de Facturae, extrae el XML original,
    muestra información relevante y lo valida.
    """
    logger.info(f"=== ANÁLISIS DE LA FACTURA {os.path.basename(ruta_xsig_file)} ===")

    try:
        # Parsear el archivo .xsig
        parser = etree.XMLParser(remove_blank_text=True, recover=True) # recover=True para intentar parsear XML malformado
        tree = etree.parse(ruta_xsig_file, parser)
        root = tree.getroot()

        # Definir namespaces para la búsqueda (ds: Signature)
        namespaces = {
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'fe': 'http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml'
        }

        facturae_element = None
        logger.info(f"DEBUG: Elemento raíz del XSIG: {root.tag}")
        logger.info(f"DEBUG: Namespaces del raíz: {root.nsmap}")

        # Intentar encontrar ds:Object
        object_element = root.find('.//ds:Object', namespaces=namespaces)

        if object_element is not None:
            logger.info("DEBUG: Encontrado <ds:Object>.")
            expected_facturae_tag = f"{{{namespaces['fe']}}}Facturae"
            logger.info(f"DEBUG: Buscando tag: {expected_facturae_tag} dentro de ds:Object")
            for child in object_element:
                if child.tag == expected_facturae_tag:
                    facturae_element = child
                    logger.info(f"DEBUG: Encontrado Facturae con tag directo: {child.tag}")
                    break
                else:
                    logger.info(f"DEBUG: Hijo de ds:Object con tag: {child.tag}, ns: {etree.QName(child).namespace}")
        else:
            logger.info("DEBUG: No se encontró <ds:Object>.")
            # Si no hay ds:Object, quizás el root es Facturae (firma enveloped donde .xsig es el XML firmado)
            if root.tag == f"{{{namespaces['fe']}}}Facturae":
                logger.info("DEBUG: El elemento raíz ES Facturae. Asumiendo firma enveloped.")
                facturae_element = root # El propio raíz es la factura
            else:
                logger.info("DEBUG: El elemento raíz NO es Facturae ni se encontró ds:Object. Listando hijos del raíz:")
                for i, child_root in enumerate(root):
                    logger.info(f"    Hijo {i} del raíz: Tag='{child_root.tag}', Text='{child_root.text}', Attributes='{child_root.attrib}', Namespace Map='{child_root.nsmap}'")

        if facturae_element is None:
            logger.info("❌ No se pudo extraer el elemento <Facturae> del archivo XSIG.")
            return

        # Guardar el XML extraído a un archivo temporal
        ruta_xml_extraido = "/tmp/factura_extraida.xml"
        # Asegurarse de que el XML extraído tenga la declaración XML y el encoding correcto
        xml_content_bytes = etree.tostring(facturae_element, pretty_print=True, xml_declaration=True, encoding='UTF-8')
        
        with open(ruta_xml_extraido, 'wb') as f:
            f.write(xml_content_bytes)
        
        logger.info(f"\n1. XML original extraído de {os.path.basename(ruta_xsig_file)} y guardado en {ruta_xml_extraido}:")
        logger.info(f"xml_content_bytes.decode('UTF-8')) # Imprimir directamente desde bytes decodificados

        # Parsear el XML extraído para análisis
        # Es importante parsear desde el string de bytes para que lxml maneje correctamente el encoding
        facturae_tree_parsed = etree.fromstring(xml_content_bytes parser=parser")
        
        # El namespace del elemento Facturae extraído
        # El namespace principal es el del elemento raíz 'Facturae'
        facturae_ns_map = facturae_tree_parsed.nsmap
        # El namespace por defecto (None) o el asociado al prefijo de facturae_tree_parsed
        fe_ns_uri = facturae_ns_map.get(facturae_tree_parsed.prefix) if facturae_tree_parsed.prefix else facturae_ns_map.get(None)
        
        if not fe_ns_uri or fe_ns_uri != namespaces['fe']:
            logger.info(f"ADVERTENCIA: El namespace del elemento Facturae extraído ('{fe_ns_uri}') no coincide con el esperado ('{namespaces['fe']}'). Los resultados del análisis XPath pueden ser incorrectos.")
            # Aun así, intentamos usar el namespace esperado para el análisis, ya que los elementos internos podrían no heredar correctamente.
            # O podríamos intentar usar el namespace detectado si estamos seguros de que es el correcto para los hijos.
        
        # Usamos el namespace 'fe' definido globalmente que es el estándar de Facturae
        current_facturae_ns_for_search = {'fe': namespaces['fe']}

        logger.info("\n2. Analizando datos del Emisor (SellerParty):")
        # Los elementos dentro de Facturae usualmente no tienen prefijo y heredan el namespace o usan xmlns=""
        # Por lo tanto, para SellerParty, TaxIdentificationNumber, etc., el namespace podría ser el de 'fe' o ninguno ('')
        # Probaremos con el namespace 'fe' y si no, sin namespace explícito en el path para esos hijos.
        seller_party = facturae_tree_parsed.find('.//fe:Parties/fe:SellerParty', namespaces=current_facturae_ns_for_search)
        if seller_party is None: # Intento sin namespace para los hijos de Parties
            seller_party = facturae_tree_parsed.find('.//Parties/SellerParty') # No pasar namespaces aquí si los hijos no tienen ns

        if seller_party is not None:
            # Para los hijos de SellerParty, el namespace puede ser el de 'fe' o "" (ninguno)
            nif_emisor = seller_party.find('.//fe:TaxIdentification/fe:TaxIdentificationNumber', namespaces=current_facturae_ns_for_search) 
            if nif_emisor is None: nif_emisor = seller_party.find('.//TaxIdentification/TaxIdentificationNumber') # Sin ns
            
            nombre_emisor_legal = seller_party.find('.//fe:LegalEntity/fe:CorporateName', namespaces=current_facturae_ns_for_search)
            if nombre_emisor_legal is None: nombre_emisor_legal = seller_party.find('.//LegalEntity/CorporateName') # Sin ns
            
            nombre_emisor_individual = seller_party.find('.//fe:Individual/fe:Name', namespaces=current_facturae_ns_for_search)
            if nombre_emisor_individual is None: nombre_emisor_individual = seller_party.find('.//Individual/Name') # Sin ns
            
            nombre_emisor_text = ''
            if nombre_emisor_legal is not None and nombre_emisor_legal.text is not None: nombre_emisor_text = nombre_emisor_legal.text
            elif nombre_emisor_individual is not None and nombre_emisor_individual.text is not None: nombre_emisor_text = nombre_emisor_individual.text
            else: nombre_emisor_text = 'No encontrado'
            
            logger.info(f"  NIF Emisor: {nif_emisor.text if nif_emisor is not None and nif_emisor.text is not None else 'No encontrado'}")
            logger.info(f"  Nombre Emisor: {nombre_emisor_text}")
        else:
            logger.info("  No se encontró SellerParty.")

        logger.info("\n3. Analizando datos del Receptor (BuyerParty):")
        buyer_party = facturae_tree_parsed.find('.//fe:Parties/fe:BuyerParty', namespaces=current_facturae_ns_for_search)
        if buyer_party is None: buyer_party = facturae_tree_parsed.find('.//Parties/BuyerParty')

        if buyer_party is not None:
            nif_receptor = buyer_party.find('.//fe:TaxIdentification/fe:TaxIdentificationNumber', namespaces=current_facturae_ns_for_search)
            if nif_receptor is None: nif_receptor = buyer_party.find('.//TaxIdentification/TaxIdentificationNumber')
            logger.info(f"  NIF Receptor: {nif_receptor.text if nif_receptor is not None and nif_receptor.text is not None else 'No encontrado'}")
            
            individual = buyer_party.find('.//fe:Individual', namespaces=current_facturae_ns_for_search)
            if individual is None: individual = buyer_party.find('.//Individual')
            
            legal_entity = buyer_party.find('.//fe:LegalEntity', namespaces=current_facturae_ns_for_search)
            if legal_entity is None: legal_entity = buyer_party.find('.//LegalEntity')

            if individual is not None:
                logger.info("  Tipo: Persona Física (Individual)")
                nombre = individual.find('.//fe:Name', namespaces=current_facturae_ns_for_search)
                if nombre is None: nombre = individual.find('.//Name')
                
                primer_apellido = individual.find('.//fe:FirstSurname', namespaces=current_facturae_ns_for_search)
                if primer_apellido is None: primer_apellido = individual.find('.//FirstSurname')
                
                segundo_apellido = individual.find('.//fe:SecondSurname', namespaces=current_facturae_ns_for_search)
                if segundo_apellido is None: segundo_apellido = individual.find('.//SecondSurname')
                
                logger.info(f"    Nombre: {nombre.text if nombre is not None and nombre.text else ''}")
                logger.info(f"    Primer Apellido: {primer_apellido.text if primer_apellido is not None and primer_apellido.text else ''}")
                logger.info(f"    Segundo Apellido: {segundo_apellido.text if segundo_apellido is not None and segundo_apellido.text else ''}")
            elif legal_entity is not None:
                logger.info("  Tipo: Persona Jurídica (LegalEntity)")
                nombre_empresa = legal_entity.find('.//fe:CorporateName', namespaces=current_facturae_ns_for_search)
                if nombre_empresa is None: nombre_empresa = legal_entity.find('.//CorporateName')
                logger.info(f"    Razón Social: {nombre_empresa.text if nombre_empresa is not None and nombre_empresa.text is not None else 'No encontrado'}")
            else:
                logger.info("  No se encontró ni Individual ni LegalEntity para el receptor.")
        else:
            logger.info("  No se encontró BuyerParty.")

        logger.info(f"\n4. Validando {os.path.basename(ruta_xml_extraido)} contra el esquema Facturae:")
        es_valido, mensaje = validar_facturae(ruta_xml_extraido)
        logger.info(f"  Validación: {'✅ VÁLIDO' if es_valido else '❌ INVÁLIDO'}: {mensaje}")

    except FileNotFoundError:
        logger.info(f"❌ Error: El archivo {ruta_xsig_file} no fue encontrado.")
    except etree.XMLSyntaxError as e:
        logger.info(f"❌ Error de sintaxis XML al parsear {ruta_xsig_file}: {e}")
    except Exception as e:
        logger.info(f"❌ Ocurrió un error inesperado: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.info("Uso: python3 analizar_factura_xsig.py <ruta_al_archivo.xsig>")
        sys.exit(1)
    
    ruta_factura = sys.argv[1]
    analizar_xsig(ruta_factura)
