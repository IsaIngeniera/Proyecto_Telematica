"""Servicio web HTTP de solo lectura para la plataforma de telemetria.

Este archivo reutiliza ClienteOperador para consultar el servidor central por
TCP y presenta la informacion mediante HTTP en http://localhost:8080.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from flask import Flask, render_template_string

from logica_cliente import (
    ClienteError,
    ClienteOperador,
    DEFAULT_HOST,
    DEFAULT_PORT,
    ProtocolError,
)


HTTP_HOST = "0.0.0.0"
HTTP_PORT = int(os.getenv("TELEMETRY_HTTP_PORT", "8080"))
SERVER_HOST = os.getenv("TELEMETRY_SERVER_HOST", DEFAULT_HOST)
SERVER_PORT = int(os.getenv("TELEMETRY_SERVER_PORT", str(DEFAULT_PORT)))
RECENT_ALERTS_LIMIT = 20

ALERT_LABELS = {
    "TEMP_HIGH": "Temperatura alta",
    "HUM_HIGH": "Humedad alta",
    "ENERGY_HIGH": "Energía alta",
    "VIBRATION_HIGH": "Vibración alta",
}

app = Flask(__name__)


PAGE_TEMPLATE = """
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="10">
    <title>Plataforma de Telemetría</title>
    <style>
        :root {
            --bg: #edf7ff;
            --panel: rgba(255, 255, 255, 0.76);
            --line: rgba(255, 255, 255, 0.92);
            --text: #1f2c3f;
            --muted: #718096;
            --blue: #5b9ee6;
            --green: #17a673;
            --red: #f16f73;
            --orange: #eeae55;
            --purple: #9d7be7;
            --shadow: 0 18px 45px rgba(67, 105, 137, 0.16);
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            min-height: 100vh;
            color: var(--text);
            font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background:
                radial-gradient(circle at 10% 5%, #ffffff 0, transparent 30%),
                radial-gradient(circle at 90% 10%, #d8eaff 0, transparent 30%),
                linear-gradient(135deg, var(--bg), #dcecff);
        }
        .container { max-width: 1500px; margin: auto; padding: 32px; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 24px;
            margin-bottom: 26px;
        }
        h1 { margin: 0; font-size: clamp(28px, 4vw, 46px); }
        h2 { margin: 0 0 20px; font-size: 22px; }
        .subtitle, .muted { color: var(--muted); }
        .connection {
            padding: 12px 18px;
            border-radius: 999px;
            font-weight: 750;
            background: rgba(255, 255, 255, 0.7);
            box-shadow: var(--shadow);
        }
        .online { color: var(--green); }
        .offline { color: var(--red); }
        .stats {
            display: grid;
            grid-template-columns: repeat(5, minmax(150px, 1fr));
            gap: 18px;
            margin-bottom: 24px;
        }
        .stat, .panel {
            border: 1px solid var(--line);
            background: var(--panel);
            box-shadow: var(--shadow);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
        }
        .stat {
            min-height: 120px;
            padding: 22px;
            border-radius: 24px;
            border-left: 7px solid var(--color);
        }
        .stat strong { display: block; font-size: 34px; margin-bottom: 7px; }
        .panel { border-radius: 26px; padding: 26px; margin-bottom: 24px; }
        .grid-two {
            display: grid;
            grid-template-columns: minmax(320px, 0.9fr) minmax(600px, 2.1fr);
            gap: 24px;
        }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 13px 12px; text-align: center; }
        th {
            color: #5f7088;
            background: rgba(255, 255, 255, 0.55);
            font-size: 14px;
        }
        tbody tr + tr { border-top: 1px solid rgba(187, 209, 227, 0.45); }
        .active { color: var(--green); font-weight: 750; }
        .inactive { color: var(--muted); font-weight: 750; }
        .alert { color: var(--red); }
        .error {
            margin-bottom: 24px;
            padding: 16px 20px;
            color: #a53e43;
            background: rgba(255, 225, 226, 0.8);
            border: 1px solid rgba(241, 111, 115, 0.4);
            border-radius: 16px;
        }
        .empty { padding: 28px; text-align: center; color: var(--muted); }
        footer { color: var(--muted); text-align: center; padding: 4px 0 20px; }
        @media (max-width: 1100px) {
            .stats { grid-template-columns: repeat(2, 1fr); }
            .grid-two { grid-template-columns: 1fr; }
        }
        @media (max-width: 620px) {
            .container { padding: 20px; }
            header { flex-direction: column; }
            .stats { grid-template-columns: 1fr; }
            .panel { overflow-x: auto; }
        }
    </style>
</head>
<body>
<main class="container">
    <header>
        <div>
            <h1>Plataforma de Telemetría</h1>
            <p class="subtitle">Servicio web HTTP de solo lectura</p>
        </div>
        <div class="connection {{ 'online' if connected else 'offline' }}">
            {{ '● Servidor disponible' if connected else '● Servidor no disponible' }}
        </div>
    </header>

    {% if error_message %}
        <div class="error">
            No fue posible consultar el servidor central: {{ error_message }}
        </div>
    {% endif %}

    <section class="stats">
        <article class="stat" style="--color: var(--blue)">
            <strong>{{ status.registered_nodes if status else '—' }}</strong>
            <span>Total registrados</span>
        </article>
        <article class="stat" style="--color: var(--green)">
            <strong>{{ status.active_nodes if status else '—' }}</strong>
            <span>Nodos activos</span>
        </article>
        <article class="stat" style="--color: var(--red)">
            <strong>{{ status.alert_count if status else '—' }}</strong>
            <span>Alertas globales</span>
        </article>
        <article class="stat" style="--color: var(--purple)">
            <strong>{{ status.udp_received if status else '—' }}</strong>
            <span>Paquetes recibidos</span>
        </article>
        <article class="stat" style="--color: var(--orange)">
            <strong>{{ status.udp_lost if status else '—' }}</strong>
            <span>Paquetes perdidos</span>
        </article>
    </section>

    <div class="grid-two">
        <section class="panel">
            <h2>Nodos registrados</h2>
            {% if nodes %}
                <table>
                    <thead><tr><th>Nodo</th><th>Estado</th></tr></thead>
                    <tbody>
                    {% for node in nodes %}
                        <tr>
                            <td>{{ node.node_id }}</td>
                            <td class="{{ 'active' if node.is_active else 'inactive' }}">
                                {{ 'ACTIVO' if node.is_active else 'INACTIVO' }}
                            </td>
                        </tr>
                    {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <div class="empty">No hay nodos disponibles.</div>
            {% endif %}
        </section>

        <section class="panel">
            <h2>Últimas mediciones</h2>
            {% if measurements %}
                <table>
                    <thead>
                        <tr>
                            <th>Nodo</th><th>Temperatura</th><th>Humedad</th>
                            <th>Energía</th><th>Vibración</th><th>Última transmisión</th>
                        </tr>
                    </thead>
                    <tbody>
                    {% for node in measurements %}
                        <tr>
                            <td>{{ node.node_id }}</td>
                            <td>{{ '%.1f °C'|format(node.temperature) if node.temperature is not none else '—' }}</td>
                            <td>{{ '%.1f %%'|format(node.humidity) if node.humidity is not none else '—' }}</td>
                            <td>{{ '%.1f W'|format(node.energy) if node.energy is not none else '—' }}</td>
                            <td>{{ '%.1f mm/s'|format(node.vibration) if node.vibration is not none else '—' }}</td>
                            <td>{{ node.last_seen }}</td>
                        </tr>
                    {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <div class="empty">No se recibieron mediciones.</div>
            {% endif %}
        </section>
    </div>

    <section class="panel">
        <h2>Alertas recientes</h2>
        {% if alerts %}
            <table>
                <thead>
                    <tr><th>Nodo</th><th>Tipo de evento</th><th>Valor</th><th>Fecha</th></tr>
                </thead>
                <tbody>
                {% for alert in alerts %}
                    <tr class="alert">
                        <td>{{ alert.node_id }}</td>
                        <td>{{ alert.label }}</td>
                        <td>{{ '%.1f'|format(alert.value) }}</td>
                        <td>{{ alert.timestamp }}</td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        {% else %}
            <div class="empty">No hay alertas recientes.</div>
        {% endif %}
    </section>

    <footer>
        Consulta generada: {{ generated_at }} · Actualización automática cada 10 segundos
    </footer>
</main>
</body>
</html>
"""


def create_client() -> ClienteOperador:
    """Crea un cliente independiente para cada consulta HTTP."""

    client = ClienteOperador(SERVER_HOST, SERVER_PORT)
    client.configurar(SERVER_HOST, SERVER_PORT)
    return client


def collect_dashboard_data() -> dict[str, Any]:
    """Consulta el servidor TCP y prepara los datos de la página."""

    client = create_client()
    status = client.obtener_estado_sistema()
    nodes = client.obtener_nodos()
    alerts = client.obtener_alertas()

    measurements = []
    for node in nodes:
        try:
            measurements.append(client.obtener_nodo(node.node_id))
        except (ClienteError, ProtocolError):
            # La página sigue disponible aunque falle el detalle de un nodo.
            continue

    alerts = sorted(alerts, key=lambda item: item.timestamp, reverse=True)
    recent_alerts = []
    for alert in alerts[:RECENT_ALERTS_LIMIT]:
        recent_alerts.append(
            {
                "node_id": alert.node_id,
                "label": ALERT_LABELS.get(alert.alert_type, alert.alert_type),
                "value": alert.value,
                "timestamp": alert.timestamp.replace("T", " "),
            }
        )

    return {
        "connected": True,
        "status": status,
        "nodes": nodes,
        "measurements": measurements,
        "alerts": recent_alerts,
        "error_message": "",
    }


@app.get("/")
def dashboard() -> str:
    """Presenta el panel web de solo lectura."""

    try:
        data = collect_dashboard_data()
    except (ClienteError, ProtocolError, OSError, ValueError) as exc:
        data = {
            "connected": False,
            "status": None,
            "nodes": [],
            "measurements": [],
            "alerts": [],
            "error_message": str(exc),
        }

    data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template_string(PAGE_TEMPLATE, **data)


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    """Permite comprobar si el proceso HTTP está ejecutándose."""

    return {"status": "ok"}, 200


def run() -> None:
    """Inicia el servidor HTTP local."""

    print(f"Servicio web disponible en http://localhost:{HTTP_PORT}")
    print(f"Servidor central configurado en {SERVER_HOST}:{SERVER_PORT}")
    app.run(host=HTTP_HOST, port=HTTP_PORT, debug=False, threaded=True)


if __name__ == "__main__":
    run()
