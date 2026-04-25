import os
import json
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Commodities de Rondônia", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .disclaimer {
        background-color: #2b2f3e; color: #d0d4dc;
        padding: 10px 14px; border-radius: 6px;
        border-left: 3px solid #00d26a;
        font-size: 13px; margin-bottom: 16px;
    }
    .context-box {
        background-color: #1e2130; border-radius: 10px;
        padding: 14px 16px; border-left: 4px solid #00d26a;
        font-size: 14px; color: #d0d4dc; margin-bottom: 16px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONSTANTES DE MERCADO ---
# Conversão tonelada -> bushel (peso oficial CBOT)
BUSHELS_POR_TONELADA = {"Soja": 36.7437, "Milho": 39.3680}

# Custos médios de produção (R$/ha) — Custo Operacional Total (COT) da CONAB
# Referências:
# - Soja: Cerejeiras/RO — safra 2024/25 — Acompanhamento da Safra Brasileira
# - Milho 2ª safra: Cone Sul/RO — safra 2024/25
# Fonte: CONAB - Custos de Produção Agrícola (conab.gov.br/info-agro/custos-de-producao)
# Atualização recomendada: a cada nova publicação mensal da CONAB.
CUSTO_HA_DEFAULT = {"Soja": 6012.0, "Milho": 4180.0}

# Basis Brasil — deságio típico do produtor em relação à CBOT (em US$/bushel).
# Reflete frete até o porto, qualidade e prazos. Para Rondônia, escoamento via
# Arco Norte tende a ter basis mais negativo que o Sul. Valores baseados em
# levantamentos públicos da Conab e relatórios setoriais (Safras & Mercado, StoneX).
BASIS_DEFAULT_USD = {"Soja": -1.20, "Milho": -0.50}

CULTURAS = {
    "Soja": {
        "ticker_col": "Soja_USD_bushel",
        "qtd_col":    "Soja_Qtd_T",
        "area_col":   "Soja_AreaPlant_Ha",
        "prod_col":   "Soja_Prod_KgHa",
        "valor_col":  "Soja_Valor_Mil",
        "contexto": (
            "Cotada na CBOT (Chicago) em USD/bushel. RO produz 2,2 Mi t/ano, "
            "com escoamento via Arco Norte (Porto Velho → Itacoatiara → Santarém)."
        ),
    },
    "Milho": {
        "ticker_col": "Milho_USD_bushel",
        "qtd_col":    "Milho_Qtd_T",
        "area_col":   "Milho_AreaPlant_Ha",
        "prod_col":   "Milho_Prod_KgHa",
        "valor_col":  "Milho_Valor_Mil",
        "contexto": (
            "Cotada na CBOT em USD/bushel. RO cultiva milho em sistema safrinha, "
            "logo após a colheita da soja, com produtividade média acima de 4.000 kg/ha."
        ),
    },
}


@st.cache_data
def carregar_producao():
    pasta = os.path.dirname(__file__)
    df = pd.read_csv(os.path.join(pasta, "dados_agro_ro_master.csv"))
    for col in df.columns:
        if col != "Municipio":
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    with open(os.path.join(pasta, "mapa_ro.json"), encoding="utf-8") as f:
        geojson = json.load(f)
    return df, geojson


@st.cache_data(ttl=3600)  # 1h cache para cotações
def carregar_cotacoes():
    pasta = os.path.dirname(__file__)
    arq = os.path.join(pasta, "cotacoes_historico.parquet")
    if not os.path.exists(arq):
        return pd.DataFrame()
    return pd.read_parquet(arq)


df_prod, geojson = carregar_producao()
df_cot = carregar_cotacoes()

# --- SIDEBAR ---
with st.sidebar:
    st.title("Commodities RO")
    st.caption("Produção × Mercado: grãos de Rondônia na perspectiva da bolsa.")
    st.markdown("---")
    cultura_sel = st.selectbox("Cultura:", list(CULTURAS.keys()))
    cfg = CULTURAS[cultura_sel]

    st.markdown("---")
    st.subheader("Perfil do produtor")
    st.caption(
        "Dentro de cada município existem produtores acima e abaixo da média. "
        "Use o controle abaixo para simular o perfil produtivo relevante."
    )
    perfil_pct = st.slider(
        "Produtividade vs. média municipal",
        min_value=60, max_value=140, value=100, step=10,
        format="%d%%",
        help="100% = produtor médio do município. 80% = abaixo da média típica. 120% = acima da média."
    )
    perfil_label = (
        "Médio" if perfil_pct == 100
        else f"{'Acima' if perfil_pct > 100 else 'Abaixo'} da média ({perfil_pct}%)"
    )
    st.caption(f"Perfil ativo: **{perfil_label}**")

    st.markdown("---")
    st.subheader("Basis Brasil")
    st.caption(
        "Deságio do produtor brasileiro em relação à CBOT (frete até o porto, "
        "qualidade, prazos). Para RO via Arco Norte, basis negativo é típico."
    )
    basis_usd = st.slider(
        f"Basis {cultura_sel}",
        min_value=-3.0, max_value=0.5,
        value=BASIS_DEFAULT_USD[cultura_sel], step=0.05,
        format="US$ %+.2f/bu",
        help="Negativo = produtor recebe menos que CBOT. Default reflete média histórica de RO.",
    )
    st.caption(
        f"**Default RO:** US$ {BASIS_DEFAULT_USD[cultura_sel]:+.2f}/bu "
        f"(Arco Norte, fonte: relatórios setoriais)"
    )

    st.markdown("---")
    st.subheader("Fontes")
    st.caption("""
    - **Produção municipal:** IBGE/PAM 2023 (tabela 1612)
    - **Cotações Soja/Milho:** CBOT via Yahoo Finance (semanal, 5 anos)
    - **Câmbio:** PTAX oficial — Banco Central do Brasil (SGS série 1)
    """)
    st.caption("Veja `METODOLOGIA.md` para detalhes técnicos e limitações.")

# Fator de produtividade aplicado a métricas que dependem da produção
fator = perfil_pct / 100

# --- HEADER ---
st.title("Commodities de Rondônia")
st.markdown(
    '<div class="disclaimer">'
    "Análise da produção agrícola de RO sob a perspectiva do mercado: "
    "cotação internacional (CBOT), câmbio e simulação cambial. "
    "Cotações atualizadas a cada hora durante o expediente da bolsa."
    "</div>",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="disclaimer" style="border-left-color:#ffbd45;">'
    "<b>Sobre a abordagem analítica:</b> as métricas são calculadas a nível municipal "
    "— média ponderada de produção, área e produtividade. Esta é uma visão estratégica "
    "e regional, útil para cooperativas, traders, seguradoras e formuladores de política. "
    "<b>Não reflete o produtor individual:</b> dentro de cada município existem "
    "produtores acima e abaixo da média, com estruturas de custo e produtividade próprias. "
    "Para análise individual seriam necessários dados que não são públicos (CPF/CNPJ)."
    "</div>",
    unsafe_allow_html=True,
)

# --- KPIs DE MERCADO ---
if not df_cot.empty and cfg["ticker_col"] in df_cot.columns:
    serie_commodity = df_cot[cfg["ticker_col"]].dropna()
    serie_dolar = df_cot["Dolar_PTAX"].dropna() if "Dolar_PTAX" in df_cot.columns else pd.Series(dtype=float)

    preco_atual = float(serie_commodity.iloc[-1])
    preco_12m = float(serie_commodity.iloc[-52]) if len(serie_commodity) > 52 else float(serie_commodity.iloc[0])
    var_12m = (preco_atual / preco_12m - 1) * 100

    dolar_atual = float(serie_dolar.iloc[-1]) if not serie_dolar.empty else 5.0
    dolar_12m = float(serie_dolar.iloc[-52]) if len(serie_dolar) > 52 else dolar_atual
    var_dolar = (dolar_atual / dolar_12m - 1) * 100

    # CBOT está em centavos/bushel. Converte para US$/bushel e aplica basis.
    preco_cbot_usd = preco_atual / 100
    preco_efetivo_usd = preco_cbot_usd + basis_usd  # basis é negativo => reduz
    bushels_t = BUSHELS_POR_TONELADA[cultura_sel]
    preco_brl_t = preco_efetivo_usd * bushels_t * dolar_atual
    saca_60kg = preco_brl_t * 0.06

    k1, k2, k3, k4 = st.columns(4)
    k1.metric(f"{cultura_sel} (CBOT)", f"US$ {preco_cbot_usd:,.2f}/bu", f"{var_12m:+.1f}% 12m")
    k2.metric("Dólar PTAX", f"R$ {dolar_atual:,.2f}", f"{var_dolar:+.1f}% 12m",
              help="Câmbio oficial PTAX divulgado pelo Banco Central — SGS série 1")
    k3.metric(
        f"{cultura_sel} efetivo (R$/saca 60kg)",
        f"R$ {saca_60kg:,.2f}",
        help=f"CBOT US$ {preco_cbot_usd:.2f} + basis US$ {basis_usd:+.2f} × dólar R$ {dolar_atual:.2f}",
    )
    k4.metric(f"{cultura_sel} efetivo (R$/t)", f"R$ {preco_brl_t:,.0f}")
else:
    st.warning("Cotações indisponíveis. Execute `python coleta_mercado.py` para atualizar.")
    st.stop()

st.markdown(
    f'<div class="context-box"><b>{cultura_sel}:</b> {cfg["contexto"]}</div>',
    unsafe_allow_html=True,
)

# --- ABAS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "Cotações × Câmbio", "Simulador de Receita", "Risco Cambial", "Matrix de Sensibilidade",
])

