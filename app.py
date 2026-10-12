"""CP3 — iniciar com: streamlit run app.py"""

import json
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st
from engine import (
    load_datasets,
    monthly_load,
    solar_size,
    list_configurations,
    compatible_battery,
    battery_sizing,
    price_for,
    build_scenario,
    compare_scenarios,
    export_text,
)
from storage import read_db, save_db, find

ROOT = Path(__file__).resolve().parent
DB = ROOT / "dados" / "projetos.json"
st.set_page_config(page_title="Dimensionamento energético — CP3", layout="wide")
st.title("Sistema de Dimensionamento Energético Residencial")
st.caption(
    "CP3 · pré-dimensionamento acadêmico; não substitui projeto elétrico executivo ou cotação comercial definitiva."
)
try:
    datasets = load_datasets(ROOT)
    db = read_db(DB)
except Exception as exc:
    st.error(f"Falha de carregamento: {exc}")
    st.stop()


def store():
    save_db(DB, db)


def fmt(r):
    return f"{r['codigo']} — {r.get('nome','')}"


def res_select():
    if not db["residencias"]:
        st.warning("Cadastre ao menos uma residência e suas cargas para prosseguir.")
        return None
    code = st.selectbox(
        "Residência",
        options=[x["codigo"] for x in db["residencias"]],
        format_func=lambda c: fmt(find(db["residencias"], c)),
    )
    return find(db["residencias"], code)


def reload():
    store()
    st.rerun()


def rowid(df):
    return df.set_index("id", drop=False)


tab = st.sidebar.radio(
    "Navegação",
    [
        "Clientes e residências",
        "Equipamentos e consumo",
        "Dimensionamento FV",
        "Comparadores e simulações",
        "Datasets e cotações",
        "Histórico e exportação",
    ],
)
if tab == "Clientes e residências":
    st.subheader("Clientes")
    with st.form("cliente"):
        co = st.text_input("Código do cliente")
        nm = st.text_input("Nome do cliente")
        email = st.text_input("E-mail (opcional)")
        submit = st.form_submit_button("Cadastrar cliente")
    if submit:
        if not co.strip() or not nm.strip():
            st.error("Código e nome obrigatórios.")
        elif find(db["clientes"], co):
            st.error("Código de cliente repetido.")
        else:
            db["clientes"].append(
                {"codigo": co.strip(), "nome": nm.strip(), "email": email.strip()}
            )
            reload()
    if db["clientes"]:
        st.dataframe(
            pd.DataFrame(db["clientes"]), hide_index=True, use_container_width=True
        )
        with st.expander("Editar/excluir cliente"):
            chosen = st.selectbox(
                "Cliente para edição", [x["codigo"] for x in db["clientes"]]
            )
            client = find(db["clientes"], chosen)
            new_name = st.text_input("Novo nome", value=client["nome"])
            new_email = st.text_input("Novo e-mail", value=client.get("email", ""))
            a, b = st.columns(2)
            if a.button("Salvar dados do cliente"):
                if new_name.strip():
                    client.update(nome=new_name.strip(), email=new_email.strip())
                    reload()
                else:
                    st.error("Nome obrigatório.")
            if b.button("Excluir cliente"):
                if any(x.get("cliente_codigo") == chosen for x in db["residencias"]):
                    st.error("Cliente possui residência vinculada.")
                else:
                    db["clientes"].remove(client)
                    reload()
    st.subheader("Residências")
    with st.form("residencia"):
        code = st.text_input("Código único da residência")
        name = st.text_input("Nome da residência")
        addr = st.text_input("Endereço ou localização")
        client_id = st.selectbox(
            "Cliente responsável",
            (
                [c["codigo"] for c in db["clientes"]]
                if db["clientes"]
                else ["SEM CLIENTE"]
            ),
        )
        add = st.form_submit_button("Cadastrar residência")
    if add:
        if not code.strip() or not name.strip() or not addr.strip():
            st.error("Código, nome e localização obrigatórios.")
        elif find(db["residencias"], code):
            st.error("Código já cadastrado.")
        else:
            db["residencias"].append(
                {
                    "codigo": code.strip(),
                    "nome": name.strip(),
                    "endereco": addr.strip(),
                    "cliente_codigo": client_id,
                    "equipamentos": [],
                    "historico_consumo": [],
                }
            )
            reload()
    if db["residencias"]:
        res = res_select()
        with st.expander("Editar/excluir residência"):
            nam = st.text_input("Nome atualizado", value=res["nome"])
            adr = st.text_input("Endereço atualizado", value=res["endereco"])
            a, b = st.columns(2)
            if a.button("Atualizar residência"):
                if nam.strip() and adr.strip():
                    res.update(nome=nam.strip(), endereco=adr.strip())
                    reload()
                else:
                    st.error("Campos obrigatórios.")
            if b.button("Excluir residência"):
                if any(
                    p.get("residencia_codigo") == res["codigo"] for p in db["propostas"]
                ):
                    st.error(
                        "Há propostas vinculadas a essa residência; não é possível excluir sem tratar o histórico."
                    )
                else:
                    db["residencias"].remove(res)
                    reload()
