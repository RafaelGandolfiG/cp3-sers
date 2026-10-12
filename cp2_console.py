import pandas as pd
import math
from datetime import datetime
from pathlib import Path

# ============================================================
# DATASETS FOTOVOLTAICOS
# ============================================================


def carregar_datasets():
    try:
        modulos = pd.read_csv(Path(__file__).resolve().parent / "modulos.csv")
        inversores = pd.read_csv(Path(__file__).resolve().parent / "inversores.csv")
        baterias = pd.read_csv(Path(__file__).resolve().parent / "baterias.csv")
        print("Datasets carregados com sucesso!")
        return modulos, inversores, baterias
    except FileNotFoundError:
        print("ERRO: algum CSV não foi encontrado.")
        print(
            "Deixe modulos.csv, inversores.csv e baterias.csv na mesma pasta do main.py."
        )
        return None, None, None


def preco_cotado(item):
    """Preço de dataset com origem documentada, ou cotação fornecida na sessão."""
    preco = pd.to_numeric(item.get("preco_brl"), errors="coerce")
    if (
        pd.notna(preco)
        and float(preco) > 0
        and str(item.get("fornecedor", "")).upper()
        not in ("PENDENTE", "VALOR_ESTIMADO")
    ):
        return float(preco)
    print(
        f"\nATENÇÃO: {item['fabricante']} {item['modelo']} não possui preço rastreável no CSV."
    )
    while True:
        entrada = input(
            "Valor unitário da cotação documentada (R$, ou ENTER para cancelar): "
        ).strip()
        if not entrada:
            return None
        try:
            valor = float(entrada.replace(",", "."))
            if not math.isfinite(valor) or valor <= 0:
                raise ValueError
        except ValueError:
            print("Valor inválido.")
            continue
        fonte = input("URL, fornecedor ou identificação da cotação: ").strip()
        if not fonte:
            print("Fonte obrigatória para essa cotação.")
            continue
        print("Cotação informada manualmente (não consta do dataset):", fonte)
        return valor


def verificar_modulo(modulo):
    try:
        p, voc, vmp, isc, imp = (
            float(modulo[k])
            for k in ("potencia_wp", "voc_v", "vmp_v", "isc_a", "imp_a")
        )
        return (
            all(math.isfinite(x) and x > 0 for x in (p, voc, vmp, isc, imp))
            and voc > vmp
            and isc >= imp
        )
    except (KeyError, TypeError, ValueError):
        return False


def configuracoes_strings(modulo, quantidade_total, inversor):
    """Só aceita strings de mesmo comprimento; uma por MPPT, sem paralelismo."""
    if not verificar_modulo(modulo):
        return []
    resultado = []
    mppts = int(inversor["numero_mppt"])
    for n_strings in range(1, min(mppts, quantidade_total) + 1):
        if quantidade_total % n_strings:
            continue
        n = quantidade_total // n_strings
        vmp = n * float(modulo["vmp_v"])
        voc = n * float(modulo["voc_v"])
        corrente = float(modulo["imp_a"])
        if (
            quantidade_total * float(modulo["potencia_wp"])
            <= float(inversor["potencia_max_fv_w"])
            and voc <= float(inversor["tensao_max_entrada_v"])
            and float(inversor["faixa_mppt_min_v"])
            <= vmp
            <= float(inversor["faixa_mppt_max_v"])
            and corrente <= float(inversor["corrente_max_entrada_a"])
        ):
            resultado.append(
                {
                    "numero_strings": n_strings,
                    "modulos_por_string": n,
                    "vmp_string": vmp,
                    "voc_string": voc,
                    "corrente_string": corrente,
                }
            )
    return resultado


def bateria_compativel(inversor, bateria):
    """Matriz restrita de pares respaldados por documentação de compatibilidade.

    GoodWe ET Plus 5-10kW pode usar BYD Battery-Box Premium HVS/HVM,
    sujeito a firmware/BMS mínimo e condições do fabricante. Outras combinações
    não serão consideradas comprovadas somente pela flag compativel_bateria.
    """
    inv = str(inversor["modelo"]).upper()
    mod = str(bateria["modelo"]).upper()
    if (
        str(inversor["fabricante"]).upper() == "GOODWE"
        and "KN-ET" in inv
        and str(bateria["fabricante"]).upper() == "BYD"
        and ("HVS" in mod or "HVM" in mod)
    ):
        v = float(bateria["tensao_nominal_v"])
        return 180 <= v <= 600
    return False


modulos, inversores, baterias = carregar_datasets()


# ============================================================
# DADOS DO SISTEMA
# ============================================================

clientes = []
imoveis = []

equipamentos = [
    {"id": 1, "nome": "Televisão", "categoria": "Eletrônico", "potencia": 100},
    {"id": 2, "nome": "Geladeira", "categoria": "Eletrodoméstico", "potencia": 200},
    {"id": 3, "nome": "Ventilador", "categoria": "Climatização", "potencia": 80},
    {"id": 4, "nome": "Micro-ondas", "categoria": "Eletrodoméstico", "potencia": 1200},
    {"id": 5, "nome": "Chuveiro", "categoria": "Aquecimento", "potencia": 5500},
]


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================


def linha():
    print("-" * 60)


def buscar_cliente(codigo):
    for cliente in clientes:
        if cliente["codigo"] == codigo:
            return cliente
    return None


def buscar_imovel(codigo):
    for imovel in imoveis:
        if imovel["codigo"] == codigo:
            return imovel
    return None


def buscar_equipamento(equipamento_id):
    for equipamento in equipamentos:
        if equipamento["id"] == equipamento_id:
            return equipamento
    return None


def calcular_consumo(potencia, quantidade, horas):
    return (potencia * quantidade * horas * 30) / 1000


def calcular_consumo_total(imovel):
    total = 0
    for equipamento in imovel["equipamentos"]:
        total += equipamento["consumo"]
    return total


def registrar_historico(imovel):
    imovel["historico"].append(
        {
            "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "consumo": calcular_consumo_total(imovel),
        }
    )


# ============================================================
# US01 - CADASTRAR CLIENTE
# ============================================================


def cadastrar_cliente():
    print("\nCADASTRAR CLIENTE")
    linha()

    codigo = input("Código do cliente (6 dígitos): ").strip()

    while len(codigo) != 6 or not codigo.isdigit():
        print("Código inválido!")
        codigo = input("Código do cliente (6 dígitos): ").strip()

    if buscar_cliente(codigo) is not None:
        print("Já existe um cliente com esse código.")
        return

    nome = input("Nome completo: ").strip()

    while nome == "":
        print("Nome obrigatório.")
        nome = input("Nome completo: ").strip()

    cep = input("CEP (8 dígitos): ").strip()

    while len(cep) != 8 or not cep.isdigit():
        print("CEP inválido!")
        cep = input("CEP (8 dígitos): ").strip()

    clientes.append({"codigo": codigo, "nome": nome, "cep": cep})

    print("Cliente cadastrado com sucesso!")


# ============================================================
# US02 - CONSULTAR CLIENTE
# ============================================================


