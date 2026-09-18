"""Punto de entrada del Cliente Operador.

Uso:
    python main.py

Por defecto se conecta a localhost:6000 (el puerto TCP del servidor
central, ver servidor/server.c). El host y el puerto se pueden cambiar
desde la propia interfaz gráfica antes de refrescar.
"""

from interfaz_cliente import run

if __name__ == "__main__":
    run()