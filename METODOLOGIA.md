# Metodologia

Este documento descreve as fontes, fórmulas e limitações do projeto **Soja e Milho de Rondônia — Preço, Câmbio e Risco**.

## Fontes

| Dado | Fonte | Frequência | Cobertura |
|------|-------|------------|-----------|
| Soja CBOT (USD/bushel) | Yahoo Finance — ticker `ZS=F` | Semanal (sexta) | Histórico máximo (~30 anos) |
| Milho CBOT (USD/bushel) | Yahoo Finance — ticker `ZC=F` | Semanal (sexta) | Histórico máximo (~30 anos) |
| Dólar PTAX (BRL/USD) | Banco Central do Brasil — SGS série 1 (API oficial) | Diário, reamostrado semanal | Desde 2000 |
| Índice IPA-OG Fertilizantes | Banco Central do Brasil — SGS série 7456 (FGV) | Mensal, reamostrado semanal | Desde 1995 |
| Produção municipal | IBGE/PAM 2023 — tabela 1612 (API SIDRA) | Anual | 2023 |
| Geometria municipal | IBGE — Malha Municipal 2022 | — | — |

A janela utilizada na visualização varia por aba: **Aba 1 (preços e câmbio)** mostra 5 ou 10 anos por seleção do usuário; **Abas 2 e 3 (simulador e risco cambial)** usam o último valor disponível como cenário corrente; **Aba 4 (risco histórico)** usa todo o histórico disponível para mapear semanas com lucro vs prejuízo; **Aba 5 (sazonalidade)** usa os últimos 10 anos com índice sazonal padronizado (ver seção própria). Esta separação é deliberada: dados nominais sem ajuste de inflação são adequados para janelas curtas e para análises baseadas em razão (poder de compra, índice sazonal); janelas longas em valores nominais são apresentadas como contexto, não como base para decisão.

## Fórmulas

### Conversão de tonelada para bushel
Os contratos da CBOT são cotados em centavos de dólar por bushel. Cada commodity tem peso oficial específico:

| Cultura | kg/bushel | Bushels/tonelada |
|---------|-----------|------------------|
| Soja    | 27.2155   | 36.7437          |
| Milho   | 25.4012   | 39.3680          |

### Preço efetivo recebido pelo produtor
O produtor brasileiro nunca recebe a cotação cheia da CBOT — recebe a cotação **menos o basis** (ver seção própria abaixo).
```
preço_efetivo_USD_bu = preço_CBOT_USD_bu + basis_USD_bu     (basis é negativo)
preço_BRL_t           = preço_efetivo_USD_bu × bushels_por_tonelada × dólar_BRL
```

### Receita estimada do município
```
receita_BRL = produção_t × bushels_por_t × preço_efetivo_USD_bu × dólar_BRL
```

### Break-even cambial
Dado um custo de produção total municipal (custo_ha × área plantada), o **dólar break-even** é o câmbio mínimo para a receita igualar o custo:
```
custo_total_BRL = receita_USD × dólar_breakeven
dólar_breakeven = custo_total_BRL ÷ receita_USD
```
Onde `receita_USD = produção × bushels_por_t × preço_efetivo_USD_bu`.

## Custos de produção (referência CONAB para Rondônia)

Valores extraídos do **Custo Operacional Total (COT)** publicado pela CONAB no Acompanhamento da Safra Brasileira — Custos de Produção:

| Cultura | Região referência | COT (R$/ha) | Safra |
|---------|------------------|-------------|-------|
| Soja    | Cerejeiras/RO    | 6.012       | 2024/25 |
| Milho 2ª safra | Cone Sul/RO | 4.180   | 2024/25 |