def consultar_cliente():
    print("\nCONSULTAR CLIENTE")
    linha()

    if len(clientes) == 0:
        print("Nenhum cliente cadastrado.")
        return

    termo = input("Digite o código ou nome do cliente: ").strip().lower()
    encontrou = False

    for cliente in clientes:
        if termo == cliente["codigo"] or termo in cliente["nome"].lower():
            encontrou = True
            linha()
            print("Código:", cliente["codigo"])
            print("Nome:", cliente["nome"])
            print("CEP:", cliente["cep"])
            print("Imóveis associados:")

            possui_imovel = False

            for imovel in imoveis:
                if imovel["cliente_codigo"] == cliente["codigo"]:
                    possui_imovel = True
                    print("-", imovel["codigo"], "-", imovel["identificacao"])

            if not possui_imovel:
                print("Nenhum imóvel associado.")

    if not encontrou:
        print("Cliente não encontrado.")


# ============================================================
# US03 - EDITAR CLIENTE
# ============================================================


def editar_cliente():
    print("\nEDITAR CLIENTE")
    linha()

    codigo = input("Código do cliente: ").strip()
    cliente = buscar_cliente(codigo)

    if cliente is None:
        print("Cliente não encontrado.")
        return

    print("Pressione ENTER para manter o valor atual.")

    nome = input(f"Nome [{cliente['nome']}]: ").strip()
    cep = input(f"CEP [{cliente['cep']}]: ").strip()

    if nome != "":
        cliente["nome"] = nome

    if cep != "":
        while len(cep) != 8 or not cep.isdigit():
            print("CEP inválido!")
            cep = input("Novo CEP: ").strip()

        cliente["cep"] = cep

    print("Cliente atualizado com sucesso!")


# ============================================================
# US04 - EXCLUIR CLIENTE
# ============================================================


def excluir_cliente():
    print("\nEXCLUIR CLIENTE")
    linha()

    codigo = input("Código do cliente: ").strip()
    cliente = buscar_cliente(codigo)

    if cliente is None:
        print("Cliente não encontrado.")
        return

    for imovel in imoveis:
        if imovel["cliente_codigo"] == codigo:
            print("O cliente possui imóvel cadastrado. Exclua o imóvel antes.")
            return

    resposta = input(f"Deseja excluir {cliente['nome']}? (S/N): ").upper()

    if resposta == "S":
        clientes.remove(cliente)
        print("Cliente excluído!")
    else:
        print("Operação cancelada.")


# ============================================================
# US05 - CADASTRAR IMÓVEL
# ============================================================


def cadastrar_imovel():
    print("\nCADASTRAR IMÓVEL")
    linha()

    if len(clientes) == 0:
        print("Cadastre um cliente primeiro.")
        return

    cliente_codigo = input("Código do cliente responsável: ").strip()
    cliente = buscar_cliente(cliente_codigo)

    if cliente is None:
        print("Cliente não encontrado.")
        return

    codigo = input("Código do imóvel (6 dígitos): ").strip()

    while len(codigo) != 6 or not codigo.isdigit():
        print("Código inválido!")
        codigo = input("Código do imóvel (6 dígitos): ").strip()

    if buscar_imovel(codigo) is not None:
        print("Já existe um imóvel com esse código.")
        return

    identificacao = input("Identificação do imóvel (Casa, Apartamento etc.): ").strip()
    cep = input("CEP do imóvel (8 dígitos): ").strip()

    while len(cep) != 8 or not cep.isdigit():
        print("CEP inválido!")
        cep = input("CEP do imóvel: ").strip()

    imoveis.append(
        {
            "codigo": codigo,
            "cliente_codigo": cliente_codigo,
            "identificacao": identificacao,
            "cep": cep,
            "equipamentos": [],
            "historico": [],
        }
    )

    print("Imóvel cadastrado com sucesso!")


# ============================================================
# US06 - VISUALIZAR IMÓVEL
# ============================================================


def mostrar_imovel(imovel):
    cliente = buscar_cliente(imovel["cliente_codigo"])

    linha()
    print("Código:", imovel["codigo"])
    print("Identificação:", imovel["identificacao"])
    print("CEP:", imovel["cep"])

    if cliente is not None:
        print("Responsável:", cliente["nome"])

    print("\nEQUIPAMENTOS")

    if len(imovel["equipamentos"]) == 0:
        print("Nenhum equipamento.")
    else:
        for equipamento in imovel["equipamentos"]:
            linha()
            print("Nome:", equipamento["nome"])
            print("Potência:", equipamento["potencia"], "W")
            print("Quantidade:", equipamento["quantidade"])
            print("Horas/dia:", equipamento["horas"])
            print(f"Consumo: {equipamento['consumo']:.2f} kWh/mês")

    linha()
    print(f"CONSUMO TOTAL: {calcular_consumo_total(imovel):.2f} kWh/mês")


def visualizar_imovel():
    print("\nVISUALIZAR IMÓVEL")
    codigo = input("Código do imóvel: ").strip()
    imovel = buscar_imovel(codigo)

    if imovel is None:
        print("Imóvel não encontrado.")
        return

    mostrar_imovel(imovel)


# ============================================================
# US07 - EDITAR IMÓVEL
# ============================================================


def editar_imovel():
    print("\nEDITAR IMÓVEL")
    linha()

    codigo = input("Código do imóvel: ").strip()
    imovel = buscar_imovel(codigo)

    if imovel is None:
        print("Imóvel não encontrado.")
        return

    identificacao = input(f"Identificação [{imovel['identificacao']}]: ").strip()
    cep = input(f"CEP [{imovel['cep']}]: ").strip()

    if identificacao != "":
        imovel["identificacao"] = identificacao

    if cep != "":
        while len(cep) != 8 or not cep.isdigit():
            print("CEP inválido!")
            cep = input("Novo CEP: ").strip()

        imovel["cep"] = cep

    print("Imóvel atualizado!")


# ============================================================
# US08 - EXCLUIR IMÓVEL
# ============================================================


def excluir_imovel():
    print("\nEXCLUIR IMÓVEL")
    linha()

    codigo = input("Código do imóvel: ").strip()
    imovel = buscar_imovel(codigo)

    if imovel is None:
        print("Imóvel não encontrado.")
        return

    resposta = input("Deseja realmente excluir o imóvel? (S/N): ").upper()

    if resposta == "S":
        imoveis.remove(imovel)
        print("Imóvel excluído!")
    else:
        print("Operação cancelada.")


# ============================================================
# US09 - VISUALIZAR EQUIPAMENTOS
# ============================================================


def visualizar_equipamentos():
    print("\nEQUIPAMENTOS DISPONÍVEIS")
    linha()

    for equipamento in equipamentos:
        print(
            "ID:",
            equipamento["id"],
            "|",
            equipamento["nome"],
            "|",
            equipamento["potencia"],
            "W",
        )


# ============================================================
# US10 - CADASTRAR EQUIPAMENTO
# ============================================================


def cadastrar_equipamento():
    print("\nCADASTRAR EQUIPAMENTO")
    linha()

    nome = input("Nome: ").strip()
    categoria = input("Categoria: ").strip()

    try:
        potencia = float(input("Potência em W: ").replace(",", "."))
    except ValueError:
        print("Potência inválida.")
        return

    maior_id = 0
    for equipamento in equipamentos:
        if equipamento["id"] > maior_id:
            maior_id = equipamento["id"]

    equipamentos.append(
        {"id": maior_id + 1, "nome": nome, "categoria": categoria, "potencia": potencia}
    )

    print("Equipamento cadastrado!")


# ============================================================
# US11 - EXCLUIR EQUIPAMENTO
# ============================================================


