# Plataforma Distribuida de Telemetría y Gestión de Infraestructura Inteligente

> **Proyecto 1 — Internet: Arquitectura y Protocolos**[cite: 3]
> Departamento de Informática y Sistemas — **Universidad EAFIT**[cite: 3]
> Docente: Alber Oswaldo Montoya Benitez[cite: 3]

---

## 👥 Equipo de Trabajo y Responsabilidades

* **Yan Frank Ríos López** — *Infraestructura Cloud en AWS EC2, Contenerización con Docker y Docker Compose, Configuración DDNS (DuckDNS) y Análisis de Tráfico de Red (Wireshark).*[cite: 3]
* **Isabella Cadavid Posada** — *Desarrollo del Cliente Operador (GUI Tkinter), Capa de Comunicación TCP y Servicio Web HTTP (Flask).*[cite: 3]
* **Wendy Vanessa Atehortua Chaverra** — *Implementación de Nodos IoT Concurrentes (Python), Manejo de Excepciones de Red y Simulación de Anomalías Térmicas.*[cite: 3]
* **Isabella Ocampo Sánchez** — *Lógica del Servidor Central en Lenguaje C, Multiplexación con `select()`, Gestión de Memoria y Protocolo de Aplicación.*[cite: 3]

---

## 📌 Visión General del Proyecto

Este sistema implementa una arquitectura distribuida de telemetría y monitoreo de infraestructura física en tiempo real orientada a la pila de protocolos **TCP/IP**[cite: 3]. Diseñado para operar en un entorno de red público y heterogéneo, desacopla la transmisión masiva y no orientada a conexión de métricas sensoriales (**UDP**) de la administración, auditoría e inspección concurrente y fiable (**TCP**)[cite: 3].

### Aspectos Destacados de Ingeniería:
* **Modelo de Red Híbrido:** Uso coordinado de sockets UDP (puerto `5000`) para telemetría continua de bajo retardo y sockets TCP (puerto `6000`) para consultas de estado seguras y libres de pérdidas[cite: 3].
* **Servidor Central de Alto Rendimiento en C:** Bucle de eventos no bloqueante mediante multiplexación de E/S con la llamada de sistema `select()`, capaz de soportar hasta 32 operadores simultáneos sin sobrecarga de hilos ni condiciones de carrera[cite: 3].
* **Despliegue Nativo en la Nube:** Contenedor optimizado sobre Debian desplegado en una instancia **AWS EC2** (Ubuntu 26.04 LTS), accesible públicamente mediante **Dynamic DNS (DuckDNS)** sin requerir direccionamiento IP estático[cite: 3].
* **Detección Automática de Anomalías:** Procesamiento en memoria de lecturas de sensores que dispara alertas automáticas cuando las variables superan los umbrales críticos de seguridad[cite: 3].
* **Auditoría Integral de Capa de Transporte:** Verificación empírica con Wireshark del *Three-Way Handshake*, segmentación, transferencia fiable y balance matemático con **0% de pérdida de paquetes** a través de Internet[cite: 3].

---

## 🏗️ Arquitectura de Red y Flujo de Datos

+----------------------------------------------------------------------------------------------------+
|                                    CAPA DE TELEMETRÍA (IoT)                                        |
|  [NODE01 (Anomalías)]  [NODE02]  [NODE03]  [NODE04]  [NODE05]                                      |
|  - Sockets Python UDP (socket.AF_INET, socket.SOCK_DGRAM)                                         |
|  - Resolución de nombres vía socket.getaddrinfo()                                                 |
|  - Ráfagas periódicas de 4 variables: TEMP, HUM, ENERGY, VIBRATION                                |
+----------------------------------------------------------------------------------------------------+
                                                  │
                                                  │  UDP Datagrams (Puerto 5000)
                                                  ▼
+----------------------------------------------------------------------------------------------------+
|                             CAPA DE NUBE & SERVIDOR CENTRAL (AWS EC2)                              |
|                                                                                                    |
|  Dominio FQDN: telematica-eafit.duckdns.org  ──>  AWS Security Group (Inbound: 22, 5000, 6000)     |
|                                                                                                    |
|  Contenedor Docker (debian:bookworm-slim)                                                          |
|  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  |
|  │ Servidor Central en Lenguaje C                                                               │  |
|  │  - Multiplexación select() sobre fd_set (1 socket UDP + 1 socket TCP Listen + N sockets TCP) │  |
|  │  - Almacén de Estado en Memoria (Tabla de dispositivos, métricas recientes y contadores)    │  |
|  │  - Motor de Reglas: TEMP > 40.0 °C  ──>  Disparo de alerta TEMP_HIGH                         │  |
|  │  - Tolerancia a fallos: SO_REUSEADDR habilitado y señal SIGPIPE ignorada                      │  |
|  └──────────────────────────────────────────────────────────────────────────────────────────────┘  |
+----------------------------------------------------------------------------------------------------+
                     ▲                                                    ▲
                     │                                                    │
                     │  TCP Stream (Puerto 6000)                          │  TCP Stream (Puerto 6000)
                     │                                                    │
