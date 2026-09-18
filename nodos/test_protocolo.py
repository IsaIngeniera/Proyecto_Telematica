"""
Pruebas automáticas para protocolo.py

Ejecutar:
    python test_protocolo.py
"""

import protocolo


def prueba(nombre, condicion):
    """Muestra PASS o FAIL para cada prueba."""
    if condicion:
        print(f"[PASS] {nombre}")
    else:
        print(f"[FAIL] {nombre}")
        raise AssertionError(nombre)


def main():
    print("=" * 60)
    print("PRUEBAS DEL PROTOCOLO DE TELEMETRÍA")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. TELEMETRY
    # ---------------------------------------------------------
    mensaje = protocolo.build_telemetry(
        "NODE01",
        1,
        protocolo.TEMP,
        25.5
    )

    print("\nMensaje de telemetría:")
    print(repr(mensaje))

    prueba(
        "build_telemetry genera mensaje",
        mensaje == "TELEMETRY|NODE01|1|TEMP|25.5\n"
    )

    campos = protocolo.parse_message(mensaje)

    prueba(
        "parse_message separa correctamente",
        campos == ["TELEMETRY", "NODE01", "1", "TEMP", "25.5"]
    )

    valido, error = protocolo.validate_telemetry_fields(campos)

    prueba(
        "telemetría válida",
        valido is True and error is None
    )

    # ---------------------------------------------------------
    # 2. NODE ID
    # ---------------------------------------------------------
    prueba(
        "NODE01 es válido",
        protocolo.is_valid_node_id("NODE01")
    )

    prueba(
        "NODE99 es válido",
        protocolo.is_valid_node_id("NODE99")
    )

    prueba(
        "NODE1 es inválido",
        not protocolo.is_valid_node_id("NODE1")
    )

    prueba(
        "ABC01 es inválido",
        not protocolo.is_valid_node_id("ABC01")
    )

    prueba(
        "NODE001 es inválido",
        not protocolo.is_valid_node_id("NODE001")
    )

    # ---------------------------------------------------------
    # 3. SEQUENCE
    # ---------------------------------------------------------
    prueba(
        "Secuencia 1 es válida",
        protocolo.is_valid_sequence("1")
    )

    prueba(
        "Secuencia 100 es válida",
        protocolo.is_valid_sequence("100")
    )

    prueba(
        "Secuencia 0 es inválida",
        not protocolo.is_valid_sequence("0")
    )

    prueba(
        "Secuencia negativa es inválida",
        not protocolo.is_valid_sequence("-1")
    )

    prueba(
        "Secuencia de texto es inválida",
        not protocolo.is_valid_sequence("abc")
    )

    # ---------------------------------------------------------
    # 4. VARIABLES
    # ---------------------------------------------------------
    prueba(
        "TEMP es válida",
        protocolo.is_valid_variable("TEMP")
    )

    prueba(
        "HUM es válida",
        protocolo.is_valid_variable("HUM")
    )

    prueba(
        "ENERGY es válida",
        protocolo.is_valid_variable("ENERGY")
    )

    prueba(
        "VIBRATION es válida",
        protocolo.is_valid_variable("VIBRATION")
    )

    prueba(
        "PRESSURE es inválida",
        not protocolo.is_valid_variable("PRESSURE")
    )

    # ---------------------------------------------------------
    # 5. VALORES
    # ---------------------------------------------------------
    prueba(
        "25.5 es un valor válido",
        protocolo.is_valid_value("25.5")
    )

    prueba(
        "0 es un valor válido",
        protocolo.is_valid_value("0")
    )

    prueba(
        "-10.5 es un valor válido",
        protocolo.is_valid_value("-10.5")
    )

    prueba(
        "abc es inválido",
        not protocolo.is_valid_value("abc")
    )

    prueba(
        "NaN es inválido",
        not protocolo.is_valid_value("NaN")
    )

    prueba(
        "Infinity es inválido",
        not protocolo.is_valid_value("Infinity")
    )

    # ---------------------------------------------------------
    # 6. TELEMETRÍA INVÁLIDA
    # ---------------------------------------------------------

    # ID inválido
    campos = [
        "TELEMETRY",
        "NODE1",
        "1",
        "TEMP",
        "25.5"
    ]

    valido, error = protocolo.validate_telemetry_fields(campos)

    prueba(
        "Detecta NODE_ID inválido",
        not valido and error == protocolo.INVALID_NODE_ID
    )

    # Secuencia inválida
    campos = [
        "TELEMETRY",
        "NODE01",
        "0",
        "TEMP",
        "25.5"
    ]

    valido, error = protocolo.validate_telemetry_fields(campos)

    prueba(
        "Detecta SEQUENCE inválida",
        not valido and error == protocolo.INVALID_SEQUENCE
    )

    # Variable inválida
    campos = [
        "TELEMETRY",
        "NODE01",
        "1",
        "PRESSURE",
        "25.5"
    ]

    valido, error = protocolo.validate_telemetry_fields(campos)

    prueba(
        "Detecta VARIABLE inválida",
        not valido and error == protocolo.INVALID_VARIABLE
    )

    # Valor inválido
    campos = [
        "TELEMETRY",
        "NODE01",
        "1",
        "TEMP",
        "abc"
    ]

    valido, error = protocolo.validate_telemetry_fields(campos)

    prueba(
        "Detecta VALUE inválido",
        not valido and error == protocolo.INVALID_VALUE
    )

    # Cantidad de campos incorrecta
    campos = [
        "TELEMETRY",
        "NODE01",
        "1"
    ]

    valido, error = protocolo.validate_telemetry_fields(campos)

    prueba(
        "Detecta cantidad incorrecta de campos",
        not valido and error == protocolo.INVALID_MESSAGE
    )

    # ---------------------------------------------------------
    # 7. REQUESTS TCP
    # ---------------------------------------------------------
    prueba(
        "GET_STATUS",
        protocolo.build_get_status() == "GET_STATUS\n"
    )

    prueba(
        "GET_NODES",
        protocolo.build_get_nodes() == "GET_NODES\n"
    )

    prueba(
        "GET_NODE",
        protocolo.build_get_node("NODE01") == "GET_NODE|NODE01\n"
    )

    prueba(
        "GET_ALERTS",
        protocolo.build_get_alerts() == "GET_ALERTS\n"
    )

    # ---------------------------------------------------------
    # 8. STATUS
    # ---------------------------------------------------------
    status = protocolo.build_status(
        registered_nodes=5,
        active_nodes=4,
        alert_count=2,
        udp_received=100,
        udp_lost=3
    )

    print("\nSTATUS:")
    print(repr(status))

    prueba(
        "STATUS contiene REGISTERED",
        "REGISTERED=5" in status
    )

    prueba(
        "STATUS contiene ACTIVE",
        "ACTIVE=4" in status
    )

    prueba(
        "STATUS contiene ALERTS",
        "ALERTS=2" in status
    )

    prueba(
        "STATUS contiene UDP_RECEIVED",
        "UDP_RECEIVED=100" in status
    )

    prueba(
        "STATUS contiene UDP_LOST",
        "UDP_LOST=3" in status
    )

    # ---------------------------------------------------------
    # 9. NODES
    # ---------------------------------------------------------
    nodes = protocolo.build_nodes({
        "NODE01": protocolo.ACTIVE,
        "NODE02": protocolo.INACTIVE,
        "NODE03": protocolo.ACTIVE,
    })

    print("\nNODES:")
    print(repr(nodes))

    prueba(
        "NODES contiene COUNT=3",
        "NODES|OK|3|" in nodes
    )

    prueba(
        "NODES contiene NODE01",
        "NODE01,ACTIVE" in nodes
    )

    prueba(
        "NODES contiene NODE02",
        "NODE02,INACTIVE" in nodes
    )

    prueba(
        "NODES vacío funciona",
        protocolo.build_nodes({}) == "NODES|OK|0|NO_DATA\n"
    )

    # ---------------------------------------------------------
    # 10. NODE_DATA
    # ---------------------------------------------------------
    node_data = protocolo.build_node_data(
        node_id="NODE01",
        state="ACTIVE",
        temperature=25.5,
        humidity=60.0,
        energy=20.0,
        vibration=3.5,
        last_seen="2026-09-12T14:30:00Z"
    )

    print("\nNODE_DATA:")
    print(repr(node_data))

    prueba(
        "NODE_DATA contiene NODE01",
        "NODE01" in node_data
    )

    prueba(
        "NODE_DATA contiene TEMP",
        "TEMP=25.5" in node_data
    )

    prueba(
        "NODE_DATA contiene HUM",
        "HUM=60.0" in node_data
    )

    prueba(
        "NODE_DATA contiene ENERGY",
        "ENERGY=20.0" in node_data
    )

    prueba(
        "NODE_DATA contiene VIBRATION",
        "VIBRATION=3.5" in node_data
    )

    prueba(
        "NODE_DATA contiene LAST_SEEN",
        "LAST_SEEN=2026-09-12T14:30:00Z" in node_data
    )

    # ---------------------------------------------------------
    # 11. NO_DATA
    # ---------------------------------------------------------
    node_data_empty = protocolo.build_node_data(
        node_id="NODE02",
        state="INACTIVE",
        temperature=None,
        humidity=None,
        energy=None,
        vibration=None,
        last_seen="NO_DATA"
    )

    prueba(
        "NODE_DATA acepta valores NO_DATA",
        "TEMP=NO_DATA" in node_data_empty
        and "HUM=NO_DATA" in node_data_empty
    )

    # ---------------------------------------------------------
    # 12. ALERTS
    # ---------------------------------------------------------
    alerts = protocolo.build_alerts([
        (
            "NODE01",
            protocolo.TEMP_HIGH,
            45.0,
            "2026-09-12T14:30:00Z"
        ),
        (
            "NODE02",
            protocolo.HUM_HIGH,
            90.0,
            "2026-09-12T14:31:00Z"
        )
    ])

    print("\nALERTS:")
    print(repr(alerts))

    prueba(
        "ALERTS contiene COUNT=2",
        "ALERTS|OK|2|" in alerts
    )

    prueba(
        "ALERTS contiene TEMP_HIGH",
        "TEMP_HIGH" in alerts
    )

    prueba(
        "ALERTS contiene HUM_HIGH",
        "HUM_HIGH" in alerts
    )

    prueba(
        "ALERTS vacío funciona",
        protocolo.build_alerts([]) == "ALERTS|OK|0|NO_DATA\n"
    )

    # ---------------------------------------------------------
    # 13. ERRORES
    # ---------------------------------------------------------
    error = protocolo.build_error(
        protocolo.ERROR_BAD_REQUEST,
        protocolo.INVALID_VARIABLE
    )

    prueba(
        "ERROR se construye correctamente",
        error == "ERROR|400|INVALID_VARIABLE\n"
    )

    # ---------------------------------------------------------
    # 14. UTF-8 Y TAMAÑO
    # ---------------------------------------------------------
    encoded = protocolo.encode_message("TEMP|25.5\n")

    prueba(
        "encode_message devuelve bytes",
        isinstance(encoded, bytes)
    )

    prueba(
        "encode_message conserva UTF-8",
        encoded == b"TEMP|25.5\n"
    )

    # ---------------------------------------------------------
    # 15. MENSAJE DEMASIADO LARGO
    # ---------------------------------------------------------
    mensaje_largo = "A" * 1025

    try:
        protocolo.encode_message(mensaje_largo)
        demasiado_largo = False
    except ValueError as exc:
        demasiado_largo = str(exc) == protocolo.MESSAGE_TOO_LONG

    prueba(
        "Rechaza mensajes mayores de 1024 bytes",
        demasiado_largo
    )

    # ---------------------------------------------------------
    # 16. FRAMING
    # ---------------------------------------------------------
    mensaje = "TELEMETRY|NODE01|5|TEMP|30.2\n"

    campos = protocolo.parse_message(mensaje)

    prueba(
        "Elimina correctamente \\n al hacer parse",
        campos == [
            "TELEMETRY",
            "NODE01",
            "5",
            "TEMP",
            "30.2"
        ]
    )

    mensaje = "TELEMETRY|NODE01|5|TEMP|30.2\r\n"

    campos = protocolo.parse_message(mensaje)

    prueba(
        "Acepta \\r\\n como final de mensaje",
        campos == [
            "TELEMETRY",
            "NODE01",
            "5",
            "TEMP",
            "30.2"
        ]
    )

    # ---------------------------------------------------------
    # RESULTADO FINAL
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("TODAS LAS PRUEBAS PASARON CORRECTAMENTE")
    print("=" * 60)


if __name__ == "__main__":
    main()