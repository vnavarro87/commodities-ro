# Grãos de Rondônia — Preço, Câmbio e Risco

Soja e milho são cotados em Chicago, em dólar, em bushel. O fazendeiro de Rondônia recebe em reais, por saca, numa fazenda a centenas de quilômetros do porto. A diferença entre esses dois mundos — o **basis** — era algo que eu queria entender de verdade, não apenas ler sobre.

Este projeto é o resultado desse estudo: uma ferramenta interativa que conecta a cotação da CBOT ao preço efetivo que cada município de Rondônia recebe, mostrando quando o câmbio vira problema e quanto a distância ao porto pesa na conta.

## O que o projeto mostra

- Cotação histórica de Soja e Milho na CBOT (5 anos, semanal) sobreposta ao dólar PTAX
- KPIs em tempo aproximado de mercado: preço em US$/bushel, R$/tonelada e R$/saca
- Simulador de receita por município ou para o estado todo: cenários de preço e câmbio
- Mapa de receita estimada por município
- **Break-even cambial município a município:** dólar mínimo para não operar no prejuízo
- Scatter histórico CBOT × câmbio com curva de break-even — quantas semanas dos últimos 5 anos estiveram no vermelho

## Stack

- **Python** + **Streamlit** + **Plotly**
- **yfinance** para cotações CBOT
- **Banco Central do Brasil (SGS)** para PTAX e índice de fertilizantes (IPA-OG série 7456)
- **IBGE/SIDRA** para produção municipal (PAM 2023)

## Como rodar

```bash
git clone https://github.com/vnavarro87/commodities-ro.git
cd commodities-ro
pip install -r requirements.txt
streamlit run app.py
```

O app já inclui um parquet com cotações recentes. Para atualizar antes de rodar:

```bash
python coleta_mercado.py
```

Ou use o botão "Atualizar cotações" na sidebar — ele busca CBOT + PTAX + IPA-OG diretamente.

## Estrutura

```
commodities_ro/
├── app.py                       # Aplicação Streamlit
├── coleta_mercado.py            # ETL de cotações (yfinance + BCB)
├── dados_agro_ro_master.csv     # Produção municipal (IBGE/PAM 2023)
├── mapa_ro.json                 # Geometria municipal (IBGE 2022)
├── cotacoes_historico.parquet   # Histórico de cotações (cache local)
├── METODOLOGIA.md               # Fontes, fórmulas e limitações
├── requirements.txt
└── README.md
```

## Limitações conhecidas

- **Custos de produção:** o break-even usa Custo Operacional Total (COT) da CONAB para Rondônia (Cerejeiras/Cone Sul). Variações intramunicipais de terra e mão de obra não estão modeladas — o slider permite ajustar.
- **Basis variável por município** usa distância geodésica (linha reta) ao terminal logístico, não distância rodoviária real.
- **Dados de produção** são anuais (PAM 2023). Não há atualização infra-anual.

Detalhamento completo em [METODOLOGIA.md](METODOLOGIA.md).

## Sobre este projeto

[Lavouras RO](https://github.com/vnavarro87/lavouras-ro) mapeou *o que Rondônia produz e onde*. Este projeto tenta responder a pergunta seguinte: *quanto vale essa produção — e por que o município onde o fazendeiro está muda o preço que ele recebe?*

Não tenho formação em ciência de dados nem em economia agrícola. Trabalho em tecnologia, tenho interesse genuíno no agronegócio de Rondônia e queria aprender fazendo. Construí este projeto com auxílio intensivo de inteligência artificial (Claude, da Anthropic) — o que me permitiu implementar modelos e pipelines que eu não conseguiria escrever sozinho neste estágio. A IA ajudou com código; as perguntas, as fontes e as escolhas metodológicas são minhas.

Se algo parece errado ou pode melhorar, abre uma issue.

## Licença

Copyright (C) 2026 Vinicius Navarro.

Este projeto está licenciado sob a [GNU Affero General Public License v3.0](LICENSE). Em resumo: você pode usar, estudar, modificar e redistribuir, mas qualquer trabalho derivado — inclusive uso como serviço de rede — precisa ser disponibilizado sob a mesma licença. Para licenciamento comercial sob outros termos, entre em contato.