+────────────────────┴───────────────────────────+    +───────────────────┴──────────────────────────+
|           CLIENTE OPERADOR (ESCRITORIO)         |    |              SERVICIO WEB (HTTP)             |
|  - Interfaz Gráfica en Tkinter                 |    |  - Microservicio Flask en Python             |
|  - Consultas en hilos secundarios (No bloquea) │    |  - Renderizado HTML/CSS (Puerto local 8080)  |
|  - Inspección global y por nodo                |    |  - Consumo directo del protocolo TCP         |
+────────────────────────────────────────────────+    +──────────────────────────────────────────────+

---

## 📡 Especificación del Protocolo de Aplicación

Protocolo de texto estructurado con delimitador por tubería (`|`), diseñado a la medida para balancear legibilidad humana con facilidad de parseo[cite: 3].

### 1. Canal de Telemetría (Nodos -> Servidor) [UDP :5000][cite: 3]
Cada ciclo del nodo emite cuatro datagramas independientes (uno por métrica)[cite: 3]:
`TELEMETRY|<NODE_ID>|<SECUENCIA>|<VARIABLE>|<VALOR>`
* **Variables admitidas:** `TEMP` (°C), `HUM` (%), `ENERGY` (W), `VIBRATION` (mm/s)[cite: 3].
* **Ejemplo real:** `TELEMETRY|NODE01|21|TEMP|45.00`[cite: 3]

### 2. Canal del Operador y Consultas [TCP :6000][cite: 3]
Comandos terminados en salto de línea (`\n`) procesados de forma secuencial sobre conexiones persistentes[cite: 3]:

| Comando | Formato de Respuesta Exitosa | Descripción |
| :--- | :--- | :--- |
| `GET_STATUS` | `STATUS\|OK\|REGISTERED=<n>\|ACTIVE=<n>\|ALERTS=<n>\|UDP_RECEIVED=<n>\|UDP_LOST=<n>` | Consulta las estadísticas consolidadas y balance de paquetes[cite: 3]. |
| `GET_ALERTS` | `ALERTS\|<NODE_ID>,<TIPO>,<VALOR>,<TIMESTAMP>\|...` | Retorna el listado cronológico de eventos críticos detectados[cite: 3]. |
| *Comando inválido* | `ERROR\|400\|INVALID_MESSAGE` | Manejo preventivo del servidor ante tramas corruptas o desconocidas[cite: 3]. |

---

## 📂 Organización del Repositorio

.
├── cliente/
│   ├── main.py                    # Aplicación cliente con interfaz gráfica Tkinter
│   ├── protocolo_cliente.py       # Serializador y parser de tramas TCP para la GUI
│   └── servicio_web.py            # Servidor HTTP Flask (puerto 8080) y vista web
├── nodos/
│   ├── nodo.py                    # Emulador de nodo sensor individual con manejo de sockets
│   ├── lanzar_nodos.py            # Orquestador multi-proceso para pruebas de concurrencia
│   ├── protocolo.py               # Lógica común compartida para formateo de tramas
│   └── test_protocolo.py          # Pruebas unitarias de construcción y validación de mensajes
├── servidor/
│   ├── Dockerfile                 # Receta de compilación nativa en C sobre debian:bookworm-slim
│   ├── docker-compose.yml         # Orquestación del servicio y forward de puertos
│   ├── Makefile                   # Reglas de compilación y limpieza con gcc
│   ├── server.c                   # Punto de entrada, bucle select(), sockets TCP/UDP y señales
│   ├── protocolo.c / .h           # Procesamiento de líneas de texto y respuestas del protocolo
│   └── nodos.c / .h               # Estructuras de datos dinámicas, estados y reglas de alerta
├── capturas/
│   └── captura_telematica.pcapng  # Archivo de trazas de red capturado en Wireshark
└── README.md                      # Documentación técnica del proyecto

---

