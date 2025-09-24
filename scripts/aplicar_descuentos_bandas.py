#!/usr/bin/env python3
import argparse
from typing import List, Dict, Optional, Tuple
import sys
import os
from decimal import Decimal, ROUND_HALF_UP, getcontext

# Asegurar que la raíz del proyecto esté en sys.path para imports directos
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from productos import (
    ensure_tabla_descuentos_bandas,
    obtener_productos,
    reemplazar_franjas_descuento_producto,
)
from constantes import DB_NAME


def _generar_porcentajes(
    bandas: int,
    min_descuento: float,
    max_descuento: float,
    curva: str = "linear",
    porcentajes_explicitos: Optional[List[float]] = None,
) -> List[float]:
    """
    Genera una lista de porcentajes de longitud `bandas` según la curva solicitada o
    usa porcentajes explícitos si se proporcionan.

    Curvas disponibles:
      - linear: incremento uniforme
      - concava: crecimiento suave al principio (raíz cuadrada)
      - convexa: crecimiento lento al principio y fuerte al final (potencia 2)
      - sigmoide: crecimiento en S, suave al principio y al final
    """
    if porcentajes_explicitos:
        if len(porcentajes_explicitos) != bandas:
            raise ValueError("La lista de porcentajes debe tener el mismo tamaño que 'bandas'")
        return [round(float(p), 4) for p in porcentajes_explicitos]

    # Normalizamos con un factor en [0,1] y luego escalamos al rango de descuentos
    vals = []
    for i in range(1, bandas + 1):
        x = i / bandas  # 0..1
        if curva == "linear":
            frac = x
        elif curva == "concava":
            frac = x ** 0.5  # raíz, sube más al inicio
        elif curva == "convexa":
            frac = x ** 2  # sube más al final
        elif curva == "sigmoide":
            # Sigmoide simple aproximada sin exp: suavizamos usando una combinación
            # mapeo en S: 3x^2 - 2x^3 (polinomio suave)
            frac = 3 * (x ** 2) - 2 * (x ** 3)
        else:
            frac = x
        p = min_descuento + (max_descuento - min_descuento) * frac
        vals.append(round(p, 4))
    return vals


def generar_franjas(
    bandas: int = 10,
    max_cantidad: int = 500,
    max_descuento: float = 60.0,
    min_descuento: float = 0.0,
    curva: str = "linear",
    porcentajes: Optional[List[float]] = None,
) -> List[Dict]:
    """
    Genera franjas de cantidad con descuentos crecientes lineales.

    - Cantidades desde 1 hasta max_cantidad, repartidas en `bandas` tramos.
    - Descuento desde `min_descuento` hasta `max_descuento` según curva seleccionada
      o usando porcentajes explícitos.

    Retorna: lista de dicts con claves: {min, max, descuento}
    """
    if bandas <= 0:
        raise ValueError("bandas debe ser > 0")
    if max_cantidad <= 0:
        raise ValueError("max_cantidad debe ser > 0")
    if max_descuento < 0 or min_descuento < 0:
        raise ValueError("Descuentos no pueden ser negativos")
    if max_descuento < min_descuento:
        raise ValueError("max_descuento debe ser >= min_descuento")

    # Reparto de cantidades en bandas: lo ideal es que sean iguales
    base = max_cantidad // bandas
    resto = max_cantidad % bandas

    # Porcentajes por banda
    perc = _generar_porcentajes(
        bandas=bandas,
        min_descuento=min_descuento,
        max_descuento=max_descuento,
        curva=curva,
        porcentajes_explicitos=porcentajes,
    )

    franjas = []
    inicio = 1
    for i in range(1, bandas + 1):
        ancho = base + (1 if i <= resto else 0)
        fin = inicio + ancho - 1
        # Selección del descuento de la banda i
        descuento = perc[i - 1] if perc else max_descuento
        franjas.append({
            'min': inicio,
            'max': fin,
            'descuento': round(descuento, 4),
        })
        inicio = fin + 1

    # Ajuste por si algún redondeo dejara huecos (no debería)
    if franjas:
        franjas[-1]['max'] = max(franjas[-1]['max'], max_cantidad)
    return franjas


