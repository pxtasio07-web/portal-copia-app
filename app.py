import os
import secrets
import cloudinary
import cloudinary.uploader
from flask import (Flask, render_template, request,
                   redirect, url_for, session, jsonify)
from database import init_db, get_conn

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "allen-portal-secret-2024")

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)

USUARIO = os.environ.get("PORTAL_USER", "allen")
PASSWORD = os.environ.get("PORTAL_PASS", "Jhamal_0729")

init_db()


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
    sesion = conn.execute("SELECT * FROM sesiones WHERE id=?", (sid,)).fetchone()
    fotos  = conn.execute("SELECT * FROM fotos WHERE sesion_id=?", (sid,)).fetchall()
    conn.close()
    cloud_name    = os.environ.get("CLOUDINARY_CLOUD_NAME")
    upload_preset = os.environ.get("CLOUDINARY_UPLOAD_PRESET", "allenportal")
    return render_template("sesion.html", sesion=sesion, fotos=fotos,
                           cloud_name=cloud_name, upload_preset=upload_preset)


# ── EDITAR SESIÓN (mensaje + portada) ───────────

@app.route("/editar/<int:sid>", methods=["POST"])
@login_required
def editar_sesion(sid):
    mensaje     = request.form.get("mensaje", "").strip()
    portada_url = request.form.get("portada_url", "").strip()
    conn = get_conn()
    conn.execute(
        "UPDATE sesiones SET mensaje=?, portada_url=? WHERE id=?",
        (mensaje or None, portada_url or None, sid)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("ver_sesion", sid=sid))


# ── GUARDAR FOTO (Cloudinary URL → DB) ──────────

@app.route("/guardar-foto/<int:sid>", methods=["POST"])
@login_required
def guardar_foto(sid):
    data      = request.get_json()
    url       = data.get("url")
    public_id = data.get("public_id")
    if not url:
        return jsonify({"error": "URL requerida"}), 400
    conn = get_conn()
    conn.execute(
        "INSERT INTO fotos (sesion_id, filename, cloudinary_url, public_id) VALUES (?,?,?,?)",
        (sid, public_id or url.split("/")[-1], url, public_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ── GALERÍA CLIENTE ─────────────────────────────

@app.route("/g/<token>")
def galeria(token):
    conn = get_conn()
    sesion = conn.execute("SELECT * FROM sesiones WHERE token=?", (token,)).fetchone()
    if not sesion:
        return "Galería no encontrada", 404
    fotos = conn.execute(
        "SELECT * FROM fotos WHERE sesion_id=?", (sesion["id"],)
    ).fetchall()
    conn.close()
    return render_template("galeria.html", sesion=sesion, fotos=fotos)


# ── DEBUG ────────────────────────────────────────

@app.route("/debug-env")
def debug_env():
    return {
        "cloud_name": os.environ.get("CLOUDINARY_CLOUD_NAME"),
        "preset":     os.environ.get("CLOUDINARY_UPLOAD_PRESET"),
    }


# ── BORRAR ──────────────────────────────────────

@app.route("/borrar/<int:sid>", methods=["POST"])
@login_required
def borrar_sesion(sid):
    conn = get_conn()
    fotos = conn.execute("SELECT public_id FROM fotos WHERE sesion_id=?", (sid,)).fetchall()
    for f in fotos:
        if f[0]:
            try: cloudinary.uploader.destroy(f[0])
            except: pass
    conn.execute("DELETE FROM fotos WHERE sesion_id=?", (sid,))
    conn.execute("DELETE FROM sesiones WHERE id=?", (sid,))
    conn.commit()
    conn.close()
    return redirect(url_for("panel"))


@app.route("/borrar-foto/<int:fid>/<int:sid>", methods=["POST"])
@login_required
def borrar_foto(fid, sid):
    conn = get_conn()
    foto = conn.execute("SELECT public_id FROM fotos WHERE id=?", (fid,)).fetchone()
    if foto and foto[0]:
        try: cloudinary.uploader.destroy(foto[0])
        except: pass
    conn.execute("DELETE FROM fotos WHERE id=?", (fid,))
    conn.commit()
    conn.close()
    return redirect(url_for("ver_sesion", sid=sid))


if __name__ == "__main__":
    app.run(debug=True)