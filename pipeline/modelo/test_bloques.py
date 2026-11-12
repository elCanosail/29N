#!/usr/bin/env python3
"""Tests de los agregados del PR-2 (issue #15): bloques, último escaño,
deltas entre corridas y MAE por casa.

Ejecutar con pytest, junto al código del pipeline:

    cd pipeline && python -m pytest -q

Ninguno de estos tests toca el modelo: comprueban los agregados que se
calculan **después** de las simulaciones (o sobre la tabla D'Hondt), y que
`dhondt()` sigue reproduciendo el escrutinio oficial de las 16 generales.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

import numpy as np
import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(RAIZ, "pipeline", "interior"))

import common as C                      # noqa: E402
import provincial as P                  # noqa: E402
from dhondt import dhondt, escalera_cocientes, ultimo_escano  # noqa: E402

PARTIES = C.MODELED_PARTIES
CFG = P.load_bloques(parties=PARTIES)


# --------------------------------------------------------------------------- #
# (0) La constante editorial cubre el universo modelado
# --------------------------------------------------------------------------- #
def test_bloques_cubren_el_universo_modelado():
    miembros = [p for ps in CFG["bloques"].values() for p in ps]
    assert len(miembros) == len(set(miembros)), "un partido está en dos bloques"
    assert not set(miembros) & set(CFG["fuera"]), "partido dentro y fuera a la vez"
    assert set(miembros) | set(CFG["fuera"]) == set(PARTIES)
    assert CFG["mayoria"] == 176


# --------------------------------------------------------------------------- #
# (a) p_ge176 suma 1 y cada bloque casa con la suma de sus partidos
# --------------------------------------------------------------------------- #
def _vector(escanos: dict) -> np.ndarray:
    return np.array([escanos.get(p, 0) for p in PARTIES], dtype=np.int32)


def test_suma_por_bloque_cuadra_con_sus_partidos():
    idx_bloque = [np.array([PARTIES.index(p) for p in ps], dtype=np.intp)
                  for ps in CFG["bloques"].values()]
    corridas = [
        {"PP": 130, "PSOE": 110, "VOX": 60, "SUMAR": 20, "ERC": 10,
         "EH BILDU": 6, "BNG": 4, "CUP": 2, "NA+": 1, "CC": 1},
        {"PP": 120, "PSOE": 120, "VOX": 55, "SUMAR": 15, "ERC": 10,
         "EH BILDU": 6, "BNG": 4, "CUP": 2, "NA+": 1, "CC": 1},
        {"PP": 100, "PSOE": 130, "VOX": 50, "SUMAR": 25, "ERC": 12,
         "EH BILDU": 7, "BNG": 5, "CUP": 3, "NA+": 2, "CC": 1},
    ]
    for corrida in corridas:
        tot = _vector(corrida)
        sumas = P.sumas_de_bloque_de_run(tot, idx_bloque)
        for suma, (nombre, miembros) in zip(sumas, CFG["bloques"].items()):
            assert suma == sum(corrida.get(p, 0) for p in miembros), nombre
        # izquierda + derecha + fuera de bloque = total de la corrida
        fuera = sum(corrida.get(p, 0) for p in CFG["fuera"])
        assert sum(sumas) + fuera == int(tot.sum())


def test_p_ge176_de_los_tres_estados_suma_uno():
    # 10 corridas sintéticas: izquierda alcanza 176 en 4, derecha en 3 y en 3
    # no llega ninguno de los dos (los bloques son disjuntos: nunca ambos).
    izquierda = [150, 180, 176, 149, 181, 160, 170, 175, 140, 190]
    derecha = [190, 165, 100, 120, 168, 185, 120, 174, 199, 160]
    bloque_runs = np.array(list(zip(izquierda, derecha)), dtype=np.int16)
    bloques, p_ninguno = P.agregar_bloques(bloque_runs, CFG, CFG["mayoria"])

    assert bloques["izquierda"]["p_ge176"] == pytest.approx(0.4)
    assert bloques["derecha"]["p_ge176"] == pytest.approx(0.3)
    assert p_ninguno == pytest.approx(0.3)
    total = (bloques["izquierda"]["p_ge176"] + bloques["derecha"]["p_ge176"]
             + p_ninguno)
    assert total == pytest.approx(1.0, abs=0.001)
    # media e IC95 son los de la suma del bloque, no los de los partidos
    assert bloques["izquierda"]["media"] == pytest.approx(float(np.mean(izquierda)), 2)
    assert bloques["izquierda"]["ic95"] == [
        int(np.percentile(izquierda, 2.5)), int(np.percentile(izquierda, 97.5))]


def test_p_ge176_del_json_real_suma_uno():
    ruta = os.path.join(C.DATA, "modelo", "seats.json")
    if not os.path.exists(ruta):
        pytest.skip("falta data/processed/modelo/seats.json")
    with open(ruta, encoding="utf-8") as fh:
        seats = json.load(fh)
    bl = seats["bloques"]
    total = bl["izquierda"]["p_ge176"] + bl["derecha"]["p_ge176"] + bl["p_ninguno"]
    assert total == pytest.approx(1.0, abs=0.001)
    for nombre in ("izquierda", "derecha"):
        assert set(bl[nombre]["partidos"]) == set(CFG["bloques"][nombre])
        assert 0.0 <= bl[nombre]["p_ge176"] <= 1.0
        assert bl[nombre]["ic95"][0] <= bl[nombre]["media"] <= bl[nombre]["ic95"][1]


# --------------------------------------------------------------------------- #
# (b) Último escaño: 52 provincias, dos partidos y p_a + p_b = 1
# --------------------------------------------------------------------------- #
def test_ultimo_escano_basico_y_desempate():
    # 1 escaño: gana el que más votos tiene, rival el siguiente cociente
    ladder = escalera_cocientes({"A": 100, "B": 90}, 1, 0.0)
    assert ultimo_escano(ladder, 1) == ("A", "B", pytest.approx(0.1))
    # si el siguiente cociente es del propio ganador, el rival es otro partido
    ladder = escalera_cocientes({"A": 1000, "B": 100, "C": 10}, 2, 0.0)
    ganador, rival, diff = ultimo_escano(ladder, 2)
    assert (ganador, rival) == ("A", "B")
    assert diff == pytest.approx((500 - 100) / 500)
    # sin escaños no hay último escaño
    assert ultimo_escano([], 0) is None


def test_agregar_ultimo_escano_reparte_el_duelo():
    parties = ["PP", "PSOE", "VOX"]
    # 10 corridas: PP gana 6 (rival PSOE), PSOE gana 3 (rival PP), VOX gana 1
    ganadores = np.array([0] * 6 + [1] * 3 + [2] * 1, dtype=np.int16)
    rivales = np.array([1] * 6 + [0] * 3 + [0] * 1, dtype=np.int16)
    diffs = np.full(10, 0.2)
    ficha = P.agregar_ultimo_escano(ganadores, rivales, diffs, parties)
    assert ficha["partidos"] == ["PP", "PSOE"]
    assert ficha["p_a"] == pytest.approx(6 / 9, abs=1e-4)
    assert ficha["p_b"] == pytest.approx(1 - 6 / 9, abs=1e-4)
    assert ficha["p_a"] + ficha["p_b"] == pytest.approx(1.0)
    assert ficha["diff_medio"] == pytest.approx(0.2)


def test_52_provincias_con_ultimo_escano():
    ruta = os.path.join(C.DATA, "modelo", "seats.json")
    if not os.path.exists(ruta):
        pytest.skip("falta data/processed/modelo/seats.json")
    with open(ruta, encoding="utf-8") as fh:
        seats = json.load(fh)
    provincias = seats["provincias"]
    assert len(provincias) == 52
    for codigo, p in provincias.items():
        u = p["ultimo_escano"]
        assert len(u["partidos"]) == 2, f"provincia {codigo}: {u['partidos']}"
        a, b = u["partidos"]
        assert a != b, f"provincia {codigo}: duelo contra sí mismo"
        assert u["p_a"] + u["p_b"] == pytest.approx(1.0, abs=1e-9)
        assert u["p_a"] >= u["p_b"] >= 0.0
        assert 0.0 <= u["diff_medio"] <= 1.0


# --------------------------------------------------------------------------- #
# (c) Deltas contra la corrida anterior (spot-check PP/PSOE/VOX)
# --------------------------------------------------------------------------- #
def test_deltas_cuadran_a_mano():
    prev = {
        "meta": {"generado": "2026-11-11"},
        "nacional": {
            "PP": {"central_escenario": 120},
            "PSOE": {"central_escenario": 116},
            "VOX": {"central_escenario": 67},
        },
        "bloques": {
            "izquierda": {"p_ge176": 0.0400},
            "derecha": {"p_ge176": 0.8000},
            "p_ninguno": 0.1600,
        },
    }
    nacional = {
        "PP": {"central_escenario": 125},
        "PSOE": {"central_escenario": 112},
        "VOX": {"central_escenario": 67},
    }
    bloques = {
        "izquierda": {"p_ge176": 0.0546},
        "derecha": {"p_ge176": 0.8558},
    }
    d = P.calcular_deltas(prev, nacional, bloques, p_ninguno=0.0896)
    assert d["contra"] == "2026-11-11"
    assert d["nacional"]["PP"] == 5
    assert d["nacional"]["PSOE"] == -4
    assert d["nacional"]["VOX"] == 0
    # p_ge176 en puntos porcentuales, 1 decimal
    assert d["bloques"]["izquierda"] == pytest.approx(1.5)
    assert d["bloques"]["derecha"] == pytest.approx(5.6)
    assert d["bloques"]["p_ninguno"] == pytest.approx(-7.0)


def test_sin_corrida_previa_no_hay_deltas():
    nacional = {"PP": {"central_escenario": 125}}
    bloques = {"izquierda": {"p_ge176": 0.0546}}
    assert P.calcular_deltas(None, nacional, bloques, 0.0896) == {}


def test_cambios_es_idempotente_por_fecha(tmp_path):
    ruta = tmp_path / "cambios.json"
    deltas = {"nacional": {"PP": 5}, "bloques": {"izquierda": 1.5}}
    P.actualizar_cambios(ruta, "2026-11-12", deltas)
    P.actualizar_cambios(ruta, "2026-11-12", {"nacional": {"PP": 3}, "bloques": {}})
    log = json.loads(ruta.read_text(encoding="utf-8"))
    assert len(log) == 1, "una corrida por fecha: se sustituye, no se duplica"
    assert log[0]["deltas_nacional"]["PP"] == 3
    # tope de 52 entradas: se descartan las más antiguas
    fechas = [f"2025-{1 + i // 28:02d}-{i % 28 + 1:02d}" for i in range(60)]
    for fecha in fechas:
        P.actualizar_cambios(ruta, fecha, deltas)
    log = json.loads(ruta.read_text(encoding="utf-8"))
    assert len(log) == P.MAX_CAMBIOS
    assert [e["generado"] for e in log] == fechas[-P.MAX_CAMBIOS:]


# --------------------------------------------------------------------------- #
# (d) casas.json: CIS en columna propia y n ≥ 3
# --------------------------------------------------------------------------- #
def _cargar_sync_data():
    """Importa web/sync-data.py, que no es un módulo importable por su nombre."""
    ruta = os.path.join(RAIZ, "web", "sync-data.py")
    spec = importlib.util.spec_from_file_location("sync_data_29n", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mae_por_casa_reglas():
    sd = _cargar_sync_data()
    oficial = {
        "2023-07-23": {"PP": 33.06, "PSOE": 31.68, "VOX": 12.38, "SUMAR": 12.33},
    }
    generales = ["2019-11-10", "2023-07-23"]

    def enc(casa, base, partidos, eleccion="generales 2023", fecha="2023-07-10"):
        return {"casa": casa, "base": base, "eleccion": eleccion,
                "fecha_trabajo": fecha, "partidos": partidos}

    perfecta = {"PP": 33.06, "PSOE": 31.68, "VOX": 12.38, "SUMAR": 12.33}
    encuestas = [
        enc("Casa3", "valido", perfecta),
        enc("Casa3", "valido", perfecta),
        enc("Casa3", "valido", perfecta),
        enc("Casa2", "valido", perfecta),
        enc("Casa2", "valido", perfecta),
        enc("CIS", "censo", perfecta, eleccion="generales", fecha="2023-07-10"),
        enc("CIS", "censo", perfecta, eleccion="generales", fecha="2023-06-08"),
        enc("CIS", "censo", perfecta, eleccion="generales", fecha="2023-09-01"),
        enc("Futura", "valido", perfecta, eleccion="generales 2026"),
        enc("Truncada", "valido", {"PP": 33.06}, fecha="2023-07-10"),
    ]
    filas = sd.mae_por_casa(encuestas, ["Casa3", "Casa2", "CIS", "Futura", "Truncada"],
                            oficial, generales, ["PP", "PSOE", "VOX", "SUMAR"])
    por_casa = {f["casa"]: f for f in filas}

    # 3 encuestas exactas → MAE 0 y n = 3
    assert por_casa["Casa3"]["n_encuestas"] == 3
    assert por_casa["Casa3"]["mae_pp"] == pytest.approx(0.0)
    assert por_casa["Casa3"]["mae_valido_pp"] == pytest.approx(0.0)
    assert por_casa["Casa3"]["mae_censo_pp"] is None
    assert por_casa["Casa3"]["elecciones_cubiertas"] == ["2023-07-23"]

    # 2 encuestas → sin dato suficiente
    assert por_casa["Casa2"]["n_encuestas"] == 2
    assert por_casa["Casa2"]["mae_pp"] is None

    # CIS: nunca en mae_pp; su MAE vive en la columna de censo
    assert por_casa["CIS"]["n_encuestas"] == 3
    assert por_casa["CIS"]["mae_pp"] is None
    assert por_casa["CIS"]["mae_valido_pp"] is None
    assert por_casa["CIS"]["mae_censo_pp"] == pytest.approx(0.0)
    assert por_casa["CIS"]["base"] == "censo"

    # una encuesta sobre 2026 no se cruza (no hay resultado oficial)
    assert por_casa["Futura"]["n_encuestas"] == 0
    # una encuesta con un solo partido publicable no da MAE
    assert por_casa["Truncada"]["n_encuestas"] == 0


def test_casas_json_real_separa_cis_y_respeta_n():
    ruta = os.path.join(RAIZ, "web", "src", "data", "casas.json")
    if not os.path.exists(ruta):
        pytest.skip("falta web/src/data/casas.json (ejecuta sync-data.py)")
    with open(ruta, encoding="utf-8") as fh:
        datos = json.load(fh)
    casas = datos["casas"]
    assert {c["casa"] for c in casas} >= {"CIS", "GAD3"}
    for c in casas:
        if c["mae_pp"] is not None:
            assert c["n_encuestas"] >= datos["meta"]["min_encuestas"]
            assert c["base"] == "valido"
            assert c["mae_censo_pp"] is None
        if c["mae_censo_pp"] is not None:
            assert c["mae_pp"] is None, "CIS no puede aparecer en la columna de privados"
            assert c["base"] == "censo"
        assert set(c) == {"casa", "n_encuestas", "elecciones_cubiertas", "mae_pp",
                          "mae_por_partido", "base", "mae_valido_pp", "mae_censo_pp"}


# --------------------------------------------------------------------------- #
# (e) dhondt() sigue reproduciendo los escaños oficiales de las 16 generales
# --------------------------------------------------------------------------- #
def test_dhondt_reproduce_escanos_oficiales():
    with open(C.DATA / "interior" / "elections.json", encoding="utf-8") as fh:
        elecciones = json.load(fh)["elecciones"]
    with open(C.DATA / "interior" / "results_provincial.jsonl", encoding="utf-8") as fh:
        filas = [json.loads(linea) for linea in fh if linea.strip()]

    por_eleccion: dict[str, list[dict]] = {}
    for fila in filas:
        por_eleccion.setdefault(fila["eleccion"], []).append(fila)

    comprobadas = 0
    discrepancias: set[tuple[str, str]] = set()
    for el in elecciones:
        provincias = {str(p["codigo"]): p for p in el["provincias"]}
        votos: dict[str, dict[str, int]] = {}
        oficial: dict[str, dict[str, int]] = {}
        for fila in por_eleccion.get(el["id"], []):
            code = str(fila["provincia"])
            votos.setdefault(code, {})[fila["partido_id"]] = fila["votos"]
            if fila["escanos"]:
                oficial.setdefault(code, {})[fila["partido_id"]] = fila["escanos"]
        for code, p in provincias.items():
            votos_prov = votos.get(code, {})
            validos = sum(votos_prov.values()) + p.get("votos_blancos", 0)
            calc = {c: s for c, s in dhondt(
                votos_prov, p["escanos"], 0.03, validos).items() if s}
            if calc != oficial.get(code, {}):
                discrepancias.add((el["id"], code))
            comprobadas += 1
    # El único desacuerdo es un caso conocido de la fuente de 1977 (Santa Cruz
    # de Tenerife: el 7.º cociente de AP supera al 2.º del PSOE y el escrutinio
    # publicado da el escaño al PSOE). Ya estaba documentado como
    # `b_dhondt_ok: false` en data/processed/interior/validation.json: este
    # test no lo introduce, lo fija para que no empeore.
    assert discrepancias == {("1977-06-15", "38")}, discrepancias
    assert comprobadas >= 16 * 50, f"solo {comprobadas} provincias comprobadas"
    with open(C.DATA / "interior" / "validation.json", encoding="utf-8") as fh:
        validaciones = json.load(fh)["validaciones"]
    fallos_validacion = {(v["id"], code) for v in validaciones
                         for code, d in v["provincias"].items() if not d["ok"]}
    assert fallos_validacion == discrepancias