def _generar_franjas_desde(
    inicio_min: int,
    bandas: int,
    max_cantidad: int,
    min_descuento: float,
    max_descuento: float,
    curva: str = "linear",
    porcentajes: Optional[List[float]] = None,
) -> List[Dict]:
    """
    Genera franjas para el rango [inicio_min .. max_cantidad] dividido en `bandas` tramos,
    con descuentos entre min_descuento y max_descuento.
    """
    if inicio_min <= 0:
        raise ValueError("inicio_min debe ser > 0")
    if max_cantidad < inicio_min:
        return []
    total = max_cantidad - inicio_min + 1
    if bandas <= 0:
        return []

    base = total // bandas
    resto = total % bandas

    perc = _generar_porcentajes(
        bandas=bandas,
        min_descuento=min_descuento,
        max_descuento=max_descuento,
        curva=curva,
        porcentajes_explicitos=porcentajes,
    )

    franjas = []
    inicio = inicio_min
    for i in range(1, bandas + 1):
        ancho = base + (1 if i <= resto else 0)
        fin = inicio + ancho - 1
        descuento = perc[i - 1] if perc else max_descuento
        franjas.append({
            'min': inicio,
            'max': fin,
            'descuento': round(descuento, 4),
        })
        inicio = fin + 1
    if franjas:
        franjas[-1]['max'] = max(franjas[-1]['max'], max_cantidad)
    return franjas


def _parse_matriz(matriz_str: str) -> List[Tuple[float, float]]:
    """
    Parsea una matriz de la forma "umbral:descuento,umbral:descuento,..." ordenada por umbral ascendente.
    Ej: "0.5:15,1:20,2:25,5:30,10:35,20:40,50:45,100:50,999999:50"
    Devuelve lista de tuplas [(umbral, descuento_max), ...]
    """
    pares: List[Tuple[float, float]] = []
    if not matriz_str:
        return pares
    for item in matriz_str.split(','):
        item = item.strip()
        if not item:
            continue
        try:
            umbral_str, desc_str = item.split(':', 1)
            pares.append((float(umbral_str.strip()), float(desc_str.strip())))
        except Exception:
            raise SystemExit(
                "Error en --matriz. Formato esperado: 'umbral:descuento,...' p.ej. 1:20,5:30,20:40,999999:50"
            )
    pares.sort(key=lambda x: x[0])
    return pares


def _descuento_max_por_precio(subtotal: float, matriz: List[Tuple[float, float]], default: float) -> float:
    if subtotal is None:
        return default
    for (umbral, desc) in matriz:
        if subtotal <= umbral:
            return float(desc)
    return default