# --- ABA 1: COTAÇÕES × CÂMBIO ---
with tab1:
    st.subheader(f"{cultura_sel} (CBOT) e Dólar — últimos 5 anos")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=serie_commodity.index, y=serie_commodity.values,
            name=f"{cultura_sel} (US$/bushel)", line=dict(color="#00d26a", width=2),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=serie_dolar.index, y=serie_dolar.values,
            name="Dólar PTAX (R$)", line=dict(color="#ffbd45", width=2, dash="dot"),
        ),
        secondary_y=True,
    )
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text=f"{cultura_sel} — US$/bushel (×100)", secondary_y=False, color="#00d26a")
    fig.update_yaxes(title_text="Dólar PTAX — R$", secondary_y=True, color="#ffbd45")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin={"t": 30, "b": 0, "l": 0, "r": 0},
        height=480,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Eixo esquerdo (verde): cotação na CBOT em centavos de dólar por bushel — referência internacional. "
        "Eixo direito (amarelo): dólar comercial. "
        "A receita do produtor brasileiro depende do produto dos dois — câmbio amplifica ou neutraliza variações de preço."
    )

    # --- ÍNDICE DE PODER DE COMPRA ---
    if "IPA_Fertilizante_Idx" in df_cot.columns:
        st.markdown("---")
        st.subheader(f"Índice de Poder de Compra do Produtor — {cultura_sel}")

        st.markdown(
            '<div class="context-box">'
            f"<b>O que mostra:</b> evolução do preço efetivo da saca de {cultura_sel.lower()} "
            "em RO comparada ao preço dos fertilizantes. Ambos normalizados em "
            f"<b>base 100</b>. Quando a curva <b>cai</b>, o produtor está empobrecendo em termos reais "
            "— mesmo que a saca esteja subindo nominalmente, o fertilizante sobe mais. "
            "Métrica clássica de <i>terms of trade</i> em economia agrícola."
            "</div>",
            unsafe_allow_html=True,
        )

        # Histórico do preço efetivo da saca
        ticker_col = cfg["ticker_col"]
        df_hist = df_cot[[ticker_col, "Dolar_PTAX", "IPA_Fertilizante_Idx"]].dropna().copy()
        bt = BUSHELS_POR_TONELADA[cultura_sel]
        df_hist["preco_BRL_saca"] = (df_hist[ticker_col] / 100 + basis_usd) * bt * df_hist["Dolar_PTAX"] * 0.06

        # Normaliza ambos em base 100 no primeiro ponto comum
        base_saca = df_hist["preco_BRL_saca"].iloc[0]
        base_fert = df_hist["IPA_Fertilizante_Idx"].iloc[0]
        df_hist["Saca_Idx"] = df_hist["preco_BRL_saca"] / base_saca * 100
        df_hist["Fert_Idx"] = df_hist["IPA_Fertilizante_Idx"] / base_fert * 100
        df_hist["Poder_Compra"] = df_hist["Saca_Idx"] / df_hist["Fert_Idx"] * 100

        # KPIs
        pc_atual = float(df_hist["Poder_Compra"].iloc[-1])
        pc_12m = float(df_hist["Poder_Compra"].iloc[-52]) if len(df_hist) > 52 else float(df_hist["Poder_Compra"].iloc[0])
        pc_pico = float(df_hist["Poder_Compra"].max())
        pc_min = float(df_hist["Poder_Compra"].min())
        data_inicio = df_hist.index.min().strftime("%b/%Y")

        rk1, rk2, rk3, rk4 = st.columns(4)
        rk1.metric(
            "Poder de compra atual",
            f"{pc_atual:.0f}",
            f"{((pc_atual / pc_12m - 1) * 100):+.1f}% 12m",
            help=f"Base 100 = {data_inicio}. Acima de 100 = ganhou poder real desde a base. Abaixo = perdeu.",
        )
        rk2.metric("Pico (5 anos)", f"{pc_pico:.0f}",
                   help="Melhor momento de poder de compra")
        rk3.metric("Mínimo (5 anos)", f"{pc_min:.0f}",
                   help="Pior momento — maior aperto sobre o produtor")
        rk4.metric(
            f"Saca {cultura_sel} (R$/saca)",
            f"R$ {df_hist['preco_BRL_saca'].iloc[-1]:,.2f}",
            help="Preço efetivo atual (CBOT + basis × dólar)",
        )

        # Gráfico das 3 curvas
        fig_rt = go.Figure()
        fig_rt.add_trace(
            go.Scatter(
                x=df_hist.index, y=df_hist["Saca_Idx"],
                line=dict(color="#00d26a", width=2),
                name=f"Saca {cultura_sel}",
                hovertemplate="<b>%{x|%b/%Y}</b><br>Saca: %{y:.0f}<extra></extra>",
            )
        )
        fig_rt.add_trace(
            go.Scatter(
                x=df_hist.index, y=df_hist["Fert_Idx"],
                line=dict(color="#ff4b4b", width=2, dash="dot"),
                name="Fertilizante (IPA-OG)",
                hovertemplate="<b>%{x|%b/%Y}</b><br>Fert.: %{y:.0f}<extra></extra>",
            )
        )
        fig_rt.add_trace(
            go.Scatter(
                x=df_hist.index, y=df_hist["Poder_Compra"],
                line=dict(color="#ffbd45", width=3),
                name="Poder de compra (saca ÷ fert.)",
                hovertemplate="<b>%{x|%b/%Y}</b><br>Poder de compra: %{y:.0f}<extra></extra>",
            )
        )
        fig_rt.add_hline(
            y=100, line_dash="dash", line_color="white", line_width=1,
            annotation_text="Base 100",
            annotation_position="bottom right",
            annotation_font_color="white",
        )
        fig_rt.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            xaxis_title="",
            yaxis_title=f"Índice (base 100 = {data_inicio})",
            margin={"t": 20, "b": 0, "l": 0, "r": 0},
            height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_rt, use_container_width=True)

        st.caption(
            f"Poder de compra = (Índice da saca) ÷ (Índice do fertilizante) × 100. "
            f"Base 100 em {data_inicio}. "
            f"Fonte do índice de fertilizantes: BCB SGS série 7456 (IPA-OG Fertilizantes e corretivos do solo, FGV). "
            f"Calculado com basis de US$ {basis_usd:+.2f}/bu. "
            f"O choque global de fertilizantes (Rússia-Ucrânia, 2022) é visível como perda forte do poder de compra naquele período."
        )
    else:
        st.info("Coluna `IPA_Fertilizante_Idx` ausente. Execute `python coleta_mercado.py` para atualizar.")

