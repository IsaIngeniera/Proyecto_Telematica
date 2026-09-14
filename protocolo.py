"""Protocolo compartido de la Plataforma de Telemetría.

Este módulo debe ser compartido por los nodos Python y, conceptualmente,
mantenerse alineado con la implementación del servidor en C.
"""

import math
import re

# Message framing
FIELD_SEPARATOR = "|"
LIST_SEPARATOR = ","
RECORD_SEPARATOR = ";"
MESSAGE_END = "\n"
MAX_MESSAGE_BYTES = 1024

# Request message types
TELEMETRY = "TELEMETRY"
GET_STATUS = "GET_STATUS"
GET_NODES = "GET_NODES"
GET_NODE = "GET_NODE"
GET_ALERTS = "GET_ALERTS"

# Response message types
STATUS = "STATUS"
NODES = "NODES"
NODE_DATA = "NODE_DATA"
ALERTS = "ALERTS"
ERROR = "ERROR"

# General response values
OK = "OK"
NO_DATA = "NO_DATA"

# Telemetry variables
TEMP = "TEMP"
HUM = "HUM"
ENERGY = "ENERGY"
VIBRATION = "VIBRATION"

VALID_VARIABLES = {TEMP, HUM, ENERGY, VIBRATION}

# Node states
ACTIVE = "ACTIVE"
INACTIVE = "INACTIVE"
VALID_STATES = {ACTIVE, INACTIVE}

# Alert types
TEMP_HIGH = "TEMP_HIGH"
HUM_HIGH = "HUM_HIGH"
ENERGY_HIGH = "ENERGY_HIGH"
VIBRATION_HIGH = "VIBRATION_HIGH"
VALID_ALERT_TYPES = {
    TEMP_HIGH,
    HUM_HIGH,
    ENERGY_HIGH,
    VIBRATION_HIGH,
}

# Error codes
ERROR_BAD_REQUEST = "400"
ERROR_NOT_FOUND = "404"
ERROR_SERVER = "500"

# Error descriptions
INVALID_MESSAGE = "INVALID_MESSAGE"
INVALID_NODE_ID = "INVALID_NODE_ID"
INVALID_SEQUENCE = "INVALID_SEQUENCE"
INVALID_VARIABLE = "INVALID_VARIABLE"
INVALID_VALUE = "INVALID_VALUE"
MESSAGE_TOO_LONG = "MESSAGE_TOO_LONG"
NODE_NOT_FOUND = "NODE_NOT_FOUND"
INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"

NODE_ID_PATTERN = re.compile(r"^NODE[0-9]{2}$")


def build_message(*fields: object) -> str:
    content = FIELD_SEPARATOR.join(str(field) for field in fields)
    return f"{content}{MESSAGE_END}"

def encode_message(message: str) -> bytes:
    data = message.encode("utf-8")
    if len(data) > MAX_MESSAGE_BYTES:
        raise ValueError(MESSAGE_TOO_LONG)
    return data


# Request builders

def build_telemetry(node_id: str, sequence_number: int, variable: str, value: float) -> str:
    return build_message(TELEMETRY, node_id, sequence_number, variable, value)

def build_get_status() -> str:
    return build_message(GET_STATUS)

def build_get_nodes() -> str:
    return build_message(GET_NODES)

def build_get_node(node_id: str) -> str:
    return build_message(GET_NODE, node_id)

def build_get_alerts() -> str:
    return build_message(GET_ALERTS)

# Response builders

def build_status(
    registered_nodes: int,
    active_nodes: int,
    alert_count: int,
    udp_received: int,
    udp_lost: int,
) -> str:
    return build_message(
        STATUS,
        OK,
        f"REGISTERED={registered_nodes}",
        f"ACTIVE={active_nodes}",
        f"ALERTS={alert_count}",
        f"UDP_RECEIVED={udp_received}",
        f"UDP_LOST={udp_lost}",
    )

def build_nodes(node_states: dict[str, str]) -> str:
    """node_states: {"NODE01": "ACTIVE", ...}"""
    if not node_states:
        return build_message(NODES, OK, 0, NO_DATA)

    records = RECORD_SEPARATOR.join(
        f"{node_id}{LIST_SEPARATOR}{state}"
        for node_id, state in sorted(node_states.items())
    )
    return build_message(NODES, OK, len(node_states), records)

def build_node_data(
    node_id: str,
    state: str,
    temperature: object,
    humidity: object,
    energy: object,
    vibration: object,
    last_seen: str,
) -> str:
    def value_or_no_data(value: object) -> object:
        return NO_DATA if value is None else value

    return build_message(
        NODE_DATA,
        OK,
        node_id,
        state,
        f"TEMP={value_or_no_data(temperature)}",
        f"HUM={value_or_no_data(humidity)}",
        f"ENERGY={value_or_no_data(energy)}",
        f"VIBRATION={value_or_no_data(vibration)}",
        f"LAST_SEEN={last_seen}",
    )

def build_alerts(alert_records: list[tuple[str, str, float, str]]) -> str:
    if not alert_records:
        return build_message(ALERTS, OK, 0, NO_DATA)

    records = RECORD_SEPARATOR.join(
        f"{node_id}{LIST_SEPARATOR}{alert_type}{LIST_SEPARATOR}{value}{LIST_SEPARATOR}{timestamp}"
        for node_id, alert_type, value, timestamp in alert_records
    )
    return build_message(ALERTS, OK, len(alert_records), records)

def build_error(code: str, description: str) -> str:
    return build_message(ERROR, code, description)


# Validation / parsing

def parse_message(message: str) -> list[str]:
    clean_message = message.rstrip("\r\n")
    if not clean_message:
        return []
    return clean_message.split(FIELD_SEPARATOR)

def is_valid_variable(variable: str) -> bool:
    return variable in VALID_VARIABLES

def is_valid_state(state: str) -> bool:
    return state in VALID_STATES

def is_valid_alert_type(alert_type: str) -> bool:
    return alert_type in VALID_ALERT_TYPES

def is_valid_node_id(node_id: str) -> bool:
    return bool(NODE_ID_PATTERN.fullmatch(node_id))

def is_valid_sequence(sequence_number: str) -> bool:
    try:
        return int(sequence_number) > 0
    except (TypeError, ValueError):
        return False

def is_valid_value(value: str) -> bool:
    try:
        number = float(value)
        return math.isfinite(number)
    except (TypeError, ValueError):
        return False

def validate_telemetry_fields(fields: list[str]) -> tuple[bool, str | None]:
    if len(fields) != 5 or fields[0] != TELEMETRY:
        return False, INVALID_MESSAGE
    if not is_valid_node_id(fields[1]):
        return False, INVALID_NODE_ID
    if not is_valid_sequence(fields[2]):
        return False, INVALID_SEQUENCE
    if not is_valid_variable(fields[3]):
        return False, INVALID_VARIABLE
    if not is_valid_value(fields[4]):
        return False, INVALID_VALUE
    return True, None
