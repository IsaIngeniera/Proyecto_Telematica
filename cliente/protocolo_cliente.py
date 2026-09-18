"""Protocolo compartido de la Plataforma de Telemetria - lado cliente.

Este modulo NO conoce sockets ni interfaces graficas. Solo sabe construir
los mensajes de peticion (GET_STATUS, GET_NODES, GET_NODE, GET_ALERTS) y
parsear las respuestas de texto que envia el servidor (servidor/*.c),
que siguen exactamente el mismo formato que nodos/protocolo.py.

Formato de mensaje:  CAMPO1|CAMPO2|...|CAMPON\n
Listas de registros:  registro1;registro2;...
Listas dentro de un registro:  valor1,valor2,...
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- Framing ---------------------------------------------------------------
FIELD_SEPARATOR = "|"
LIST_SEPARATOR = ","
RECORD_SEPARATOR = ";"
MESSAGE_END = "\n"

# --- Tipos de peticion -------------------------------------------------------
GET_STATUS = "GET_STATUS"
GET_NODES = "GET_NODES"
GET_NODE = "GET_NODE"
GET_ALERTS = "GET_ALERTS"

# --- Tipos de respuesta -------------------------------------------------------
STATUS = "STATUS"
NODES = "NODES"
NODE_DATA = "NODE_DATA"
ALERTS = "ALERTS"
ERROR = "ERROR"

OK = "OK"
NO_DATA = "NO_DATA"

ACTIVE = "ACTIVE"
INACTIVE = "INACTIVE"

NODE_ID_PATTERN = re.compile(r"^NODE[0-9]{2}$")


def is_valid_node_id(node_id: str) -> bool:
    return bool(NODE_ID_PATTERN.fullmatch(node_id.strip().upper()))


def _build_message(*fields: object) -> str:
    return FIELD_SEPARATOR.join(str(f) for f in fields) + MESSAGE_END


def build_get_status() -> str:
    return _build_message(GET_STATUS)


def build_get_nodes() -> str:
    return _build_message(GET_NODES)


def build_get_node(node_id: str) -> str:
    return _build_message(GET_NODE, node_id)


def build_get_alerts() -> str:
    return _build_message(GET_ALERTS)


# --- Estructuras de datos de respuesta ---------------------------------------

@dataclass
class NodeSummary:
    node_id: str
    state: str

    @property
    def is_active(self) -> bool:
        return self.state == ACTIVE


@dataclass
class NodeData:
    node_id: str
    state: str
    temperature: float | None
    humidity: float | None
    energy: float | None
    vibration: float | None
    last_seen: str

    @property
    def is_active(self) -> bool:
        return self.state == ACTIVE


@dataclass
class Alert:
    node_id: str
    alert_type: str
    value: float
    timestamp: str


@dataclass
class SystemStatus:
    registered_nodes: int = 0
    active_nodes: int = 0
    alert_count: int = 0
    udp_received: int = 0
    udp_lost: int = 0


class ProtocolError(Exception):
    """Se lanza cuando el servidor responde con un ERROR o un mensaje mal formado."""

    def __init__(self, code: str, description: str) -> None:
        super().__init__(f"[{code}] {description}")
        self.code = code
        self.description = description


def _parse_fields(line: str) -> list[str]:
    clean = line.rstrip("\r\n")
    if not clean:
        return []
    return clean.split(FIELD_SEPARATOR)


def _value_or_none(raw: str) -> float | None:
    if raw == NO_DATA:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _extract_kv(field_text: str) -> tuple[str, str]:
    key, _, value = field_text.partition("=")
    return key, value


def parse_response(line: str) -> object:
    """Parsea una linea de respuesta del servidor y devuelve el objeto tipado
    correspondiente (SystemStatus, list[NodeSummary], NodeData, list[Alert]).

    Lanza ProtocolError si la respuesta es un ERROR o no se pudo interpretar.
    """
    fields = _parse_fields(line)
    if not fields:
        raise ProtocolError("000", "RESPUESTA_VACIA")

    kind = fields[0]

    if kind == ERROR:
        code = fields[1] if len(fields) > 1 else "000"
        desc = fields[2] if len(fields) > 2 else "ERROR_DESCONOCIDO"
        raise ProtocolError(code, desc)

    if kind == STATUS:
        status = SystemStatus()
        for part in fields[2:]:
            key, value = _extract_kv(part)
            if key == "REGISTERED":
                status.registered_nodes = int(value)
            elif key == "ACTIVE":
                status.active_nodes = int(value)
            elif key == "ALERTS":
                status.alert_count = int(value)
            elif key == "UDP_RECEIVED":
                status.udp_received = int(value)
            elif key == "UDP_LOST":
                status.udp_lost = int(value)
        return status

    if kind == NODES:
        count = int(fields[2]) if len(fields) > 2 else 0
        records_text = fields[3] if len(fields) > 3 else NO_DATA
        nodes: list[NodeSummary] = []
        if count > 0 and records_text != NO_DATA:
            for record in records_text.split(RECORD_SEPARATOR):
                if not record:
                    continue
                node_id, state = record.split(LIST_SEPARATOR)
                nodes.append(NodeSummary(node_id=node_id, state=state))
        return nodes

    if kind == NODE_DATA:
        node_id = fields[2]
        state = fields[3]
        kv = dict(_extract_kv(f) for f in fields[4:9])
        return NodeData(
            node_id=node_id,
            state=state,
            temperature=_value_or_none(kv.get("TEMP", NO_DATA)),
            humidity=_value_or_none(kv.get("HUM", NO_DATA)),
            energy=_value_or_none(kv.get("ENERGY", NO_DATA)),
            vibration=_value_or_none(kv.get("VIBRATION", NO_DATA)),
            last_seen=kv.get("LAST_SEEN", NO_DATA),
        )

    if kind == ALERTS:
        count = int(fields[2]) if len(fields) > 2 else 0
        records_text = fields[3] if len(fields) > 3 else NO_DATA
        alerts: list[Alert] = []
        if count > 0 and records_text != NO_DATA:
            for record in records_text.split(RECORD_SEPARATOR):
                if not record:
                    continue
                node_id, alert_type, value, timestamp = record.split(LIST_SEPARATOR)
                alerts.append(
                    Alert(
                        node_id=node_id,
                        alert_type=alert_type,
                        value=float(value),
                        timestamp=timestamp,
                    )
                )
        return alerts

    raise ProtocolError("000", f"TIPO_RESPUESTA_DESCONOCIDO:{kind}")