def excluir_equipamento():
    visualizar_equipamentos()

    try:
        equipamento_id = int(input("\nID do equipamento: "))
    except ValueError:
        print("ID inválido.")
        return

    equipamento = buscar_equipamento(equipamento_id)

    if equipamento is None:
        print("Equipamento não encontrado.")
        return

    for imovel in imoveis:
        for equipamento_imovel in imovel["equipamentos"]:
            if equipamento_imovel["equipamento_id"] == equipamento_id:
                print("Este equipamento está vinculado a um imóvel.")
                return

    equipamentos.remove(equipamento)
    print("Equipamento excluído!")


# ============================================================
# US12 - ADICIONAR EQUIPAMENTO AO IMÓVEL
# ============================================================


def adicionar_equipamento_imovel():
    print("\nADICIONAR EQUIPAMENTO AO IMÓVEL")
    linha()

    codigo = input("Código do imóvel: ").strip()
    imovel = buscar_imovel(codigo)

    if imovel is None:
        print("Imóvel não encontrado.")
        return

    while True:
        visualizar_equipamentos()

        try:
            equipamento_id = int(input("\nID do equipamento: "))
            quantidade = int(input("Quantidade: "))
            horas = float(input("Horas de uso por dia: ").replace(",", "."))
        except ValueError:
            print("Valor inválido.")
            continue

        equipamento = buscar_equipamento(equipamento_id)

        if equipamento is None:
            print("Equipamento inválido!")
        elif quantidade <= 0 or horas < 0 or horas > 24:
            print("Quantidade ou horas inválidas.")
        else:
            consumo = calcular_consumo(equipamento["potencia"], quantidade, horas)

            imovel["equipamentos"].append(
                {
                    "equipamento_id": equipamento["id"],
                    "nome": equipamento["nome"],
                    "categoria": equipamento["categoria"],
                    "potencia": equipamento["potencia"],
                    "quantidade": quantidade,
                    "horas": horas,
                    "consumo": consumo,
                }
            )

            print(f"Consumo: {consumo:.2f} kWh/mês")

        resposta = input("Adicionar outro equipamento? (S/N): ").upper()

        if resposta != "S":
            break

    registrar_historico(imovel)
    print(f"\nConsumo total: {calcular_consumo_total(imovel):.2f} kWh/mês")


# ============================================================
# US13 - HISTÓRICO
# ============================================================


def visualizar_historico():
    print("\nHISTÓRICO DE CONSUMO")
    linha()

    codigo = input("Código do imóvel: ").strip()
    imovel = buscar_imovel(codigo)

    if imovel is None:
        print("Imóvel não encontrado.")
        return

    if len(imovel["historico"]) == 0:
        print("Nenhum histórico disponível.")
        return

    for registro in imovel["historico"]:
        print(registro["data"], "-", f"{registro['consumo']:.2f} kWh/mês")


# ============================================================
# US14 - DATASETS FOTOVOLTAICOS
# ============================================================


def visualizar_modulos():
    print("\nMÓDULOS FOTOVOLTAICOS")
    linha()

    if modulos is None:
        print("Dataset de módulos não carregado.")
        return

    for _, modulo in modulos.iterrows():
        print("ID:", modulo["id"])
        print("Fabricante:", modulo["fabricante"])
        print("Modelo:", modulo["modelo"])
        print("Potência:", modulo["potencia_wp"], "Wp")
        print("Voc:", modulo["voc_v"], "V")
        print("Isc:", modulo["isc_a"], "A")
        print("Vmp:", modulo["vmp_v"], "V")
        print("Imp:", modulo["imp_a"], "A")
        print("Eficiência:", modulo["eficiencia_pct"], "%")
        print(f"Preço: R$ {pd.to_numeric(modulo['preco_brl'], errors='coerce'):.2f}")
        print("Fornecedor:", modulo["fornecedor"])
        print("Data da coleta:", modulo["data_coleta"])
        print("Fonte:", modulo["url_fonte"])
        linha()


def visualizar_inversores():
    print("\nINVERSORES")
    linha()

    if inversores is None:
        print("Dataset de inversores não carregado.")
        return

    for _, inversor in inversores.iterrows():
        print("ID:", inversor["id"])
        print("Fabricante:", inversor["fabricante"])
        print("Modelo:", inversor["modelo"])
        print("Tipo:", inversor["tipo"])
        print("Potência nominal:", inversor["potencia_nominal_w"], "W")
        print("Potência máxima FV:", inversor["potencia_max_fv_w"], "W")
        print("Tensão máxima de entrada:", inversor["tensao_max_entrada_v"], "V")
        print(
            "Faixa MPPT:",
            inversor["faixa_mppt_min_v"],
            "-",
            inversor["faixa_mppt_max_v"],
            "V",
        )
        print("Corrente máxima de entrada:", inversor["corrente_max_entrada_a"], "A")
        print("Número de MPPT:", inversor["numero_mppt"])
        print("Compatível com bateria:", inversor["compativel_bateria"])
        print(f"Preço: R$ {pd.to_numeric(inversor['preco_brl'], errors='coerce'):.2f}")
        print("Fornecedor:", inversor["fornecedor"])
        print("Data da coleta:", inversor["data_coleta"])
        print("Fonte:", inversor["url_fonte"])
        linha()


def visualizar_baterias():
    print("\nBATERIAS")
    linha()

    if baterias is None:
        print("Dataset de baterias não carregado.")
        return

    for _, bateria in baterias.iterrows():
        print("ID:", bateria["id"])
        print("Fabricante:", bateria["fabricante"])
        print("Modelo:", bateria["modelo"])
        print("Tecnologia:", bateria["tecnologia"])
        print("Tensão nominal:", bateria["tensao_nominal_v"], "V")
        print("Capacidade:", bateria["capacidade_ah"], "Ah")
        print("Capacidade energética:", bateria["capacidade_kwh"], "kWh")
        print("DoD:", bateria["dod_pct"], "%")
        print("Ciclos:", bateria["ciclos"])
        print(f"Preço: R$ {pd.to_numeric(bateria['preco_brl'], errors='coerce'):.2f}")
        print("Fornecedor:", bateria["fornecedor"])
        print("Data da coleta:", bateria["data_coleta"])
        print("Fonte:", bateria["url_fonte"])
        linha()


def menu_datasets():
    while True:
        print("\n" + "=" * 60)
        print("DATASETS FOTOVOLTAICOS")
        print("=" * 60)
        print("1 - Visualizar módulos")
        print("2 - Visualizar inversores")
        print("3 - Visualizar baterias")
        print("0 - Voltar")

        opcao = input("Escolha: ").strip()

        if opcao == "1":
            visualizar_modulos()
        elif opcao == "2":
            visualizar_inversores()
        elif opcao == "3":
            visualizar_baterias()
        elif opcao == "0":
            break
        else:
            print("Opção inválida!")


# ============================================================
# US15 + US16 - DADOS E CÁLCULO FOTOVOLTAICO
# ============================================================


