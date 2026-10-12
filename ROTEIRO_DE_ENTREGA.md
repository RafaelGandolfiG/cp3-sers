# Checklist antes de apresentar

- [ ] Instalar dependências e iniciar Streamlit.
- [ ] Realizar cadastro de cliente, residência e aparelhos pela interface.
- [ ] Mostrar consumo diário, mensal e potência instalada.
- [ ] Mostrar fonte HSP e premissa PR.
- [ ] Demonstrar cálculo, seleção de módulos e inversor e relações elétricas.
- [ ] Demonstrar um cenário completo sem bateria.
- [ ] Registrar cotação rastreável para o inversor híbrido e a bateria e demonstrar cenário com bateria.
- [ ] Confirmar na documentação do fabricante o par de bateria escolhido, firmware e BMS.
- [ ] Demonstrar comparação de investimento, economia e payback.
- [ ] Salvar e recuperar proposta, exportar TXT/JSON.
- [ ] Testar valores inválidos e demonstrar mensagens ao usuário.
- [ ] Substituir preços pendentes por cotações comerciais reais quando possível.
- [ ] Anexar evidências/prints de dois cenários e explicar escolha final.

As 6 provas automatizadas em `tests/test_engine.py` verificam o motor, mas não substituem demonstração manual da interface e confirmação comercial dos dados.
