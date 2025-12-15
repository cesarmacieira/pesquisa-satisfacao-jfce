
import os
import uuid
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except Exception:
    px = None

DATA_FILE = "Dados.xlsx"
SHEET = "respostas"
TZ = "America/Sao_Paulo"

# ---- Metas (ajuste livre) ----
TARGET_SATISFACAO_1_5 = 4.2
TARGET_NPS = 50  # -100 a 100

LIKERT = {
    1: "1 — Muito insatisfeito(a)",
    2: "2 — Insatisfeito(a)",
    3: "3 — Neutro",
    4: "4 — Satisfeito(a)",
    5: "5 — Muito satisfeito(a)",
}

CANALS = [
    "Balcão Virtual",
    "E-mail",
    "Telefone",
    "Presencial",
    "PJe",
    "WhatsApp (institucional)",
    "Outro",
]

UNIDADES = [
    "Fortaleza",
    "Juazeiro do Norte",
    "Outra (informar)",
]

TIPOS_USUARIO = [
    "Jurisdicionado",
    "Advogado",
    "Servidor/Colaborador",
    "Outro",
]

FAIXAS_IDADE = ["18-30", "31-40", "41-50", "51-60", "61+"]
GENEROS = ["F", "M", "Outro", "Prefiro não informar"]

COLUMNS = [
    "timestamp",
    "respondent_id",
    "unidade",
    "tipo_usuario",
    "atua_como",
    "faixa_idade",
    "genero",
    "canal_contato_mais_usado",
    "ja_usou_balcao_virtual",
    "ja_participou_audiencia",
    "clareza_informacoes",
    "cordialidade_respeito",
    "facilidade_contato",
    "tempo_resposta",
    "resolutividade",
    "acessibilidade",
    "usabilidade_ferramentas",
    "experiencia_audiencia",
    "satisfacao_geral",
    "recomendacao_0_10",
    "comentario_aberto",
]

DIMENSOES = [
    ("clareza_informacoes", "Clareza das informações"),
    ("cordialidade_respeito", "Cordialidade e respeito"),
    ("facilidade_contato", "Facilidade de contato"),
    ("tempo_resposta", "Tempo de resposta/retorno"),
    ("resolutividade", "Resolutividade"),
    ("acessibilidade", "Acessibilidade/Inclusão"),
    ("usabilidade_ferramentas", "Usabilidade de ferramentas/canais"),
    ("experiencia_audiencia", "Experiência em audiência (se aplicável)"),
]


def ensure_data_file():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=COLUMNS)
        with pd.ExcelWriter(DATA_FILE, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=SHEET, index=False)


def load_data() -> pd.DataFrame:
    ensure_data_file()
    df = pd.read_excel(DATA_FILE, sheet_name=SHEET)
    # Normaliza colunas (caso o arquivo tenha sido editado)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[COLUMNS]
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


def append_row(row: dict):
    ensure_data_file()
    df = load_data()
    df2 = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    with pd.ExcelWriter(DATA_FILE, engine="openpyxl", mode="w") as writer:
        df2.to_excel(writer, sheet_name=SHEET, index=False)


def compute_nps(series_0_10: pd.Series) -> float:
    s = pd.to_numeric(series_0_10, errors="coerce").dropna()
    if len(s) == 0:
        return float("nan")
    promoters = (s >= 9).mean() * 100
    detractors = (s <= 6).mean() * 100
    return promoters - detractors


def period_floor(ts: pd.Series, freq: str) -> pd.Series:
    # freq: 'D', 'W', 'M'
    if freq == "W":
        return ts.dt.to_period("W").dt.start_time
    if freq == "M":
        return ts.dt.to_period("M").dt.start_time
    return ts.dt.floor("D")


# ---------------- UI ----------------
st.set_page_config(page_title="Pesquisa de Satisfação — JFCE", layout="wide")
st.title("📋 Pesquisa de Satisfação — JFCE")

page = st.sidebar.radio("Navegação", ["Responder pesquisa", "Painel (análises)"])

