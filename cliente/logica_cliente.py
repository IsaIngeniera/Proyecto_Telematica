"""Logica del Cliente Operador - Plataforma Distribuida de Telemetria.

Esta capa se encarga UNICAMENTE de la comunicacion por socket TCP con el
servidor central y de traducir el protocolo de texto a estructuras de datos
de Python (dataclasses). No debe importar tkinter ni saber nada sobre como
se dibuja la informacion: eso vive en interfaz_cliente.py.
"""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass

import protocolo_cliente as proto
from protocolo_cliente import (
    Alert,
    NodeData,
    NodeSummary,
    ProtocolError,
    SystemStatus,
)

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 6000
SOCKET_TIMEOUT_SECONDS = 4.0
RECV_BUFFER_SIZE = 4096


class ClienteError(Exception):
    """Errores de conexion / comunicacion (no de protocolo)."""


@dataclass
class ConexionInfo:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    conectado: bool = False
    ultima_actualizacion: float | None = None


class ClienteOperador:
    """Cliente TCP que consulta al servidor central de telemetria.

    Abre una conexion nueva y corta por cada peticion (el protocolo es
    simple: se envia una linea y se recibe una linea de respuesta), lo
    que evita mantener estado de socket entre refrescos de la interfaz
    y hace que reconectar tras un error sea trivial.
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self.info = ConexionInfo(host=host, port=port)

    def configurar(self, host: str, port: int) -> None:
        self.info.host = host
        self.info.port = port

    # -- Mecanica interna de red ---------------------------------------

    def _enviar_y_recibir(self, mensaje: str) -> str:
        try:
            with socket.create_connection(
                (self.info.host, self.info.port), timeout=SOCKET_TIMEOUT_SECONDS
            ) as sock:
                sock.settimeout(SOCKET_TIMEOUT_SECONDS)
                sock.sendall(mensaje.encode("utf-8"))

                buffer = b""
                while b"\n" not in buffer:
                    chunk = sock.recv(RECV_BUFFER_SIZE)
                    if not chunk:
                        break
                    buffer += chunk

                if not buffer:
                    raise ClienteError("El servidor cerro la conexion sin responder.")

                self.info.conectado = True
                self.info.ultima_actualizacion = time.time()
                return buffer.decode("utf-8", errors="replace")

        except socket.timeout as exc:
            self.info.conectado = False
            raise ClienteError(
                f"Tiempo de espera agotado conectando a {self.info.host}:{self.info.port}"
            ) from exc
        except (ConnectionRefusedError, OSError) as exc:
            self.info.conectado = False
            raise ClienteError(
                f"No se pudo conectar a {self.info.host}:{self.info.port} ({exc})"
            ) from exc

    # -- Operaciones publicas --------------------------------------------

    def obtener_estado_sistema(self) -> SystemStatus:
        respuesta = self._enviar_y_recibir(proto.build_get_status())
        resultado = proto.parse_response(respuesta)
        assert isinstance(resultado, SystemStatus)
        return resultado

    def obtener_nodos(self) -> list[NodeSummary]:
        respuesta = self._enviar_y_recibir(proto.build_get_nodes())
        resultado = proto.parse_response(respuesta)
        assert isinstance(resultado, list)
        return resultado

    def obtener_nodo(self, node_id: str) -> NodeData:
        node_id = node_id.strip().upper()
        if not proto.is_valid_node_id(node_id):
            raise ClienteError(f"ID de nodo invalido: '{node_id}' (formato NODE##)")
        respuesta = self._enviar_y_recibir(proto.build_get_node(node_id))
        resultado = proto.parse_response(respuesta)
        assert isinstance(resultado, NodeData)
        return resultado

    def obtener_alertas(self) -> list[Alert]:
        respuesta = self._enviar_y_recibir(proto.build_get_alerts())
        resultado = proto.parse_response(respuesta)
        assert isinstance(resultado, list)
        return resultado


__all__ = [
    "ClienteOperador",
    "ClienteError",
    "ConexionInfo",
    "ProtocolError",
    "NodeSummary",
    "NodeData",
    "Alert",
    "SystemStatus",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
]