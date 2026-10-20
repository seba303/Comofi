"""Interfaz web de Comofi (Flask).

Rutas principales:
  GET  /                          -> panel de importación e historial
  POST /conciliar                 -> ejecuta una conciliación con los archivos subidos
  GET  /revision/<id>             -> detalle de una revisión del historial
  GET  /revision/<id>/descargar   -> descarga del CSV emparejado de una revisión
  GET  /salud                     -> comprobación para despliegues

Programa creado por Sebastián Romero
"""

from datetime import datetime, date

import pandas as pd
from flask import (
    Flask,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

from comofi import config
from comofi.csv_loader import CsvValidationError, Movements, load_movements
from comofi.exporter import export_results
from comofi.history import list_revisions, save_revision
from comofi.reconciler import ReconciliationResult, reconcile

app = Flask(__name__, template_folder=str(config.BASE_DIR / "templates"))
# Clave local sin secretos reales: la app no maneja datos bancarios privados,
# solo ficheros de ejemplo que sube el propio usuario en su máquina.
app.secret_key = "comofi-local-session"

MAX_UPLOAD_BYTES = 16 * 1024 * 1024  # 16 MB por archivo
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

ALLOWED_SUFFIX = ".csv"

# Estado en memoria de la última conciliación (suficiente para una sesión local)
_last_result: ReconciliationResult | None = None
_last_files: tuple[str, str] = ("", "")


def _read_upload(storage, kind: str) -> Movements:
    """Guarda un upload temporal y lo carga con el validador de CSV."""
    filename = secure_filename(storage.filename)
    if not filename.endswith(ALLOWED_SUFFIX):
        raise CsvValidationError(f"{filename}: solo se aceptan archivos {ALLOWED_SUFFIX}")
    tmp_path = config.DATA_DIR / f"tmp_{kind}_{filename}"
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    storage.save(tmp_path)
    try:
        return load_movements(tmp_path, kind)
    finally:
        tmp_path.unlink(missing_ok=True)


@app.template_filter("eur")
def format_eur(value) -> str:
    try:
        return f"{float(value):,.2f} EUR".replace(",", " ")
    except (TypeError, ValueError):
        return "-"


@app.template_filter("dia")
def format_date(value) -> str:
    if isinstance(value, (date, datetime)):
        return value.strftime("%d/%m/%Y")
    return str(value)


@app.route("/")
def index():
    return render_template(
        "index.html",
        result=_last_result,
        files=_last_files,
        revisions=list_revisions(),
        samples=[str(config.SAMPLES_DIR / name) for name in
                 (config.BANK_SAMPLE_NAME, config.INTERNAL_SAMPLE_NAME)],
    )


@app.route("/conciliar", methods=["POST"])
def conciliate():
    global _last_result, _last_files
    bank_file = request.files.get("banco")
    internal_file = request.files.get("interno")
    if not bank_file or not internal_file:
        flash("Selecciona los dos archivos CSV antes de conciliar.", "error")
        return redirect(url_for("index"))
    try:
        bank = _read_upload(bank_file, "bank")
        internal = _read_upload(internal_file, "internal")
    except CsvValidationError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))

    _last_result = reconcile(bank, internal)
    _last_files = (bank.source_name, internal.source_name)
    revision_id = save_revision(_last_result, bank.source_name, internal.source_name)
    paths = export_results(_last_result)
    flash(
        f"Conciliación terminada. Revisión #{revision_id} guardada. "
        f"Resultado exportado a {paths[0].name}",
        "ok",
    )
    return redirect(url_for("revision_view", revision_id=revision_id))


@app.route("/revision/<int:revision_id>")
def revision_view(revision_id: int):
    for rev in list_revisions(limit=config.MAX_REVISIONS_KEPT):
        if rev["id"] == revision_id:
            return render_template("revision.html", revision=rev)
    abort(404)


@app.route("/revision/<int:revision_id>/descargar")
def download_revision(revision_id: int):
    """Regenera el CSV consolidado de una revisión desde su detalle guardado."""
    target = None
    for rev in list_revisions(limit=config.MAX_REVISIONS_KEPT):
        if rev["id"] == revision_id:
            target = rev
            break
    if target is None:
        abort(404)

    rows = []
    for pair in target["detail"]["matched"]:
        rows.append({"categoria": "emparejados", **pair})
    output_dir = config.DATA_DIR / config.RESULTS_DIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"revision_{revision_id}.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    return Response(
        csv_path.read_text(encoding="utf-8"),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=revision_{revision_id}.csv"},
    )


@app.route("/salud")
def health() -> str:
    return "ok"


def create_app() -> Flask:
    return app


if __name__ == "__main__":
    app.run(debug=True)