def aplicar_franjas_por_precio(
    bandas_total: int = 10,
    max_cantidad: int = 500,
    curva: str = "linear",
    matriz_tramos: Optional[List[Tuple[float, float]]] = None,
    min_descuento_resto: float = 5.0,
    default_max_desc: float = 40.0,
    dry_run: bool = False,
    uplift_desde_cantidad: int = 100,
    uplift_puntos: float = 5.0,
    uplift_tope_global: float = 60.0,
    color_keyword: str = "color",
    color_boost_pp: float = 5.0,
    producto_ids: Optional[List[int]] = None,
    paso_cantidad: int = 10,
) -> None:
    """
    Para cada producto, aplica franjas calculadas según su precio unitario (subtotal).
    - Siempre fija 1..10 con 0%.
    - Para 11..max_cantidad, genera (bandas_total-1) franjas entre min_descuento_resto y descuento_max_por_precio(producto).
    """
    # Requisito: 1..10 = 0% y el resto en bloques de tamaño configurable (paso_cantidad):
    # [11..(10+paso)], [(11+paso)..(10+2*paso)], ... hasta max_cantidad.

    ensure_tabla_descuentos_bandas()
    productos = obtener_productos() or []
    if producto_ids:
        ids_set = {int(x) for x in producto_ids}
        productos = [p for p in productos if int(p.get('id') or p.get('producto_id') or 0) in ids_set]
        print(f"[INFO] Filtrado por productos: {sorted(ids_set)} | a procesar={len(productos)}")
    matriz = matriz_tramos or []

    print(f"[INFO] Modo por-precio (paso={paso_cantidad}): max_cantidad={max_cantidad}, curva={curva}")
    print(f"[INFO] 1..10 = 0% para todos. min_descuento_resto={min_descuento_resto}%. default_max_desc={default_max_desc}%.")
    print(f"[INFO] Uplift desde cantidad >= {uplift_desde_cantidad}: +{uplift_puntos}pp (tope global {uplift_tope_global}%).")
    if color_keyword:
        print(f"[INFO] Productos 'de color' (nombre contiene '{color_keyword}', case-insensitive) reciben +{color_boost_pp}pp adicionales en todas las franjas >10 (respetando tope).")
    if matriz:
        print("[INFO] Matriz precio->max%:")
        for u, d in matriz:
            print(f"  - <= {u}: {d}%")

    aplicados = 0
    for p in productos:
        pid = p.get('id') or p.get('producto_id')
        nombre = p.get('nombre', '')
        subtotal = p.get('subtotal')
        impuestos = p.get('impuestos') or 0
        nombre_lc = (nombre or '').lower()
        es_color = (str(color_keyword).lower() in nombre_lc) if color_keyword else False
        if pid is None:
            continue

        max_desc = _descuento_max_por_precio(float(subtotal) if subtotal is not None else None, matriz, default_max_desc)
        max_desc = max(0.0, float(max_desc))
        # Componer franjas fijas: 1..10 = 0%, y bloques de 10 en 10 hasta max_cantidad
        franjas: List[Dict] = [{'min': 1, 'max': 10, 'descuento': 0.0}]
        if max_cantidad > 10:
            # Número de bloques de 'paso_cantidad' a partir de 11
            resto_total = max_cantidad - 10
            bloques = (resto_total + (paso_cantidad - 1)) // paso_cantidad  # ceil(resto_total/paso)
            # Porcentajes crecientes entre min_descuento_resto y max_desc según curva
            perc = _generar_porcentajes(
                bandas=bloques,
                min_descuento=min_descuento_resto,
                max_descuento=max_desc,
                curva=curva,
                porcentajes_explicitos=None,
            ) if bloques > 0 else []
            for i in range(bloques):
                bmin = 11 + i * paso_cantidad
                bmax = min(11 + (i + 1) * paso_cantidad - 1, max_cantidad)
                base = float(perc[i]) if perc else float(max_desc)
                if bmin >= uplift_desde_cantidad:
                    base = min(base + float(uplift_puntos), float(uplift_tope_global))
                # Boost adicional para productos de color
                if es_color and bmin >= 11:
                    base = min(base + float(color_boost_pp), float(uplift_tope_global))
                base = round(base, 4)
                # Si alcanzamos el tope, extendemos esta franja hasta max_cantidad y terminamos
                if base >= round(float(uplift_tope_global), 4):
                    franjas.append({'min': bmin, 'max': max_cantidad, 'descuento': round(float(uplift_tope_global), 4)})
                    break
                franjas.append({'min': bmin, 'max': bmax, 'descuento': base})

        # Enforce monotonicidad estricta (creciente) en descuentos a partir de >10
        # Evita repetir el mismo % entre bandas consecutivas; usa incremento mínimo de 0.0001
        if len(franjas) > 1:
            prev = round(float(franjas[0]['descuento']), 4)
            for k in range(1, len(franjas)):
                cur = round(float(franjas[k]['descuento']), 4)
                # Si no crece, forzar incremento mínimo de 0.0001 respetando tope
                if cur <= prev:
                    cur = prev + 0.0001
                # Respetar tope global
                cur = min(cur, float(uplift_tope_global))
                # Redondear a 4 decimales y fijar
                cur = round(cur, 4)
                # Si por redondeo aún no crece, elevar en el último decimal hasta tope
                if cur <= prev and prev < float(uplift_tope_global):
                    cur = round(min(prev + 0.0001, float(uplift_tope_global)), 4)
                franjas[k]['descuento'] = cur
                prev = cur

        # Enforce que el precio final con IVA (2 decimales) sea estrictamente decreciente por franja
        # Alineado con frontend: base (4 dec), IVA unitario (4 dec), total (2 dec) con ROUND_HALF_UP
        def precio_final(desc_pct: float) -> Decimal:
            try:
                st = Decimal(str(subtotal or 0))
                imp = Decimal(str(impuestos or 0))
                base = (st * (Decimal('1') - Decimal(str(desc_pct)) / Decimal('100'))).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
                iva_u = (base * (imp / Decimal('100'))).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
                total = (base + iva_u).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                return total
            except Exception:
                return Decimal('0.00')

        if len(franjas) > 0:
            # Asegurar 1..10 calculado
            prev_price = precio_final(franjas[0]['descuento'])
            j = 1
            while j < len(franjas):
                cur_desc = round(float(franjas[j]['descuento']), 4)
                cur_price = precio_final(cur_desc)
                # Exigir que baje al menos 0.01€ respecto a la franja previa
                target_price = (prev_price - Decimal('0.01'))
                if cur_price > target_price:
                    # Calcular incremento mínimo que garantice bajar al menos 0.01 con redondeo HALF_UP
                    limite = float(uplift_tope_global)
                    st_dec = Decimal(str(subtotal or 0))
                    imp_dec = Decimal(str(impuestos or 0))
                    # Reconstrucción del total como en frontend: total = round2(round4(st*(1-d)) + round4(round4(st*(1-d))*imp/100))
                    # Para hallar descuento mínimo que baje 0.01€, hacemos búsqueda incremental fina limitada
                    base_factor = (Decimal('1') + imp_dec / Decimal('100'))  # solo para cota superior/inferior rápida
                    base_total = st_dec * base_factor
                    if base_total <= 0:
                        # Si el subtotal es 0, fusionar franjas para evitar duplicados
                        franjas[j-1]['max'] = franjas[j]['max']
                        franjas.pop(j)
                        continue
                    # Para asegurar que el HALF_UP baje 1 céntimo, el total no redondeado debe ser < prev_price - 0.005
                    # Exploración adaptativa: saltos grandes primero y luego finos
                    saltos = [0.05, 0.01, 0.005, 0.001, 0.0005, 0.0001]
                    cur_price_dec = cur_price
                    for s in saltos:
                        pasos = 0
                        while cur_price_dec > target_price and cur_desc < limite and pasos < 10000:
                            cur_desc = round(min(cur_desc + s, limite), 4)
                            cur_price_dec = precio_final(cur_desc)
                            pasos += 1
                        if cur_price_dec <= target_price or cur_desc >= limite:
                            break
                    cur_price = cur_price_dec
                    if cur_price > target_price and cur_desc >= limite:
                        # No se puede bajar el precio: fusionar esta franja con la anterior
                        franjas[j-1]['max'] = franjas[j]['max']
                        # Eliminar franja j
                        franjas.pop(j)
                        # No avanzamos j para reevaluar con la nueva franja siguiente
                        continue
                    else:
                        franjas[j]['descuento'] = cur_desc
                        prev_price = cur_price
                        j += 1
                else:
                    prev_price = cur_price
                    j += 1

        if dry_run:
            print(f"[DRY] Producto {pid} - {nombre} (subtotal={subtotal}) -> max_desc={max_desc}% | franjas={len(franjas)}")
        else:
            reemplazar_franjas_descuento_producto(pid, franjas)
            aplicados += 1
            if aplicados % 50 == 0:
                print(f"[INFO] Aplicados {aplicados} productos...")

    if dry_run:
        print("[DRY] No se realizaron cambios en la base de datos.")
    else:
        print(f"[OK] Franjas por-precio aplicadas a {aplicados} productos.")