if page == "Responder pesquisa":
    st.subheader("Responder")

    st.caption("As respostas são registradas de forma **anonimizada** (sem nome/e-mail/CPF).")

    col1, col2, col3 = st.columns(3)
    with col1:
        unidade = st.selectbox("Unidade", UNIDADES)
        if unidade == "Outra (informar)":
            unidade = st.text_input("Informe a unidade", value="").strip() or "Outra"
    with col2:
        tipo_usuario = st.selectbox("Tipo de usuário", TIPOS_USUARIO)
    with col3:
        canal = st.selectbox("Canal mais usado para contato", CANALS)

    col4, col5, col6 = st.columns(3)
    with col4:
        faixa_idade = st.selectbox("Faixa etária (opcional)", ["(não informar)"] + FAIXAS_IDADE)
        if faixa_idade == "(não informar)":
            faixa_idade = ""
    with col5:
        genero = st.selectbox("Gênero (opcional)", ["(não informar)"] + GENEROS)
        if genero == "(não informar)":
            genero = ""
    with col6:
        ja_usou_balcao = st.radio("Já usou o Balcão Virtual?", ["Sim", "Não"], horizontal=True)

    # ---- Perguntas por perfil (diferenças pequenas, sem “explodir” o questionário) ----
    atua_como = ""
    if tipo_usuario == "Advogado":
        atua_como = st.selectbox(
            "Atua como (opcional)",
            ["(não informar)", "Advogado(a) cível", "Advogado(a) tributário", "Advogado(a) previdenciário", "Advogado(a) trabalhista", "Outro"],
        )
        if atua_como == "(não informar)":
            atua_como = ""

    st.markdown("---")
    st.subheader("Avalie sua experiência (1 a 5)")

    def likert_q(label: str, key: str, help_txt: str = "") -> int:
        return st.radio(label, options=[1, 2, 3, 4, 5], format_func=lambda x: LIKERT[x], key=key, horizontal=True, help=help_txt)

    clareza = likert_q("Clareza das informações", "q_clareza")
    cordial = likert_q("Cordialidade e respeito", "q_cordial")
    facilidade = likert_q("Facilidade para entrar em contato", "q_facilidade")
    tempo_resp = likert_q("Tempo de resposta/retorno", "q_tempo")
    resol = likert_q("Resolutividade (capacidade de resolver sua demanda)", "q_resol")
    acess = likert_q("Acessibilidade/Inclusão (linguagem, atendimento a necessidades específicas)", "q_acess")
    usabilidade = likert_q("Usabilidade das ferramentas/canais (ex.: Balcão Virtual, e-mail, telefone)", "q_usabilidade")

    st.markdown("---")
    st.subheader("Audiências (se aplicável)")
    ja_part_aud = st.radio("Você participou de audiência na JFCE recentemente?", ["Não", "Sim"], horizontal=True)

    exp_aud = None
    if ja_part_aud == "Sim":
        exp_aud = likert_q("Como foi sua experiência na audiência?", "q_aud")

    st.markdown("---")
    st.subheader("Síntese")
    sat_geral = likert_q("Satisfação geral com o atendimento/serviço", "q_sat_geral")
    recomendacao = st.slider("Em uma escala de 0 a 10, qual a chance de você recomendar a JFCE?", 0, 10, 8)

    comentario = st.text_area("Comentário/sugestão (opcional)", placeholder="Escreva aqui (máx. 500 caracteres)...", max_chars=500)

    if st.button("Enviar resposta", type="primary"):
        row = {
            "timestamp": datetime.now(),
            "respondent_id": str(uuid.uuid4()),
            "unidade": unidade,
            "tipo_usuario": tipo_usuario,
            "atua_como": atua_como,
            "faixa_idade": faixa_idade,
            "genero": genero,
            "canal_contato_mais_usado": canal,
            "ja_usou_balcao_virtual": ja_usou_balcao,
            "ja_participou_audiencia": ja_part_aud,
            "clareza_informacoes": clareza,
            "cordialidade_respeito": cordial,
            "facilidade_contato": facilidade,
            "tempo_resposta": tempo_resp,
            "resolutividade": resol,
            "acessibilidade": acess,
            "usabilidade_ferramentas": usabilidade,
            "experiencia_audiencia": exp_aud,
            "satisfacao_geral": sat_geral,
            "recomendacao_0_10": recomendacao,
            "comentario_aberto": comentario.strip(),
        }
        append_row(row)
        st.success("Resposta registrada com sucesso. Obrigado(a)!")

