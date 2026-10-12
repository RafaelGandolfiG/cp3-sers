"""Motor de pré-dimensionamento acadêmico; funções puras e testáveis."""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
import math
import pandas as pd

DAYS = 30
BATTERY_EFFICIENCY = 0.95
REQUIRED = {
    "modulos.csv": {
        "id",
        "fabricante",
        "modelo",
        "potencia_wp",
        "voc_v",
        "isc_a",
        "vmp_v",
        "imp_a",
        "eficiencia_pct",
        "preco_brl",
        "fornecedor",
        "data_coleta",
        "url_fonte",
    },
    "inversores.csv": {
        "id",
        "fabricante",
        "modelo",
        "tipo",
        "potencia_nominal_w",
        "potencia_max_fv_w",
        "tensao_max_entrada_v",
        "faixa_mppt_min_v",
        "faixa_mppt_max_v",
        "corrente_max_entrada_a",
        "numero_mppt",
        "compativel_bateria",
        "preco_brl",
        "fornecedor",
        "data_coleta",
        "url_fonte",
    },
    "baterias.csv": {
        "id",
        "fabricante",
        "modelo",
        "tecnologia",
        "tensao_nominal_v",
        "capacidade_ah",
        "capacidade_kwh",
        "dod_pct",
        "ciclos",
        "preco_brl",
        "fornecedor",
        "data_coleta",
        "url_fonte",
    },
}


def positive(value, label):
    try:
        v = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{label} precisa ser numérico.")
    if not math.isfinite(v) or v <= 0:
        raise ValueError(f"{label} precisa ser positivo e finito.")
    return v


def load_datasets(folder):
    out = {}
    for name, fields in REQUIRED.items():
        df = pd.read_csv(Path(folder) / name, dtype={"id": str})
        absent = fields - set(df.columns)
        if absent:
            raise ValueError(f"{name}: faltam colunas {sorted(absent)}")
        if df["id"].duplicated().any():
            raise ValueError(f"{name}: IDs repetidos.")
        out[name.replace(".csv", "")] = df
    return out


def verified_price(row):
    supplier = str(row.get("fornecedor", "")).strip().upper()
    url = str(row.get("url_fonte", "")).strip()
    try:
        val = float(row["preco_brl"])
    except (TypeError, ValueError):
        return None
    if (
        not math.isfinite(val)
        or val <= 0
        or supplier in ("", "PENDENTE", "VALOR_ESTIMADO", "NAN")
        or not url.startswith("https://")
    ):
        return None
    return val


def price_for(row, quotations=None):
    p = verified_price(row)
    if p is not None:
        return p, {
            "tipo": "dataset",
            "fornecedor": str(row["fornecedor"]),
            "fonte": str(row["url_fonte"]),
            "data": str(row["data_coleta"]),
        }
    q = (quotations or {}).get(str(row["id"]))
    if q and str(q.get("fonte", "")).strip():
        return positive(q["preco_brl"], "Cotação"), {
            "tipo": "cotação informada",
            "fornecedor": q["fonte"],
            "fonte": q["fonte"],
            "data": str(datetime.now().date()),
        }
    raise ValueError(
        f"Preço de {row['id']} sem cotação rastreável. Informe fonte e valor antes de orçar."
    )


def monthly_load(items):
    total_w = 0.0
    total_kwh = 0.0
    detail = []
    for e in items:
        p = positive(e["potencia_w"], "Potência")
        q = int(positive(e["quantidade"], "Quantidade"))
        h = positive(e["horas_dia"], "Horas/dia")
        if q != float(e["quantidade"]) or h > 24:
            raise ValueError("Quantidade inteira e horas/dia até 24.")
        kwh = p * q * h * DAYS / 1000
        detail.append(
            {
                "equipamento": e["nome"],
                "potencia_w": p,
                "quantidade": q,
                "horas_dia": h,
                "consumo_mes_kwh": kwh,
            }
        )
        total_w += p * q
        total_kwh += kwh
    return {
        "potencia_cargas_w": total_w,
        "consumo_mes_kwh": total_kwh,
        "consumo_dia_kwh": total_kwh / DAYS,
        "itens": detail,
    }