Fonte: [CONAB - Custos de Produção](https://www.conab.gov.br/info-agro/custos-de-producao).

A metodologia COT da CONAB inclui:
- Custos variáveis (insumos: sementes, fertilizantes, defensivos)
- Operações mecanizadas (combustível, manutenção, depreciação)
- Mão de obra
- Despesas administrativas e arrendamento da terra

**Não inclui:** frete da fazenda ao porto (embutido no basis), impostos sobre a comercialização, custos financeiros sobre capital próprio.

Os valores são publicados mensalmente pela CONAB e variam conforme a safra. O usuário pode ajustar o slider para refletir realidades específicas do município ou cenários alternativos.

## Basis (deságio do produtor brasileiro vs. CBOT)

**O que é:** diferença, em US$ por bushel, entre a cotação internacional na CBOT e o preço efetivo que o produtor brasileiro recebe na fazenda. Costuma ser negativo: o produtor recebe **menos** que a cotação de Chicago. Reflete:

- Frete da fazenda até o porto de exportação
- Qualidade média da safra brasileira vs. especificação CBOT
- Prazos e custo financeiro do ciclo de comercialização
- Concorrência regional entre tradings

**Defaults aplicados (US$/bushel, média 2023–25):**

| Cultura | Basis default RO | Justificativa |
|---------|-----------------:|---------------|
| Soja    | −1.20           | Arco Norte (PVH → Itacoatiara/Santarém) tende a basis mais negativo que Sul/MT por gargalo logístico do Madeira em estiagem |
| Milho   | −0.50           | Milho safrinha do Cone Sul de RO/MT escoa via Rondonópolis → Santos; basis menos punido que soja por mercado interno robusto |

**Fontes de calibração:**
- **USDA FAS — Brazil Oilseeds and Products Annual (GAIN report)** — relatório anual oficial do USDA com basis por região brasileira
- **CONAB — Acompanhamento da Safra Brasileira, módulo Logística** — fretes por corredor e dinâmica do basis Brasil
- **ABIOVE — Boletim de Comércio Exterior** — basis FOB para soja/farelo/óleo
- **CEPEA/USP** — indicadores diários de soja e milho (proxy para MT/Cone Sul de RO)

O slider permite ao usuário simular cenários alternativos. Quando o toggle "Basis variável por município (geo)" está ativo, o basis é ajustado pela distância de cada município ao hub de transbordo mais próximo (ver seção *Basis variável por município* abaixo).

## Basis variável por município (multi-hub)

Quando o usuário ativa o toggle **"Basis variável por município (geo)"** na sidebar, o app calcula um basis individual para cada município com base no hub de transbordo mais conveniente para escoamento da safra.

**Hubs modelados:**

| Hub | Coordenada (lat, lon) | Modal predominante | Operadores |
|-----|---|---|---|
| Porto Velho (Arco Norte) | -8.76, -63.90 | Hidrovia do Madeira → Itacoatiara/Santarém | Hermasa/Amaggi, Cargill |
| Rondonópolis (MT) | -16.47, -54.64 | Ferrovia Rumo → Santos | Rumo Logística |
| Miritituba (PA) | -4.28, -55.98 | Barcaças do Tapajós → Vila do Conde | Cargill, Bunge, Hidrovias do Brasil |

**Lógica de roteamento — modelo aditivo:**

Para cada município, o modelo calcula a distância geodésica (Haversine) ao centroide de cada hub e atribui o município ao hub que **minimiza o custo logístico total**:

```
custo_total_BRL_t  = km × tarifa_rod + custo_fixo_pos_hub[hub]
custo_total_USD_bu = custo_total_BRL_t ÷ (dólar × bushels_por_t)
hub_escolhido      = argmin(custo_total_USD_bu)
basis_municipal    = basis_base − custo_total_USD_bu[hub_escolhido]
```

O modelo é **aditivo**: frete rodoviário variável (fazenda → hub) + custo fixo do trecho pós-hub (modal específico de cada corredor). O slider controla a tarifa rodoviária; o custo pós-hub é parâmetro calibrado por fonte.

**Custo fixo pós-hub (trecho hub → porto de exportação):**

| Hub | custo_fixo (R$/t) | Modal pós-hub | Fonte |
|-----|---:|---|---|
| PVH | 90 | Hidrovia Madeira → Itacoatiara/Santarém | ANTAQ/HBSA — range R$70-110/t (2024) |
| Rondonópolis | 160 | Ferrovia Rumo → Santos | IMEA/Rumo Relatório Tarifário 2024 — range R$140-180/t |
| Miritituba | 100 | Barcaças Tapajós → Vila do Conde | Estimativa ESALQ-LOG — dado primário pendente |

**Tarifa rodoviária (slider):** default R$15/t por 100 km — calibrado pela tarifa ANTT 2024 (~R$160/t para Vilhena→Rondonópolis, ~1.050 km).

**Resultado esperado:** PVH domina a quase totalidade dos municípios de RO por proximidade geodésica. Isso é consistente com dados reais: para Vilhena (extremo sul de RO), o custo total via PVH (~R$230/t) ainda é inferior ao custo via Rondonópolis (~R$310/t) porque a vantagem da ferrovia não compensa os ~1.050 km de rodoviário adicionais. Rondonópolis se torna competitiva para municípios de RO apenas com premissas de tarifa rodoviária elevada ou desconto ferroviário maior do que o observado.

**Limitações honestas deste modelo:**

1. **Distância em linha reta ≠ distância rodoviária.** O Haversine subestima quilometragem real. Para análise de portfólio é aproximação razoável; para decisão operacional, não.
2. **Não modela contratos comerciais.** A escolha de hub depende de quem comprou a safra (Cargill domina o Madeira; Rumo+ADM/Bunge dominam Santos via Rondonópolis). Esses contratos não são públicos.
3. **Não modela capacidade de transbordo nem sazonalidade.** Estiagem do Madeira, manutenção de eclusas, gargalos de embarque — simplificados em parâmetros médios.
4. **Pedágios não computados.** A concessão Nova 364 (BR-364/RO) e concessões de outros corredores (BR-163, Rumo) introduzem custos por praça que variam por categoria de veículo. Em termos relativos entre hubs, esse custo é pequeno frente ao frete rodoviário e ao custo fixo pós-hub — o modelo segue defensável para análise de portfólio. Para pricing operacional, refazer com tabelas tarifárias atualizadas.

A intenção do modelo é mostrar **heterogeneidade espacial-econômica do basis brasileiro** de forma defensável, não substituir um sistema de pricing real de trader.

## Índice de Poder de Compra do Produtor (terms of trade)

Métrica clássica em economia agrícola, baseada em índices oficiais. Compara a evolução do preço efetivo da saca em RO com a evolução do custo do fertilizante. Quando o índice de poder de compra cai, o produtor está empobrecendo em termos reais — mesmo que a saca esteja subindo nominalmente.

**Fonte do índice de fertilizantes:**
- **BCB SGS série 7456** — IPA-OG: Fertilizantes e corretivos do solo (FGV).
- API oficial do Banco Central do Brasil, periodicidade mensal.
- Série retorna variação % mensal — reconstruímos o índice em nível por `cumprod((1 + var/100))` partindo de base 100.

**Fórmula:**
```
saca_idx       = preço_efetivo_saca / preço_efetivo_saca[início] × 100
fertilizante_idx = IPA_OG_Fertilizantes (base 100 reconstruída)
poder_de_compra = saca_idx ÷ fertilizante_idx × 100
```

**Por que essa é a abordagem correta:** o preço absoluto do NPK em R$/tonelada não é publicado por nenhuma API pública estável no Brasil (Mosaic, StoneX e CEPEA mantêm dados em planos pagos). Trabalhar com o **índice IPA-OG do BCB** elimina dependência de fonte privada e usa série oficial — a mesma usada pelo IPEA, FGV e Ministério da Agricultura para análises de macroeconomia agrícola.

## Limitações

1. **CBOT é referência, não preço de balcão.** O produtor brasileiro vende grão a uma trading (Cargill, Bunge, ADM, Amaggi, Cofco, Louis Dreyfus) ou cooperativa, não diretamente à Bolsa de Chicago. O "preço Chicago" é a cotação internacional de referência sobre a qual o contrato com a trading é construído. O preço efetivo recebido na fazenda é **CBOT − basis**, e o basis embute frete até o porto, qualidade, prazos e a margem comercial da trading. Esta análise modela o preço efetivo via basis calibrado por fontes setoriais — não substitui o contrato real.

2. **Basis calibrado por valores médios setoriais.** O basis padrão (soja −1.20, milho −0.50) é a média 2023–25 de USDA, CONAB e ABIOVE — e o slider permite simular cenários. O modo "basis variável por município" ajusta dinamicamente pelo frete até o hub mais próximo, mas continua sendo aproximação: o basis real depende também de safra, capacidade de transbordo, contratos de compra do trader e câmbio do dia. Não é uma cotação de balcão real-time.

3. **Custo de produção uniforme entre municípios.** O custo do slider é aplicado igualmente a todos os municípios. Variações regionais reais existem (preço de terra, mão de obra, distância de revendas) — o slider permite ajustar para cima/baixo, mas não há diferenciação automática município a município.

4. **Dados de produção anuais.** PAM/IBGE publica dados consolidados com defasagem de ~1 ano. Não há captura infra-anual; o último ano fechado é 2023.

5. **Cotações com defasagem.** Yahoo Finance tem ~15 min de atraso para futuros CBOT. O PTAX é divulgado pelo BCB ao final de cada dia útil. O cache da aplicação tem TTL de 1 hora — adequado para análise de cenário, não para trading.

6. **Cotação semanal.** Para reduzir tamanho do parquet, o histórico é semanal. Para análise diária, ajustar `INTERVALO` em `coleta_mercado.py` para `"1d"`.

## Reprodutibilidade

```bash
pip install -r requirements.txt
python coleta_mercado.py     # popula cotacoes_historico.parquet
streamlit run app.py
```

Para atualizar cotações antes de uma sessão de análise, basta rodar novamente `python coleta_mercado.py`.