def calcular_dimensionamento_fv(consumo_mensal):
    print("\nDADOS DO DIMENSIONAMENTO FOTOVOLTAICO")
    linha()

    while True:
        try:
            percentual = float(
                input("Percentual do consumo que deseja atender (0 a 100): ").replace(
                    ",", "."
                )
            )
            if 0 < percentual <= 100:
                break
        except ValueError:
            pass
        print("Percentual inválido.")

    localizacao = input("Localização do imóvel: ").strip()
    while localizacao == "":
        print("A localização é obrigatória.")
        localizacao = input("Localização do imóvel: ").strip()

    while True:
        try:
            hsp = float(input("Horas de Sol Pleno (HSP): ").replace(",", "."))
            if hsp > 0:
                break
        except ValueError:
            pass
        print("HSP inválido.")

    origem_hsp = input("Fonte/origem do HSP: ").strip()
    while origem_hsp == "":
        print("A origem do HSP é obrigatória.")
        origem_hsp = input("Fonte/origem do HSP: ").strip()

    fator_atendimento = percentual / 100
    dias = 30
    eficiencia = 0.80

    # E_FV = C_m × f
    energia_fv = consumo_mensal * fator_atendimento

    # P_FV = E_FV ÷ (HSP × D × η)
    potencia_fv = energia_fv / (hsp * dias * eficiencia)

    print("\nRESULTADO DO CÁLCULO FOTOVOLTAICO")
    linha()
    print(f"Consumo mensal: {consumo_mensal:.2f} kWh/mês")
    print(f"Percentual atendido: {percentual:.2f}%")
    print(f"Energia mensal pretendida: {energia_fv:.2f} kWh/mês")
    print("Localização:", localizacao)
    print(f"HSP: {hsp:.2f} h/dia")
    print("Origem do HSP:", origem_hsp)
    print(f"Fator global de desempenho: {eficiencia * 100:.0f}%")
    print(f"Potência FV necessária: {potencia_fv:.2f} kWp")

    return {
        "consumo_mensal": consumo_mensal,
        "percentual": percentual,
        "energia_fv": energia_fv,
        "localizacao": localizacao,
        "hsp": hsp,
        "origem_hsp": origem_hsp,
        "dias": dias,
        "eficiencia": eficiencia,
        "potencia_fv": potencia_fv,
    }


# ============================================================
# US17 - SELEÇÃO DE MÓDULOS
# ============================================================


def selecionar_modulo(potencia_fv):
    if modulos is None:
        print("Dataset de módulos não carregado.")
        return None

    visualizar_modulos()

    id_modulo = input("Digite o ID do módulo desejado: ").strip().upper()
    modulo_escolhido = None

    for _, modulo in modulos.iterrows():
        if str(modulo["id"]).strip().upper() == id_modulo:
            modulo_escolhido = modulo
            break

    if modulo_escolhido is None:
        print("Módulo não encontrado.")
        return None

    if not verificar_modulo(modulo_escolhido):
        print(
            "Dados técnicos incoerentes para esse módulo. Corrija a fonte antes de usá-lo."
        )
        return None

    potencia_modulo = float(modulo_escolhido["potencia_wp"])

    # N = ceil((P_FV × 1000) ÷ P_mod)
    quantidade = math.ceil((potencia_fv * 1000) / potencia_modulo)

    # P_inst = (N × P_mod) ÷ 1000
    potencia_instalada = (quantidade * potencia_modulo) / 1000

    preco_unitario = preco_cotado(modulo_escolhido)
    if preco_unitario is None:
        return None

    # C_mod = N × Preço_mod
    custo_modulos = quantidade * preco_unitario

    print("\nMÓDULO SELECIONADO")
    linha()
    print("Fabricante:", modulo_escolhido["fabricante"])
    print("Modelo:", modulo_escolhido["modelo"])
    print("Potência unitária:", potencia_modulo, "Wp")
    print("Quantidade necessária:", quantidade)
    print(f"Potência instalada: {potencia_instalada:.2f} kWp")
    print(f"Custo dos módulos: R$ {custo_modulos:.2f}")

    return {
        "modulo": modulo_escolhido,
        "quantidade": quantidade,
        "potencia_instalada": potencia_instalada,
        "custo": custo_modulos,
    }


# ============================================================
# US18 - SELEÇÃO DO INVERSOR
# ============================================================


def selecionar_inversor(resultado_modulos):
    print("\nSELEÇÃO DO INVERSOR")
    linha()

    if inversores is None:
        print("Dataset de inversores não carregado.")
        return None

    modulo = resultado_modulos["modulo"]
    quantidade_total = resultado_modulos["quantidade"]
    potencia_instalada = resultado_modulos["potencia_instalada"]

    inversores_compativeis = []
    for _, inversor in inversores.iterrows():
        for config in configuracoes_strings(modulo, quantidade_total, inversor):
            inversores_compativeis.append({"inversor": inversor, **config})

    if not inversores_compativeis:
        print("Nenhum inversor compatível foi encontrado.")
        print("Tente selecionar outro módulo ou alterar o dimensionamento.")
        return None

    print("\nINVERSORES COMPATÍVEIS")
    linha()

    for item in inversores_compativeis:
        inversor = item["inversor"]
        print("ID:", inversor["id"])
        print("Fabricante:", inversor["fabricante"])
        print("Modelo:", inversor["modelo"])
        print("Tipo:", inversor["tipo"])
        print("Potência nominal:", inversor["potencia_nominal_w"], "W")
        print("Strings consideradas:", item["numero_strings"])
        print("Módulos por string:", item["modulos_por_string"])
        print(f"Vmp da string: {item['vmp_string']:.2f} V")
        print(f"Voc da string: {item['voc_string']:.2f} V")
        print(f"Corrente da string: {item['corrente_string']:.2f} A")
        print(f"Preço: R$ {pd.to_numeric(inversor['preco_brl'], errors='coerce'):.2f}")
        linha()

    id_inversor = input("Digite o ID do inversor desejado: ").strip().upper()

    for item in inversores_compativeis:
        inversor = item["inversor"]
        if str(inversor["id"]).strip().upper() == id_inversor:
            preco = preco_cotado(inversor)
            if preco is None:
                return None
            item = dict(item)
            item["inversor"] = inversor.copy()
            item["inversor"]["preco_brl"] = preco
            print("\nINVERSOR SELECIONADO")
            linha()
            print("Fabricante:", inversor["fabricante"])
            print("Modelo:", inversor["modelo"])
            print("Compatibilidade técnica básica: OK")
            return item

    print("Inversor inválido ou incompatível.")
    return None


# ============================================================
# US19 - ARMAZENAMENTO POR BATERIAS
# ============================================================


def valor_booleano(valor):
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() in ("true", "1", "sim", "s", "yes")