elif tab == "Equipamentos e consumo":
    st.subheader("Catálogo residencial de equipamentos")
    st.dataframe(
        pd.DataFrame(db["equipamentos_catalogo"]),
        hide_index=True,
        use_container_width=True,
    )
    with st.form("cat"):
        code = st.text_input("ID equipamento")
        name = st.text_input("Nome")
        cat = st.text_input("Categoria")
        p = st.number_input("Potência nominal (W)", min_value=0.1, value=100.0)
        add = st.form_submit_button("Cadastrar equipamento no catálogo")
    if add:
        if not code.strip() or not name.strip() or not cat.strip():
            st.error("Todos os campos são obrigatórios.")
        elif any(x["id"] == code for x in db["equipamentos_catalogo"]):
            st.error("ID já utilizado.")
        else:
            db["equipamentos_catalogo"].append(
                {"id": code, "nome": name, "categoria": cat, "potencia_w": p}
            )
            reload()
    if db["equipamentos_catalogo"]:
        with st.expander("Editar ou excluir equipamento do catálogo"):
            eqid = st.selectbox(
                "Equipamento a alterar", [x["id"] for x in db["equipamentos_catalogo"]]
            )
            eq = next(x for x in db["equipamentos_catalogo"] if x["id"] == eqid)
            newp = st.number_input(
                "Nova potência (W)",
                min_value=0.1,
                value=float(eq["potencia_w"]),
                key="editp",
            )
            aa, bb = st.columns(2)
            if aa.button("Atualizar potência no catálogo"):
                eq["potencia_w"] = newp
                reload()
            if bb.button("Excluir do catálogo"):
                if any(
                    e.get("catalogo_id") == eqid
                    for r in db["residencias"]
                    for e in r["equipamentos"]
                ):
                    st.error("Equipamento está vinculado a uma residência.")
                else:
                    db["equipamentos_catalogo"].remove(eq)
                    reload()
    res = res_select()
    if res:
        with st.form("carga"):
            idx = st.selectbox(
                "Adicionar equipamento",
                [x["id"] for x in db["equipamentos_catalogo"]],
                format_func=lambda c: next(
                    x["nome"] for x in db["equipamentos_catalogo"] if x["id"] == c
                ),
            )
            q = st.number_input("Quantidade", min_value=1, step=1, value=1)
            h = st.number_input(
                "Horas de uso diário", min_value=0.1, max_value=24.0, value=4.0
            )
            add = st.form_submit_button("Adicionar ao imóvel")
        if add:
            eq = next(x for x in db["equipamentos_catalogo"] if x["id"] == idx)
            res["equipamentos"].append(
                {
                    "catalogo_id": idx,
                    "nome": eq["nome"],
                    "potencia_w": eq["potencia_w"],
                    "quantidade": int(q),
                    "horas_dia": h,
                }
            )
            reload()
        if res["equipamentos"]:
            info = monthly_load(res["equipamentos"])
            st.dataframe(
                pd.DataFrame(info["itens"]), hide_index=True, use_container_width=True
            )
            a, b, c = st.columns(3)
            a.metric("Potência de cargas (W)", f"{info['potencia_cargas_w']:.1f}")
            b.metric("Consumo diário (kWh)", f"{info['consumo_dia_kwh']:.2f}")
            c.metric("Consumo mensal (kWh)", f"{info['consumo_mes_kwh']:.2f}")
            if st.button("Registrar consumo no histórico"):
                res.setdefault("historico_consumo", []).append(
                    {
                        "data": datetime.now().isoformat(timespec="seconds"),
                        "consumo_mes_kwh": info["consumo_mes_kwh"],
                    }
                )
                reload()
            remove = st.selectbox(
                "Remover carga",
                range(len(res["equipamentos"])),
                format_func=lambda i: f"{i+1} — {res['equipamentos'][i]['nome']}",
            )
            if st.button("Excluir carga selecionada"):
                res["equipamentos"].pop(remove)
                reload()
        else:
            st.info("Cadastre cargas para calcular o consumo.")
        st.write("Histórico de consumo")
        st.dataframe(
            pd.DataFrame(res.get("historico_consumo", [])),
            hide_index=True,
            use_container_width=True,
        )
