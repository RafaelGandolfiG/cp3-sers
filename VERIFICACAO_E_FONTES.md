# Correções verificadas e pendências

## Correções efetuadas

- Corrigido `NameError`: função de carregamento agora utiliza a variável `modulos` corretamente.
- Leitura dos três CSVs relativa ao arquivo `main.py`.
- Módulo Huasun MOD010: Voc alterada de 40,13 V (incompatível com Vmp=42,10 V) para 50,13 V, conforme folha de dados do fabricante (versão para DS700).
- Preços anteriormente classificados como `VALOR_ESTIMADO` foram removidos do CSV; precisam de cotação de fornecedor para poder compor orçamento.
- Fonte comercial verificada para GoodWe Lynx Home U (BAT001): Eletrotrafo, R$ 10.545,00 na consulta de 11/10/2026.
- Fonte comercial localizada para Pylontech US5000 (BAT002): Solar Shop, R$ 5.999,00 na consulta de 11/10/2026.
- Strings fotovoltaicas agora só são aceitas com módulos igualmente distribuídos, uma string por MPPT (sem paralelismo), além dos limites básicos de potência, tensão e corrente.
- Programa impede combinação de bateria não presente na matriz preliminar GoodWe ET Plus / BYD HVS ou HVM; confirmações finais de firmware/BMS continuam necessárias.

## Links de documentação / evidências externas

- Huasun DS700: https://genyx.com.br/novo-site/wp-content/uploads/2022/08/G12-132-DS_EN.pdf
- Huasun página fabricante: https://www.huasunsolar.com/uploads/file/hs-210-b132-ds-700-730-en.pdf
- GoodWe ET Plus+: https://br.goodwe.com/et-plus-16a
- GoodWe compatibilidade de baterias: https://br.goodwe.com/Ftp/Downloads/User%20Manual/GW_Battery%20Compatibility%20Overview-EMEA_EN.pdf
- GoodWe Lynx Home U (não compatível com GoodWe ET Plus de alta tensão): https://br.goodwe.com/Skippower/downloadFileF?id=2118&mid=60
- BAT001 preço: https://www.eletrotrafo.com.br/bateria-solar-litio-goodwe-lynx-home-lxu5-4-20-51-2v-5-4kwh-50ah-306157-8-f-l--70030680/p
- BAT002 preço: https://solar-shops.com/produto/6a7a8e63960a61cd6272bfc1

## Limitações e pendências IMPORTANTES

1. Datasheets e tabelas originais para outros produtos foram herdados do repositório do grupo. Ainda exigem revisão individual contra fabricantes e lojas; a presença de URL não atesta precisão do número nem preço atualizado.
2. Módulos MOD003/MOD004 sem preço verificável; inversores INV001–INV005, INV008–INV010 sem preço rastreável; baterias BAT003–BAT008 sem preço rastreável. Devem ser pesquisados/registrados no CSV antes de usar em orçamento final da escola. O sistema pede cotação temporária com identificação da fonte para testes.
3. A compatibilidade do par GoodWe ET / BYD HVS/HVM requer verificação de firmware, topologia, faixa de tensão, comunicação BMS e tabelas exatas do fabricante.
4. O script não inclui persistência permanente de clientes/imóveis; na CP2 original, o cadastro é mantido em memória durante a sessão. Não foi implantada a CP3.
5. Foi realizado teste automatizado do fluxo sem bateria e com bateria, mas não a validação elétrica exaustiva de todas as combinações nem a revisão manual das 26 opções.
