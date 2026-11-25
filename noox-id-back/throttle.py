"""Límite de intentos fallidos por clave (usuario, aplicación+usuario…), en memoria del proceso.

Tras `max_fallos` en `ventana` segundos la clave queda bloqueada hasta que el fallo más antiguo salga de la
ventana. Un acierto reinicia el contador. Sirve para el prototipo; con varios procesos habría que moverlo a
un almacén compartido (Redis o la base de datos).
"""
import threading
import time


class Throttle:
    def __init__(self, max_fallos, ventana):
        self.max_fallos = max_fallos
        self.ventana = ventana
        self._lock = threading.Lock()
        self._fallos = {}

    def _recientes(self, clave, ahora):
        return [t for t in self._fallos.get(clave, []) if ahora - t < self.ventana]

    def locked(self, clave):
        """Segundos de bloqueo restantes (0 si puede intentar)."""
        ahora = time.time()
        with self._lock:
            recientes = self._recientes(clave, ahora)
            self._fallos[clave] = recientes
            if len(recientes) >= self.max_fallos:
                return int(self.ventana - (ahora - recientes[0])) + 1
        return 0

    def fail(self, clave):
        ahora = time.time()
        with self._lock:
            recientes = self._recientes(clave, ahora)
            recientes.append(ahora)
            self._fallos[clave] = recientes

    def reset(self, clave):
        with self._lock:
            self._fallos.pop(clave, None)


# Contraseña: 10 fallos en 15 min. Rostro (NIST SP 800-63B-4 limita a 5 fallos seguidos sin PAD): 5 en 15 min.
LOGIN = Throttle(10, 900)
FACE = Throttle(5, 900)
