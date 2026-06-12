# ============================================================
# app.py — Med-Core App
# Punto de entrada principal de la aplicación Flask.
# Gestiona la autenticación de usuarios consultando la tabla
# 'usuarios' mediante SQL puro (sin ORM).
#
# ADVERTENCIA EDUCATIVA: Las contraseñas en este entorno de
# prueba se almacenan en texto plano para demostrar
# vulnerabilidades comunes. NUNCA usar en producción.
# ============================================================

from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    flash,
)

import atexit

from config import Config
from database import init_pool, init_db, get_db_connection, close_pool

# ------------------------------------------------------------------
# Creación e inicialización de la aplicación Flask
# ------------------------------------------------------------------

app = Flask(__name__)

# Cargar la configuración desde la clase Config (lee el archivo .env)
app.secret_key = Config.SECRET_KEY
app.debug = Config.DEBUG


# ------------------------------------------------------------------
# Ciclo de vida del pool de conexiones
# ------------------------------------------------------------------
# IMPORTANTE: El pool se inicializa a nivel de módulo, FUERA de
# cualquier app_context. Usar 'with app.app_context()' aquí sería
# un error: al salir del bloque 'with', Flask dispara teardown_appcontext
# y cerraría el pool antes de atender cualquier petición real.
# ------------------------------------------------------------------

# Inicializar el pool al arrancar el proceso (no necesita app context)
init_pool()

# Registrar el cierre del pool al apagar el proceso con atexit,
# que se ejecuta una sola vez cuando el servidor Flask termina.
atexit.register(close_pool)

# Bandera para ejecutar init_db() una única vez antes de la primera petición
_db_inicializada = False


@app.before_request
def bootstrap_db():
    """
    Ejecuta init_db() una sola vez antes de la primera petición HTTP.
    Usa una bandera de módulo para no repetir la inicialización en
    cada petición subsiguiente.
    """
    global _db_inicializada
    if not _db_inicializada:
        init_db()
        _db_inicializada = True


# ------------------------------------------------------------------
# Rutas de autenticación
# ------------------------------------------------------------------

@app.route("/login", methods=["GET"])
def login_get():
    """
    GET /login
    Muestra la página de inicio de sesión.
    Si ya existe una sesión activa, redirige directamente al dashboard.
    """
    # Si el usuario ya inició sesión, no tiene sentido mostrar el login
    if "usuario_id" in session:
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_post():
    """
    POST /login
    Procesa el formulario de inicio de sesión.

    Recibe 'username' y 'password' del formulario HTML, consulta la
    tabla 'usuarios' con SQL puro y, si las credenciales coinciden,
    almacena el id, username y rol del usuario en la sesión de Flask.

    NOTA: La consulta usa parámetros posicionales (%s) para evitar
    inyección SQL básica, aunque las contraseñas estén en texto plano.
    """
    # Obtener los datos enviados por el formulario
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    # Validación básica: los campos no deben estar vacíos
    if not username or not password:
        flash("Por favor, ingresa tu usuario y contraseña.", "warning")
        return redirect(url_for("login_get"))

    # Consulta SQL para verificar las credenciales en la tabla 'usuarios'.
    # Se usan parámetros posicionales (%s) para prevenir inyección SQL.
    # Las columnas 'username', 'password' y 'rol' deben existir en la tabla.
    sql_autenticacion = """
        SELECT id, username, rol
        FROM usuarios
        WHERE username = %s
          AND password = %s
        LIMIT 1;
    """

    usuario_encontrado = None

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Ejecutar la consulta pasando los valores como parámetros
                cur.execute(sql_autenticacion, (username, password))
                # fetchone() retorna una tupla o None si no hay coincidencia
                usuario_encontrado = cur.fetchone()

    except Exception as error:
        # Registrar el error en consola y mostrar un mensaje genérico al usuario
        print(f"[app] Error al consultar la base de datos en /login: {error}")
        flash("Ocurrió un error interno. Intenta nuevamente.", "danger")
        return redirect(url_for("login_get"))

    if usuario_encontrado is None:
        # Las credenciales no coinciden con ningún registro
        flash("Usuario o contraseña incorrectos.", "danger")
        return redirect(url_for("login_get"))

    # Desempaquetar los datos del usuario retornados por la consulta
    usuario_id, usuario_nombre, usuario_rol = usuario_encontrado

    # Limpiar cualquier sesión previa antes de crear una nueva
    session.clear()

    # Guardar los datos del usuario autenticado en la sesión de Flask.
    # Flask firma la sesión con SECRET_KEY, por lo que no puede ser
    # manipulada desde el cliente sin invalidarla.
    session["usuario_id"]     = usuario_id
    session["usuario_nombre"] = usuario_nombre
    session["usuario_rol"]    = usuario_rol

    # Redirigir al dashboard tras el inicio de sesión exitoso
    return redirect(url_for("dashboard"))