# --- ABA 2: SIMULADOR DE RECEITA ---
with tab2:
    st.subheader(f"Simulador de Receita — {cultura_sel}")

    df_prod_filt = df_prod[df_prod[cfg["qtd_col"]] > 0].copy()
    municipios_disp = sorted(df_prod_filt["Municipio"].tolist())

    col_input, col_output = st.columns([1, 2])

    with col_input:
        mun_sim = st.selectbox("Município:", municipios_disp)
        st.markdown("**Cenário de mercado**")
        preco_sim_cbot_cents = st.slider(
            f"{cultura_sel} CBOT (centavos US$/bushel)",
            min_value=float(serie_commodity.min() * 0.7),
            max_value=float(serie_commodity.max() * 1.3),
            value=float(preco_atual),
            step=0.5,
        )
        dolar_sim = st.slider(
            "Dólar (R$)",
            min_value=float(serie_dolar.min() * 0.85),
            max_value=float(serie_dolar.max() * 1.15),
            value=float(dolar_atual),
            step=0.05,
        )
        # Preço efetivo do produtor = CBOT (em US$) + basis
        preco_sim_efetivo = preco_sim_cbot_cents / 100 + basis_usd
        st.caption(
            f"Preço efetivo: US$ {preco_sim_efetivo:.2f}/bu (CBOT US$ {preco_sim_cbot_cents/100:.2f} + basis US$ {basis_usd:+.2f})"
        )

    with col_output:
        mun_row = df_prod_filt[df_prod_filt["Municipio"] == mun_sim].iloc[0]
        producao_t = float(mun_row[cfg["qtd_col"]])
        area_ha = float(mun_row[cfg["area_col"]]) if cfg["area_col"] in mun_row else 0
        prod_kgha = float(mun_row[cfg["prod_col"]])

        # Produtividade ajustada pelo perfil
        prod_kgha_perfil = prod_kgha * fator

        # Receita por hectare (perfil do produtor)
        receita_ha = (prod_kgha_perfil / 1000) * BUSHELS_POR_TONELADA[cultura_sel] * preco_sim_efetivo * dolar_sim
        receita_saca = receita_ha * 0.06 / (prod_kgha_perfil / 1000) if prod_kgha_perfil > 0 else 0

        # Receita total municipal (escalada pelo perfil)
        receita_brl = producao_t * fator * BUSHELS_POR_TONELADA[cultura_sel] * preco_sim_efetivo * dolar_sim
        receita_usd = receita_brl / dolar_sim

        st.markdown(f"**Perfil do produtor: {perfil_label}**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Receita por hectare", f"R$ {receita_ha:,.0f}/ha",
                  help="Receita gerada por hectare no perfil produtivo selecionado")
        c2.metric("Equivalente em sacas 60kg/ha", f"{prod_kgha_perfil/60:,.1f} sc/ha")
        c3.metric("Receita por saca", f"R$ {receita_saca:,.2f}")

        st.markdown("**Município (agregado escalado pelo perfil):**")
        d1, d2, d3 = st.columns(3)
        d1.metric("Receita total", f"R$ {receita_brl/1e6:,.2f} Mi")
        d2.metric("Em dólares", f"US$ {receita_usd/1e6:,.2f} Mi")
        d3.metric("Produtividade aplicada", f"{prod_kgha_perfil:,.0f} kg/ha",
                  f"vs média municipal {prod_kgha:,.0f} kg/ha")

    st.markdown("---")
    st.subheader(f"Receita estimada por município — cenário atual")

    df_mapa = df_prod_filt.copy()
    df_mapa["Receita_BRL_Mi"] = (
        df_mapa[cfg["qtd_col"]] * fator
        * BUSHELS_POR_TONELADA[cultura_sel]
        * preco_sim_efetivo
        * dolar_sim
        / 1e6
    )

    fig_mapa = px.choropleth_mapbox(
        df_mapa, geojson=geojson, locations="Municipio",
        featureidkey="properties.name",
        color="Receita_BRL_Mi",
        color_continuous_scale="Viridis",
        mapbox_style="carto-darkmatter", zoom=5.6,
        center={"lat": -10.9, "lon": -62.8},
        opacity=0.7, hover_name="Municipio",
        labels={"Receita_BRL_Mi": "Receita (R$ Mi)"},
    )
    fig_mapa.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_mapa, use_container_width=True)

    st.caption(
        f"Cenário: CBOT US$ {preco_sim_cbot_cents/100:.2f}/bu + basis US$ {basis_usd:+.2f} "
        f"= preço efetivo US$ {preco_sim_efetivo:.2f}/bu × dólar R$ {dolar_sim:.2f}. "
        "Receita = produção × bushels/t × preço efetivo × câmbio. Não inclui custos."
    )

    # --- CONCENTRAÇÃO DE RISCO: % do PIB Agro municipal vinculado à cultura ---
    if "PIB_Agro_Mil" in df_prod.columns:
        st.markdown("---")
        st.subheader(f"Concentração de risco — exposição do PIB Agro à {cultura_sel}")

        st.markdown(
            '<div class="context-box">'
            f"<b>O que mostra:</b> percentual do <b>PIB Agropecuário municipal</b> "
            f"vinculado à receita estimada de {cultura_sel.lower()} no cenário atual. "
            "Responde à pergunta-chave de risco macroeconômico: <i>se essa commodity "
            "cair 20%, qual município sofre mais?</i> Quanto maior a exposição, maior "
            "a fragilidade do município a choques de preço — dimensão clássica de "
            "<i>concentration risk</i> em portfólios de crédito agro."
            "</div>",
            unsafe_allow_html=True,
        )

        df_exp = df_prod.copy()
        # Receita estimada (R$ Mi) com mesmo cenário do simulador
        df_exp["Receita_BRL_Mi"] = (
            df_exp[cfg["qtd_col"]] * fator
            * BUSHELS_POR_TONELADA[cultura_sel]
            * preco_sim_efetivo
            * dolar_sim
            / 1e6
        )
        # PIB_Agro_Mil está em R$ mil; receita em R$ Mi → multiplicar por 1000
        df_exp["Exposicao_Pct"] = np.where(
            df_exp["PIB_Agro_Mil"] > 0,
            (df_exp["Receita_BRL_Mi"] * 1000 / df_exp["PIB_Agro_Mil"]) * 100,
            0.0,
        )
        # Clip para coerência visual (alguns podem estourar 100% por ruído de PIB defasado)
        df_exp["Exposicao_Pct_Clip"] = df_exp["Exposicao_Pct"].clip(upper=100)

        col_e1, col_e2 = st.columns([2, 1])

        with col_e1:
            fig_exp = px.choropleth_mapbox(
                df_exp, geojson=geojson, locations="Municipio",
                featureidkey="properties.name",
                color="Exposicao_Pct_Clip",
                color_continuous_scale="YlOrRd",
                range_color=(0, 100),
                mapbox_style="carto-darkmatter", zoom=5.6,
                center={"lat": -10.9, "lon": -62.8},
                opacity=0.75, hover_name="Municipio",
                custom_data=["Exposicao_Pct", "Receita_BRL_Mi", "PIB_Agro_Mil"],
                labels={"Exposicao_Pct_Clip": "% do PIB Agro"},
            )
            fig_exp.update_traces(
                hovertemplate=(
                    "<b>%{hovertext}</b><br>"
                    "Exposição: %{customdata[0]:.1f}% do PIB Agro<br>"
                    "Receita estimada: R$ %{customdata[1]:,.1f} Mi<br>"
                    "PIB Agro: R$ %{customdata[2]:,.0f} mil<extra></extra>"
                )
            )
            fig_exp.update_layout(
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_exp, use_container_width=True)

        with col_e2:
            st.markdown("**Top 5 municípios mais expostos**")
            top5 = (
                df_exp[df_exp[cfg["qtd_col"]] > 0]
                .sort_values("Exposicao_Pct", ascending=False)
                .head(5)
            )
            for _, row in top5.iterrows():
                st.markdown(
                    f"**{row['Municipio']}** — "
                    f"<span style='color:#ff4b4b;font-weight:600'>{row['Exposicao_Pct']:.1f}%</span> "
                    f"<span style='color:#888;font-size:12px'>"
                    f"(R$ {row['Receita_BRL_Mi']:,.0f} Mi de R$ {row['PIB_Agro_Mil']/1000:,.0f} Mi)"
                    f"</span>",
                    unsafe_allow_html=True,
                )

            criticos = df_exp[df_exp["Exposicao_Pct"] >= 70]
            n_criticos = len(criticos)
            if n_criticos > 0:
                st.markdown("---")
                st.markdown(
                    f'<div class="disclaimer" style="border-left-color:#ff4b4b;">'
                    f"<b>Alerta de concentração:</b> {n_criticos} município(s) "
                    f"com exposição ≥ 70% do PIB Agro. "
                    f"Choque de −20% no preço impactaria diretamente "
                    f"<b>{0.20 * criticos['Exposicao_Pct'].mean():.1f}%</b> do PIB Agro médio "
                    f"desses municípios."
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.caption(
            f"Exposição = (receita estimada de {cultura_sel.lower()} no cenário atual) ÷ "
            f"(PIB Agropecuário municipal IBGE) × 100. "
            f"PIB Agro: IBGE — Produto Interno Bruto dos Municípios, ótica da agropecuária. "
            f"Mapa com escala fixa 0–100% (valores acima de 100% — ruído de PIB defasado vs. "
            f"safra atual — são saturados em vermelho profundo). "
            f"Cenário aplicado: o mesmo do simulador acima."
        )

# --- ABA 3: RISCO CAMBIAL ---
with tab3:
    st.subheader(f"Break-even do dólar — {cultura_sel}")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        custo_ha = st.slider(
            f"Custo de produção — {cultura_sel}",
            min_value=2000.0, max_value=10000.0,
            value=CUSTO_HA_DEFAULT[cultura_sel], step=100.0,
            format="R$ %.0f/ha",
            help=(
                f"Default: COT (Custo Operacional Total) CONAB para "
                f"{'Cerejeiras/RO' if cultura_sel == 'Soja' else 'Cone Sul/RO milho safrinha'}, "
                f"safra 2024/25. Inclui insumos, operações mecanizadas, mão de obra e "
                f"arrendamento. NÃO inclui frete (embutido no basis). "
                f"Fonte: CONAB - Custos de Produção Agrícola."
            )
        )
        st.caption(
            f"**Default CONAB:** R$ {CUSTO_HA_DEFAULT[cultura_sel]:,.0f}/ha "
            f"({'Cerejeiras/RO' if cultura_sel == 'Soja' else 'Cone Sul/RO'} safra 2024/25)"
        )
    with col_c2:
        choque_frete = st.slider(
            "Choque de frete adicional",
            min_value=0.0, max_value=2000.0,
            value=0.0, step=50.0,
            format="R$ %.0f/ha",
            help="Em zero: modelo padrão (basis cobre frete). Positivo: simula choque "
                 "logístico (alta do diesel, fechamento de via, gargalo no Arco Norte). "
                 "Útil para testar resiliência da margem em cenários adversos."
        )
        st.caption(
            f"**Custo total aplicado:** R$ {custo_ha + choque_frete:,.0f}/ha"
            + (" *(custo + choque)*" if choque_frete > 0 else "")
        )

    custo_total_ha = custo_ha + choque_frete

    df_be = df_prod[(df_prod[cfg["qtd_col"]] > 0) & (df_prod[cfg["area_col"]] > 0)].copy()
    df_be["Custo_Total_BRL"] = df_be[cfg["area_col"]] * custo_total_ha
    # Aplica perfil de produtividade na receita (perfil afeta produção, não custo)
    df_be["Receita_USD"] = (
        df_be[cfg["qtd_col"]] * fator
        * BUSHELS_POR_TONELADA[cultura_sel] * preco_efetivo_usd
    )
    # Break-even: Custo = Receita_USD × Dólar  =>  Dólar = Custo / Receita_USD
    df_be["Dolar_Breakeven"] = df_be["Custo_Total_BRL"] / df_be["Receita_USD"]
    df_be["Margem_Atual_BRL_Mi"] = (
        df_be["Receita_USD"] * dolar_atual - df_be["Custo_Total_BRL"]
    ) / 1e6

    media_be = df_be["Dolar_Breakeven"].mean()
    pior = df_be.loc[df_be["Dolar_Breakeven"].idxmax()]
    melhor = df_be.loc[df_be["Dolar_Breakeven"].idxmin()]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dólar break-even médio", f"R$ {media_be:,.2f}")
    c2.metric("Dólar atual", f"R$ {dolar_atual:,.2f}",
              f"{((dolar_atual - media_be) / media_be * 100):+.1f}% vs break-even")
    c3.metric("Município mais resiliente", melhor["Municipio"],
              f"break-even R$ {melhor['Dolar_Breakeven']:.2f}")
    c4.metric("Município mais vulnerável", pior["Municipio"],
              f"break-even R$ {pior['Dolar_Breakeven']:.2f}")

    st.markdown("---")
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("**Dólar break-even por município**")
        df_be_sorted = df_be.sort_values("Dolar_Breakeven")
        df_be_sorted["cor"] = df_be_sorted["Dolar_Breakeven"].apply(
            lambda v: "#00d26a" if v <= dolar_atual else "#ff4b4b"
        )
        fig_be = px.bar(
            df_be_sorted, x="Dolar_Breakeven", y="Municipio",
            orientation="h", color="cor", color_discrete_map="identity",
            labels={"Dolar_Breakeven": "Dólar break-even (R$)", "Municipio": ""},
        )
        fig_be.add_vline(
            x=dolar_atual, line_dash="dash", line_color="white",
            annotation_text=f"Dólar atual R$ {dolar_atual:.2f}",
            annotation_position="top right",
            annotation_font_color="white",
        )
        fig_be.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white", showlegend=False,
            height=600,
            margin={"t": 20, "b": 0, "l": 0, "r": 0},
        )
        st.plotly_chart(fig_be, use_container_width=True)

    with col_g2:
        st.markdown("**Margem estimada no cenário atual (R$ Mi)**")
        df_marg = df_be.sort_values("Margem_Atual_BRL_Mi", ascending=True).tail(20)
        df_marg["cor_marg"] = df_marg["Margem_Atual_BRL_Mi"].apply(
            lambda v: "#00d26a" if v >= 0 else "#ff4b4b"
        )
        fig_m = px.bar(
            df_marg, x="Margem_Atual_BRL_Mi", y="Municipio",
            orientation="h", color="cor_marg", color_discrete_map="identity",
            labels={"Margem_Atual_BRL_Mi": "Margem (R$ Mi)", "Municipio": ""},
        )
        fig_m.add_vline(x=0, line_color="white", line_width=1)
        fig_m.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white", showlegend=False,
            height=600,
            margin={"t": 20, "b": 0, "l": 0, "r": 0},
        )
        st.plotly_chart(fig_m, use_container_width=True)

    custo_str = f"R$ {custo_ha:,.0f}/ha"
    if choque_frete > 0:
        custo_str += f" + choque de frete R$ {choque_frete:,.0f}/ha = R$ {custo_total_ha:,.0f}/ha"

    st.caption(
        f"Break-even = custo total municipal ÷ receita em dólares (preço efetivo CBOT + basis). "
        f"Verde: município com break-even abaixo do câmbio atual (margem positiva). "
        f"Vermelho: break-even acima do câmbio (operando no prejuízo no cenário atual). "
        f"**Perfil aplicado:** {perfil_label} · "
        f"Custo: {custo_str} · CBOT: US$ {preco_cbot_usd:.2f}/bu · "
        f"Basis: US$ {basis_usd:+.2f}/bu · Preço efetivo: US$ {preco_efetivo_usd:.2f}/bu."
    )