elif tab == "Datasets e cotações":
    st.info(
        "Valores pendentes nos CSVs não são inventados. Uma cotação manual precisa de valor e fonte e fica salva para orçamento."
    )
    for label, key in [
        ("Módulos", "modulos"),
        ("Inversores", "inversores"),
        ("Baterias", "baterias"),
    ]:
        with st.expander(label, expanded=label == "Módulos"):
            st.dataframe(datasets[key], hide_index=True, use_container_width=True)
    combined = pd.concat(
        [
            datasets[x][["id", "fabricante", "modelo", "preco_brl", "fornecedor"]]
            for x in ("modulos", "inversores", "baterias")
        ],
        ignore_index=True,
    )
    ident = st.selectbox("Equipamento para registrar cotação", combined["id"].tolist())
    row = combined.loc[combined["id"] == ident].iloc[0]
    st.write(row[["fabricante", "modelo", "fornecedor"]].to_dict())
    with st.form("quote"):
        price = st.number_input(
            "Preço unitário de cotação (R$)", min_value=0.01, value=1000.0
        )
        source = st.text_input("URL ou identificação verificável do fornecedor")
        submit = st.form_submit_button("Salvar cotação")
    if submit:
        if not source.strip():
            st.error("A cotação exige fonte identificada.")
        else:
            db["cotacoes"][ident] = {
                "preco_brl": price,
                "fonte": source.strip(),
                "data": str(datetime.now().date()),
            }
            reload()
    st.write("Cotações registradas:")
    st.json(db["cotacoes"])
elif tab == "Histórico e exportação":
    if not db["propostas"]:
        st.info("Nenhuma proposta salva.")
    else:
        for i, p in enumerate(db["propostas"]):
            with st.expander(f"{p['data']} — {p['residencia_codigo']}"):
                st.dataframe(
                    pd.DataFrame(compare_scenarios(*(p["cenarios"] + [None])[:2])),
                    hide_index=True,
                    use_container_width=True,
                )
                st.download_button(
                    "Exportar TXT",
                    export_text(p),
                    f"proposta_{i+1}.txt",
                    key=f"hist{i}",
                )
                st.download_button(
                    "Exportar JSON",
                    json.dumps(p, ensure_ascii=False, indent=2),
                    f"proposta_{i+1}.json",
                    key=f"json{i}",
                )