def dimensionar_bateria(consumo_mensal, resultado_inversor):
    print("\nARMAZENAMENTO DE ENERGIA")
    linha()

    resposta = input("Deseja adicionar bateria ao sistema? (S/N): ").strip().upper()

    if resposta != "S":
        print("Sistema dimensionado sem bateria.")
        return {
            "possui_bateria": False,
            "bateria": None,
            "autonomia": 0,
            "consumo_diario": consumo_mensal / 30,
            "energia_autonomia": 0,
            "capacidade_necessaria": 0,
            "quantidade": 0,
            "capacidade_instalada": 0,
            "eficiencia_bateria": 0,
            "custo": 0,
        }

    inversor = resultado_inversor["inversor"]

    if not valor_booleano(inversor["compativel_bateria"]):
        print("O inversor selecionado não é compatível com bateria.")
        return None

    while True:
        try:
            autonomia = float(
                input("Autonomia desejada em horas (1 a 24): ").replace(",", ".")
            )
            if 0 < autonomia <= 24:
                break
        except ValueError:
            pass
        print("Autonomia inválida.")

    # E_d = C_m ÷ 30
    consumo_diario = consumo_mensal / 30

    # E_aut = E_d × (A ÷ 24)
    energia_autonomia = consumo_diario * (autonomia / 24)

    # O dataset solicitado não possui eficiência de ciclo.
    # Premissa documentada do protótipo: 95%.
    eficiencia_bateria = 0.95

    print(f"Consumo médio diário: {consumo_diario:.2f} kWh/dia")
    print(f"Energia necessária para autonomia: {energia_autonomia:.2f} kWh")
    print("Eficiência de bateria adotada como premissa: 95%")

    if baterias is None:
        print("Dataset de baterias não carregado.")
        return None
    visualizar_baterias()

    id_bateria = input("Digite o ID da bateria desejada: ").strip().upper()
    bateria_escolhida = None

    for _, bateria in baterias.iterrows():
        if str(bateria["id"]).strip().upper() == id_bateria:
            bateria_escolhida = bateria
            break

    if bateria_escolhida is None:
        print("Bateria não encontrada.")
        return None

    if not bateria_compativel(inversor, bateria_escolhida):
        print(
            "Combinação inversor/bateria não comprovada pela matriz de compatibilidade."
        )
        print("Consulte a lista oficial do fabricante e requisitos de firmware/BMS.")
        return None

    preco_bateria = preco_cotado(bateria_escolhida)
    if preco_bateria is None:
        return None
    dod = float(bateria_escolhida["dod_pct"]) / 100
    capacidade_unitaria = float(bateria_escolhida["capacidade_kwh"])

    if dod <= 0 or dod > 1:
        print("DoD inválido no dataset.")
        return None

    # C_bat = E_aut ÷ (DoD × η_bat)
    capacidade_necessaria = energia_autonomia / (dod * eficiencia_bateria)

    # N_bat = ceil(C_bat ÷ C_un)
    quantidade = math.ceil(capacidade_necessaria / capacidade_unitaria)

    # C_inst_bat = N_bat × C_un
    capacidade_instalada = quantidade * capacidade_unitaria

    # C_baterias = N_bat × Preço_bat
    custo = quantidade * preco_bateria

    print("\nDIMENSIONAMENTO DA BATERIA")
    linha()
    print("Fabricante:", bateria_escolhida["fabricante"])
    print("Modelo:", bateria_escolhida["modelo"])
    print(f"Autonomia desejada: {autonomia:.2f} horas")
    print(f"Capacidade necessária: {capacidade_necessaria:.2f} kWh")
    print("Quantidade necessária:", quantidade)
    print(f"Capacidade instalada: {capacidade_instalada:.2f} kWh")
    print(f"Custo das baterias: R$ {custo:.2f}")
    print(
        "Observação: o dataset atual informa se o inversor aceita bateria, "
        "mas não traz a faixa de tensão de bateria do inversor. "
        "Por isso, a compatibilidade de tensão bateria-inversor não é "
        "calculada automaticamente."
    )

    return {
        "possui_bateria": True,
        "bateria": bateria_escolhida,
        "autonomia": autonomia,
        "consumo_diario": consumo_diario,
        "energia_autonomia": energia_autonomia,
        "capacidade_necessaria": capacidade_necessaria,
        "quantidade": quantidade,
        "capacidade_instalada": capacidade_instalada,
        "eficiencia_bateria": eficiencia_bateria,
        "custo": custo,
    }


# ============================================================
# US20 - ORÇAMENTO E PROPOSTA PRELIMINAR
# ============================================================


def calcular_orcamento(resultado_modulos, resultado_inversor, resultado_bateria):
    print("\nORÇAMENTO PRELIMINAR")
    linha()

    custo_modulos = resultado_modulos["custo"]
    custo_inversor = float(resultado_inversor["inversor"]["preco_brl"])
    custo_baterias = resultado_bateria["custo"]

    while True:
        try:
            outros_custos = float(
                input("Outros custos (instalação, cabos etc.) ou 0: R$ ").replace(
                    ",", "."
                )
            )
            if outros_custos >= 0:
                break
        except ValueError:
            pass
        print("Valor inválido.")

    # C_equip = C_mod + C_inv + C_baterias
    custo_equipamentos = custo_modulos + custo_inversor + custo_baterias

    # C_total = C_equip + C_outros
    custo_total = custo_equipamentos + outros_custos

    print("\nORÇAMENTO DO SISTEMA FOTOVOLTAICO")
    linha()
    print(f"Módulos:             R$ {custo_modulos:.2f}")
    print(f"Inversor:            R$ {custo_inversor:.2f}")
    print(f"Baterias:            R$ {custo_baterias:.2f}")
    print(f"Outros custos:       R$ {outros_custos:.2f}")
    linha()
    print(f"Total equipamentos:  R$ {custo_equipamentos:.2f}")
    print(f"CUSTO TOTAL:         R$ {custo_total:.2f}")

    return {
        "custo_modulos": custo_modulos,
        "custo_inversor": custo_inversor,
        "custo_baterias": custo_baterias,
        "outros_custos": outros_custos,
        "custo_equipamentos": custo_equipamentos,
        "custo_total": custo_total,
    }


def gerar_proposta(
    dados, resultado_modulos, resultado_inversor, resultado_bateria, resultado_orcamento
):
    modulo = resultado_modulos["modulo"]
    inversor = resultado_inversor["inversor"]
    potencia_instalada = resultado_modulos["potencia_instalada"]

    # E_ger = P_inst × HSP × D × η
    geracao_estimada = (
        potencia_instalada * dados["hsp"] * dados["dias"] * dados["eficiencia"]
    )

    print("\n" + "=" * 60)
    print("        PROPOSTA PRELIMINAR - SISTEMA FOTOVOLTAICO")
    print("=" * 60)

    print("\nDADOS DE CONSUMO")
    linha()
    print(f"Consumo mensal de referência: {dados['consumo_mensal']:.2f} kWh/mês")
    print(f"Percentual atendido: {dados['percentual']:.2f}%")
    print(f"Energia mensal pretendida: {dados['energia_fv']:.2f} kWh/mês")

    print("\nRECURSO SOLAR")
    linha()
    print("Localização:", dados["localizacao"])
    print(f"HSP utilizado: {dados['hsp']:.2f} h/dia")
    print("Origem do HSP:", dados["origem_hsp"])
    print(f"Fator global de desempenho: {dados['eficiencia'] * 100:.0f}%")

    print("\nDIMENSIONAMENTO FOTOVOLTAICO")
    linha()
    print(f"Potência necessária: {dados['potencia_fv']:.2f} kWp")
    print(f"Potência instalada: {potencia_instalada:.2f} kWp")
    print(f"Geração mensal estimada: {geracao_estimada:.2f} kWh/mês")

    print("\nMÓDULOS")
    linha()
    print("Fabricante:", modulo["fabricante"])
    print("Modelo:", modulo["modelo"])
    print("Potência unitária:", modulo["potencia_wp"], "Wp")
    print("Quantidade:", resultado_modulos["quantidade"])
    print(f"Custo: R$ {resultado_modulos['custo']:.2f}")

    print("\nINVERSOR")
    linha()
    print("Fabricante:", inversor["fabricante"])
    print("Modelo:", inversor["modelo"])
    print("Tipo:", inversor["tipo"])
    print("Potência nominal:", inversor["potencia_nominal_w"], "W")
    print("Strings:", resultado_inversor["numero_strings"])
    print("Módulos por string:", resultado_inversor["modulos_por_string"])
    print(f"Vmp da string: {resultado_inversor['vmp_string']:.2f} V")
    print(f"Voc da string: {resultado_inversor['voc_string']:.2f} V")
    print(f"Corrente da string: {resultado_inversor['corrente_string']:.2f} A")
    print(f"Custo: R$ {resultado_orcamento['custo_inversor']:.2f}")

    print("\nARMAZENAMENTO")
    linha()
    if resultado_bateria["possui_bateria"]:
        bateria = resultado_bateria["bateria"]
        print("Sistema com bateria: SIM")
        print("Fabricante:", bateria["fabricante"])
        print("Modelo:", bateria["modelo"])
        print(f"Autonomia: {resultado_bateria['autonomia']:.2f} horas")
        print(
            f"Capacidade necessária: {resultado_bateria['capacidade_necessaria']:.2f} kWh"
        )
        print("Quantidade:", resultado_bateria["quantidade"])
        print(
            f"Capacidade instalada: {resultado_bateria['capacidade_instalada']:.2f} kWh"
        )
        print(f"Custo: R$ {resultado_bateria['custo']:.2f}")
    else:
        print("Sistema com bateria: NÃO")

    print("\nORÇAMENTO")
    linha()
    print(f"Módulos:             R$ {resultado_orcamento['custo_modulos']:.2f}")
    print(f"Inversor:            R$ {resultado_orcamento['custo_inversor']:.2f}")
    print(f"Baterias:            R$ {resultado_orcamento['custo_baterias']:.2f}")
    print(f"Outros custos:       R$ {resultado_orcamento['outros_custos']:.2f}")
    linha()
    print(f"Total equipamentos:  R$ {resultado_orcamento['custo_equipamentos']:.2f}")
    print(f"CUSTO TOTAL:         R$ {resultado_orcamento['custo_total']:.2f}")
    print("=" * 60)