def solar_size(consumption, coverage_pct, hsp, pr):
    c = positive(consumption, "Consumo")
    hs = positive(hsp, "HSP")
    efficiency = positive(pr, "PR")
    pct = positive(coverage_pct, "Atendimento")
    if not (0 < pct <= 100 and 0 < efficiency <= 1 and hs <= 24):
        raise ValueError("Cobertura 0–100%, PR 0–1, HSP até 24.")
    target = c * pct / 100
    return {
        "consumo_mes_kwh": c,
        "consumo_dia_kwh": c / DAYS,
        "percentual_solicitado": pct,
        "energia_fv_alvo_kwh": target,
        "potencia_necessaria_kwp": target / (hs * DAYS * efficiency),
        "hsp": hs,
        "pr": efficiency,
    }


def panel_valid(row):
    try:
        p, voc, vmp, isc, imp = (
            positive(row[k], k)
            for k in ["potencia_wp", "voc_v", "vmp_v", "isc_a", "imp_a"]
        )
        return (
            voc > vmp
            and isc >= imp
            and 0 < positive(row["eficiencia_pct"], "eficiência") <= 100
        )
    except (ValueError, KeyError):
        return False


def string_layouts(panel, inverter, count):
    if not panel_valid(panel):
        return []
    if count < 1:
        return []
    try:
        max_mppt = int(positive(inverter["numero_mppt"], "MPPT"))
        max_dc = positive(inverter["potencia_max_fv_w"], "potência CC máxima")
        max_v = positive(inverter["tensao_max_entrada_v"], "tensão máxima")
        low = positive(inverter["faixa_mppt_min_v"], "MPPT mínimo")
        high = positive(inverter["faixa_mppt_max_v"], "MPPT máximo")
        max_i = positive(inverter["corrente_max_entrada_a"], "corrente máxima")
    except (ValueError, KeyError):
        return []
    if count * float(panel["potencia_wp"]) > max_dc or low > high:
        return []
    layouts = []
    for strings in range(1, min(count, max_mppt) + 1):
        if count % strings:
            continue
        per = count // strings
        vmp = per * float(panel["vmp_v"])
        voc = per * float(panel["voc_v"])
        current = float(panel["imp_a"])
        if voc <= max_v and low <= vmp <= high and current <= max_i:
            layouts.append(
                {
                    "numero_strings": strings,
                    "modulos_por_string": per,
                    "vmp_string_v": vmp,
                    "voc_string_v": voc,
                    "corrente_string_a": current,
                }
            )
    return layouts


def compatible_battery(inverter, battery):
    """Lista didática restrita; não certifica BMS/firmware nem instalação."""
    inv = str(inverter["modelo"]).upper()
    mod = str(battery["modelo"]).upper()
    if str(inverter["fabricante"]).upper() != "GOODWE" or "KN-ET" not in inv:
        return False
    if str(battery["fabricante"]).upper() != "BYD" or not (
        "HVS" in mod or "HVM" in mod
    ):
        return False
    try:
        return 180 <= float(battery["tensao_nominal_v"]) <= 600
    except (TypeError, ValueError):
        return False


def battery_sizing(consumption, hours, battery, price):
    h = positive(hours, "Autonomia")
    if h > 24:
        raise ValueError("Autonomia deve ser de 1 até 24 horas.")
    dod = positive(battery["dod_pct"], "DoD") / 100
    cap = positive(battery["capacidade_kwh"], "Capacidade da bateria")
    if dod > 1:
        raise ValueError("DoD não pode superar 100%.")
    energy = positive(consumption, "Consumo") / DAYS * h / 24
    nominal = energy / (dod * BATTERY_EFFICIENCY)
    count = math.ceil(nominal / cap)
    return {
        "id": str(battery["id"]),
        "fabricante": str(battery["fabricante"]),
        "modelo": str(battery["modelo"]),
        "autonomia_h": h,
        "energia_autonomia_kwh": energy,
        "capacidade_necessaria_kwh": nominal,
        "quantidade": count,
        "capacidade_instalada_kwh": count * cap,
        "capacidade_util_kwh": count * cap * dod * BATTERY_EFFICIENCY,
        "preco_unitario_brl": price,
        "subtotal_brl": count * price,
        "dod": dod,
        "eta_bateria": BATTERY_EFFICIENCY,
    }