elif tab == "Dimensionamento FV":
    res = res_select()
    if res is None:
        st.stop()
    try:
        consume = monthly_load(res["equipamentos"])
    except (KeyError, ValueError) as e:
        st.error(f"Dados das cargas inválidos: {e}")
        st.stop()
    if consume["consumo_mes_kwh"] <= 0:
        st.warning("Cadastre os equipamentos da residência primeiro.")
        st.stop()
    st.write(
        f"Consumo: **{consume['consumo_mes_kwh']:.2f} kWh/mês** | **{consume['consumo_dia_kwh']:.2f} kWh/dia** | Cargas: **{consume['potencia_cargas_w']:.1f} W**"
    )
    local = st.text_input("Localização", value=res["endereco"])
    source = st.text_input("Fonte das HSP (obrigatória)")
    hsp = st.number_input("HSP (h/dia)", min_value=0.1, max_value=12.0, value=5.0)
    pr = st.number_input(
        "PR (desempenho)", min_value=0.01, max_value=1.0, value=0.80, step=0.01
    )
    explanation = st.text_area(
        "Justificativa do PR",
        value="PR=0,80: hipótese didática para perdas elétricas e operacionais; verificar no projeto real.",
    )
    coverage = st.slider(
        "Percentual pretendido (%)", min_value=1, max_value=100, value=80
    )
    tariff = st.number_input("Tarifa (R$/kWh)", min_value=0.01, value=0.90)
    extras = st.number_input(
        "Materiais, instalação e outros custos (R$)", min_value=0.0, value=0.0
    )
    if not source.strip() or not explanation.strip():
        st.warning("Informe a fonte HSP e a justificativa do PR para calcular.")
        st.stop()
    dim = solar_size(consume["consumo_mes_kwh"], coverage, hsp, pr)
    st.write(
        f"Alvo: **{dim['energia_fv_alvo_kwh']:.2f} kWh/mês**; potência necessária: **{dim['potencia_necessaria_kwp']:.3f} kWp**"
    )
    configs = list_configurations(
        dim, datasets["modulos"], datasets["inversores"], db["cotacoes"]
    )
    if not configs:
        st.error(
            "Nenhuma combinação com preço documentado e verificação elétrica básica válida. Registre cotações de módulos/inversores pendentes na aba Datasets."
        )
        st.stop()
    st.caption(
        "Recomendação preliminar: menor custo dentre as configurações com valores/fonte e verificações básicas válidas."
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    k: v
                    for k, v in c.items()
                    if k
                    in (
                        "painel_id",
                        "inversor_id",
                        "quantidade_modulos",
                        "potencia_instalada_kwp",
                        "razao_dc_ac",
                        "geracao_mes_kwh",
                        "subtotal_equipamentos_brl",
                    )
                }
                for c in configs[:50]
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )
    choice = st.selectbox(
        "Escolha do arranjo",
        range(len(configs)),
        format_func=lambda i: f"{configs[i]['painel_id']} × {configs[i]['quantidade_modulos']} + {configs[i]['inversor_id']} — R$ {configs[i]['subtotal_equipamentos_brl']:.2f}",
    )
    config = configs[choice]
    st.write("Layout elétrico básico:", config["layout"])
    without = build_scenario(dim, config, tariff, extras)
    with_battery = None
    if st.checkbox("Dimensionar e comparar com baterias"):
        inv = datasets["inversores"].set_index("id").loc[config["inversor_id"]]
        eligible = datasets["baterias"][
            datasets["baterias"].apply(lambda b: compatible_battery(inv, b), axis=1)
        ]
        if eligible.empty:
            st.warning(
                "Nenhuma bateria com par preliminar de compatibilidade aprovado para este inversor. Considere selecionar um inversor GoodWe ET compatível, conforme documentação."
            )
        else:
            bid = st.selectbox(
                "Bateria",
                eligible["id"].tolist(),
                format_func=lambda i: f"{i} — {eligible.set_index('id').loc[i,'modelo']}",
            )
            hours = st.number_input(
                "Autonomia (h)", min_value=1.0, max_value=24.0, value=12.0
            )
            battery = eligible.set_index("id").loc[bid]
            try:
                p, psource = price_for(battery, db["cotacoes"])
                b = battery_sizing(consume["consumo_mes_kwh"], hours, battery, p)
                with_battery = build_scenario(dim, config, tariff, extras, b, psource)
            except ValueError as e:
                st.warning(str(e) + " Registre cotação na aba Datasets.")
    scenarios = [without] + ([with_battery] if with_battery else [])
    st.subheader("Resultado e comparação dos cenários")
    st.dataframe(
        pd.DataFrame(compare_scenarios(without, with_battery)),
        hide_index=True,
        use_container_width=True,
    )
    for sc in scenarios:
        with st.expander(sc["titulo"] + " — orçamento discriminado", expanded=True):
            st.dataframe(
                pd.DataFrame(sc["itens_orcamento"]),
                hide_index=True,
                use_container_width=True,
            )
            st.write(
                f"**Investimento: R$ {sc['investimento_total_brl']:.2f}** | Economia: R$ {sc['economia_mensal_brl']:.2f}/mês, R$ {sc['economia_anual_brl']:.2f}/ano"
            )
            st.write(
                f"Payback simples: {sc['payback_simples_anos']:.2f} anos"
                if sc["payback_simples_anos"] is not None
                else "Payback indisponível"
            )
    st.warning(
        "Pré-dimensionamento acadêmico: verificar Voc a frio, Isc por entrada, MPPT, topologia, BMS/firmware, equipamentos auxiliares, sombreamento e requisitos da concessionária antes de qualquer instalação. A economia é simplificada."
    )
    proposal = {
        "data": datetime.now().isoformat(timespec="seconds"),
        "residencia_codigo": res["codigo"],
        "residencia": {
            "codigo": res["codigo"],
            "nome": res["nome"],
            "endereco": res["endereco"],
            "cliente_codigo": res["cliente_codigo"],
        },
        "consumo": consume,
        "dados_solares": {
            "hsp": hsp,
            "fonte_hsp": source,
            "pr": pr,
            "justificativa_pr": explanation,
            "cobertura_pct": coverage,
            "localizacao": local,
        },
        "cenarios": scenarios,
    }
    st.download_button(
        "Exportar proposta em TXT",
        export_text(proposal),
        "proposta_cp3.txt",
        mime="text/plain",
    )
    st.download_button(
        "Exportar proposta em JSON",
        json.dumps(proposal, ensure_ascii=False, indent=2),
        "proposta_cp3.json",
        mime="application/json",
    )
    if st.button("Salvar dimensionamento e proposta"):
        db["propostas"].append(proposal)
        reload()
    if st.button("Registrar consumo atual no histórico"):
        res.setdefault("historico_consumo", []).append(
            {
                "data": datetime.now().isoformat(timespec="seconds"),
                "consumo_mes_kwh": consume["consumo_mes_kwh"],
            }
        )
        reload()