# ------------------------------------------------------------------
# Ruta de búsqueda de pacientes (vista)
# ------------------------------------------------------------------

@app.route("/search")
def search_page():
    """
    GET /search
    Muestra la página de búsqueda de pacientes.
    Requiere sesión activa.
    """
    if "usuario_id" not in session:
        flash("Debes iniciar sesión para acceder a la búsqueda.", "warning")
        return redirect(url_for("login_get"))

    return render_template("search.html")


# ------------------------------------------------------------------
# API de búsqueda de pacientes (INTENCIONALMENTE VULNERABLE)
#
# ADVERTENCIA EDUCATIVA: Este endpoint concatena el input del usuario
# directamente en la consulta SQL para demostrar SQL Injection (A05).
# NUNCA hacer esto en producción — usar consultas parametrizadas.
# ------------------------------------------------------------------

@app.route("/patients/search")
def patients_search():
    """
    GET /patients/search?q=<término>
    Busca pacientes cuyo nombre coincida parcialmente con el término.
    Devuelve JSON.

    VULNERABLE a SQL Injection: el parámetro 'q' se concatena
    directamente en la consulta SQL (sin parámetros ni sanitización).

    Consulta original:
        SELECT id, full_name, document_id, email, phone, birth_date
        FROM patients
        WHERE full_name LIKE '%<q>%';
    """
    if "usuario_id" not in session:
        return {"error": "No autorizado"}, 401

    q = request.args.get("q", "").strip()

    if not q:
        return {"error": "Parámetro 'q' requerido"}, 400

    # VULNERABILIDAD INTENCIONAL: concatenación directa del input
    # Permite inyección SQL: ', OR, UNION, ORDER BY, etc.
    sql = (
        "SELECT id, full_name, document_id, email, phone, birth_date "
        f"FROM patients WHERE full_name LIKE '%{q}%'"
    )

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                filas = cur.fetchall()
    except Exception as error:
        print(f"[app] Error en /patients/search: {error}")
        return {"error": "Error interno del servidor"}, 500

    if not filas:
        return []

    columnas = ["id", "full_name", "document_id", "email", "phone", "birth_date"]
    resultados = [dict(zip(columnas, fila)) for fila in filas]

    return resultados


# ------------------------------------------------------------------
# Ruta de cierre de sesión
# ------------------------------------------------------------------

@app.route("/logout")
def logout():
    """
    GET /logout
    Elimina todos los datos de la sesión actual y redirige al login.
    """
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("login_get"))


# ------------------------------------------------------------------
# Rutas protegidas (requieren sesión activa)
# ------------------------------------------------------------------

@app.route("/dashboard")
def dashboard():
    """
    GET /dashboard
    Vista principal protegida de la aplicación.

    Verifica que exista una sesión activa. Si no hay sesión, redirige
    al login. Si existe, renderiza el template del dashboard pasando
    el nombre y rol del usuario para personalizar la vista.
    """
    # Verificar si existe una sesión activa comprobando la clave de usuario
    if "usuario_id" not in session:
        flash("Debes iniciar sesión para acceder al dashboard.", "warning")
        return redirect(url_for("login_get"))

    # Recuperar los datos del usuario desde la sesión
    nombre_usuario = session.get("usuario_nombre")
    rol_usuario    = session.get("usuario_rol")

    # Renderizar el template pasando los datos de sesión al contexto
    # Los roles posibles son: 'medico', 'administrador', 'paciente'
    return render_template(
        "dashboard.html",
        username=nombre_usuario,
        rol=rol_usuario,
    )


# ------------------------------------------------------------------
# Punto de entrada cuando se ejecuta directamente
# ------------------------------------------------------------------

if __name__ == "__main__":
    # Ejecutar el servidor de desarrollo integrado de Flask.
    # En producción se debe usar un servidor WSGI como Gunicorn o uWSGI.
    app.run(
        host="0.0.0.0",   # Escuchar en todas las interfaces de red
        port=5000,         # Puerto por defecto de Flask
        debug=Config.DEBUG,
    )