def list_configurations(
    dim, modules, inverters, quotations=None, battery_required=False
):
    results = []
    for _, panel in modules.iterrows():
        if not panel_valid(panel):
            continue
        count = math.ceil(
            dim["potencia_necessaria_kwp"] * 1000 / float(panel["potencia_wp"])
        )
        if count < 1:
            continue
        try:
            mp, mp_source = price_for(panel, quotations)
        except ValueError:
            continue
        for _, inv in inverters.iterrows():
            if battery_required and str(inv["compativel_bateria"]).lower() not in (
                "true",
                "1",
                "sim",
            ):
                continue
            layout = string_layouts(panel, inv, count)
            if not layout:
                continue
            try:
                ip, ip_source = price_for(inv, quotations)
            except ValueError:
                continue
            installed = count * float(panel["potencia_wp"]) / 1000
            generation = installed * dim["hsp"] * dim["pr"] * DAYS
            nominal = positive(inv["potencia_nominal_w"], "Potência nominal") / 1000
            results.append(
                {
                    "painel_id": str(panel["id"]),
                    "painel_fabricante": str(panel["fabricante"]),
                    "painel_modelo": str(panel["modelo"]),
                    "painel_preco_brl": mp,
                    "painel_fonte": mp_source,
                    "quantidade_modulos": count,
                    "potencia_instalada_kwp": installed,
                    "inversor_id": str(inv["id"]),
                    "inversor_fabricante": str(inv["fabricante"]),
                    "inversor_modelo": str(inv["modelo"]),
                    "inversor_preco_brl": ip,
                    "inversor_fonte": ip_source,
                    "inversor_compativel_bateria": str(
                        inv["compativel_bateria"]
                    ).lower()
                    in ("true", "1", "sim"),
                    "layout": layout[0],
                    "razao_dc_ac": installed / nominal,
                    "geracao_dia_kwh": generation / DAYS,
                    "geracao_mes_kwh": generation,
                    "atendimento_gerado_pct": generation / dim["consumo_mes_kwh"] * 100,
                    "energia_compensada_mes_kwh": min(
                        generation, dim["consumo_mes_kwh"]
                    ),
                    "subtotal_modulos_brl": count * mp,
                    "subtotal_inversor_brl": ip,
                    "subtotal_equipamentos_brl": count * mp + ip,
                }
            )
    return sorted(
        results,
        key=lambda x: (
            x["subtotal_equipamentos_brl"],
            x["painel_id"],
            x["inversor_id"],
        ),
    )


def build_scenario(dim, config, tariff, extra_cost, battery=None, battery_source=None):
    rate = positive(tariff, "Tarifa")
    other = float(extra_cost)
    if not math.isfinite(other) or other < 0:
        raise ValueError("Outros custos devem ser ≥ 0.")
    rows = [
        {
            "equipamento": f"Módulo {config['painel_modelo']}",
            "quantidade": config["quantidade_modulos"],
            "preco_unitario_brl": config["painel_preco_brl"],
            "subtotal_brl": config["subtotal_modulos_brl"],
            "fonte": config["painel_fonte"],
        },
        {
            "equipamento": f"Inversor {config['inversor_modelo']}",
            "quantidade": 1,
            "preco_unitario_brl": config["inversor_preco_brl"],
            "subtotal_brl": config["subtotal_inversor_brl"],
            "fonte": config["inversor_fonte"],
        },
    ]
    if battery:
        rows.append(
            {
                "equipamento": f"Bateria {battery['modelo']}",
                "quantidade": battery["quantidade"],
                "preco_unitario_brl": battery["preco_unitario_brl"],
                "subtotal_brl": battery["subtotal_brl"],
                "fonte": battery_source,
            }
        )
    if other:
        rows.append(
            {
                "equipamento": "Instalação e materiais diversos",
                "quantidade": 1,
                "preco_unitario_brl": other,
                "subtotal_brl": other,
                "fonte": {"tipo": "informado pelo usuário"},
            }
        )
    total = sum(row["subtotal_brl"] for row in rows)
    compensated = config["energia_compensada_mes_kwh"]
    month = compensated * rate
    year = month * 12
    return {
        "titulo": "Com baterias" if battery else "Sem baterias",
        "dimensionamento": dim,
        "configuracao": config,
        "bateria": battery,
        "itens_orcamento": rows,
        "investimento_total_brl": total,
        "tarifa_brl_kwh": rate,
        "energia_compensada_mes_kwh": compensated,
        "economia_mensal_brl": month,
        "economia_anual_brl": year,
        "payback_simples_anos": total / year if year > 0 else None,
        "premissas": "Economia acadêmica simplificada, sem impostos, encargos, créditos tarifários, degradação ou manutenção. Payback simples não é previsão financeira exata.",
    }