def dimensionar_sistema_fotovoltaico():
    print("\nDIMENSIONAMENTO FOTOVOLTAICO")
    linha()

    if modulos is None or inversores is None or baterias is None:
        print("Os datasets fotovoltaicos precisam estar carregados.")
        return

    codigo = input("Código do imóvel: ").strip()
    imovel = buscar_imovel(codigo)

    if imovel is None:
        print("Imóvel não encontrado.")
        return

    consumo_mensal = calcular_consumo_total(imovel)

    if consumo_mensal <= 0:
        print("O imóvel não possui consumo cadastrado.")
        print("Adicione equipamentos ao imóvel primeiro.")
        return

    dados = calcular_dimensionamento_fv(consumo_mensal)

    resultado_modulos = selecionar_modulo(dados["potencia_fv"])
    if resultado_modulos is None:
        return

    resultado_inversor = selecionar_inversor(resultado_modulos)
    if resultado_inversor is None:
        return

    resultado_bateria = dimensionar_bateria(consumo_mensal, resultado_inversor)
    if resultado_bateria is None:
        return

    resultado_orcamento = calcular_orcamento(
        resultado_modulos, resultado_inversor, resultado_bateria
    )

    gerar_proposta(
        dados,
        resultado_modulos,
        resultado_inversor,
        resultado_bateria,
        resultado_orcamento,
    )


# ============================================================
# US21 - COMPARAR MÓDULOS FOTOVOLTAICOS
# ============================================================


def calcular_opcao_modulo(modulo, potencia_fv):
    if not verificar_modulo(modulo):
        return None
    potencia_modulo = float(modulo["potencia_wp"])
    quantidade = math.ceil((potencia_fv * 1000) / potencia_modulo)
    potencia_instalada = (quantidade * potencia_modulo) / 1000
    preco = pd.to_numeric(modulo["preco_brl"], errors="coerce")
    custo = quantidade * float(preco) if pd.notna(preco) else None

    return {
        "modulo": modulo,
        "quantidade": quantidade,
        "potencia_instalada": potencia_instalada,
        "custo": custo,
    }


def comparar_modulos():
    if modulos is None:
        print("Dataset de módulos não carregado.")
        return

    try:
        potencia_fv = float(input("Potência FV necessária em kWp: ").replace(",", "."))
    except ValueError:
        print("Potência inválida.")
        return

    if potencia_fv <= 0:
        print("A potência precisa ser maior que zero.")
        return

    visualizar_modulos()
    ids = (
        input("Digite dois ou mais IDs de módulos separados por vírgula: ")
        .upper()
        .split(",")
    )

    ids = [item.strip() for item in ids if item.strip()]

    if len(ids) < 2:
        print("Selecione pelo menos dois módulos.")
        return

    resultados = []

    for id_modulo in ids:
        encontrado = None

        for _, modulo in modulos.iterrows():
            if str(modulo["id"]).strip().upper() == id_modulo:
                encontrado = modulo
                break

        if encontrado is None:
            print(f"Módulo {id_modulo} não encontrado.")
            continue

        calculo = calcular_opcao_modulo(encontrado, potencia_fv)
        if calculo is None or calculo["custo"] is None:
            print(
                f"Módulo {id_modulo}: dados técnicos/preço pendentes. Não incluído na comparação."
            )
            continue
        resultados.append(calculo)

    if len(resultados) < 2:
        print("Não há pelo menos duas opções válidas para comparar.")
        return

    print("\nCOMPARAÇÃO DE MÓDULOS")
    linha()

    for resultado in resultados:
        modulo = resultado["modulo"]
        print("ID:", modulo["id"])
        print("Fabricante:", modulo["fabricante"])
        print("Modelo:", modulo["modelo"])
        print("Potência:", modulo["potencia_wp"], "Wp")
        print("Eficiência:", modulo["eficiencia_pct"], "%")
        print("Quantidade:", resultado["quantidade"])
        print(f"Potência instalada: {resultado['potencia_instalada']:.2f} kWp")
        print(f"Custo dos módulos: R$ {resultado['custo']:.2f}")
        linha()


# ============================================================
# US22 - COMPARAR INVERSORES COMPATÍVEIS
# ============================================================


def obter_inversores_compativeis(resultado_modulos):
    if inversores is None:
        return []

    modulo = resultado_modulos["modulo"]
    quantidade_total = resultado_modulos["quantidade"]
    potencia_instalada = resultado_modulos["potencia_instalada"]

    compativeis = []
    for _, inversor in inversores.iterrows():
        for config in configuracoes_strings(modulo, quantidade_total, inversor):
            compativeis.append({"inversor": inversor, **config})

    return compativeis