if tab == "Comparadores e simulações":
    st.divider()
    st.subheader("Comparadores e simulações US21–US26")
    st.info(
        "Use a aba Dimensionamento FV para selecionar e comparar conjuntos módulo/inversor completos. Abaixo, simule mudanças de HSP e atendimento mantendo uma residência e listando opções viáveis."
    )
    res = res_select()
    if res and res["equipamentos"]:
        consume = monthly_load(res["equipamentos"])["consumo_mes_kwh"]
        cover = st.multiselect(
            "Cobertura (%)", [20, 40, 60, 80, 100], default=[60, 80, 100]
        )
        hsp_list = st.multiselect(
            "HSP", [3.0, 4.0, 4.5, 5.0, 5.5, 6.0], default=[4.0, 5.0]
        )
        pr = st.number_input("PR simulação", min_value=0.01, max_value=1.0, value=0.8)
        rows = []
        for c in cover:
            for h in hsp_list:
                d = solar_size(consume, c, h, pr)
                choices = list_configurations(
                    d, datasets["modulos"], datasets["inversores"], db["cotacoes"]
                )
                rows.append(
                    {
                        "cobertura_pct": c,
                        "hsp": h,
                        "potencia_necessaria_kwp": d["potencia_necessaria_kwp"],
                        "melhor_painel": (
                            choices[0]["painel_id"] if choices else "sem opção"
                        ),
                        "modulos": (
                            choices[0]["quantidade_modulos"] if choices else None
                        ),
                        "potencia_instalada_kwp": (
                            choices[0]["potencia_instalada_kwp"] if choices else None
                        ),
                        "geracao_mes_kwh": (
                            choices[0]["geracao_mes_kwh"] if choices else None
                        ),
                        "custo_brl": (
                            choices[0]["subtotal_equipamentos_brl"] if choices else None
                        ),
                    }
                )
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