# --- ABA 4: MATRIX DE SENSIBILIDADE ---
with tab4:
    st.subheader(f"Matrix de Sensibilidade — {cultura_sel}")

    st.markdown(
        '<div class="context-box">'
        "<b>O que mostra:</b> margem estimada em cada combinação de variação do "
        "<b>dólar</b> (eixo X) e da <b>cotação CBOT</b> (eixo Y) em relação ao cenário atual. "
        "Cada célula é um cenário; a cor indica resiliência. Verde = lucro confortável; "
        "vermelho = prejuízo. É o mesmo instrumento que mesas de crédito agro de bancos "
        "(Itaú BBA, Rabobank, BTG Pactual Agro) usam para aprovar limites — sliders mostram "
        "<i>um</i> cenário; a matrix mostra a <b>paisagem completa</b> de risco."
        "</div>",
        unsafe_allow_html=True,
    )

    df_ms_base = df_prod[(df_prod[cfg["qtd_col"]] > 0) & (df_prod[cfg["area_col"]] > 0)].copy()
    municipios_ms = sorted(df_ms_base["Municipio"].tolist())

    col_ms1, col_ms2, col_ms3 = st.columns([1, 1, 1])
    with col_ms1:
        escopo_ms = st.radio(
            "Escopo:", ["Município", "RO inteiro"], horizontal=True, key="escopo_ms",
            help="Município: margem por hectare. RO inteiro: margem agregada do estado em R$ Bi.",
        )
    with col_ms2:
        if escopo_ms == "Município":
            mun_ms = st.selectbox("Município:", municipios_ms, key="mun_ms")
        else:
            mun_ms = None
            st.caption("Agregado: somatório de todos os municípios produtores de RO.")
    with col_ms3:
        custo_ha_ms = st.slider(
            f"Custo total — {cultura_sel}",
            min_value=2000.0, max_value=10000.0,
            value=CUSTO_HA_DEFAULT[cultura_sel], step=100.0,
            format="R$ %.0f/ha", key="custo_ms",
            help=f"Default CONAB: R$ {CUSTO_HA_DEFAULT[cultura_sel]:,.0f}/ha (safra 2024/25).",
        )

    var_dolar_pct = np.arange(-10.0, 10.01, 2.5)
    var_cbot_pct = np.arange(-15.0, 15.01, 5.0)
    bushels_t = BUSHELS_POR_TONELADA[cultura_sel]

    if escopo_ms == "Município":
        mun_row_ms = df_ms_base[df_ms_base["Municipio"] == mun_ms].iloc[0]
        prod_kgha_ms = float(mun_row_ms[cfg["prod_col"]]) * fator
        toneladas_ha = prod_kgha_ms / 1000

        # margem_ha = (t/ha) × bushels/t × (cbot×(1+vc) + basis) × dolar×(1+vd) − custo
        cbot_grid = preco_cbot_usd * (1 + var_cbot_pct[:, None] / 100) + basis_usd
        dolar_grid = dolar_atual * (1 + var_dolar_pct[None, :] / 100)
        receita_ha_grid = toneladas_ha * bushels_t * cbot_grid * dolar_grid
        matrix = receita_ha_grid - custo_ha_ms

        unidade = "R$/ha"
        valor_fmt = ".0f"
        titulo_z = "Margem (R$/ha)"
        legenda_extra = (
            f"Município: <b>{mun_ms}</b> · Produtividade aplicada: "
            f"{prod_kgha_ms:,.0f} kg/ha ({perfil_label})"
        )
    else:
        prod_total_t = float((df_ms_base[cfg["qtd_col"]] * fator).sum())
        area_total_ha = float(df_ms_base[cfg["area_col"]].sum())
        custo_total_ro = area_total_ha * custo_ha_ms

        cbot_grid = preco_cbot_usd * (1 + var_cbot_pct[:, None] / 100) + basis_usd
        dolar_grid = dolar_atual * (1 + var_dolar_pct[None, :] / 100)
        receita_grid = prod_total_t * bushels_t * cbot_grid * dolar_grid
        matrix = (receita_grid - custo_total_ro) / 1e9  # R$ Bi

        unidade = "R$ Bi"
        valor_fmt = ".2f"
        titulo_z = "Margem (R$ Bi)"
        legenda_extra = (
            f"RO inteiro · Produção total aplicada: {prod_total_t/1e6:,.2f} Mi t · "
            f"Área: {area_total_ha/1e6:,.2f} Mi ha"
        )

    # Centralizar colorscale em zero (vermelho = prejuízo, verde = lucro)
    abs_max = float(np.abs(matrix).max())

    text_matrix = np.array([[format(v, valor_fmt) for v in row] for row in matrix])

    fig_ms = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=[f"{v:+.1f}%" for v in var_dolar_pct],
            y=[f"{v:+.0f}%" for v in var_cbot_pct],
            colorscale="RdYlGn",
            zmid=0, zmin=-abs_max, zmax=abs_max,
            text=text_matrix,
            texttemplate="%{text}",
            textfont={"size": 11, "color": "black"},
            colorbar=dict(title=titulo_z, tickfont=dict(color="white"), title_font=dict(color="white")),
            hovertemplate=(
                "Δ Dólar: %{x}<br>Δ CBOT: %{y}<br>"
                f"Margem: %{{z:,{valor_fmt}}} {unidade}<extra></extra>"
            ),
        )
    )
    fig_ms.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        xaxis_title="Variação do Dólar vs. cenário atual",
        yaxis_title="Variação CBOT vs. cenário atual",
        height=520,
        margin={"t": 20, "b": 0, "l": 0, "r": 0},
    )
    # Inverter Y para CBOT crescer de baixo pra cima
    fig_ms.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_ms, use_container_width=True)

    # KPIs interpretativos
    n_celulas = matrix.size
    n_neg = int((matrix < 0).sum())
    n_pos = int((matrix > 0).sum())
    pior = float(matrix.min())
    melhor = float(matrix.max())
    central = float(matrix[len(var_cbot_pct) // 2, len(var_dolar_pct) // 2])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cenário central (0%, 0%)", f"{central:,{valor_fmt}} {unidade}",
              help="Cenário sem variação — câmbio e CBOT atuais")
    m2.metric("Pior cenário", f"{pior:,{valor_fmt}} {unidade}",
              help="Dólar mais baixo combinado com CBOT mais baixa")
    m3.metric("Melhor cenário", f"{melhor:,{valor_fmt}} {unidade}",
              help="Dólar mais alto combinado com CBOT mais alta")
    m4.metric("Zonas de prejuízo", f"{n_neg}/{n_celulas} células",
              f"{n_pos} positivas",
              help="Quantas células da matrix resultam em margem negativa")

    st.caption(
        f"{legenda_extra} · Custo: R$ {custo_ha_ms:,.0f}/ha · "
        f"CBOT base: US$ {preco_cbot_usd:.2f}/bu · Basis: US$ {basis_usd:+.2f}/bu · "
        f"Dólar base: R$ {dolar_atual:.2f}. "
        f"Eixo X: variações de dólar de −10% a +10% (passo 2,5%). "
        f"Eixo Y: variações CBOT de −15% a +15% (passo 5%). "
        f"Quadrante superior-direito = duplo choque positivo (alta do dólar + alta da commodity); "
        f"inferior-esquerdo = duplo choque negativo, zona crítica para crédito."
    )

# --- RODAPÉ ---
st.markdown("---")
st.caption(
    "Dados de produção: IBGE/PAM 2023 (tabela 1612) via API SIDRA. "
    "Cotações: yfinance (CBOT e câmbio). "
    "Custo de produção é referencial e não capta variações regionais — ajuste o slider conforme contexto. "
    "Boi Gordo será incluído em V2 com pipeline dedicado. "
    "Veja METODOLOGIA.md para detalhes técnicos."
)