def comparar_inversores():
    if modulos is None or inversores is None:
        print("Datasets de módulos/inversores não carregados.")
        return

    try:
        potencia_fv = float(input("Potência FV necessária em kWp: ").replace(",", "."))
    except ValueError:
        print("Potência inválida.")
        return

    if potencia_fv <= 0:
        print("A potência precisa ser maior que zero.")
        return

    visualizar_modulos()
    id_modulo = input("ID do módulo que será usado: ").strip().upper()

    modulo_escolhido = None
    for _, modulo in modulos.iterrows():
        if str(modulo["id"]).strip().upper() == id_modulo:
            modulo_escolhido = modulo
            break

    if modulo_escolhido is None:
        print("Módulo não encontrado.")
        return

    resultado_modulos = calcular_opcao_modulo(modulo_escolhido, potencia_fv)
    if resultado_modulos is None:
        print("Dados técnicos inválidos no módulo.")
        return

    compativeis = obter_inversores_compativeis(resultado_modulos)

    if not compativeis:
        print("Nenhum inversor compatível encontrado.")
        return

    print("\nINVERSORES COMPATÍVEIS")
    linha()

    for item in compativeis:
        inversor = item["inversor"]
        print("ID:", inversor["id"])
        print("Fabricante:", inversor["fabricante"])
        print("Modelo:", inversor["modelo"])
        print("Tipo:", inversor["tipo"])
        print("Potência nominal:", inversor["potencia_nominal_w"], "W")
        print("Potência máxima FV:", inversor["potencia_max_fv_w"], "W")
        print(
            "Faixa MPPT:",
            inversor["faixa_mppt_min_v"],
            "-",
            inversor["faixa_mppt_max_v"],
            "V",
        )
        print("Tensão máxima:", inversor["tensao_max_entrada_v"], "V")
        print("Corrente máxima:", inversor["corrente_max_entrada_a"], "A")
        print("MPPTs:", inversor["numero_mppt"])
        print("Compatível com bateria:", inversor["compativel_bateria"])
        print(f"Preço: R$ {pd.to_numeric(inversor['preco_brl'], errors='coerce'):.2f}")
        print("Strings consideradas:", item["numero_strings"])
        print("Módulos/string:", item["modulos_por_string"])
        print(f"Vmp string: {item['vmp_string']:.2f} V")
        print(f"Voc string: {item['voc_string']:.2f} V")
        print(f"Corrente string: {item['corrente_string']:.2f} A")
        linha()


# ============================================================
# US23 - RECOMENDAR CONFIGURAÇÃO FOTOVOLTAICA
# ============================================================


def recomendar_configuracao():
    if modulos is None or inversores is None:
        print("Datasets fotovoltaicos não carregados.")
        return

    codigo = input("Código do imóvel: ").strip()
    imovel = buscar_imovel(codigo)

    if imovel is None:
        print("Imóvel não encontrado.")
        return

    consumo_mensal = calcular_consumo_total(imovel)

    if consumo_mensal <= 0:
        print("O imóvel não possui consumo cadastrado.")
        return

    dados = calcular_dimensionamento_fv(consumo_mensal)
    configuracoes = []

    for _, modulo in modulos.iterrows():
        if (
            not verificar_modulo(modulo)
            or pd.isna(pd.to_numeric(modulo.get("preco_brl"), errors="coerce"))
            or str(modulo.get("fornecedor", "")).upper()
            in ("PENDENTE", "VALOR_ESTIMADO")
        ):
            continue
        resultado_modulos = calcular_opcao_modulo(modulo, dados["potencia_fv"])

        compativeis = obter_inversores_compativeis(resultado_modulos)

        for item_inversor in compativeis:
            if pd.isna(
                pd.to_numeric(
                    item_inversor["inversor"].get("preco_brl"), errors="coerce"
                )
            ) or str(item_inversor["inversor"].get("fornecedor", "")).upper() in (
                "PENDENTE",
                "VALOR_ESTIMADO",
            ):
                continue
            custo_inversor = float(item_inversor["inversor"]["preco_brl"])
            custo_total = resultado_modulos["custo"] + custo_inversor

            configuracoes.append(
                {
                    "resultado_modulos": resultado_modulos,
                    "resultado_inversor": item_inversor,
                    "custo_total": custo_total,
                }
            )

    if not configuracoes:
        print("Nenhuma configuração tecnicamente válida foi encontrada.")
        return

    # Critério documentado no projeto:
    # entre as combinações tecnicamente válidas, recomendar o menor
    # custo de módulos + inversor.
    melhor = min(configuracoes, key=lambda item: item["custo_total"])

    modulo = melhor["resultado_modulos"]["modulo"]
    inversor = melhor["resultado_inversor"]["inversor"]

    print("\nCONFIGURAÇÃO RECOMENDADA")
    linha()
    print("Critério: menor custo entre combinações tecnicamente compatíveis.")
    print(f"Potência necessária: {dados['potencia_fv']:.2f} kWp")
    print("Módulo:", modulo["fabricante"], modulo["modelo"])
    print("Quantidade:", melhor["resultado_modulos"]["quantidade"])
    print(
        f"Potência instalada: "
        f"{melhor['resultado_modulos']['potencia_instalada']:.2f} kWp"
    )
    print("Inversor:", inversor["fabricante"], inversor["modelo"])
    print(f"Custo módulos + inversor: " f"R$ {melhor['custo_total']:.2f}")

    resposta = (
        input(
            "Deseja continuar com essa recomendação e dimensionar bateria/orçamento? (S/N): "
        )
        .strip()
        .upper()
    )

    if resposta != "S":
        print("Recomendação exibida. Nenhuma configuração foi confirmada.")
        return

    resultado_bateria = dimensionar_bateria(
        consumo_mensal, melhor["resultado_inversor"]
    )

    if resultado_bateria is None:
        return

    resultado_orcamento = calcular_orcamento(
        melhor["resultado_modulos"], melhor["resultado_inversor"], resultado_bateria
    )

    gerar_proposta(
        dados,
        melhor["resultado_modulos"],
        melhor["resultado_inversor"],
        resultado_bateria,
        resultado_orcamento,
    )


# ============================================================
# US24 - SIMULAR PERCENTUAIS DE ATENDIMENTO
# ============================================================


def simular_percentuais():
    codigo = input("Código do imóvel: ").strip()
    imovel = buscar_imovel(codigo)

    if imovel is None:
        print("Imóvel não encontrado.")
        return

    consumo_mensal = calcular_consumo_total(imovel)

    if consumo_mensal <= 0:
        print("O imóvel não possui consumo cadastrado.")
        return

    try:
        hsp = float(input("HSP utilizado: ").replace(",", "."))
    except ValueError:
        print("HSP inválido.")
        return

    if hsp <= 0:
        print("HSP precisa ser maior que zero.")
        return

    origem_hsp = input("Origem/fonte do HSP: ").strip()

    visualizar_modulos()
    id_modulo = input("ID do módulo para a simulação: ").strip().upper()

    modulo_escolhido = None
    for _, modulo in modulos.iterrows():
        if str(modulo["id"]).strip().upper() == id_modulo:
            modulo_escolhido = modulo
            break

    if modulo_escolhido is None:
        print("Módulo não encontrado.")
        return

    entrada = input(
        "Percentuais para comparar, separados por vírgula (ex.: 50,80,100): "
    )

    try:
        percentuais = [
            float(valor.strip().replace(",", "."))
            for valor in entrada.split(",")
            if valor.strip()
        ]
    except ValueError:
        print("Existe um percentual inválido.")
        return

    if not percentuais or any(p <= 0 or p > 100 for p in percentuais):
        print("Todos os percentuais devem ser maiores que 0 e até 100.")
        return

    eficiencia = 0.80
    dias = 30

    print("\nSIMULAÇÃO DE PERCENTUAIS")
    print("Origem do HSP:", origem_hsp)
    linha()

    for percentual in percentuais:
        energia_fv = consumo_mensal * (percentual / 100)
        potencia_fv = energia_fv / (hsp * dias * eficiencia)
        resultado = calcular_opcao_modulo(modulo_escolhido, potencia_fv)

        geracao = resultado["potencia_instalada"] * hsp * dias * eficiencia

        print(f"Atendimento: {percentual:.2f}%")
        print(f"E_FV: {energia_fv:.2f} kWh/mês")
        print(f"P_FV: {potencia_fv:.2f} kWp")
        print("Quantidade de módulos:", resultado["quantidade"])
        print(f"Potência instalada: {resultado['potencia_instalada']:.2f} kWp")
        print(f"Geração estimada: {geracao:.2f} kWh/mês")
        print(f"Custo dos módulos: R$ {resultado['custo']:.2f}")
        linha()


