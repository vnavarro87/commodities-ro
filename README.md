# Soja e Milho de Rondônia — Preço, Câmbio e Risco

Soja e milho são cotados na Bolsa de Chicago (CBOT), em dólar, em bushel. O produtor de Rondônia recebe em reais, por saca, depois de descontado o basis (frete até o porto, qualidade, prazo, margem da trading). A receita final depende de três variáveis ao mesmo tempo: cotação CBOT, câmbio PTAX, basis. Este projeto coloca as três no mesmo painel — município por município — e responde quanto da produção de RO está em zona de prejuízo no cenário de mercado atual.

Em Rondônia, milho é majoritariamente segunda safra — semeado em fevereiro, sobre o mesmo campo da soja recém-colhida. As duas culturas compartilham logística (mesmo corredor de escoamento), frequência de comercialização e exposição à CBOT, e por isso são tratadas no mesmo painel.

## O que o app responde

- Como o preço efetivo recebido em RO se moveu nos últimos 5 a 10 anos, em razão de CBOT e câmbio.
- Qual o **câmbio mínimo** para cada município não operar no prejuízo, dado custo de produção e basis configurados.
- Em quantas semanas do histórico cada município teria operado no vermelho com o custo atual.
- Qual o **basis municipal** quando o roteamento ao terminal logístico mais barato é considerado (Porto Velho via hidrovia do Madeira, Rondonópolis via Rumo, Miritituba via Tapajós).
- Como o **poder de compra do produtor** evoluiu — preço da saca relativo ao índice de fertilizantes (IPA-OG/FGV).
- Qual o **padrão sazonal** de preço efetivo (índice mensal sobre média móvel anual, últimos 10 anos).
- Qual a **magnitude da variação cambial intra-safra** entre plantio e colheita, safra a safra.

## Decisões de design

**PTAX em vez de dólar comercial.** O PTAX é a referência oficial do Banco Central usada na liquidação de contratos cambiais. É o câmbio relevante para análise de risco — não o ticker que aparece no aplicativo do banco.

**Basis calibrado por fontes setoriais, não real-time.** O basis efetivo depende de contratos privados entre tradings e produtores e não é público. Os defaults (soja −1,20, milho −0,50) refletem a média setorial 2023-25 cruzando USDA FAS, CONAB e ABIOVE. O slider permite simular cenários alternativos. O modo "basis variável por município" ajusta pelo custo logístico até o terminal mais barato.

**Scatter com curva de break-even em vez de heatmap.** Um heatmap mostra dados; o scatter responde: *"em quantas semanas do histórico o produtor teria operado no prejuízo com o custo configurado?"*. A curva tracejada é o break-even — acima dela o câmbio cobre o custo, abaixo não — e a estrela amarela posiciona o cenário atual no contexto histórico.

**Distância geodésica (Haversine) para basis municipal.** Roteirização rodoviária real exigiria dados de frete por trecho que ou são privados (planilhas de tradings) ou exigem manutenção manual periódica. Haversine é aproximação aceitável para análise de portfólio — não para pricing operacional.

**Índice sazonal sobre média móvel anual, não média mensal absoluta.** Calcular média mensal de preço nominal com 30 anos de histórico mistura inflação acumulada e padrão sazonal — o resultado fica dominado pela inflação. O índice sazonal (preço dividido pela média móvel de 52 semanas) cancela a tendência inflacionária por construção. É o método-padrão da economia agrícola para sazonalidade de commodities.

**yfinance como fonte de cotações CBOT.** É wrapper não-oficial sem SLA — pode ser interrompido sem aviso. Escolhido pela cobertura dos contratos sem custo. Substituto natural para versão paga: Bloomberg ou Refinitiv.

## Como o produtor brasileiro se relaciona com a CBOT

Importante para quem está chegando ao tema: o produtor brasileiro **não vende direto à Bolsa de Chicago**. Vende a uma trading (Cargill, Bunge, ADM, Amaggi, Cofco, Louis Dreyfus) ou cooperativa, que constrói o contrato como **CBOT − basis**. O preço efetivo na fazenda é sempre menor que a cotação Chicago — a diferença é o basis, que embute frete, qualidade, prazo e a margem da trading. Toda a modelagem deste projeto assume essa estrutura.

## Stack

- **Python**, **Streamlit**, **Plotly**
- **yfinance** — cotações CBOT
- **BCB SGS** — PTAX (série 1, desde 2000) e IPA-OG Fertilizantes (série 7456, desde 1995)
- **IBGE/SIDRA** — produção municipal PAM 2023 (tabela 1612)

## Como rodar

```bash
git clone https://github.com/vnavarro87/soja-milho-ro.git
cd soja-milho-ro
pip install -r requirements.txt
streamlit run app.py
```

O parquet com cotações já está no repositório. Para atualizar antes de rodar:

```bash
python coleta_mercado.py
```

Ou clique em "Atualizar cotações" na sidebar do app.

## Estrutura

```
soja_milho_ro/
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

- **CBOT é referência, não preço de balcão.** A trading que compra o grão precifica como CBOT − basis. O preço efetivo na fazenda é sempre menor que a cotação Chicago. O slider de basis permite simular cenários, e o modo geográfico ajusta por município.

- **Basis municipal é aproximação.** Distância em linha reta ao hub de transbordo, modelo aditivo (rodoviário variável + custo fixo pós-hub). Defensável para análise de portfólio; não substitui pricing operacional de trader.

- **Custo de produção uniforme entre municípios.** O slider aplica o mesmo R$/ha a todos. Variações regionais de preço de terra e mão de obra existem mas não há fonte pública municipalizada disponível.

- **Cotações com defasagem.** Yahoo Finance ~15 min para futuros CBOT; PTAX divulgado pelo BCB ao final de cada dia útil. Cache de 1 hora — adequado para análise de cenário, não para decisão de comercialização em tempo real.

- **Dados de produção com defasagem de ~1 ano.** PAM/IBGE 2023 é o último ano fechado; não há captura infra-anual.

- **Análise de variação cambial intra-safra ≠ simulação de hedge real.** A Aba 5 mostra a magnitude da variação do PTAX entre plantio e colheita de cada safra. Hedge cambial real (NDF, futuro de dólar B3) trava o forward, que embute cupom cambial — não está modelado aqui. A análise serve como indicador de risco, não como simulador de operação financeira.

Detalhamento completo em [METODOLOGIA.md](METODOLOGIA.md).

## Sobre

Segundo projeto de uma série sobre o agronegócio de Rondônia. O primeiro — [Lavouras RO](https://github.com/vnavarro87/lavouras-ro) — mapeou o que o estado produz e onde. Este responde à pergunta seguinte: quanto vale essa produção, e por que o município muda o preço que o produtor recebe.

## Licença

Copyright (C) 2026 Vinicius Navarro.

Licenciado sob a [GNU Affero General Public License v3.0](LICENSE). Em resumo: uso, estudo, modificação e redistribuição são livres, mas qualquer trabalho derivado — inclusive uso como serviço de rede — precisa ser disponibilizado sob a mesma licença. Para licenciamento comercial sob outros termos, entre em contato.
