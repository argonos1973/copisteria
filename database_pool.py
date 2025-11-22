#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DATABASE CONNECTION POOL PARA SQLITE
====================================
Sistema avanzado de connection pooling con todas las características solicitadas
"""

import sqlite3
import threading
import time
import queue
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PoolMetrics:
    """Métricas del pool de conexiones"""
    total_connections: int = 0
    active_connections: int = 0
    connections_in_use: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    retry_attempts: int = 0
    avg_wait_time: float = 0.0
    max_wait_time: float = 0.0
    errors: list = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class PooledConnection:
    """Wrapper para conexiones con context manager"""
    
    def __init__(self, conn: sqlite3.Connection, pool: 'DatabasePool'):
        self.connection = conn
        self.pool = pool
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.in_use = False
    
    def close(self):
        """Devuelve la conexión al pool en lugar de cerrarla"""
        self.pool._return_connection(self)

    def cursor(self):
        return self.connection.cursor()

    def execute(self, *args, **kwargs):
        return self.connection.execute(*args, **kwargs)

    def commit(self):
        return self.connection.commit()
        
    def rollback(self):
        return self.connection.rollback()
        
    def __getattr__(self, name):
        return getattr(self.connection, name)

    def __enter__(self):
        self.in_use = True
        self.last_used = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.in_use = False
        self.pool._return_connection(self)
    
    def is_healthy(self) -> bool:
        """Verifica si la conexión está activa"""
        try:
            self.connection.execute('SELECT 1').fetchone()
            return True
        except Exception:
            return False

class DatabasePool:
    """
    Pool de conexiones SQLite con todas las funcionalidades requeridas:
    - Máximo 10 conexiones
    - Context managers automáticos  
    - Retry logic para fallos
    - Timeout handling
    - Métricas completas
    """
    
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        self.max_connections = max_connections
        self.metrics = PoolMetrics()
        
        # Pool y sincronización
        self._pool: queue.Queue = queue.Queue(maxsize=max_connections)
        self._lock = threading.RLock()
        self._all_connections = []
        self._shutdown = False
        
        # Configuración de retry y timeout
        self.retry_attempts = 5
        self.retry_delay = 1.0
        self.default_timeout = 60.0
        
        # Inicializar con 2 conexiones mínimas
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Inicializa el pool con conexiones mínimas"""
        try:
            for _ in range(2):  # Conexiones mínimas
                conn = self._create_connection()
                if conn:
                    self._pool.put(conn, block=False)
            logger.info(f"Pool inicializado para {self.db_path}")
        except Exception as e:
            logger.error(f"Error inicializando pool: {e}")
    
    def _create_connection(self) -> Optional[PooledConnection]:
        """Crea nueva conexión SQLite optimizada"""
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=self.default_timeout,
                check_same_thread=False
            )
            
            # Configurar conexión para rendimiento
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA encoding="UTF-8"')
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            
            pooled_conn = PooledConnection(conn, self)
            
            with self._lock:
                self._all_connections.append(pooled_conn)
                self.metrics.total_connections += 1
                self.metrics.active_connections += 1
            
            return pooled_conn
            
        except Exception as e:
            logger.error(f"Error creando conexión: {e}")
            with self._lock:
                self.metrics.failed_requests += 1
                self.metrics.errors.append(f"{datetime.now()}: {str(e)}")
            return None
    
    def get_connection(self, timeout: Optional[float] = None) -> PooledConnection:
        """
        Obtiene conexión con retry logic y timeout handling
        """
        if self._shutdown:
            raise RuntimeError("Pool cerrado")
        
        timeout = timeout or self.default_timeout
        start_time = time.time()
        
        with self._lock:
            self.metrics.total_requests += 1
        
        # Retry logic implementado
        for attempt in range(self.retry_attempts + 1):
            try:
                # Intentar obtener conexión existente
                try:
                    pooled_conn = self._pool.get(timeout=min(timeout, 5.0))
                    
                    if pooled_conn.is_healthy():
                        wait_time = time.time() - start_time
                        self._update_wait_metrics(wait_time)
                        
                        with self._lock:
                            self.metrics.connections_in_use += 1
                        
                        return pooled_conn
                    else:
                        # Conexión no saludable, cerrar y crear nueva
                        self._close_connection(pooled_conn)
                        
                except queue.Empty:
                    # Pool vacío, crear nueva conexión si hay espacio
                    if len(self._all_connections) < self.max_connections:
                        new_conn = self._create_connection()
                        if new_conn and new_conn.is_healthy():
                            wait_time = time.time() - start_time
                            self._update_wait_metrics(wait_time)
                            
                            with self._lock:
                                self.metrics.connections_in_use += 1
                            
                            return new_conn
                
                # Si llegamos aquí, hacer retry
                if attempt < self.retry_attempts:
                    with self._lock:
                        self.metrics.retry_attempts += 1
                    
                    logger.warning(f"Retry {attempt + 1}/{self.retry_attempts} en {self.retry_delay}s")
                    time.sleep(self.retry_delay)
                    
                    # Actualizar timeout restante
                    elapsed = time.time() - start_time
                    timeout = max(timeout - elapsed, 1.0)
                
            except Exception as e:
                logger.error(f"Error en intento {attempt + 1}: {e}")
        
        # Todos los intentos fallaron
        error_msg = f"No se pudo obtener conexión después de {self.retry_attempts + 1} intentos"
        logger.error(error_msg)
        
        with self._lock:
            self.metrics.failed_requests += 1
            self.metrics.errors.append(f"{datetime.now()}: {error_msg}")
        
        raise RuntimeError(error_msg)
    
    def _return_connection(self, pooled_conn: PooledConnection):
        """Devuelve conexión al pool"""
        try:
            # CRÍTICO: Asegurar que la conexión esté limpia de transacciones
            try:
                pooled_conn.connection.rollback()
            except Exception:
                pass

            with self._lock:
                self.metrics.connections_in_use = max(0, self.metrics.connections_in_use - 1)
                
                if not self._shutdown and pooled_conn.is_healthy():
                    self._pool.put(pooled_conn, block=False)
                else:
                    self._close_connection(pooled_conn)
                    
        except queue.Full:
            # Pool lleno, cerrar conexión
            self._close_connection(pooled_conn)
    
    def _close_connection(self, pooled_conn: PooledConnection):
        """Cierra conexión específica"""
        try:
            pooled_conn.connection.close()
            
            with self._lock:
                if pooled_conn in self._all_connections:
                    self._all_connections.remove(pooled_conn)
                self.metrics.active_connections = max(0, self.metrics.active_connections - 1)
                
        except Exception as e:
            logger.error(f"Error cerrando conexión: {e}")
    
    def _update_wait_metrics(self, wait_time: float):
        """Actualiza métricas de tiempo de espera"""
        with self._lock:
            if wait_time > self.metrics.max_wait_time:
                self.metrics.max_wait_time = wait_time
            
            # Calcular promedio móvil
            current_avg = self.metrics.avg_wait_time
            total_requests = self.metrics.total_requests
            self.metrics.avg_wait_time = (
                (current_avg * (total_requests - 1) + wait_time) / total_requests
            )
    
    @contextmanager
    def get_db_connection(self):
        """
        Context manager principal - AUTO-CERRADO GARANTIZADO
        
        Usage:
            with pool.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM table")
        """
        pooled_conn = None
        try:
            pooled_conn = self.get_connection()
            yield pooled_conn
        finally:
            if pooled_conn:
                self._return_connection(pooled_conn)
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False):
        """
        Ejecuta query automáticamente usando el pool
        
        Returns:
            dict: {'success': bool, 'data': any, 'error': str}
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch_one:
                    result = cursor.fetchone()
                    data = dict(result) if result else None
                else:
                    results = cursor.fetchall()
                    data = [dict(row) for row in results] if results else []
                
                conn.commit()
                return {'success': True, 'data': data, 'error': None}
                
        except Exception as e:
            error_msg = f"Error ejecutando query: {e}"
            logger.error(error_msg)
            return {'success': False, 'data': None, 'error': error_msg}
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Devuelve métricas detalladas del pool
        """
        with self._lock:
            return {
                'total_connections': self.metrics.total_connections,
                'active_connections': self.metrics.active_connections,
                'connections_in_use': self.metrics.connections_in_use,
                'connections_available': self._pool.qsize(),
                'total_requests': self.metrics.total_requests,
                'failed_requests': self.metrics.failed_requests,
                'retry_attempts': self.metrics.retry_attempts,
                'avg_wait_time': round(self.metrics.avg_wait_time, 4),
                'max_wait_time': round(self.metrics.max_wait_time, 4),
                'success_rate': round(
                    (1 - self.metrics.failed_requests / max(self.metrics.total_requests, 1)) * 100, 2
                ),
                'pool_utilization': round(
                    (self.metrics.connections_in_use / self.max_connections) * 100, 2
                ),
                'recent_errors': self.metrics.errors[-5:] if self.metrics.errors else []
            }
    
    def reset_metrics(self):
        """Resetea todas las métricas"""
        with self._lock:
            self.metrics = PoolMetrics()
            logger.info("Métricas del pool reseteadas")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Verifica salud del pool y conexiones
        """
        healthy_connections = 0
        unhealthy_connections = 0
        
        with self._lock:
            for conn in self._all_connections:
                if not conn.in_use:
                    if conn.is_healthy():
                        healthy_connections += 1
                    else:
                        unhealthy_connections += 1
                        self._close_connection(conn)
        
        return {
            'pool_status': 'healthy' if healthy_connections > 0 else 'degraded',
            'healthy_connections': healthy_connections,
            'unhealthy_connections': unhealthy_connections,
            'pool_size': self._pool.qsize(),
            'max_connections': self.max_connections
        }
    
    def shutdown(self):
        """Cierra el pool y todas las conexiones"""
        self._shutdown = True
        
        with self._lock:
            while self._all_connections:
                conn = self._all_connections[0]
                self._close_connection(conn)
        
        logger.info(f"Pool cerrado para {self.db_path}")

# =====================================================
# INSTANCIA GLOBAL DEL POOL
# =====================================================

# Pool global para la aplicación
_global_pools = {}
_pool_lock = threading.Lock()

def get_database_pool(db_path: str) -> DatabasePool:
    """
    Obtiene o crea pool para una base de datos específica
    """
    with _pool_lock:
        if db_path not in _global_pools:
            _global_pools[db_path] = DatabasePool(db_path)
        return _global_pools[db_path]

def shutdown_all_pools():
    """Cierra todos los pools activos"""
    with _pool_lock:
        for pool in _global_pools.values():
            pool.shutdown()
        _global_pools.clear()
