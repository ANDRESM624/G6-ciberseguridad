# ============================================================
# config.py — Med-Core App
# Capa de configuración: carga los parámetros de la aplicación
# desde variables de entorno definidas en un archivo .env.
# Las credenciales nunca deben estar escritas directamente
# en el código fuente.
# ============================================================

import os
from dotenv import load_dotenv

# Cargar las variables del archivo .env en el entorno del proceso.
# Debe ejecutarse antes de acceder a cualquier atributo de Config.
load_dotenv()


class Config:
    """
    Clase de configuración central para la aplicación Med-Core.

    Todos los valores sensibles se leen exclusivamente desde variables
    de entorno, de modo que las credenciales nunca se almacenan en el
    repositorio. Crea un archivo '.env' local (ver '.env.example') para
    proveer los valores durante el desarrollo.
    """

    # ------------------------------------------------------------------
    # Configuración principal de Flask
    # ------------------------------------------------------------------

    # Clave secreta utilizada por Flask para firmar criptográficamente
    # las sesiones y las cookies. Debe ser una cadena larga y aleatoria
    # en entornos de producción.
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me-in-production")

    # Activa el modo de depuración solo cuando se solicita explícitamente.
    DEBUG: bool = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    # ------------------------------------------------------------------
    # Parámetros de conexión a PostgreSQL
    # ------------------------------------------------------------------

    DB_HOST: str = os.environ.get("DB_HOST", "localhost")
    DB_NAME: str = os.environ.get("DB_NAME", "med_core_db")
    DB_USER: str = os.environ.get("DB_USER", "postgres")
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD", "")
    DB_PORT: int = int(os.environ.get("DB_PORT", "5432"))

    @classmethod
    def get_dsn(cls) -> str:
        """
        Construye y retorna una cadena DSN compatible con libpq a partir
        de los parámetros de conexión individuales.

        Ejemplo de salida:
            host=localhost dbname=med_core_db user=postgres password=secreto port=5432
        """
        return (
            f"host={cls.DB_HOST} "
            f"dbname={cls.DB_NAME} "
            f"user={cls.DB_USER} "
            f"password={cls.DB_PASSWORD} "
            f"port={cls.DB_PORT}"
        )
