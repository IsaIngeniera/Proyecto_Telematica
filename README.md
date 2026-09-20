
# Plataforma Distribuida de Telemetría y Gestión de Infraestructura Inteligente

> **Proyecto 1 — Internet: Arquitectura y Protocolos**  
> Departamento de Informática y Sistemas — **Universidad EAFIT**  
> Docente: Alber Oswaldo Montoya Benitez

---

## Equipo de Trabajo y Responsabilidades

* **Yan Frank Ríos López** — *Infraestructura Cloud en AWS EC2, Contenerización con Docker y Docker Compose, Configuración DDNS (DuckDNS) y Análisis de Tráfico de Red (Wireshark).*
* **Isabella Cadavid Posada** — *Desarrollo del Cliente Operador (GUI Tkinter), Capa de Comunicación TCP y Servicio Web HTTP (Flask).*
* **Wendy Vanessa Atehortua Chaverra** — *Implementación de Nodos IoT Concurrentes (Python), Manejo de Excepciones de Red y Simulación de Anomalías Térmicas.*
* **Isabella Ocampo Sánchez** — *Lógica del Servidor Central en Lenguaje C, Multiplexación con `select()`, Gestión de Memoria y Protocolo de Aplicación.*

---

## Visión General del Proyecto

Este sistema implementa una arquitectura distribuida de telemetría y monitoreo de infraestructura física en tiempo real orientada a la pila de protocolos **TCP/IP**. Diseñado para operar en un entorno de red público y heterogéneo, desacopla la transmisión masiva y no orientada a conexión de métricas sensoriales (**UDP**) de la administración, auditoría e inspección concurrente y fiable (**TCP**).

### Aspectos Destacados de Ingeniería:
* **Modelo de Red Híbrido:** Uso coordinado de sockets UDP (puerto `5000`) para telemetría continua de bajo retardo y sockets TCP (puerto `6000`) para consultas de estado seguras y libres de pérdidas.
* **Servidor Central de Alto Rendimiento en C:** Bucle de eventos no bloqueante mediante multiplexación de E/S con la llamada de sistema `select()`, capaz de soportar hasta 32 operadores simultáneos sin sobrecarga de hilos ni condiciones de carrera.
* **Despliegue Nativo en la Nube:** Contenedor optimizado sobre Debian desplegado en una instancia **AWS EC2** (Ubuntu 26.04 LTS), accesible públicamente mediante **Dynamic DNS (DuckDNS)** sin requerir direccionamiento IP estático.
* **Detección Automática de Anomalías:** Procesamiento en memoria de lecturas de sensores que dispara alertas automáticas cuando las variables superan los umbrales críticos de seguridad.
* **Auditoría Integral de Capa de Transporte:** Verificación empírica con Wireshark del *Three-Way Handshake*, segmentación, transferencia fiable y balance matemático con **0% de pérdida de paquetes** a través de Internet.

---

## Arquitectura de Red y Flujo de Datos
```text
+----------------------------------------------------------------------------------------------------+
|                                    CAPA DE TELEMETRÍA (IoT)                                        |
|  [NODE01 (Anomalías)]  [NODE02]  [NODE03]  [NODE04]  [NODE05]                                      |
|  - Sockets Python UDP (socket.AF_INET, socket.SOCK_DGRAM)                                          |
|  - Resolución de nombres vía socket.getaddrinfo()                                                  |
|  - Ráfagas periódicas de 4 variables: TEMP, HUM, ENERGY, VIBRATION                                 |
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
|  │  - Almacén de Estado en Memoria (Tabla de dispositivos, métricas recientes y contadores)     │  |
|  │  - Motor de Reglas: TEMP > 40.0 °C  ──>  Disparo de alerta TEMP_HIGH                         │  |
|  │  - Tolerancia a fallos: SO_REUSEADDR habilitado y señal SIGPIPE ignorada                     │  |
|  └──────────────────────────────────────────────────────────────────────────────────────────────┘  |
+----------------------------------------------------------------------------------------------------+
                     ▲                                                    ▲
                     │                                                    │
                     │  TCP Stream (Puerto 6000)                          │  TCP Stream (Puerto 6000)
                     │                                                    │
+────────────────────┴───────────────────────────+    +───────────────────┴────────────────────────+
|           CLIENTE OPERADOR (ESCRITORIO)        |    |              SERVICIO WEB (HTTP)             |
|  - Interfaz Gráfica en Tkinter                 |    |  - Microservicio Flask en Python             |
|  - Consultas en hilos secundarios (No bloquea) │    |  - Renderizado HTML/CSS (Puerto local 8080)  |
|  - Inspección global y por nodo                |    |  - Consumo directo del protocolo TCP         |
+────────────────────────────────────────────────+    +──────────────────────────────────────────────+
```
⸻

