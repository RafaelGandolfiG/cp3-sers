import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import *
from storage import *

ROOT = Path(__file__).resolve().parents[1]


def test_datasets_and_minimums():
    d = load_datasets(ROOT)
    assert (
        len(d["modulos"]) >= 10
        and len(d["inversores"]) >= 8
        and len(d["baterias"]) >= 6
    )
    assert all(x in d for x in ("modulos", "inversores", "baterias"))


def test_consumption_and_sizing():
    consumption = monthly_load(
        [
            {"nome": "TV", "potencia_w": 100, "quantidade": 1, "horas_dia": 5},
            {"nome": "Geladeira", "potencia_w": 200, "quantidade": 1, "horas_dia": 10},
            {"nome": "Ventilador", "potencia_w": 80, "quantidade": 2, "horas_dia": 6},
        ]
    )
    assert consumption["consumo_mes_kwh"] == pytest.approx(103.8)
    d = solar_size(600, 80, 5, 0.8)
    assert d["potencia_necessaria_kwp"] == pytest.approx(4.0)


def test_actual_dataset_configurations_with_quotes():
    d = load_datasets(ROOT)
    quotes = {
        row["id"]: {
            "preco_brl": 10000,
            "fonte": "Cotação de teste (não usar comercialmente)",
        }
        for _, row in d["inversores"].iterrows()
    }
    quotes.update(
        {
            row["id"]: {
                "preco_brl": 15000,
                "fonte": "Cotação de teste (não usar comercialmente)",
            }
            for _, row in d["baterias"].iterrows()
        }
    )
    cfgs = list_configurations(
        solar_size(600, 80, 5, 0.8), d["modulos"], d["inversores"], quotes
    )
    assert cfgs
    c = cfgs[0]
    assert c["energia_compensada_mes_kwh"] <= 600
    s = build_scenario(solar_size(600, 80, 5, 0.8), c, 0.90, 3000)
    assert s["payback_simples_anos"] > 0


def test_with_and_without_batteries():
    d = load_datasets(ROOT)
    quotes = {
        row["id"]: {"preco_brl": 10000, "fonte": "Cotação de teste não comercial"}
        for _, row in d["inversores"].iterrows()
    }
    quotes.update(
        {
            row["id"]: {"preco_brl": 15000, "fonte": "Cotação de teste não comercial"}
            for _, row in d["baterias"].iterrows()
        }
    )
    dim = solar_size(600, 80, 5, 0.8)
    options = list_configurations(dim, d["modulos"], d["inversores"], quotes)
    pair = None
    for opt in options:
        inv = d["inversores"].set_index("id").loc[opt["inversor_id"]]
        for _, bat in d["baterias"].iterrows():
            if compatible_battery(inv, bat):
                pair = (opt, bat)
                break
        if pair:
            break
    assert pair is not None
    opt, bat = pair
    pr, source = price_for(bat, quotes)
    b = battery_sizing(600, 12, bat, pr)
    no = build_scenario(dim, opt, 0.9, 2500)
    yes = build_scenario(dim, opt, 0.9, 2500, b, source)
    assert yes["investimento_total_brl"] > no["investimento_total_brl"]
    assert len(compare_scenarios(no, yes)) == 2
    prop = {
        "residencia": {"nome": "Teste", "codigo": "1"},
        "consumo": {"consumo_mes_kwh": 600},
        "dados_solares": {
            "hsp": 5,
            "fonte_hsp": "exemplo",
            "pr": 0.8,
            "cobertura_pct": 80,
        },
        "cenarios": [no, yes],
    }
    assert "Payback simples" in export_text(prop)


def test_reject_invalid_data():
    with pytest.raises(ValueError):
        solar_size(500, 0, 5, 0.8)
    with pytest.raises(ValueError):
        monthly_load(
            [{"nome": "x", "potencia_w": 100, "quantidade": 1, "horas_dia": 25}]
        )
    with pytest.raises(ValueError):
        battery_sizing(500, 25, {"dod_pct": 90, "capacidade_kwh": 5}, 5000)


def test_storage(tmp_path):
    path = tmp_path / "store.json"
    d = read_db(path)
    d["clientes"].append({"codigo": "C1", "nome": "Teste"})
    save_db(path, d)
    assert find(read_db(path)["clientes"], "C1")["nome"] == "Teste"
