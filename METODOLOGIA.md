# Metodologia

Este documento descreve as fontes, fórmulas e limitações do projeto **Commodities de Rondônia**.

## Fontes

| Dado | Fonte | Frequência | Período |
|------|-------|------------|---------|
| Soja CBOT (USD/bushel) | Yahoo Finance — ticker `ZS=F` | Semanal | 5 anos |
| Milho CBOT (USD/bushel) | Yahoo Finance — ticker `ZC=F` | Semanal | 5 anos |
| Dólar PTAX (BRL/USD) | Banco Central do Brasil — SGS série 1 (API oficial) | Diário, reamostrado semanal | 5 anos |
| Índice IPA-OG Fertilizantes | Banco Central do Brasil — SGS série 7456 (FGV) | Mensal, reamostrado semanal | 5 anos |
| Produção municipal | IBGE/PAM 2023 — tabela 1612 (API SIDRA) | Anual | 2023 |
| Geometria municipal | IBGE — Malha Municipal 2022 | — | — |

## Fórmulas

### Conversão de tonelada para bushel
Os contratos da CBOT são cotados em centavos de dólar por bushel. Cada commodity tem peso oficial específico:

| Cultura | kg/bushel | Bushels/tonelada |
|---------|-----------|------------------|
| Soja    | 27.2155   | 36.7437          |
| Milho   | 25.4012   | 39.3680          |

### Preço em R$/tonelada
```
preço_BRL_t = preço_CBOT_centavos × bushels_por_tonelada × dólar_BRL ÷ 100
```

### Receita estimada do município
```
receita_BRL = produção_t × bushels_por_t × preço_USD_bushel × dólar_BRL ÷ 100
```
A divisão por 100 converte centavos de dólar (cotação CBOT) em dólares.

### Break-even cambial
Dado um custo de produção total municipal (custo_ha × área plantada), o **dólar break-even** é o câmbio mínimo para a receita igualar o custo:
```
custo_total_BRL = receita_USD × dólar_breakeven
dólar_breakeven = custo_total_BRL ÷ receita_USD
```
Onde `receita_USD = produção × bushels_por_t × preço_USD ÷ 100`.

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

1. **Boi Gordo ausente em V1.** As APIs públicas brasileiras estão fragmentadas: IPEADATA descontinuou a série `BM_BOI`, BCB SGS não expõe série de boi gordo, CEPEA não tem API. Solução requer scraping ou subscrição paga, deixado para V2.

2. **CBOT vs. preço de balcão.** A cotação de Chicago é a referência internacional. O produtor brasileiro recebe um preço com deságio (basis) que reflete frete até o porto, qualidade e prazos. Esse deságio varia por região e safra — não modelado aqui.

3. **Custo de produção uniforme.** O custo é aplicado igualmente a todos os municípios. Na realidade, regiões com frete mais alto (caso da maior parte de RO via Arco Norte) têm custo total maior. O slider permite ajuste, mas o modelo é simplificado.

4. **Dados de produção anuais.** PAM/IBGE publica dados consolidados com defasagem de ~1 ano. Não há captura infra-anual; o último ano fechado é 2023.

5. **Cotações com defasagem.** Yahoo Finance tem ~15 min de atraso para futuros CBOT. O PTAX é divulgado pelo BCB ao final de cada dia útil. O cache da aplicação tem TTL de 1 hora — adequado para análise de cenário, não para trading.

7. **PTAX vs. dólar comercial:** o PTAX é a média ponderada das negociações entre instituições financeiras divulgada pelo BCB ao final de cada dia útil. É a referência oficial para liquidação de contratos cambiais e é o câmbio adequado para análise econômica e modelagem de risco. Foi escolhido em vez do dólar comercial do Yahoo Finance por ser fonte primária e de origem oficial.

6. **Cotação semanal.** Para reduzir tamanho do parquet, o histórico é semanal. Para análise diária, ajustar `INTERVALO` em `coleta_mercado.py` para `"1d"`.

## Reprodutibilidade

```bash
pip install -r requirements.txt
python coleta_mercado.py     # popula cotacoes_historico.parquet
streamlit run app.py
```

Para atualizar cotações antes de uma sessão de análise, basta rodar novamente `python coleta_mercado.py`.
