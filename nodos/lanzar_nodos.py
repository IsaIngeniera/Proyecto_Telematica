"""Levanta 5+ nodos de telemetría simultáneamente."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time

processes: list[subprocess.Popen] = []

# En Windows, un proceso hijo solo puede recibir CTRL_BREAK_EVENT de forma
# selectiva si se creó en su propio grupo de procesos. En Linux/macOS esto
# no aplica (ahí basta con terminate(), que envía SIGTERM).
_CREATIONFLAGS = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0


def _request_graceful_stop(process: subprocess.Popen) -> None:
    """Pide a un nodo que se apague ordenadamente antes de matarlo a la fuerza."""

    if os.name == "nt":
        try:
            process.send_signal(signal.CTRL_BREAK_EVENT)
            return
        except (OSError, ValueError):
            pass  # Si falla, seguimos con terminate() más abajo.

    process.terminate()  # SIGTERM en Linux/macOS; respaldo en Windows.


def stop_all(*_args: object) -> None:
    for process in processes:
        if process.poll() is None:
            _request_graceful_stop(process)

    # Ventana de gracia para que cada nodo imprima su resumen y cierre el socket.
    deadline = time.time() + 3
    while time.time() < deadline:
        if all(p.poll() is not None for p in processes):
            return
        time.sleep(0.1)

    # A quien no haya alcanzado a cerrar solo, se le mata a la fuerza.
    for process in processes:
        if process.poll() is None:
            process.kill()


def main() -> None:
    parser = argparse.ArgumentParser(description="Lanza múltiples nodos.")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--host", default=os.getenv("SERVER_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("SERVER_UDP_PORT", "5000")))
    parser.add_argument("--interval", type=float, default=float(os.getenv("TELEMETRY_INTERVAL", "5")))
    args = parser.parse_args()

    if args.count < 5:
        parser.error("El proyecto exige ejecutar 5 nodos o más.")

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nodo.py")

    for number in range(1, args.count + 1):
        node_id = f"NODE{number:02d}"
        command = [
            sys.executable,
            script,
            "--node-id", node_id,
            "--host", args.host,
            "--port", str(args.port),
            "--interval", str(args.interval),
        ]
        if number == 1:
            # Facilita la prueba de alerta: NODE01 genera TEMP alta desde el ciclo 3.
            command += ["--anomaly-after", "3", "--anomaly-variable", "TEMP"]

        process = subprocess.Popen(command, creationflags=_CREATIONFLAGS)
        processes.append(process)
        print(f"Iniciado {node_id} (PID={process.pid})")

    print(f"\n{len(processes)} nodos activos. Ctrl+C para detenerlos.")
    try:
        while True:
            time.sleep(1)
            if all(p.poll() is not None for p in processes):
                break
    except KeyboardInterrupt:
        pass
    finally:
        stop_all()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, stop_all)
    main()