## Especificación del Protocolo de Aplicación

Protocolo de texto estructurado con delimitador por tubería (`|`), diseñado a la medida para balancear legibilidad humana con facilidad de parseo.

### 1. Canal de Telemetría (Nodos -> Servidor) [UDP :5000]
Cada ciclo del nodo emite cuatro datagramas independientes (uno por métrica):
`TELEMETRY|<NODE_ID>|<SECUENCIA>|<VARIABLE>|<VALOR>`
* **Variables admitidas:** `TEMP` (°C), `HUM` (%), `ENERGY` (W), `VIBRATION` (mm/s).
* **Ejemplo real:** `TELEMETRY|NODE01|21|TEMP|45.00`

### 2. Canal del Operador y Consultas [TCP :6000]
Comandos terminados en salto de línea (`\n`) procesados de forma secuencial sobre conexiones persistentes:

| Comando | Formato de Respuesta Exitosa | Descripción |
| :--- | :--- | :--- |
| `GET_STATUS` | `STATUS\|OK\|REGISTERED=<n>\|ACTIVE=<n>\|ALERTS=<n>\|UDP_RECEIVED=<n>\|UDP_LOST=<n>` | Consulta las estadísticas consolidadas y balance de paquetes. |
| `GET_ALERTS` | `ALERTS\|<NODE_ID>,<TIPO>,<VALOR>,<TIMESTAMP>\|...` | Retorna el listado cronológico de eventos críticos detectados. |
| *Comando inválido* | `ERROR\|400\|INVALID_MESSAGE` | Manejo preventivo del servidor ante tramas corruptas o desconocidas. |

---

## Organización del Repositorio

```text
.
├── cliente/
│   ├── interfaz_cliente.py        # Componentes visuales y ventanas de la GUI en Tkinter
│   ├── logica_cliente.py          # Gestión de estados, hilos y lógica de negocio del cliente
│   ├── main.py                    # Punto de entrada principal del cliente operador TCP
│   ├── protocolo_cliente.py       # Serializador y parser de tramas TCP para la GUI
│   ├── requirements_web.txt       # Dependencias de Python para el servicio web
│   └── servicio_web.py            # Servidor HTTP Flask (puerto 8080) y panel de solo lectura
├── infraestructura/               # Scripts y configuraciones de red y despliegue cloud
├── nodos/
│   ├── lanzar_nodos.py            # Orquestador multi-proceso para pruebas de concurrencia
│   ├── nodo.py                    # Emulador de nodo sensor individual con manejo de sockets UDP
│   ├── protocolo.py               # Módulo común de formateo y validación de tramas
│   └── test_protocolo.py          # Pruebas unitarias de construcción de mensajes
├── servidor/
│   ├── Dockerfile                 # Receta de compilación nativa en C sobre debian:bookworm-slim
│   ├── Makefile                   # Reglas de compilación y limpieza del binario con gcc
│   ├── nodos.c / nodos.h          # Estructuras de datos dinámicas, estados y reglas de alerta
│   ├── protocolo.c / protocolo.h  # Procesamiento de líneas de texto y respuestas del protocolo
│   ├── server                     # Binario ejecutable compilado del servidor central
│   └── server.c                   # Punto de entrada, bucle select(), sockets TCP/UDP y señales
├── .gitignore                     # Exclusión de binarios, temporales y cachés (__pycache__)
├── docker-compose.yml             # Orquestación del servicio central y mapeo de puertos
└── README.md                      # Documentación técnica del proyecto
```
---

