import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

st.set_page_config(page_title='FAST', layout='wide')

# ========== CONEXÃO BANCO DE DADOS ==========
conn = sqlite3.connect("dados_fast.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS produtos (
    codigo TEXT PRIMARY KEY,
    descricao TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS padaria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lote TEXT,
    codigo TEXT,
    descricao TEXT,
    quantidade REAL,
    unidade TEXT,
    motivo TEXT,
    data TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS carnes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lote TEXT,
    codigo_origem TEXT,
    descricao TEXT,
    quantidade REAL,
    unidade TEXT,
    codigo_destino TEXT,
    data TEXT
)
""")
conn.commit()

# ========== FUNÇÕES ==========
def carregar_base_produtos(uploaded_file):
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.lower()
    df = df[["codigo", "descricao"]]
    df.to_sql("produtos", conn, if_exists="replace", index=False)
    st.success("Base de produtos carregada com sucesso!")

def buscar_descricao(codigo):
    if not codigo:
        return ""
    cursor.execute("SELECT descricao FROM produtos WHERE codigo = ?", (codigo,))
    res = cursor.fetchone()
    return res[0] if res else ""

def exportar_padaria():
    df = pd.read_sql("SELECT * FROM padaria", conn)
    if df.empty:
        st.warning("Nenhum dado encontrado para exportar.")
        return

    total_desc = df.groupby("descricao")["quantidade"].sum().reset_index()
    total_motivo = df.groupby("motivo")["quantidade"].sum().reset_index()

    with pd.ExcelWriter("padaria_export.xlsx") as writer:
        df.to_excel(writer, sheet_name="Detalhado", index=False)
        total_desc.to_excel(writer, sheet_name="Por Descrição", index=False)
        total_motivo.to_excel(writer, sheet_name="Por Motivo", index=False)
    st.success("Exportação realizada com sucesso!")
    with open("padaria_export.xlsx", "rb") as f:
        st.download_button("📥 Baixar Excel (Padaria)", data=f, file_name="padaria_export.xlsx")

def exportar_carnes():
    df = pd.read_sql("SELECT * FROM carnes", conn)
    if df.empty:
        st.warning("Nenhum dado encontrado para exportar.")
        return

    total_desc = df.groupby("descricao")["quantidade"].sum().reset_index()
    total_destino = df.groupby("codigo_destino")["quantidade"].sum().reset_index()

    with pd.ExcelWriter("carnes_export.xlsx") as writer:
        df.to_excel(writer, sheet_name="Detalhado", index=False)
        total_desc.to_excel(writer, sheet_name="Por Descrição", index=False)
        total_destino.to_excel(writer, sheet_name="Por Destino", index=False)
    st.success("Exportação realizada com sucesso!")
    with open("carnes_export.xlsx", "rb") as f:
        st.download_button("📥 Baixar Excel (Carnes)", data=f, file_name="carnes_export.xlsx")

# ========== INTERFACE ==========
st.title("📊 FAST - Sistema de Transformações e Requisições")
tabs = st.tabs(["📦 Padaria / Confeitaria", "🥩 Transformações Carnes", "📁 Carregar Base de Produtos", "📦 Lotes Gerados"])

# ========== ABA BASE DE PRODUTOS ==========
with tabs[2]:
    st.header("📁 Carregar Base de Produtos")
    arquivo = st.file_uploader("Selecione o arquivo Excel com as colunas 'codigo' e 'descricao'", type="xlsx")
    if arquivo:
        carregar_base_produtos(arquivo)

# ========== ABA PADARIA ==========
with tabs[0]:
    st.header("📦 Lançamentos - Padaria e Confeitaria")

    codigo_padaria = st.text_input("Código do Produto (Padaria / Confeitaria)", key="codigo_padaria")
    descricao_padaria = buscar_descricao(codigo_padaria)

    with st.form("form_padaria"):
        lote = st.text_input("Lote")
        descricao = st.text_input("Descrição", value=descricao_padaria)
        quantidade = st.number_input("Quantidade", min_value=0.0, step=0.01)
        unidade = st.selectbox("Unidade", ["kg", "un"])
        motivo = st.selectbox("Motivo", ["Avaria", "Doação", "Refeitório", "Inventário"])
        codigo = codigo_padaria
        enviar = st.form_submit_button("Registrar")

    if enviar:
        if not (lote and codigo and descricao):
            st.error("Preencha todos os campos obrigatórios: lote, código e descrição.")
        else:
            data = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("""
                INSERT INTO padaria (lote, codigo, descricao, quantidade, unidade, motivo, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (lote, codigo, descricao, quantidade, unidade, motivo, data))
            conn.commit()
            st.success("Registro salvo com sucesso!")

    st.divider()
    st.subheader("📋 Registros por Lote (Padaria)")
    lote_busca = st.text_input("Buscar lote para visualizar ou excluir (Padaria)", key="lote_busca_padaria")
    if lote_busca:
        df_lote = pd.read_sql("SELECT * FROM padaria WHERE lote = ?", conn, params=(lote_busca,))
        st.dataframe(df_lote, use_container_width=True)
        if st.button("🗑️ Excluir Lote (Padaria)", key="excluir_lote_padaria"):
            cursor.execute("DELETE FROM padaria WHERE lote = ?", (lote_busca,))
            conn.commit()
            st.warning("Lote excluído com sucesso.")
    exportar_padaria()

