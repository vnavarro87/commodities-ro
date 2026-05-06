"""
Coleta de cotações de mercado para o projeto Soja e Milho de Rondônia.

Fontes:
- Soja (CBOT, USD/bushel): yfinance ticker ZS=F — histórico máximo disponível
- Milho (CBOT, USD/bushel): yfinance ticker ZC=F — histórico máximo disponível
- Dólar PTAX (R$/USD): API oficial do Banco Central do Brasil (SGS série 1) desde 2000
- Fertilizantes (IPA-OG): BCB SGS série 7456 — histórico máximo disponível

Salva parquet com histórico semanal completo (máximo disponível por fonte).
"""
import os
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import requests

PASTA = os.path.dirname(__file__)
ARQUIVO_SAIDA = os.path.join(PASTA, "cotacoes_historico.parquet")

PERIODO = "max"   # máximo disponível no yfinance para CBOT
INTERVALO = "1wk"
PTAX_INICIO = datetime(2000, 1, 1)  # PTAX BCB disponível desde 1999

TICKERS_YF = {
    "Soja_USD_bushel": "ZS=F",
    "Milho_USD_bushel": "ZC=F",
}

URL_PTAX = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados"
# Série 7456: IPA-OG - Fertilizantes e corretivos do solo (variação % mensal, FGV)
URL_FERTILIZANTE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.7456/dados"


def coletar_yfinance():
    """Coleta diária do yfinance e reamostra para semanal (sexta-feira)
    — alinha com PTAX/BCB que também usa W-FRI."""
    df_final = pd.DataFrame()
    for nome, ticker in TICKERS_YF.items():
        print(f"Coletando {nome} ({ticker})...")
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period=PERIODO, interval="1d", auto_adjust=False)
            if hist.empty:
                print(f"  AVISO: {ticker} retornou vazio")
                continue
            serie = hist["Close"].rename(nome)
            serie.index = pd.to_datetime(serie.index).tz_localize(None)
            # Reamostra para sexta-feira (último valor da semana)
            serie = serie.resample("W-FRI").last().dropna()
            df_temp = serie.to_frame()
            if df_final.empty:
                df_final = df_temp
            else:
                df_final = df_final.join(df_temp, how="outer")
            print(f"  {len(serie)} pontos semanais | ultimo: {serie.iloc[-1]:.2f}")
        except Exception as e:
            print(f"  ERRO em {ticker}: {e}")
    return df_final


def _buscar_ptax_chunk(inicio, fim):
    params = {
        "formato": "json",
        "dataInicial": inicio.strftime("%d/%m/%Y"),
        "dataFinal": fim.strftime("%d/%m/%Y"),
    }
    res = requests.get(URL_PTAX, params=params, timeout=60)
    res.raise_for_status()
    return res.json() or []


def coletar_ptax_bcb():
    """API do BCB tem timeout em janelas longas. Fragmenta em chunks anuais.
    Coleta desde PTAX_INICIO (default 2000) até hoje."""
    print("Coletando Dolar PTAX (BCB SGS serie 1)...")
    fim_total = datetime.now()
    inicio_total = PTAX_INICIO

    todos = []
    cursor = inicio_total
    while cursor < fim_total:
        chunk_fim = min(cursor + timedelta(days=365), fim_total)
        try:
            dados = _buscar_ptax_chunk(cursor, chunk_fim)
            todos.extend(dados)
            print(f"  {cursor.date()} a {chunk_fim.date()}: {len(dados)} pontos")
        except Exception as e:
            print(f"  Falha no chunk {cursor.date()}-{chunk_fim.date()}: {e}")
        cursor = chunk_fim + timedelta(days=1)

    if not todos:
        return pd.DataFrame()

    df = pd.DataFrame(todos)
    df["data"] = pd.to_datetime(df["data"], dayfirst=True)
    df["Dolar_PTAX"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df[["data", "Dolar_PTAX"]].dropna().drop_duplicates("data").set_index("data").sort_index()
    df = df.resample("W-FRI").last().dropna()
    print(f"  TOTAL: {len(df)} pontos semanais | ultimo: {df['Dolar_PTAX'].iloc[-1]:.4f}")
    return df


def coletar_fertilizante_bcb():
    """
    Coleta IPA-OG Fertilizantes (BCB SGS 7456) e reconstrói o índice em nível.
    Série original: variação % mensal. Reconstrução: índice base 100 no primeiro mês.
    """
    print("Coletando IPA-OG Fertilizantes (BCB SGS 7456)...")
    fim = datetime.now()
    inicio = datetime(1995, 1, 1)  # série disponível desde meados dos anos 90
    params = {
        "formato": "json",
        "dataInicial": inicio.strftime("%d/%m/%Y"),
        "dataFinal": fim.strftime("%d/%m/%Y"),
    }
    try:
        res = requests.get(URL_FERTILIZANTE, params=params, timeout=60)
        res.raise_for_status()
        dados = res.json()
        if not dados:
            return pd.DataFrame()
        df = pd.DataFrame(dados)
        df["data"] = pd.to_datetime(df["data"], dayfirst=True)
        df["var_pct"] = pd.to_numeric(df["valor"], errors="coerce")
        df = df[["data", "var_pct"]].dropna().set_index("data").sort_index()
        # Reconstruir índice em nível: base 100 no primeiro mês
        df["IPA_Fertilizante_Idx"] = (1 + df["var_pct"] / 100).cumprod() * 100
        # Reamostra para semanal (forward fill — índice é mensal)
        idx = df["IPA_Fertilizante_Idx"].resample("D").ffill().resample("W-FRI").last().dropna()
        print(f"  {len(idx)} pontos | base 100 em {df.index.min().date()} | atual: {idx.iloc[-1]:.1f}")
        return idx.to_frame()
    except Exception as e:
        print(f"  ERRO: {e}")
        return pd.DataFrame()


def coletar():
    df_yf = coletar_yfinance()
    df_ptax = coletar_ptax_bcb()
    df_fert = coletar_fertilizante_bcb()

    frames = [d for d in (df_yf, df_ptax, df_fert) if not d.empty]
    if not frames:
        print("Nenhum dado coletado.")
        return

    df_final = frames[0]
    for d in frames[1:]:
        df_final = df_final.join(d, how="outer")

    df_final = df_final.sort_index().ffill()
    df_final.to_parquet(ARQUIVO_SAIDA)
    print(f"\nArquivo salvo: {ARQUIVO_SAIDA}")
    print(f"Periodo: {df_final.index.min().date()} a {df_final.index.max().date()}")
    print(f"Linhas: {len(df_final)} | Colunas: {list(df_final.columns)}")


if __name__ == "__main__":
    coletar()