def compare_scenarios(a, b):
    return [
        {
            "cenario": x["titulo"],
            "potencia_instalada_kwp": x["configuracao"]["potencia_instalada_kwp"],
            "modulos": x["configuracao"]["quantidade_modulos"],
            "inversor": x["configuracao"]["inversor_modelo"],
            "geracao_kwh_mes": x["configuracao"]["geracao_mes_kwh"],
            "atendimento_pct": x["configuracao"]["atendimento_gerado_pct"],
            "baterias": x["bateria"]["quantidade"] if x["bateria"] else 0,
            "autonomia_h": x["bateria"]["autonomia_h"] if x["bateria"] else 0,
            "investimento_brl": x["investimento_total_brl"],
            "economia_brl_mes": x["economia_mensal_brl"],
            "payback_anos": x["payback_simples_anos"],
        }
        for x in [a, b]
        if x is not None
    ]


def export_text(proposal):
    r = proposal["residencia"]
    d = proposal["dados_solares"]
    s = proposal["cenarios"]
    out = [
        f"PROPOSTA FOTOVOLTAICA — PRÉ-DIMENSIONAMENTO ACADÊMICO",
        f"Residência: {r['nome']} ({r['codigo']}) — {r.get('endereco','')}",
        f"Consumo de referência: {proposal['consumo']['consumo_mes_kwh']:.2f} kWh/mês",
        f"HSP: {d['hsp']} h/dia | Fonte: {d['fonte_hsp']} | PR: {d['pr']:.2f}",
        f"Meta: {d['cobertura_pct']}%",
        "",
    ]
    for sc in s:
        c = sc["configuracao"]
        out.extend(
            [
                f"{sc['titulo']}",
                f"Potência necessária: {sc['dimensionamento']['potencia_necessaria_kwp']:.2f} kWp",
                f"Instalada: {c['potencia_instalada_kwp']:.2f} kWp",
                f"Módulos: {c['quantidade_modulos']} × {c['painel_fabricante']} {c['painel_modelo']}",
                f"Inversor: {c['inversor_fabricante']} {c['inversor_modelo']}",
                f"Geração: {c['geracao_dia_kwh']:.2f} kWh/dia e {c['geracao_mes_kwh']:.2f} kWh/mês",
                f"Atendimento: {c['atendimento_gerado_pct']:.1f}% | Compensada: {sc['energia_compensada_mes_kwh']:.2f} kWh/mês",
                f"Autonomia: {sc['bateria']['autonomia_h'] if sc['bateria'] else 0} h",
                "ORÇAMENTO",
            ]
        )
        for item in sc["itens_orcamento"]:
            out.append(
                f"- {item['equipamento']}: {item['quantidade']} × R$ {item['preco_unitario_brl']:.2f} = R$ {item['subtotal_brl']:.2f} | {item['fonte']}"
            )
        out.extend(
            [
                f"Investimento total: R$ {sc['investimento_total_brl']:.2f}",
                f"Economia mensal: R$ {sc['economia_mensal_brl']:.2f} | anual: R$ {sc['economia_anual_brl']:.2f}",
                (
                    f"Payback simples: {sc['payback_simples_anos']:.2f} anos"
                    if sc["payback_simples_anos"] is not None
                    else "Payback indisponível"
                ),
                sc["premissas"],
                "",
            ]
        )
    return "\n".join(out)
