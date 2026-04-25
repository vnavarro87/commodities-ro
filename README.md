# Commodities de Rondônia — Grãos × Mercado

Análise da produção agrícola de Rondônia sob a perspectiva do mercado financeiro: cotação internacional na CBOT, câmbio do dólar e simulação de receita e risco cambial por município.

Cobre **Soja** e **Milho** — as duas principais lavouras temporárias do estado, ambas cotadas em USD/bushel na bolsa de Chicago.

## O que o projeto mostra

- Cotação histórica de Soja e Milho na CBOT (5 anos, semanal) sobreposta ao dólar
- KPIs em tempo aproximado de mercado: preço em US$/bushel, R$/tonelada e R$/saca
- Simulador de receita por município: cenários de preço e câmbio
- Mapa de receita estimada por município no estado todo
- **Análise de break-even cambial:** dólar mínimo para o produtor não operar no prejuízo, município por município
- Visualização de margem estimada no cenário atual

## Stack

- **Python** + **Streamlit** + **Plotly**
- **yfinance** para cotações CBOT e câmbio
- **IBGE/SIDRA** para produção municipal (PAM 2023)
- Pipeline ETL automatizado e cache de cotações com TTL

## Como rodar

```bash
git clone https://github.com/vnavarro87/commodities-ro.git
cd commodities-ro
pip install -r requirements.txt
python coleta_mercado.py    # baixa cotações atualizadas
streamlit run app.py
```

## Estrutura

```
commodities_ro/
├── app.py                       # Aplicação Streamlit
├── coleta_mercado.py            # ETL de cotações via yfinance
├── dados_agro_ro_master.csv     # Produção municipal (IBGE/PAM 2023)
├── mapa_ro.json                 # Geometria municipal (IBGE 2022)
├── cotacoes_historico.parquet   # Histórico de cotações
├── METODOLOGIA.md               # Fontes, tratamento e limitações
├── requirements.txt
└── README.md
```

## Limitações conhecidas

- **Boi Gordo:** APIs públicas brasileiras (IPEADATA, BCB SGS) deprecadas; CEPEA não expõe API estável. Será incluído em V2 com pipeline dedicado.
- **Custos de produção:** o break-even usa custo médio nacional como referência. Variações regionais de logística (frete Arco Norte) não estão modeladas — usuário pode ajustar via slider.
- **Cotação na CBOT** reflete o mercado internacional. O preço de balcão pago ao produtor brasileiro tem deságio de frete e basis — não modelado nesta versão.
- **Dados de produção** são anuais (PAM 2023). Não há atualização infra-anual.

Detalhamento completo em [METODOLOGIA.md](METODOLOGIA.md).

## Sobre

Segundo projeto público com foco na interseção entre **dados públicos do agronegócio** e **mercado financeiro**. Construído como peça de portfólio para demonstrar pipeline ETL multi-fonte, modelagem de cenários e visualização orientada a decisão.

## Licença

Copyright (C) 2026 Vinicius Navarro.

Este projeto está licenciado sob a [GNU Affero General Public License v3.0](LICENSE). Em resumo: você pode usar, estudar, modificar e redistribuir, mas qualquer trabalho derivado — inclusive uso como serviço de rede — precisa ser disponibilizado sob a mesma licença. Para licenciamento comercial sob outros termos, entre em contato.
