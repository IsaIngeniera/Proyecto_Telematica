"""Simulador de nodo IoT para la Plataforma Distribuida de Telemetría."""

from __future__ import annotations

import argparse
import logging
import os
import random
import signal
import socket
import time
from dataclasses import dataclass

from protocolo import (
    ENERGY,
    HUM,
    TEMP,
    VIBRATION,
    build_telemetry,
    encode_message,
    is_valid_node_id,
)

LOG = logging.getLogger("nodo")

# Colores ANSI para distinguir cada nodo en la terminal.
# Se asignan por el número del nodo (NODE01 -> índice 0, NODE02 -> índice 1, ...)
# en vez de por hash(), para garantizar que no se repitan entre nodos consecutivos.
_COLORS = [
    "\033[36m",  # cian
    "\033[32m",  # verde
    "\033[33m",  # amarillo
    "\033[35m",  # magenta
    "\033[31m",  # rojo
    "\033[34m",  # azul
    "\033[96m",  # cian brillante
    "\033[92m",  # verde brillante
    "\033[93m",  # amarillo brillante
    "\033[95m",  # magenta brillante
]
_RESET = "\033[0m"


def _color_for(node_id: str) -> str:
    try:
        # Extrae el número de NODE##, ej. "NODE02" -> 2
        number = int(node_id[4:])
    except (ValueError, IndexError):
        # Respaldo por si el ID no sigue el formato esperado.
        number = sum(ord(c) for c in node_id)
    return _COLORS[(number - 1) % len(_COLORS)]


@dataclass
class NodeConfig:
    node_id: str
    server_host: str
    server_udp_port: int
    interval: float
    anomaly_after: int | None
    anomaly_variable: str