else:
    st.subheader("Painel (análises)")

    df = load_data()

    if df.empty:
        st.info("Ainda não há respostas registradas.")
        st.stop()

    # Filtros
    st.sidebar.markdown("### Filtros")
    unidades = ["(todas)"] + sorted([x for x in df["unidade"].dropna().unique().tolist() if str(x).strip() != ""])
    tipos = ["(todos)"] + sorted([x for x in df["tipo_usuario"].dropna().unique().tolist() if str(x).strip() != ""])
    freq = st.sidebar.selectbox("Periodicidade", ["Diário", "Semanal", "Mensal"])
    freq_map = {"Diário": "D", "Semanal": "W", "Mensal": "M"}

    un_sel = st.sidebar.selectbox("Unidade", unidades)
    tp_sel = st.sidebar.selectbox("Tipo de usuário", tipos)

    dmin = df["timestamp"].min()
    dmax = df["timestamp"].max()
    date_range = st.sidebar.date_input("Período", value=(dmin.date(), dmax.date()))
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
    else:
        start, end = dmin.date(), dmax.date()

    f = df.copy()
    f = f[(f["timestamp"].dt.date >= start) & (f["timestamp"].dt.date <= end)]
    if un_sel != "(todas)":
        f = f[f["unidade"] == un_sel]
    if tp_sel != "(todos)":
        f = f[f["tipo_usuario"] == tp_sel]

    if f.empty:
        st.warning("Sem dados para os filtros selecionados.")
        st.stop()

    # KPIs e alertas (últimos 30 dias dentro do filtro)
    cutoff = max(f["timestamp"].max() - timedelta(days=30), f["timestamp"].min())
    last30 = f[f["timestamp"] >= cutoff]

    sat_last = pd.to_numeric(last30["satisfacao_geral"], errors="coerce").mean()
    nps_last = compute_nps(last30["recomendacao_0_10"])
    n_last = len(last30)

    c1, c2, c3 = st.columns(3)
    c1.metric("Respostas (período)", len(f))
    c2.metric("Satisfação média (últ. 30d)", f"{sat_last:.2f}" if pd.notna(sat_last) else "—", delta=f"Meta {TARGET_SATISFACAO_1_5}")
    c3.metric("NPS (últ. 30d)", f"{nps_last:.0f}" if pd.notna(nps_last) else "—", delta=f"Meta {TARGET_NPS}")

    if pd.notna(sat_last) and sat_last < TARGET_SATISFACAO_1_5:
        st.warning(f"⚠️ Satisfação média nos últimos 30 dias abaixo da meta ({sat_last:.2f} < {TARGET_SATISFACAO_1_5}).")
    if pd.notna(nps_last) and nps_last < TARGET_NPS:
        st.warning(f"⚠️ NPS nos últimos 30 dias abaixo da meta ({nps_last:.0f} < {TARGET_NPS}).")

    st.caption(f"Janela dos “últimos 30 dias” no filtro: **{cutoff.date()}** até **{f['timestamp'].max().date()}** (n={n_last}).")

    # Séries temporais
    f = f.sort_values("timestamp")
    f["periodo"] = period_floor(f["timestamp"], freq_map[freq])

    agg = f.groupby("periodo", as_index=False).agg(
        respostas=("respondent_id", "count"),
        satisfacao_media=("satisfacao_geral", lambda x: pd.to_numeric(x, errors="coerce").mean()),
        nps=("recomendacao_0_10", compute_nps),
    )

    st.markdown("---")
    st.subheader("Evolução temporal")

    if px is None:
        st.write("Instale plotly para gráficos interativos: `pip install plotly`")
        st.dataframe(agg)
    else:
        colA, colB = st.columns(2)
        with colA:
            fig1 = px.line(agg, x="periodo", y="satisfacao_media", markers=True, title="Satisfação média (1–5)")
            fig1.update_yaxes(range=[1, 5])
            st.plotly_chart(fig1, use_container_width=True)
        with colB:
            fig2 = px.line(agg, x="periodo", y="nps", markers=True, title="NPS (0–10)")
            fig2.update_yaxes(range=[-100, 100])
            st.plotly_chart(fig2, use_container_width=True)

        fig3 = px.bar(agg, x="periodo", y="respostas", title="Volume de respostas")
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    st.subheader("Dimensões (média no período selecionado)")

    dim_rows = []
    for col, label in DIMENSOES:
        s = pd.to_numeric(f[col], errors="coerce")
        dim_rows.append({"Dimensão": label, "Média": float(s.mean()) if s.notna().any() else float("nan")})
    dims = pd.DataFrame(dim_rows).sort_values("Média", ascending=False)

    if px is None:
        st.dataframe(dims)
    else:
        figd = px.bar(dims, x="Média", y="Dimensão", orientation="h", title="Média por dimensão (1–5)")
        figd.update_xaxes(range=[1, 5])
        st.plotly_chart(figd, use_container_width=True)

    st.markdown("---")
    st.subheader("Cortes rápidos")

    colX, colY = st.columns(2)
    with colX:
        by_unit = f.groupby("unidade", as_index=False).agg(
            respostas=("respondent_id", "count"),
            satisfacao=("satisfacao_geral", lambda x: pd.to_numeric(x, errors="coerce").mean()),
            nps=("recomendacao_0_10", compute_nps),
        ).sort_values("respostas", ascending=False)
        st.write("**Por unidade**")
        st.dataframe(by_unit, use_container_width=True)

    with colY:
        by_tipo = f.groupby("tipo_usuario", as_index=False).agg(
            respostas=("respondent_id", "count"),
            satisfacao=("satisfacao_geral", lambda x: pd.to_numeric(x, errors="coerce").mean()),
            nps=("recomendacao_0_10", compute_nps),
        ).sort_values("respostas", ascending=False)
        st.write("**Por tipo de usuário**")
        st.dataframe(by_tipo, use_container_width=True)

    st.markdown("---")
    st.subheader("Comentários (últimos 50)")
    comm = f.loc[f["comentario_aberto"].fillna("").str.strip() != "", ["timestamp", "unidade", "tipo_usuario", "comentario_aberto"]]
    comm = comm.sort_values("timestamp", ascending=False).head(50)
    if comm.empty:
        st.info("Sem comentários abertos no recorte atual.")
    else:
        st.dataframe(comm, use_container_width=True)