def aplicar_franjas_a_todos(
    bandas: int = 10,
    max_cantidad: int = 500,
    max_descuento: float = 90.0,
    min_descuento: float = 0.0,
    curva: str = "linear",
    porcentajes: Optional[List[float]] = None,
    dry_run: bool = False,
    producto_ids: Optional[List[int]] = None,
) -> None:
    ensure_tabla_descuentos_bandas()
    productos = obtener_productos() or []
    if producto_ids:
        ids_set = {int(x) for x in producto_ids}
        productos = [p for p in productos if int(p.get('id') or p.get('producto_id') or 0) in ids_set]
        print(f"[INFO] Filtrado por productos: {sorted(ids_set)} | a procesar={len(productos)}")
    franjas = generar_franjas(
        bandas=bandas,
        max_cantidad=max_cantidad,
        max_descuento=max_descuento,
        min_descuento=min_descuento,
        curva=curva,
        porcentajes=porcentajes,
    )

    # Asegurar que la primera franja (1..10) sea 0% explícito en modo uniforme
    if franjas:
        try:
            # Solo si efectivamente inicia en 1 y cubre 1..10, fijamos 0%
            if int(franjas[0].get('min', 0)) == 1 and int(franjas[0].get('max', 0)) >= 10:
                franjas[0]['descuento'] = 0.0
        except Exception:
            # Ante cualquier anomalía, simplemente establecer a 0 la primera banda
            franjas[0]['descuento'] = 0.0

    print(f"[INFO] Generadas {len(franjas)} franjas 1..{max_cantidad} con descuentos {min_descuento}% -> {max_descuento}% (curva={curva})")
    for fr in franjas:
        print(f"  - {fr['min']:>4}-{fr['max']:<4}: {fr['descuento']}%")

    print(f"[INFO] Productos a procesar: {len(productos)}")
    aplicados = 0
    for p in productos:
        pid = p.get('id') or p.get('producto_id')
        nombre = p.get('nombre', '')
        if not pid:
            continue
        if dry_run:
            print(f"[DRY] Reemplazar franjas para producto {pid} - {nombre}")
        else:
            reemplazar_franjas_descuento_producto(pid, franjas)
            aplicados += 1
            if aplicados % 50 == 0:
                print(f"[INFO] Aplicados {aplicados} productos...")
    if dry_run:
        print("[DRY] No se realizaron cambios en la base de datos.")
    else:
        print(f"[OK] Franjas aplicadas a {aplicados} productos.")