## Requisitos Previos

Para ejecutar el proyecto se requiere:

* **Python 3.10 o superior.**
* **Tkinter** para la interfaz gráfica.
* **Flask** para el servicio web.
* **GCC y GNU Make** para compilar el servidor localmente.
* **Docker y Docker Compose** para ejecutar el servidor en un contenedor.
* **Conexión a Internet** para utilizar el servidor desplegado mediante DuckDNS.

### Verificar Python 3

```bash
python3 --version
```

Si Python 3 no está instalado en macOS, puede instalarse desde [python.org](https://www.python.org/) o mediante Homebrew:

```bash
brew install python
```

### Verificar Tkinter

Tkinter normalmente está incluido en la instalación oficial de Python. Puede comprobarse con:

```bash
python3 -c "import tkinter; print('TKINTER DISPONIBLE')"
```

Si aparece:

```text
TKINTER DISPONIBLE
```

no es necesario instalar nada adicional.

Si se utilizó Python mediante Homebrew y Tkinter no está disponible, debe instalarse el paquete compatible con la versión de Python utilizada. También puede instalarse Python desde el instalador oficial de [python.org](https://www.python.org/), que incluye soporte para Tkinter.

### Instalar Flask

Desde la carpeta principal `Proyecto_Telematica`:

```bash
python3 -m pip install -r cliente/requirements_web.txt
```

Para comprobar la instalación:

```bash
python3 -c "import flask; print('FLASK DISPONIBLE')"
```

---

## Ejecución Usando el Servidor en la Nube

Antes de comenzar, la instancia EC2 y el contenedor Docker deben estar encendidos.

### Terminal 1: Comprobar la Conexión TCP

Este comando puede ejecutarse desde cualquier carpeta:

```bash
python3 -c 'import socket; s=socket.create_connection(("telematica-eafit.duckdns.org",6000),5); print("CONEXIÓN TCP EXITOSA"); s.close()'
```

Resultado esperado:

```text
CONEXIÓN TCP EXITOSA
```

### Terminal 2: Ejecutar Cinco Nodos

Desde la carpeta principal del proyecto:

```bash
cd nodos
python3 lanzar_nodos.py --count 5 --interval 2 --host telematica-eafit.duckdns.org --port 5000
```

Los nodos utilizan:

```text
UDP → telematica-eafit.duckdns.org:5000
```

Esta terminal debe permanecer abierta.

### Terminal 3: Ejecutar el Cliente Operador

Desde la carpeta principal, en otra terminal:

```bash
cd cliente
python3 main.py
```

En la interfaz verificar:

```text
Host: telematica-eafit.duckdns.org
Puerto: 6000
```

Después, presionar **Actualizar**.

### Terminal 4: Ejecutar el Servicio Web

En otra terminal:

```bash
cd cliente
TELEMETRY_SERVER_HOST=telematica-eafit.duckdns.org TELEMETRY_SERVER_PORT=6000 python3 servicio_web.py
```

Abrir en el navegador:

```text
http://127.0.0.1:8080
```

Aunque la página se abre localmente en el puerto `8080`, el servicio Flask consulta al servidor central desplegado en AWS mediante TCP y el dominio configurado.

---

## Ejecución Completamente Local

Para esta prueba no se necesita EC2, DuckDNS ni el contenedor remoto.

Se necesitan cuatro terminales.

### Terminal 1: Compilar y Ejecutar el Servidor Local

Desde la carpeta principal:

```bash
cd servidor
make
./server 5000 6000
```

El servidor escuchará en:

```text
UDP 5000 → telemetría
TCP 6000 → operadores
```

No cierres esta terminal.

### Terminal 2: Ejecutar los Cinco Nodos Localmente

Desde la carpeta principal:

```bash
cd nodos
python3 lanzar_nodos.py --count 5 --interval 2 --host localhost --port 5000
```

No cierres esta terminal.

### Terminal 3: Ejecutar Tkinter

Desde la carpeta principal:

```bash
cd cliente
python3 main.py
```

Como el valor predeterminado del código es el dominio de la nube, en la interfaz debes cambiar manualmente:

```text
Host: localhost
Puerto: 6000
```

Luego presiona **Actualizar**.

### Terminal 4: Ejecutar el Servicio Web Localmente

Desde la carpeta principal:

```bash
cd cliente
TELEMETRY_SERVER_HOST=localhost TELEMETRY_SERVER_PORT=6000 python3 servicio_web.py
```

Abrir en el navegador:

```text
http://127.0.0.1:8080
```

##  Guía de Despliegue y Ejecución

### Paso 1: Puesta en marcha del Servidor Central (AWS EC2 o Local)
El servidor corre dentro de un contenedor aislado con compilación nativa.

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
Los nodos resuelven el FQDN antes de transmitir.

```bash
# 1. Ingresar a la carpeta de nodos
cd nodos

# Opción A: Lanzar un único nodo sensor (con reporte de logs detallado)
python3 nodo.py --node-id NODE01 --host telematica-eafit.duckdns.org --port 5000

# Opción B: Lanzar la malla completa de 5 nodos simultáneos (con inyección de anomalía en NODE01)
python3 lanzar_nodos.py --count 5
```
*(Al presionar `Ctrl + C`, los nodos ejecutan un cierre ordenado de sockets y muestran el resumen de paquetes enviados vs errores).*

### Paso 3: Operación y Auditoría

#### Opción A: Cliente con Interfaz Gráfica (Python Tkinter)
```bash
cd cliente
python3 main.py
```
*Configura el Host como `telematica-eafit.duckdns.org` y el Puerto en `6000` para iniciar la monitorización interactiva.*

#### Opción B: Dashboard Web HTTP (Flask)
```bash
cd cliente
pip install flask
python3 servicio_web.py
```
*Abre tu navegador e ingresa a `http://localhost:8080` para visualizar el panel de solo lectura.*

#### Opción C: Auditoría rápida mediante Netcat (Línea de comandos)
```bash
nc telematica-eafit.duckdns.org 6000
GET_STATUS
GET_ALERTS
```

---

## Validación Empírica y Pruebas de Integración

### Balance Cruzado de Paquetes (Tx vs Rx vs Pérdida)
Durante la prueba de integración de punta a punta a través de Internet público, se reiniciaron los contadores del servidor y se emitieron ráfagas continuas desde una red externa:

* **Datagramas transmitidos por los nodos (Tx):** 5 nodos concurrentes × 36 datagramas = **180 paquetes emitidos**.
* **Datagramas procesados en el contenedor (Rx):** `UDP_RECEIVED=180`.
* **Pérdida de paquetes en la capa de transporte:** **0.0%** (`UDP_LOST=0`).
* **Alertas críticas detectadas:** 7 alertas generadas de forma determinista ante la anomalía térmica de 45.00 °C programada en `NODE01`.

### Análisis de Tráfico en Wireshark (`captura_telematica.pcapng`)
1. **Concurrencia de Protocolos:** Coexistencia pacífica sobre la misma interfaz del flujo constante de datagramas UDP (5000) y las sesiones fiables TCP (6000).
2. **Ciclo de Vida TCP:** Inspección completa del *Three-Way Handshake* (`SYN`, `SYN-ACK`, `ACK`), intercambio de carga útil PSH/ACK para `GET_STATUS` y terminación ordenada con banderas `FIN, ACK`.
3. **Estructura UDP:** Verificación del encabezado mínimo de 8 bytes sin sobrecarga y entrega del payload en texto plano ASCII.

---

## Tecnologías y Herramientas Utilizadas

* **Lenguajes:** C (C99 / POSIX Sockets), Python 3.10+.
* **Infraestructura Cloud:** AWS EC2 (Instancia Ubuntu Server), Security Groups.
* **Contenerización:** Docker Engine, Docker Compose, Debian Bookworm Slim.
* **Redes y Resolución:** Dynamic DNS (DuckDNS API), POSIX `getaddrinfo()`.
* **Auditoría e Inspección:** Wireshark Network Analyzer, Netcat (`nc`), GNU Make, GCC.
* **Frameworks y GUI:** Python Tkinter, Flask Microframework.