# ============================================================
# US25 - SIMULAR DIFERENTES VALORES DE HSP
# ============================================================


def simular_hsp():
    codigo = input("Código do imóvel: ").strip()
    imovel = buscar_imovel(codigo)

    if imovel is None:
        print("Imóvel não encontrado.")
        return

    consumo_mensal = calcular_consumo_total(imovel)

    if consumo_mensal <= 0:
        print("O imóvel não possui consumo cadastrado.")
        return

    try:
        percentual = float(input("Percentual do consumo a atender: ").replace(",", "."))
    except ValueError:
        print("Percentual inválido.")
        return

    if percentual <= 0 or percentual > 100:
        print("Percentual deve ser maior que 0 e até 100.")
        return

    visualizar_modulos()
    id_modulo = input("ID do módulo para a simulação: ").strip().upper()

    modulo_escolhido = None
    for _, modulo in modulos.iterrows():
        if str(modulo["id"]).strip().upper() == id_modulo:
            modulo_escolhido = modulo
            break

    if modulo_escolhido is None:
        print("Módulo não encontrado.")
        return

    entrada = input("Valores de HSP separados por vírgula (ex.: 4,4.5,5): ")

    try:
        valores_hsp = [
            float(valor.strip().replace(",", "."))
            for valor in entrada.split(",")
            if valor.strip()
        ]
    except ValueError:
        print("Existe um HSP inválido.")
        return

    if len(valores_hsp) < 2 or any(hsp <= 0 for hsp in valores_hsp):
        print("Informe pelo menos dois valores de HSP maiores que zero.")
        return

    origem = input("Origem/fonte dos valores de HSP ou 'simulação': ").strip()

    energia_fv = consumo_mensal * (percentual / 100)
    eficiencia = 0.80
    dias = 30

    print("\nSIMULAÇÃO DE HSP")
    print("Origem:", origem)
    linha()

    for hsp in valores_hsp:
        potencia_fv = energia_fv / (hsp * dias * eficiencia)
        resultado = calcular_opcao_modulo(modulo_escolhido, potencia_fv)

        geracao = resultado["potencia_instalada"] * hsp * dias * eficiencia

        print(f"HSP: {hsp:.2f} h/dia")
        print(f"P_FV necessária: {potencia_fv:.2f} kWp")
        print("Quantidade de módulos:", resultado["quantidade"])
        print(f"Potência instalada: {resultado['potencia_instalada']:.2f} kWp")
        print(f"Geração mensal estimada: {geracao:.2f} kWh/mês")
        linha()


# ============================================================
# US26 - ESTIMAR ECONOMIA DE ENERGIA
# ============================================================


def estimar_economia():
    codigo = input("Código do imóvel: ").strip()
    imovel = buscar_imovel(codigo)

    if imovel is None:
        print("Imóvel não encontrado.")
        return

    consumo_mensal = calcular_consumo_total(imovel)

    if consumo_mensal <= 0:
        print("O imóvel não possui consumo cadastrado.")
        return

    try:
        geracao_mensal = float(
            input("Geração mensal estimada do sistema (kWh/mês): ").replace(",", ".")
        )
        tarifa = float(input("Tarifa de energia (R$/kWh): ").replace(",", "."))
    except ValueError:
        print("Valor inválido.")
        return

    if geracao_mensal < 0 or tarifa <= 0:
        print("A geração não pode ser negativa e a tarifa deve ser maior que zero.")
        return

    # A economia não usa mais energia do que o consumo mensal de referência.
    energia_compensada = min(geracao_mensal, consumo_mensal)
    economia_mensal = energia_compensada * tarifa
    economia_anual = economia_mensal * 12

    print("\nESTIMATIVA DE ECONOMIA")
    linha()
    print(f"Consumo mensal: {consumo_mensal:.2f} kWh/mês")
    print(f"Geração informada: {geracao_mensal:.2f} kWh/mês")
    print(f"Energia considerada: {energia_compensada:.2f} kWh/mês")
    print(f"Tarifa: R$ {tarifa:.4f}/kWh")
    print(f"Economia mensal estimada: R$ {economia_mensal:.2f}")
    print(f"Economia anual estimada: R$ {economia_anual:.2f}")
    print(
        "Observação: estimativa simplificada; não considera reajustes "
        "tarifários nem outras regras de compensação."
    )


# ============================================================
# MENU PRINCIPAL - US01 A US26
# ============================================================


def menu():
    while True:
        print("\n" + "=" * 60)
        print("SISTEMA DE DIMENSIONAMENTO ENERGÉTICO")
        print("=" * 60)

        print("1 - Cadastrar cliente")
        print("2 - Consultar cliente")
        print("3 - Editar cliente")
        print("4 - Excluir cliente")

        print("5 - Cadastrar imóvel")
        print("6 - Visualizar imóvel")
        print("7 - Editar imóvel")
        print("8 - Excluir imóvel")

        print("9 - Visualizar equipamentos")
        print("10 - Cadastrar equipamento")
        print("11 - Excluir equipamento")
        print("12 - Adicionar equipamento ao imóvel")
        print("13 - Visualizar histórico")

        print("\n--- DIMENSIONAMENTO FOTOVOLTAICO ---")
        print("14 - Visualizar datasets fotovoltaicos")
        print("15 - Dimensionar sistema fotovoltaico")
        print("16 - Comparar módulos fotovoltaicos")
        print("17 - Comparar inversores compatíveis")
        print("18 - Recomendar configuração fotovoltaica")
        print("19 - Simular percentuais de atendimento")
        print("20 - Simular diferentes valores de HSP")
        print("21 - Estimar economia de energia")

        print("\n0 - Encerrar")

        opcao = input("\nEscolha: ").strip()

        if opcao == "1":
            cadastrar_cliente()
        elif opcao == "2":
            consultar_cliente()
        elif opcao == "3":
            editar_cliente()
        elif opcao == "4":
            excluir_cliente()
        elif opcao == "5":
            cadastrar_imovel()
        elif opcao == "6":
            visualizar_imovel()
        elif opcao == "7":
            editar_imovel()
        elif opcao == "8":
            excluir_imovel()
        elif opcao == "9":
            visualizar_equipamentos()
        elif opcao == "10":
            cadastrar_equipamento()
        elif opcao == "11":
            excluir_equipamento()
        elif opcao == "12":
            adicionar_equipamento_imovel()
        elif opcao == "13":
            visualizar_historico()
        elif opcao == "14":
            menu_datasets()
        elif opcao == "15":
            dimensionar_sistema_fotovoltaico()
        elif opcao == "16":
            comparar_modulos()
        elif opcao == "17":
            comparar_inversores()
        elif opcao == "18":
            recomendar_configuracao()
        elif opcao == "19":
            simular_percentuais()
        elif opcao == "20":
            simular_hsp()
        elif opcao == "21":
            estimar_economia()
        elif opcao == "0":
            print("Sistema encerrado.")
            break
        else:
            print("Opção inválida!")


if __name__ == "__main__":
    menu()
