# ============================================================
# database.py — Med-Core App
# Capa de acceso a datos: gestión de conexiones a PostgreSQL
# mediante un pool de conexiones de psycopg2.
# No se utiliza ORM; todas las consultas son SQL puro.
# ============================================================

import os
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool, OperationalError

from config import Config

# ------------------------------------------------------------------
# Pool de conexiones
# ------------------------------------------------------------------
# ThreadedConnectionPool mantiene un número fijo de conexiones
# reutilizables. psycopg2 entrega conexiones del pool bajo demanda
# y las devuelve automáticamente cuando se llama a putconn().
#
#   minconn — número mínimo de conexiones abiertas en todo momento.
#   maxconn — límite máximo; los solicitantes esperan si se alcanza.
#
# El pool es de nivel de módulo para que se inicialice una sola vez
# y sea compartido por todo el proceso de la aplicación.
# ------------------------------------------------------------------

_pool: pool.ThreadedConnectionPool | None = None


def init_pool(minconn: int = 1, maxconn: int = 10) -> None:
    """
    Crea el pool global de conexiones usando las credenciales de Config.

    Debe llamarse una sola vez al iniciar la aplicación (por ejemplo,
    dentro de la fábrica de la aplicación Flask).

    Args:
        minconn: Número mínimo de conexiones a mantener abiertas.
        maxconn: Número máximo de conexiones permitidas en el pool.

    Raises:
        OperationalError: Si psycopg2 no puede conectarse a PostgreSQL.
    """
    global _pool

    if _pool is not None:
        # El pool ya fue inicializado — no se hace nada.
        return

    try:
        _pool = pool.ThreadedConnectionPool(
            minconn,
            maxconn,
            dsn=Config.get_dsn(),
        )
        print(f"[database] Pool de conexiones inicializado "
              f"(min={minconn}, max={maxconn}).")
    except OperationalError as exc:
        print(f"[database] FATAL — no se pudo conectar a PostgreSQL: {exc}")
        raise


def get_connection() -> psycopg2.extensions.connection:
    """
    Obtiene una conexión disponible del pool.

    Siempre acompañar esta llamada con `release_connection()` dentro
    de un bloque finally, o utilizar el gestor de contexto
    `get_db_connection()` para que la devolución sea automática.

    Returns:
        Un objeto de conexión activo de psycopg2.

    Raises:
        RuntimeError: Si el pool aún no ha sido inicializado.
    """
    if _pool is None:
        raise RuntimeError(
            "El pool de conexiones no está inicializado. "
            "Llama a init_pool() antes de solicitar conexiones."
        )
    return _pool.getconn()


def release_connection(conn: psycopg2.extensions.connection) -> None:
    """
    Devuelve una conexión al pool para que pueda ser reutilizada.

    Args:
        conn: El objeto de conexión previamente obtenido con get_connection().
    """
    if _pool is not None and conn is not None:
        _pool.putconn(conn)


def close_pool() -> None:
    """
    Cierra todas las conexiones del pool y libera los recursos.

    Llamar durante el apagado de la aplicación (por ejemplo, en un
    manejador atexit o en teardown_appcontext de Flask).
    """
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        print("[database] Pool de conexiones cerrado.")


# ------------------------------------------------------------------
# Gestor de contexto (patrón de uso recomendado)
# ------------------------------------------------------------------

@contextmanager
def get_db_connection():
    """
    Gestor de contexto que obtiene una conexión del pool, la cede al
    llamador y garantiza su devolución al pool al finalizar — incluso
    si ocurre una excepción.

    Uso:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM usuarios;")
                filas = cur.fetchall()
        # La conexión se devuelve automáticamente aquí.
    """
    conn = get_connection()
    try:
        yield conn
    except Exception:
        # Revertir cualquier transacción no confirmada antes de devolver
        # la conexión al pool para no dejarla en un estado sucio.
        conn.rollback()
        raise
    finally:
        release_connection(conn)


# ------------------------------------------------------------------
# Inicialización / bootstrap de la base de datos
# ------------------------------------------------------------------

# Resolver la ruta a init.sql relativa a la ubicación de este archivo
# para que la función funcione sin importar el directorio de trabajo.
_SQL_INIT_PATH = os.path.join(
    os.path.dirname(__file__), "database", "init.sql"
)


def init_db() -> None:
    """
    Inicializa la base de datos ejecutando el script 'database/init.sql'.

    El script SQL utiliza guardas DROP/CREATE que hacen seguro llamar
    esta función en cada arranque; solo creará las tablas que falten.

    Requiere que el pool de conexiones esté inicializado primero
    (llama a init_pool() antes que a init_db()).

    Raises:
        FileNotFoundError: Si 'database/init.sql' no se encuentra.
        psycopg2.Error:    Si la ejecución del SQL falla.
    """
    if not os.path.exists(_SQL_INIT_PATH):
        raise FileNotFoundError(
            f"[database] init.sql no encontrado en: {_SQL_INIT_PATH}\n"
            "Asegúrate de que el directorio 'database/' exista junto a este archivo."
        )

    # Leer el contenido completo del script de inicialización
    with open(_SQL_INIT_PATH, "r", encoding="utf-8") as archivo_sql:
        script_sql = archivo_sql.read()

    print(f"[database] Ejecutando init.sql desde: {_SQL_INIT_PATH}")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(script_sql)
        conn.commit()

    print("[database] Bootstrap de la base de datos completado.")