## 🚀 Guía de Despliegue y Ejecución

### Paso 1: Puesta en marcha del Servidor Central (AWS EC2 o Local)
El servidor corre dentro de un contenedor aislado con compilación nativa[cite: 3].

```bash
# 1. Ingresar al directorio del servidor
cd servidor

# 2. Construir la imagen y levantar el contenedor en segundo plano
docker compose up -d --build

# 3. Validar estado de los puertos expuestos (5000/udp y 6000/tcp)
docker compose ps

# 4. Monitorear los registros de telemetría y conexiones en vivo
docker logs -f servidor_central
```

### Paso 2: Ejecución de la Malla de Nodos de Telemetría (Emisores UDP)
Los nodos resuelven el FQDN antes de transmitir[cite: 3].

```bash
# 1. Ingresar a la carpeta de nodos
cd nodos

# Opción A: Lanzar un único nodo sensor (con reporte de logs detallado)
python3 nodo.py --node-id NODE01 --host telematica-eafit.duckdns.org --port 5000

# Opción B: Lanzar la malla completa de 5 nodos simultáneos (con inyección de anomalía en NODE01)
python3 lanzar_nodos.py --count 5
```
*(Al presionar `Ctrl + C`, los nodos ejecutan un cierre ordenado de sockets y muestran el resumen de paquetes enviados vs errores)*[cite: 3].

### Paso 3: Operación y Auditoría

#### Opción A: Cliente con Interfaz Gráfica (Python Tkinter)
```bash
cd cliente
python3 main.py
```
*Configura el Host como `telematica-eafit.duckdns.org` y el Puerto en `6000` para iniciar la monitorización interactiva.*[cite: 3]

#### Opción B: Dashboard Web HTTP (Flask)
```bash
cd cliente
pip install flask
python3 servicio_web.py
```
*Abre tu navegador e ingresa a `http://localhost:8080` para visualizar el panel de solo lectura.*[cite: 3]

#### Opción C: Auditoría rápida mediante Netcat (Línea de comandos)
```bash
nc telematica-eafit.duckdns.org 6000
GET_STATUS
GET_ALERTS
```

---

## 📊 Validación Empírica y Pruebas de Integración

### Balance Cruzado de Paquetes (Tx vs Rx vs Pérdida)
Durante la prueba de integración de punta a punta a través de Internet público, se reiniciaron los contadores del servidor y se emitieron ráfagas continuas desde una red externa[cite: 3]:

* **Datagramas transmitidos por los nodos (Tx):** 5 nodos concurrentes × 36 datagramas = **180 paquetes emitidos**[cite: 3].
* **Datagramas procesados en el contenedor (Rx):** `UDP_RECEIVED=180`[cite: 3].
* **Pérdida de paquetes en la capa de transporte:** **0.0%** (`UDP_LOST=0`)[cite: 3].
* **Alertas críticas detectadas:** 7 alertas generadas de forma determinista ante la anomalía térmica de 45.00 °C programada en `NODE01`[cite: 3].

### Análisis de Tráfico en Wireshark (`captura_telematica.pcapng`)
1. **Concurrencia de Protocolos:** Coexistencia pacífica sobre la misma interfaz del flujo constante de datagramas UDP (5000) y las sesiones fiables TCP (6000)[cite: 2, 3].
2. **Ciclo de Vida TCP:** Inspección completa del *Three-Way Handshake* (`SYN`, `SYN-ACK`, `ACK`), intercambio de carga útil PSH/ACK para `GET_STATUS` y terminación ordenada con banderas `FIN, ACK`[cite: 2, 3].
3. **Estructura UDP:** Verificación del encabezado mínimo de 8 bytes sin sobrecarga y entrega del payload en texto plano ASCII[cite: 2, 3].

---

## 🛠️ Tecnologías y Herramientas Utilizadas

* **Lenguajes:** C (C99 / POSIX Sockets), Python 3.10+[cite: 3].
* **Infraestructura Cloud:** AWS EC2 (Instancia Ubuntu Server), Security Groups[cite: 3].
* **Contenerización:** Docker Engine, Docker Compose, Debian Bookworm Slim[cite: 3].
* **Redes y Resolución:** Dynamic DNS (DuckDNS API), POSIX `getaddrinfo()`[cite: 3].
* **Auditoría e Inspección:** Wireshark Network Analyzer, Netcat (`nc`), GNU Make, GCC[cite: 3].
* **Frameworks y GUI:** Python Tkinter, Flask Microframework[cite: 3].
