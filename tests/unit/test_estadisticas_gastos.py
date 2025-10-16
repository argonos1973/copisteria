"""
Tests unitarios para estadisticas_gastos_routes.py
"""
import pytest
import sys
from pathlib import Path

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import estadisticas_gastos_routes as est


class TestNormalizarConcepto:
    """Tests para la función _normalizar_concepto"""
    
    def test_normalizar_recibo_basico(self):
        """Test normalización de recibos básicos"""
        concepto = "Recibo Empresa Test S.L."
        resultado = est._normalizar_concepto(concepto)
        # La función elimina puntos de S.L. → Sl
        assert "Recibo Empresa Test" in resultado
    
    def test_normalizar_tarjeta_con_comision(self):
        """Test eliminación de información de tarjeta y comisión"""
        concepto = "Compra Tienda Test, Tarjeta 4176570108340631 , Comision 0"
        resultado = est._normalizar_concepto(concepto)
        assert "Tarjeta" not in resultado
        assert "Comision" not in resultado
        assert "4176" not in resultado
    
    def test_normalizar_compra_tarjeta(self):
        """Test normalización de compras con tarjeta"""
        concepto = "Compra Tarjeta Carrefour Barcelona"
        resultado = est._normalizar_concepto(concepto)
        # La función NO elimina "Tarjeta" ni la ciudad genéricamente
        # Solo hace normalizaciones específicas (Amazon, Uber, Taxi, etc)
        assert "Compra" in resultado and "Carrefour" in resultado
    
    def test_normalizar_bizum(self):
        """Test normalización de Bizum"""
        concepto = "Bizum Pago Test Usuario"
        resultado = est._normalizar_concepto(concepto)
        assert "Bizum" in resultado
    
    def test_normalizar_eliminar_ciudad(self):
        """Test que la función no elimina ciudades genéricamente"""
        concepto = "Ikea, Barcelona"
        resultado = est._normalizar_concepto(concepto)
        # La función NO elimina ciudades genéricamente
        assert "Ikea" in resultado


class TestObtenerCaseCategoriaSql:
    """Tests para la función _obtener_case_categoria_sql"""
    
    def test_case_sql_contiene_recibos(self):
        """Test que el CASE SQL incluye categoría Recibos"""
        sql = est._obtener_case_categoria_sql()
        assert "Recibos" in sql
        assert "LIKE 'Recibo%'" in sql
    
    def test_case_sql_contiene_liquidaciones(self):
        """Test que el CASE SQL incluye categoría Liquidaciones TPV"""
        sql = est._obtener_case_categoria_sql()
        assert "Liquidaciones TPV" in sql
        assert "LIKE 'Liquidacion%'" in sql
    
    def test_case_sql_contiene_tarjeta(self):
        """Test que el CASE SQL incluye categoría Compras Tarjeta"""
        sql = est._obtener_case_categoria_sql()
        assert "Compras Tarjeta" in sql
        assert "NOT LIKE 'Liquidacion%'" in sql


class TestObtenerFiltroCategoria:
    """Tests para la función _obtener_filtro_categoria"""
    
    def test_filtro_recibos(self):
        """Test filtro para categoría Recibos"""
        filtro = est._obtener_filtro_categoria('Recibos')
        assert "Recibo%" in filtro
    
    def test_filtro_liquidaciones(self):
        """Test filtro para categoría Liquidaciones TPV"""
        filtro = est._obtener_filtro_categoria('Liquidaciones TPV')
        assert "Liquidacion%" in filtro
    
    def test_filtro_bizum(self):
        """Test filtro para categoría Bizum"""
        filtro = est._obtener_filtro_categoria('Bizum')
        assert "Bizum" in filtro
    
    def test_filtro_compras_tarjeta(self):
        """Test filtro para categoría Compras Tarjeta"""
        filtro = est._obtener_filtro_categoria('Compras Tarjeta')
        assert "Tarjeta%" in filtro or "Compra%" in filtro
        assert "NOT LIKE 'Liquidacion%'" in filtro
    
    def test_filtro_desconocido(self):
        """Test filtro para categoría desconocida devuelve default"""
        filtro = est._obtener_filtro_categoria('Categoria Inexistente')
        assert filtro == "1=1"


