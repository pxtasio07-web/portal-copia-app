import os
import secrets
from flask import (Flask, render_template, request,  redirect, url_for, session, send_from_directory)
from database import init_db, get_conn
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "allen-portal-secret-2024"

UPLOAD_FOLDER = "static/uploads"
ALLOWED = {"jpg", "jpeg", "png", "webp"}
USUARIO = "allen"
PASSWORD = "Jhamal_0729"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── AUTH ────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if (request.form["usuario"] == USUARIO and
                request.form["password"] == PASSWORD):
            session["logged_in"] = True
            return redirect(url_for("panel"))
        error = "Credenciales incorrectas"
    return render_template("login.html", error=error)


@app.route("/salir")
def salir():
    session.clear()
    return redirect(url_for("login"))


# ── PANEL ───────────────────────────────────────

@app.route("/panel")
@login_required
def panel():
    conn = get_conn()
    sesiones = conn.execute("""
        SELECT s.id, s.cliente, s.tipo, s.fecha, s.token,
               COUNT(f.id) as total_fotos
        FROM sesiones s
        LEFT JOIN fotos f ON f.sesion_id = s.id
        GROUP BY s.id
        ORDER BY s.id DESC
    """).fetchall()
    conn.close()
    return render_template("panel.html", sesiones=sesiones)

# ── SESIÓN ──────────────────────────────────────

@app.route("/nueva", methods=["POST"])
@login_required
def nueva_sesion():
    cliente = request.form["cliente"]
    tipo    = request.form["tipo"]
    fecha   = request.form["fecha"]
    token   = secrets.token_urlsafe(6)
    conn = get_conn()
    conn.execute(
        "INSERT INTO sesiones (cliente, tipo, fecha, token) VALUES (?,?,?,?)",
        (cliente, tipo, fecha, token)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("panel"))

@app.route("/sesion/<int:sid>")
@login_required
def ver_sesion(sid):
    conn = get_conn()
    sesion = conn.execute(
        "SELECT * FROM sesiones WHERE id=?", (sid,)
    ).fetchone()
    fotos = conn.execute(
        "SELECT * FROM fotos WHERE sesion_id=?", (sid,)
    ).fetchall()
    conn.close()
    return render_template("sesion.html", sesion=sesion, fotos=fotos)


@app.route("/subir/<int:sid>", methods=["POST"])
@login_required
def subir_fotos(sid):
    archivos = request.files.getlist("fotos")
    conn = get_conn()
    for f in archivos:
        if f and allowed_file(f.filename):
            nombre = secure_filename(f.filename)
            f.save(os.path.join(UPLOAD_FOLDER, nombre))
            conn.execute(
                "INSERT INTO fotos (sesion_id, filename) VALUES (?,?)",
                (sid, nombre)
            )
    conn.commit()
    conn.close()
    return redirect(url_for("ver_sesion", sid=sid))


# ── GALERÍA CLIENTE ─────────────────────────────

@app.route("/g/<token>")
def galeria(token):
    conn = get_conn()
    sesion = conn.execute(
        "SELECT * FROM sesiones WHERE token=?", (token,)
    ).fetchone()
    if not sesion:
        return "Galería no encontrada", 404
    fotos = conn.execute(
        "SELECT * FROM fotos WHERE sesion_id=?", (sesion[0],)
    ).fetchall()
    conn.close()
    return render_template("galeria.html", sesion=sesion, fotos=fotos)

@app.route("/borrar/<int:sid>", methods=["POST"])
@login_required
def borrar_sesion(sid):
    conn = get_conn()
    fotos = conn.execute("SELECT filename FROM fotos WHERE sesion_id=?", (sid,)).fetchall()
    for f in fotos:
        path = os.path.join(UPLOAD_FOLDER, f[0])
        if os.path.exists(path):
            os.remove(path)
    conn.execute("DELETE FROM fotos WHERE sesion_id=?", (sid,))
    conn.execute("DELETE FROM sesiones WHERE id=?", (sid,))
    conn.commit()
    conn.close()
    return redirect(url_for("panel"))

@app.route("/borrar-foto/<int:fid>/<int:sid>", methods=["POST"])
@login_required
def borrar_foto(fid, sid):
    conn = get_conn()
    foto = conn.execute("SELECT filename FROM fotos WHERE id=?", (fid,)).fetchone()
    if foto:
        path = os.path.join(UPLOAD_FOLDER, foto[0])
        if os.path.exists(path):
            os.remove(path)
        conn.execute("DELETE FROM fotos WHERE id=?", (fid,))
        conn.commit()
    conn.close()
    return redirect(url_for("ver_sesion", sid=sid))

if __name__ == "__main__":
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    init_db()
    app.run(debug=True)