class TelemetryNode:
    """Nodo que envía las cuatro variables mediante UDP."""

    def __init__(self, config: NodeConfig) -> None:
        if not is_valid_node_id(config.node_id):
            raise ValueError("El ID debe tener formato NODE##.")

        self.config = config
        self.sequence = 1
        self.messages_sent = 0
        self.send_errors = 0
        self.cycles = 0
        self.sock: socket.socket | None = None
        self.destination: tuple[str, int] | None = None
        self._color = _color_for(config.node_id)

    def _c(self, text: str) -> str:
        """Envuelve el texto con el color asignado a este nodo."""
        return f"{self._color}{text}{_RESET}"

    def resolve_server(self) -> None:
        """Resuelve el nombre del servidor mediante DNS, sin IP pública fija."""

        infos = socket.getaddrinfo(
            self.config.server_host,
            self.config.server_udp_port,
            family=socket.AF_INET,
            type=socket.SOCK_DGRAM,
        )

        if not infos:
            raise OSError("DNS no devolvió direcciones para el servidor.")

        # Guardamos la dirección obtenida mediante DNS.
        sockaddr = infos[0][4]
        host = sockaddr[0]
        port = sockaddr[1]
        if not isinstance(host, str) or not isinstance(port, int):
            raise OSError("DNS devolvió una dirección IPv4 no válida.")

        self.destination = (host, port)

        LOG.info(
            self._c("[%s] DNS: %s -> %s"),
            self.config.node_id,
            self.config.server_host,
            sockaddr[0],
        )

    def open_socket(self) -> None:
        """Crea el socket UDP que utilizará el nodo."""

        self.close_socket()

        self.sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )

    def close_socket(self) -> None:
        """Cierra el socket si existe."""

        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def reconnect(self) -> None:
        """Recrea el socket y vuelve a resolver DNS tras un error."""

        self.close_socket()

        time.sleep(1.0)

        self.resolve_server()
        self.open_socket()

    def generate_measurements(self) -> dict[str, float]:
        """Genera valores simulados para las cuatro variables."""

        values = {
            TEMP: round(random.uniform(20.0, 35.0), 2),
            HUM: round(random.uniform(40.0, 75.0), 2),
            ENERGY: round(random.uniform(10.0, 40.0), 2),
            VIBRATION: round(random.uniform(1.0, 8.0), 2),
        }

        # Generación opcional de una anomalía.
        if (
            self.config.anomaly_after is not None
            and self.cycles + 1 >= self.config.anomaly_after
        ):
            if self.config.anomaly_variable == TEMP:
                values[TEMP] = 45.0

            elif self.config.anomaly_variable == HUM:
                values[HUM] = 90.0

            elif self.config.anomaly_variable == ENERGY:
                values[ENERGY] = 60.0

            elif self.config.anomaly_variable == VIBRATION:
                values[VIBRATION] = 12.0

        return values

    def send_measurement(self, variable: str, value: float) -> bool:
        """Construye y envía una medición mediante UDP."""

        if self.sock is None or self.destination is None:
            self.reconnect()

        assert self.sock is not None
        assert self.destination is not None

        message = build_telemetry(
            self.config.node_id,
            self.sequence,
            variable,
            value,
        )

        try:
            self.sock.sendto(
                encode_message(message),
                self.destination,
            )

            LOG.info(
                self._c("[%s] UDP enviado: seq=%d | %s=%.2f"),
                self.config.node_id,
                self.sequence,
                variable,
                value,
            )

            self.sequence += 1
            self.messages_sent += 1

            return True

        except (OSError, ValueError) as exc:
            self.send_errors += 1

            LOG.warning(
                self._c(
                    "[%s] Error de comunicación UDP: %s. "
                    "Reintentando socket..."
                ),
                self.config.node_id,
                exc,
            )

            try:
                self.reconnect()

            except OSError as reconnect_error:
                LOG.error(
                    self._c("[%s] No se pudo recuperar la comunicación: %s"),
                    self.config.node_id,
                    reconnect_error,
                )

            return False

    def run(self) -> None:
        """Ejecuta el ciclo continuo de medición y envío."""

        LOG.info(
            self._c("[%s] Iniciando -> DNS=%s UDP=%d intervalo=%.1fs"),
            self.config.node_id,
            self.config.server_host,
            self.config.server_udp_port,
            self.config.interval,
        )

        while True:
            try:
                # Resolver el servidor mediante DNS.
                if self.destination is None:
                    self.resolve_server()

                # Crear el socket UDP.
                if self.sock is None:
                    self.open_socket()

                # Generar las cuatro mediciones.
                values = self.generate_measurements()

                # Mostrar claramente el inicio del ciclo.
                print(
                    self._c(
                        f"\n[{self.config.node_id}] "
                        f"CICLO {self.cycles + 1} "
                        f"-------------------------------------------------------------"
                    )
                )

                # Enviar las cuatro variables.
                for variable, value in values.items():
                    self.send_measurement(variable, value)

                # Terminamos un ciclo.
                self.cycles += 1

                # Esperar antes del siguiente ciclo.
                time.sleep(self.config.interval)

            except KeyboardInterrupt:
                LOG.info(
                    self._c("[%s] Nodo detenido por el usuario."),
                    self.config.node_id,
                )
                break

            except OSError as exc:
                self.send_errors += 1

                LOG.warning(
                    self._c(
                        "[%s] Fallo de DNS/socket: %s. "
                        "Se intentará recuperar."
                    ),
                    self.config.node_id,
                    exc,
                )

                try:
                    self.reconnect()

                except OSError as reconnect_error:
                    LOG.error(
                        self._c("[%s] Reintento fallido: %s"),
                        self.config.node_id,
                        reconnect_error,
                    )

                    time.sleep(2.0)

            except Exception:
                LOG.exception(
                    self._c(
                        "[%s] Error inesperado en el nodo; "
                        "continúa ejecutándose."
                    ),
                    self.config.node_id,
                )

                time.sleep(2.0)

        self.close_socket()

        LOG.info(
            self._c("[%s] Resumen: enviados=%d errores_envio=%d"),
            self.config.node_id,
            self.messages_sent,
            self.send_errors,
        )


def parse_args() -> NodeConfig:
    parser = argparse.ArgumentParser(
        description="Simulador de nodo IoT UDP"
    )

    parser.add_argument(
        "--node-id",
        required=True,
        help="ID único, por ejemplo NODE01",
    )

    parser.add_argument(
        "--host",
        default=os.getenv("SERVER_HOST", "localhost"),
        help=(
            "Nombre DNS del servidor "
            "(por defecto SERVER_HOST o localhost)"
        ),
    )

    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("SERVER_UDP_PORT", "5000")),
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.getenv("TELEMETRY_INTERVAL", "5")),
        help="Segundos entre ciclos de cuatro mediciones",
    )

    parser.add_argument(
        "--anomaly-after",
        type=int,
        default=None,
        help="Ciclo a partir del cual se fuerza una anomalía",
    )

    parser.add_argument(
        "--anomaly-variable",
        choices=[TEMP, HUM, ENERGY, VIBRATION],
        default=TEMP,
    )

    args = parser.parse_args()

    return NodeConfig(
        node_id=args.node_id,
        server_host=args.host,
        server_udp_port=args.port,
        interval=max(0.1, args.interval),
        anomaly_after=args.anomaly_after,
        anomaly_variable=args.anomaly_variable,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    # En Windows, lanzar_nodos.py pide un apagado ordenado mediante
    # CTRL_BREAK_EVENT (señal SIGBREAK). Por defecto Python la ignora;
    # aquí la tratamos igual que un Ctrl+C normal para poder cerrar
    # el socket y mostrar el resumen antes de salir.
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, signal.default_int_handler)

    TelemetryNode(parse_args()).run()