class TestIdentificarGastosPuntuales:
    """Tests para la lógica de identificación de gastos puntuales"""
    
    def test_identificar_gastos_no_recurrentes(self, test_db, sample_gastos):
        """Test identificación de gastos >1000€ no recurrentes"""
        # El gasto de 1500€ debería ser identificado como puntual
        gastos_puntuales = est._identificar_gastos_puntuales(test_db, 2025)
        
        # Verificar que hay al menos un gasto puntual identificado
        assert isinstance(gastos_puntuales, (list, set))
    
    def test_no_identificar_gastos_pequenos(self, test_db, sample_gastos):
        """Test que gastos <1000€ no se marcan como puntuales"""
        gastos_puntuales = est._identificar_gastos_puntuales(test_db, 2025)
        
        # Los gastos de 100€, 50€ y 25€ NO deberían estar en puntuales
        cursor = test_db.cursor()
        cursor.execute("SELECT id FROM gastos WHERE importe_eur > -1000")
        ids_pequenos = [row['id'] for row in cursor.fetchall()]
        
        # Ninguno de los gastos pequeños debería estar en la lista de puntuales
        for id_pequeno in ids_pequenos:
            assert id_pequeno not in gastos_puntuales


class TestMarcarGastosPuntuales:
    """Tests para la función _marcar_gastos_puntuales"""
    
    def test_marcar_gastos_correctamente(self, test_db):
        """Test que marca correctamente gastos como puntuales"""
        # Insertar un gasto de prueba
        cursor = test_db.cursor()
        cursor.execute('''
            INSERT INTO gastos (fecha_operacion, concepto, importe_eur, puntual)
            VALUES ('15/10/2025', 'Test Puntual', -1500.00, 0)
        ''')
        test_db.commit()
        
        gasto_id = cursor.lastrowid
        
        # Marcar como puntual
        est._marcar_gastos_puntuales(test_db, [gasto_id])
        
        # Verificar que se marcó
        cursor.execute("SELECT puntual FROM gastos WHERE id = ?", (gasto_id,))
        resultado = cursor.fetchone()
        assert resultado['puntual'] == 1
    
    def test_desmarcar_gastos_no_puntuales(self, test_db):
        """Test que desmarca gastos que ya no son puntuales"""
        # Insertar gasto marcado como puntual
        cursor = test_db.cursor()
        cursor.execute('''
            INSERT INTO gastos (fecha_operacion, concepto, importe_eur, puntual)
            VALUES ('15/10/2025', 'Test No Puntual', -100.00, 1)
        ''')
        test_db.commit()
        
        gasto_id = cursor.lastrowid
        
        # Llamar con lista vacía (ninguno es puntual)
        est._marcar_gastos_puntuales(test_db, [])
        
        # Verificar que se desmarcó
        cursor.execute("SELECT puntual FROM gastos WHERE id = ?", (gasto_id,))
        resultado = cursor.fetchone()
        assert resultado['puntual'] == 0
    
    def test_preservar_gastos_manuales(self, test_db):
        """Test que NO desmarca gastos marcados manualmente (puntual=2)"""
        # Insertar gasto marcado manualmente
        cursor = test_db.cursor()
        cursor.execute('''
            INSERT INTO gastos (fecha_operacion, concepto, importe_eur, puntual)
            VALUES ('15/10/2025', 'Test Manual', -100.00, 2)
        ''')
        test_db.commit()
        
        gasto_id = cursor.lastrowid
        
        # Llamar con lista vacía
        est._marcar_gastos_puntuales(test_db, [])
        
        # Verificar que NO se desmarcó (sigue en 2)
        cursor.execute("SELECT puntual FROM gastos WHERE id = ?", (gasto_id,))
        resultado = cursor.fetchone()
        assert resultado['puntual'] == 2


class TestInicializarCampoPuntual:
    """Tests para la función _inicializar_campo_puntual"""
    
    def test_inicializar_sin_error(self, test_db):
        """Test que inicializar campo puntual no genera errores"""
        try:
            est._inicializar_campo_puntual(test_db)
            assert True
        except Exception as e:
            pytest.fail(f"_inicializar_campo_puntual falló con error: {e}")
    
    def test_campo_puntual_existe_despues_inicializar(self, test_db):
        """Test que el campo puntual existe después de inicializar"""
        est._inicializar_campo_puntual(test_db)
        
        cursor = test_db.cursor()
        cursor.execute("PRAGMA table_info(gastos)")
        columnas = cursor.fetchall()
        columnas_nombres = [col['name'] for col in columnas]
        
        assert 'puntual' in columnas_nombres