def main():
    parser = argparse.ArgumentParser(
        description="Aplicar franjas de descuento a todos los productos"
    )
    parser.add_argument(
        "--modo",
        choices=["uniforme", "por-precio"],
        default="uniforme",
        help="Modo de aplicación: 'uniforme' (actual por defecto) o 'por-precio' (según subtotal).",
    )
    parser.add_argument("--bandas", type=int, default=10, help="Número de franjas (default: 10)")
    parser.add_argument("--max-cantidad", type=int, default=500, help="Cantidad máxima (default: 500)")
    parser.add_argument("--max-descuento", type=float, default=60.0, help="Descuento máximo % (default: 60.0)")
    parser.add_argument("--min-descuento", type=float, default=0.0, help="Descuento mínimo % (default: 0.0)")
    parser.add_argument(
        "--curva",
        type=str,
        choices=["linear", "concava", "convexa", "sigmoide"],
        default="linear",
        help="Curva de incremento del % (linear, concava, convexa, sigmoide).",
    )
    parser.add_argument(
        "--porcentajes",
        type=str,
        default="",
        help="Lista explícita de % separada por comas (anula --curva). Ej: 5,10,15,25,35,45,55,58,60",
    )
    # Opciones específicas modo por-precio
    parser.add_argument(
        "--matriz",
        type=str,
        default="0.5:15,1:20,2:25,5:30,10:35,20:40,50:45,100:60,999999:60",
        help="Matriz precio->max% (umbral:descuento,...) aplicada según subtotal. Ej: 1:20,5:30,20:40,999999:60",
    )
    parser.add_argument(
        "--min-descuento-resto",
        type=float,
        default=5.0,
        help="% mínimo para el rango 11..max_cantidad (se combina con el max% resultante por precio).",
    )
    parser.add_argument(
        "--default-max-desc",
        type=float,
        default=40.0,
        help="% máximo por defecto si el subtotal no encaja en la matriz (o está vacío).",
    )
    parser.add_argument(
        "--uplift-desde",
        type=int,
        default=100,
        help="Cantidad mínima desde la cual se aplica un uplift en puntos porcentuales a cada franja (default: 100)",
    )
    parser.add_argument(
        "--uplift-puntos",
        type=float,
        default=5.0,
        help="Puntos porcentuales a sumar al descuento desde --uplift-desde en adelante (default: 5.0)",
    )
    parser.add_argument(
        "--uplift-tope",
        type=float,
        default=60.0,
        help="Tope global de descuento tras aplicar uplift (default: 60.0)",
    )
    parser.add_argument(
        "--color-keyword",
        type=str,
        default="color",
        help="Palabra clave para identificar productos 'de color' en el nombre (case-insensitive).",
    )
    parser.add_argument(
        "--color-boost-pp",
        type=float,
        default=5.0,
        help="Puntos porcentuales adicionales para productos 'de color' (aplica en franjas >10).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Simula sin escribir en BD")
    parser.add_argument(
        "--producto-ids",
        type=str,
        default="",
        help="Lista de IDs de producto separados por comas para limitar el alcance. Ej: 118,205,306",
    )
    parser.add_argument(
        "--paso",
        type=int,
        default=10,
        help="Tamaño del bloque de cantidad para franjas en modo por-precio (default: 10). Ej: 100",
    )

    args = parser.parse_args()
    # Log de la BD que se usará
    try:
        print(f"[INFO] Usando base de datos: {DB_NAME}")
    except Exception:
        pass
    # Parseo de producto-ids
    lista_ids: Optional[List[int]] = None
    if args.producto_ids:
        try:
            lista_ids = [int(x.strip()) for x in args.producto_ids.split(',') if x.strip() != ""]
        except Exception:
            raise SystemExit("Error: no se pudo parsear --producto-ids. Use enteros separados por comas, p.ej. 118,205")

    if args.modo == "uniforme":
        lista_porcentajes = None
        if args.porcentajes:
            try:
                lista_porcentajes = [float(x.strip()) for x in args.porcentajes.split(',') if x.strip() != ""]
            except Exception:
                raise SystemExit("Error: no se pudo parsear --porcentajes. Use una lista separada por comas, p.ej. 5,10,15,...")
        aplicar_franjas_a_todos(
            bandas=args.bandas,
            max_cantidad=args.max_cantidad,
            max_descuento=args.max_descuento,
            min_descuento=args.min_descuento,
            curva=args.curva,
            porcentajes=lista_porcentajes,
            dry_run=args.dry_run,
            producto_ids=lista_ids,
        )
    else:
        matriz = _parse_matriz(args.matriz) if args.matriz else []
        aplicar_franjas_por_precio(
            bandas_total=args.bandas,
            max_cantidad=args.max_cantidad,
            curva=args.curva,
            matriz_tramos=matriz,
            min_descuento_resto=args.min_descuento_resto,
            default_max_desc=args.default_max_desc,
            dry_run=args.dry_run,
            uplift_desde_cantidad=args.uplift_desde,
            uplift_puntos=args.uplift_puntos,
            uplift_tope_global=args.uplift_tope,
            color_keyword=args.color_keyword,
            color_boost_pp=args.color_boost_pp,
            producto_ids=lista_ids,
            paso_cantidad=args.paso,
        )
        # Verificación rápida: contar filas en la tabla
        try:
            from db_utils import get_db_connection
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM descuento_producto_franja")
            total_filas = cur.fetchone()[0]
            print(f"[INFO] Filas en descuento_producto_franja tras aplicar: {total_filas}")
            conn.close()
        except Exception as e:
            print(f"[WARN] No se pudo verificar conteo de filas: {e}")


if __name__ == "__main__":
    main()
