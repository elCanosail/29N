#!/usr/bin/env python3
"""Tests del modulo dhondt.py (29N). Ejecutar: python3 pipeline/interior/test_dhondt.py

Sin dependencias (assert nativo). Cubre: reparto basico, empates, umbral del 3 %,
circunscripcion de 1 escano y coherencia de la suma de escanos.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dhondt import dhondt  # noqa: E402


def check(name, got, exp):
    assert got == exp, f"{name}: esperado {exp}, obtenido {got}"
    print(f"  OK {name}")


def run():
    print("test_dhondt")
    # 1) ejemplo basico (sin umbral)
    check("basico-5",
          dhondt({"A": 100000, "B": 80000, "C": 30000}, 5, threshold_frac=0.0),
          {"A": 3, "B": 2, "C": 0})
    # 2) un solo escano -> gana el mas votado
    check("1-escano", dhondt({"A": 5000, "B": 4900, "C": 100}, 1, 0.0), {"A": 1, "B": 0, "C": 0})
    # 3) umbral 3 %: C queda fuera (10 < 3 % de 1000 = 30), B entra justo (30)
    check("umbral", dhondt({"A": 960, "B": 30, "C": 10}, 1, 0.03, valid_votes=1000),
          {"A": 1, "B": 0, "C": 0})
    # 4) empate exacto de cociente: se rompe de forma determinista (nombre asc)
    check("empate", dhondt({"A": 10, "B": 10}, 1, 0.0), {"A": 1, "B": 0})
    # 5) la suma de escanos repartidos == seats
    v = {"A": 123456, "B": 98765, "C": 45678, "D": 12345, "E": 4321}
    r = dhondt(v, 17, 0.0)
    assert sum(r.values()) == 17, f"suma escanos {sum(r.values())} != 17"
    print("  OK suma-escanos=17")
    # 6) todos por debajo del umbral -> no reparte (situacion imposible en la practica)
    check("nadie-supera-umbral", dhondt({"A": 1, "B": 1}, 5, 0.03, valid_votes=100000),
          {"A": 0, "B": 0})
    # 7) CERA con valid_votes explicito (no cuenta para el reparto, si para el umbral)
    check("valid-votes-explicito",
          dhondt({"A": 500, "B": 300}, 2, 0.03, valid_votes=1000), {"A": 1, "B": 1})
    print("todos los tests OK")


if __name__ == "__main__":
    run()
