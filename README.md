# Simulador de Nodos de Telemetría (IoT)

Este módulo contiene la implementación en Python de los nodos sensores para la plataforma distribuida. Los dispositivos generan mediciones simuladas (temperatura, humedad, energía y vibración) y las transmiten mediante sockets UDP al servidor central.

## Archivos del Módulo

* **`protocolo.py`**: Define la estructura estándar de los mensajes. Contiene las funciones compartidas para empaquetar y parsear las cadenas de texto del protocolo de capa de aplicación.
* **`nodo.py`**: Script principal de cada dispositivo individual. Resuelve dinámicamente el DNS del servidor, genera las métricas, inyecta anomalías configuradas y maneja la recuperación automática de red para que el programa no se caiga abruptamente ante fallos de conexión.
* **`lanzar_nodos.py`**: Orquestador diseñado para pruebas de concurrencia. Instancia y ejecuta múltiples nodos simultáneamente (ej. 5 o más) para validar el comportamiento del servidor bajo carga.
* **`mock_server.py`**: Servidor UDP de prueba. Permite validar la transmisión local de datagramas y la lógica de los nodos sin depender de que el servidor principal en C esté encendido.
* **`test_protocolo.py`**: Batería de pruebas para garantizar que la codificación y decodificación de mensajes cumpla estrictamente con la especificación del sistema.

## Instrucciones de Ejecución

1. **Ejecutar pruebas locales con el Mock Server:** 
   Para probar el ecosistema de forma aislada, levanta primero el servidor simulado en una terminal:
   `python3 mock_server.py`

2. **Ejecutar el orquestador de nodos:** 
   En una segunda terminal, asegúrate de apuntar la dirección de destino temporalmente a `localhost` y lanza la simulación concurrente:
   `python3 lanzar_nodos.py`

3. **Detener la simulación y ver métricas:** 
   Presiona `Ctrl + C` para detener el script de forma segura. El orquestador atrapará la interrupción y mostrará un resumen final en consola con la cantidad de paquetes enviados vs. errores locales.

4. **Validar el protocolo de aplicación:** 
   Para confirmar que el formato de los mensajes sigue las reglas del proyecto, ejecuta:
   `python3 test_protocolo.py`
