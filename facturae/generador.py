#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo principal para generar facturas electrónicas Facturae.
"""

import json
import logging
import os
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from facturae.firma import corregir_etiqueta_n_por_name, firmar_xml
from facturae.utils import procesar_serie_numero, separar_nombre_apellidos
from facturae.validacion import es_persona_fisica
from facturae.xml_template import (generar_individual_template,
                                   generar_item_template,
                                   generar_party_template,
                                   generar_taxes_template,
                                   obtener_plantilla_xml)

logger = logging.getLogger(__name__)

# Rutas por defecto para certificados
CLAVE_PRIVADA_PATH = "/var/www/html/certs/clave_privada.key"
CERTIFICADO_PATH = "/var/www/html/certs/certificado.crt"

def generar_facturae(datos_factura, ruta_salida_xml=None):
    """
    Genera una factura electrónica en formato Facturae (XML)
    
    Args:
        datos_factura (dict): Datos de la factura (emisor, receptor, líneas, etc.)
        ruta_salida_xml (str, opcional): Ruta donde se guardará el archivo XML generado
        
    Returns:
        str: Ruta al archivo generado (.xml o .xsig si está firmado)
    """
    # Asegurar que tenemos acceso global a estas dependencias
    
    # Determinar ruta de salida si no se proporciona
    if not ruta_salida_xml:
        fecha = datos_factura.get('fecha')
        numero = datos_factura.get('numero', 'factura')
        if fecha:
            ano, mes = fecha.split('-')[0], fecha.split('-')[1]
        else:
            now = datetime.now()
            ano, mes = str(now.year), str(now.month).zfill(2)
            
        # Usar la ruta de producción para guardar las facturas
        dir_destino = f"/var/www/html/factura_e/{ano}/{mes}"
        print(f"📁 Usando directorio de salida: {dir_destino}")
        os.makedirs(dir_destino, exist_ok=True)
        ruta_salida_xml = os.path.join(dir_destino, f"{numero}.xml")
    else:
        os.makedirs(os.path.dirname(ruta_salida_xml), exist_ok=True)

    try:
        emisor = datos_factura['emisor']
        receptor = datos_factura['receptor']
        detalles = datos_factura.get("detalles", datos_factura.get("items", []))
        fecha = datos_factura.get('fecha', '')
        numero = datos_factura.get('numero', '')
        porcentaje_iva = float(datos_factura.get('iva', 21.0))
        
        # Validar si NIF emisor y receptor son iguales
        nif_emisor_check = emisor.get('nif', '')
        nif_receptor_check = receptor.get('nif', '')
        if nif_emisor_check and nif_receptor_check and nif_emisor_check == nif_receptor_check:
            print(f"⚠️ ADVERTENCIA: NIF emisor ({nif_emisor_check}) es igual al NIF receptor ({nif_receptor_check}).")
            
        # Verificar si emisor y receptor son personas físicas o jurídicas
        es_emisor_persona_fisica = es_persona_fisica(emisor.get('nif', ''))
        print(f"⚠️ Tipo de emisor: {'PERSONA FÍSICA' if es_emisor_persona_fisica else 'PERSONA JURÍDICA'}")
        
        es_receptor_persona_fisica = es_persona_fisica(receptor.get('nif', ''))
        print(f"⚠️ Tipo de receptor: {'PERSONA FÍSICA' if es_receptor_persona_fisica else 'PERSONA JURÍDICA'}")
        
        # Usar los totales proporcionados directamente desde el frontend en lugar de recalcular
        base_imponible_total = Decimal(str(datos_factura.get('base_amount', '0.00')))
        cuota_iva = Decimal(str(datos_factura.get('taxes', '0.00')))
        total_factura = Decimal(str(datos_factura.get('total_amount', '0.00')))
        
        # Si alguno de los valores no viene del frontend, entonces calculamos
        if base_imponible_total == Decimal('0.00') and detalles:
            # Modo compatibilidad: calcular solo si no viene del frontend
            base_imponible_temp = Decimal('0.00')
            for detalle in detalles:
                cantidad = Decimal(str(detalle.get('cantidad', 1)))
                importe = Decimal(str(detalle.get('importe', detalle.get('precio', 0))))
                base_imponible_temp += cantidad * importe
            
            # Solo asignar si el original estaba en 0
            if base_imponible_total == Decimal('0.00'):
                base_imponible_total = base_imponible_temp.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
            # Calcular IVA solo si no viene del frontend
            if cuota_iva == Decimal('0.00'):
                cuota_iva = (base_imponible_total * Decimal(str(porcentaje_iva)) / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
            # Calcular total solo si no viene del frontend
            if total_factura == Decimal('0.00'):
                total_factura = base_imponible_total + cuota_iva
                
        # Asegurar que los valores están formateados correctamente
        base_imponible_total = base_imponible_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        cuota_iva = cuota_iva.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_factura = total_factura.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        print(f"📊 Usando importes del frontend: Base={base_imponible_total}, IVA={cuota_iva}, Total={total_factura}")
        
        # Crear las secciones del XML
        xml_plantilla = obtener_plantilla_xml()
        
        # Preparar los datos para las partes
        batch_id = f"BATCH-{numero}"
        
        # Preparar datos del emisor
        if es_emisor_persona_fisica:
            # Es una persona física
            nombre, primer_apellido, segundo_apellido = separar_nombre_apellidos(emisor.get('nombre', ''))
            xml_emisor = generar_individual_template().format(
                person_type_code="F",
                tax_number=emisor.get('nif', ''),
                name=nombre,
                first_surname=primer_apellido,
                second_surname=segundo_apellido,
                address=emisor.get('direccion', ''),
                post_code=emisor.get('cp', ''),
                town=emisor.get('localidad', ''),
                province=emisor.get('provincia', '')
            )
        else:
            # Es una persona jurídica
            xml_emisor = generar_party_template('seller').format(
                person_type_code="J",
                tax_number=emisor.get('nif', ''),
                corporate_name=emisor.get('nombre', ''),
                address=emisor.get('direccion', ''),
                post_code=emisor.get('cp', ''),
                town=emisor.get('localidad', ''),
                province=emisor.get('provincia', '')
            )
            
        # Preparar datos del receptor
        if es_receptor_persona_fisica:
            # Es una persona física
            nombre, primer_apellido, segundo_apellido = separar_nombre_apellidos(receptor.get('nombre', ''))
            xml_receptor = generar_individual_template().format(
                person_type_code="F",
                tax_number=receptor.get('nif', ''),
                name=nombre,
                first_surname=primer_apellido,
                second_surname=segundo_apellido,
                address=receptor.get('direccion', ''),
                post_code=receptor.get('cp', ''),
                town=receptor.get('localidad', ''),
                province=receptor.get('provincia', '')
            )
        else:
            # Es una persona jurídica
            xml_receptor = generar_party_template('buyer').format(
                person_type_code="J",
                tax_number=receptor.get('nif', ''),
                corporate_name=receptor.get('nombre', ''),
                address=receptor.get('direccion', ''),
                post_code=receptor.get('cp', ''),
                town=receptor.get('localidad', ''),
                province=receptor.get('provincia', '')
            )
            
        # Preparar los impuestos (formato correcto según el estándar Facturae)
        xml_impuestos = generar_taxes_template().format(
            tax_rate='{:.2f}'.format(porcentaje_iva),  # Tasa IVA solo necesita 2 decimales
            taxable_base='{:.2f}'.format(base_imponible_total),  # Base imponible para TotalAmount: 2 decimales
            tax_amount='{:.2f}'.format(cuota_iva)  # Importe de impuesto para TotalAmount: 2 decimales
        )
        
        # Preparar los ítems
        items_xml = []
        # Registrar el número total de detalles que se procesarán
        with open('/var/www/html/facturae_debug.log', 'a') as log_file:
            log_file.write(f"\n[{datetime.now().isoformat()}] Procesando {len(detalles)} detalles para la factura\n")
            
        for idx, detalle in enumerate(detalles):
            # Registrar cada detalle para depuración
            with open('/var/www/html/facturae_debug.log', 'a') as log_file:
                log_file.write(f"Procesando detalle #{idx+1}: {json.dumps(detalle, default=str)}\n")
            
            cantidad = Decimal(str(detalle.get('cantidad', 1)))
            
            # Obtener el precio - puede venir como 'importe' o como 'precio'
            if 'importe' in detalle and detalle['importe']:
                importe = Decimal(str(detalle['importe']))
            elif 'precio' in detalle and detalle['precio']:
                importe = Decimal(str(detalle['precio']))
            else:
                importe = Decimal('0')
                
            # Registrar para depuración
            with open('/var/www/html/facturae_debug.log', 'a') as log_file:
                log_file.write(f"  - Precio encontrado: {importe}\n")
                
            # Calcular base
            base_item = cantidad * importe
            base_item = base_item.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Calcular IVA del ítem
            iva_item = (base_item * Decimal(str(porcentaje_iva)) / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Registrar los cálculos para depuración
            with open('/var/www/html/facturae_debug.log', 'a') as log_file:
                log_file.write(f"  - Cantidad: {cantidad}, Precio: {importe}, Base: {base_item}, IVA: {iva_item}\n")
            
            # Añadir a la lista
            # Formato correcto para cada campo según el tipo en el XSD de Facturae
            item_xml = generar_item_template().format(
                description=detalle.get('concepto', ''),
                quantity='{:.2f}'.format(cantidad),  # DoubleTwoDecimalType
                unit_price='{:.6f}'.format(importe),  # DoubleSixDecimalType
                total_cost='{:.6f}'.format(base_item),  # DoubleSixDecimalType
                gross_amount='{:.6f}'.format(base_item),  # DoubleSixDecimalType
                tax_rate='{:.2f}'.format(porcentaje_iva),  # DoubleTwoDecimalType
                taxable_base='{:.2f}'.format(base_item),  # DoubleTwoDecimalType para TotalAmount
                tax_amount='{:.2f}'.format(iva_item)  # DoubleTwoDecimalType para TotalAmount
            )
            items_xml.append(item_xml)
            
        # Unir todos los ítems
        items_xml_final = '\n                '.join(items_xml)
        
        # Completar la plantilla con formato correcto para cada campo
        xml_completo = xml_plantilla.format(
            batch_id=batch_id,
            # Para los totales principales usamos 2 decimales (DoubleTwoDecimalType)
            total_amount='{:.2f}'.format(total_factura),
            seller_party=xml_emisor,
            buyer_party=xml_receptor,
            # Usamos la función procesar_serie_numero para separar correctamente serie y número
            # según requerimientos de AEAT VERI*FACTU
            invoice_series=procesar_serie_numero(numero)[0] if numero else "SER",
            invoice_number=procesar_serie_numero(numero)[1] if numero else numero,
            issue_date=fecha,
            taxes_outputs=xml_impuestos,
            total_gross='{:.2f}'.format(base_imponible_total),
            total_tax='{:.2f}'.format(cuota_iva),
            items=items_xml_final
        )
        
        # Guardar el XML
        with open(ruta_salida_xml, 'w', encoding='utf-8') as f:
            f.write(xml_completo)
            
        # Corregir etiquetas problemáticas
        corregir_etiqueta_n_por_name(ruta_salida_xml)
        
        # Proceder a firmar el XML si se dispone de clave y certificado
        # Si la firma falla se devolverá la ruta del XML sin firmar
        try:
            pass  # la ejecución continuará más abajo con el proceso normal de firma
        except Exception:
            # Si hay errores volveremos al XML sin firmar
            return ruta_salida_xml
        
        # Ruta donde se guardará el archivo firmado
        nombre_base = os.path.basename(ruta_salida_xml)
        nombre_sin_ext = os.path.splitext(nombre_base)[0]
        dir_destino = os.path.dirname(ruta_salida_xml)
        ruta_xsig = os.path.join(dir_destino, f"{nombre_sin_ext}.xsig")
        
        # Datos del certificado
        # Usar archivos separados de clave privada y certificado en lugar del PKCS#12
        ruta_clave_privada = CLAVE_PRIVADA_PATH
        ruta_certificado_publico = CERTIFICADO_PATH
        
        print(f"DEBUG: Usando clave privada: {ruta_clave_privada}")
        print(f"DEBUG: Usando certificado público: {ruta_certificado_publico}")
        print(f"DEBUG: Ruta XML original: {ruta_salida_xml}")
        print(f"DEBUG: Ruta final XSIG: {ruta_xsig}")
        
        try:
            # Firma con archivos separados
            print("DEBUG: Llamando a firmar_xml con archivos separados de clave privada y certificado")
            xml_firmado = firmar_xml(ruta_salida_xml, 
                                    ruta_clave_privada=ruta_clave_privada, 
                                    ruta_certificado_publico=ruta_certificado_publico)
            
            print(f"DEBUG: XML firmado recibido, tamaño: {len(xml_firmado)} bytes")
            
            # Guardar el XML firmado
            with open(ruta_xsig, 'wb') as f:
                f.write(xml_firmado)
                
            print(f"DEBUG: XML firmado escrito en: {ruta_xsig}")
            
            # Integración VERI*FACTU desactivada aquí para evitar reenvío duplicado
            if False and datos_factura.get('verifactu', False) and datos_factura.get('factura_id'):
                factura_id = datos_factura.get('factura_id')
                try:
                    # Importamos aquí para evitar dependencias circulares
                    import sys
                    sys.path.append('/var/www/html')
                    import verifactu
                    
                    print(f"[VERIFACTU] Procesando factura {factura_id} para formato VERI*FACTU")
                    # Usamos los datos de VERI*FACTU para esta factura
                    datos_verifactu = verifactu.generar_datos_verifactu_para_factura(factura_id)
                    
                    if datos_verifactu:
                        print(f"[VERIFACTU] Datos generados correctamente para factura_id: {factura_id}")
                        # Acceso seguro al hash para evitar KeyError
                        if 'datos' in datos_verifactu and 'hash' in datos_verifactu['datos']:
                            print(f"[VERIFACTU] Hash generado: {datos_verifactu['datos']['hash'][:20]}...")
                        else:
                            print("[VERIFACTU] Hash no disponible en la respuesta")
                    else:
                        print(f"[VERIFACTU] Error generando datos para VERI*FACTU, factura_id: {factura_id}")
                except Exception as e:
                    import traceback
                    print(f"[VERIFACTU] Error en integración: {str(e)}")
                    print(traceback.format_exc())
            
            # Devolver ruta al archivo firmado
            ruta_final = ruta_xsig
            return ruta_final
        except Exception as e:
            import traceback
            print(f"⚠️ Firma fallida: {e}")
            print(traceback.format_exc())
            print("⚠️ Continuaremos con el XML sin firmar")
            # Devuelve la ruta del XML sin firmar para que el flujo continúe
            return ruta_salida_xml
    except Exception as e:
        print(f"⚠️ Error en generar_facturae: {e}. Se usará XML sin firmar")
        return ruta_salida_xml