# ========== ABA CARNES ==========
with tabs[1]:
    st.header("🥩 Transformações - Carne Bovina")

    codigo_carnes = st.text_input("Código Origem (Carnes)", key="codigo_carnes")
    descricao_carnes = buscar_descricao(codigo_carnes)

    with st.form("form_carnes"):
        lote = st.text_input("Lote")
        descricao = st.text_input("Descrição", value=descricao_carnes)
        quantidade = st.number_input("Quantidade", min_value=0.0, step=0.01)
        unidade = st.selectbox("Unidade", ["kg", "un"])
        destino = st.text_input("Código Destino")
        codigo_origem = codigo_carnes
        enviar = st.form_submit_button("Registrar Transformação")

    if enviar:
        if not (lote and codigo_origem and descricao and destino):
            st.error("Preencha todos os campos obrigatórios: lote, código origem, descrição e código destino.")
        else:
            data = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("""
                INSERT INTO carnes (lote, codigo_origem, descricao, quantidade, unidade, codigo_destino, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (lote, codigo_origem, descricao, quantidade, unidade, destino, data))
            conn.commit()
            st.success("Transformação registrada com sucesso!")

    st.divider()
    st.subheader("📋 Registros por Lote (Carnes)")
    lote_busca = st.text_input("Buscar lote para visualizar ou excluir (Carnes)", key="lote_busca_carnes")
    if lote_busca:
        df_lote = pd.read_sql("SELECT * FROM carnes WHERE lote = ?", conn, params=(lote_busca,))
        st.dataframe(df_lote, use_container_width=True)
        if st.button("🗑️ Excluir Lote (Carnes)", key="excluir_lote_carnes"):
            cursor.execute("DELETE FROM carnes WHERE lote = ?", (lote_busca,))
            conn.commit()
            st.warning("Lote excluído com sucesso.")
    exportar_carnes()

# ========== ABA LOTES GERADOS ==========
with tabs[3]:
    st.header("📦 Lotes Gerados - Padaria e Carnes")

    # Lista de lotes da padaria e carnes
    lotes_padaria = pd.read_sql("SELECT DISTINCT lote FROM padaria ORDER BY lote DESC", conn)["lote"].tolist()
    lotes_carnes = pd.read_sql("SELECT DISTINCT lote FROM carnes ORDER BY lote DESC", conn)["lote"].tolist()

    tipo_lote = st.selectbox("Escolha a categoria", ["Padaria / Confeitaria", "Carnes"])
    if tipo_lote == "Padaria / Confeitaria":
        lote_selecionado = st.selectbox("Selecione o lote", lotes_padaria)
        if lote_selecionado:
            df_lote = pd.read_sql("SELECT * FROM padaria WHERE lote = ?", conn, params=(lote_selecionado,))
            st.dataframe(df_lote, use_container_width=True)
    else:
        lote_selecionado = st.selectbox("Selecione o lote", lotes_carnes)
        if lote_selecionado:
            df_lote = pd.read_sql("SELECT * FROM carnes WHERE lote = ?", conn, params=(lote_selecionado,))
            st.dataframe(df_lote, use_container_width=True)
