{% extends "base.html" %}
{% block content %}
<h2>Importar movimientos</h2>
<div class="card">
  <form action="{{ url_for('conciliate') }}" method="post" enctype="multipart/form-data">
    <div class="grid-2">
      <div>
        <label for="banco">Extracto bancario (CSV)</label>
        <input type="file" id="banco" name="banco" accept=".csv" required>
        <p class="muted">Columnas esperadas: fecha, referencia, concepto, importe</p>
      </div>
      <div>
        <label for="interno">Registro interno (CSV)</label>
        <input type="file" id="interno" name="interno" accept=".csv" required>
        <p class="muted">Columnas esperadas: fecha, id_operacion, detalle, importe</p>
      </div>
    </div>
    <p><button type="submit">Conciliar</button></p>
  </form>
  <p class="muted">
    ¿Sin ficheros a mano? Ejecuta <code>python main.py generar-ejemplos</code> y usa los CSV de
    <code>{{ samples[0] }}</code> y <code>{{ samples[1] }}</code>.
  </p>
</div>

{% if result %}
<h2>Resumen de la última revisión</h2>
<div class="stats">
  <div class="stat">
    <div class="label">Coincidentes</div>
    <div class="value">{{ result.summary().coincidentes }}</div>
  </div>
  <div class="stat">
    <div class="label">Discrepancias</div>
    <div class="value">{{ result.summary().discrepancias }}</div>
  </div>
  <div class="stat">
    <div class="label">Duplicados</div>
    <div class="value">{{ result.summary().duplicados }}</div>
  </div>
  <div class="stat">
    <div class="label">Pendientes</div>
    <div class="value">{{ result.summary().pendientes_banco + result.summary().pendientes_interno }}</div>
  </div>
</div>
{% endif %}

<h2>Historial de revisiones</h2>
<div class="card">
  {% if revisions %}
  <table>
    <thead>
      <tr>
        <th>#</th><th>Fecha y hora</th><th>Extracto</th><th>Interno</th>
        <th class="num">Coincidentes</th><th class="num">Discrepancias</th>
        <th class="num">Duplicados</th><th class="num">Pendientes</th><th></th>
      </tr>
    </thead>
    <tbody>
      {% for rev in revisions %}
      <tr>
        <td>{{ rev.id }}</td>
        <td>{{ rev.timestamp.replace('T', ' ') }}</td>
        <td>{{ rev.bank_file }}</td>
        <td>{{ rev.internal_file }}</td>
        <td class="num">{{ rev.summary.coincidentes }}</td>
        <td class="num">{{ rev.summary.discrepancias }}</td>
        <td class="num">{{ rev.summary.duplicados }}</td>
        <td class="num">{{ rev.summary.pendientes_banco + rev.summary.pendientes_interno }}</td>
        <td><a class="btn" href="{{ url_for('revision_view', revision_id=rev.id) }}">Ver</a></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <p class="muted">Aún no hay revisiones. Concilia dos CSV para empezar.</p>
  {% endif %}
</div>
{% endblock %}
