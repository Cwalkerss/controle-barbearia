import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import time

# --- CONFIGURAÇÃO DA PÁGINA (Equivalente às propriedades do Form Principal) ---
st.set_page_config(page_title="BarberSystem Pro", page_icon="✂️", layout="wide")

# --- ESTILIZAÇÃO (CSS PERSONALIZADO - Equivalente ao StyleBook do FMX) ---
st.markdown("""
<style>
    /* Cores principais */
    :root {
        --primary: #d4af37;
    }
    .stApp {
        background-color: #121212;
        color: #f4f4f4;
    }
    /* Botões */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        background-color: #d4af37;
        color: #121212;
        font-weight: bold;
        border: none;
    }
    .stButton>button:hover {
        background-color: #b5952f;
        color: white;
    }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e1e1e;
        border-radius: 4px;
        color: white;
    }
    .stTabs [aria-selected="true"] {
        background-color: #d4af37 !important;
        color: black !important;
    }
    /* Métricas */
    div[data-testid="metric-container"] {
        background-color: #1e1e1e;
        border-left: 5px solid #d4af37;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS (SQLite) ---
def init_db():
    conn = sqlite3.connect('barbearia.db')
    c = conn.cursor()
    # Tabela de Cortes (Fila/Histórico)
    c.execute('''CREATE TABLE IF NOT EXISTS cortes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  cliente TEXT, 
                  chegada DATETIME, 
                  saida DATETIME, 
                  pago BOOLEAN, 
                  valor REAL)''')
    # Tabela de Planos
    c.execute('''CREATE TABLE IF NOT EXISTS planos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  cliente TEXT, 
                  vencimento DATE, 
                  status TEXT,
                  obs TEXT)''')
    conn.commit()
    conn.close()

# Inicializa o DB ao abrir
init_db()

# --- FUNÇÕES AUXILIARES (Helpers) ---
def run_query(query, params=(), return_data=False):
    conn = sqlite3.connect('barbearia.db')
    if return_data:
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    else:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        conn.close()

# --- INTERFACE: MODO RECEPÇÃO (TABLET) ---
def show_kiosk():
    st.markdown("<h1 style='text-align: center; color: #d4af37;'>💈 Check-in Barbearia 💈</h1>", unsafe_allow_html=True)
    st.write("---")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.info("👋 Bem-vindo! Coloque seu nome abaixo para entrar na fila.")
        nome = st.text_input("Seu Nome Completo", key="kiosk_nome")
        
        # Equivalente ao TButton.OnClick
        if st.button("📍 CHEGUEI (Check-in)", use_container_width=True):
            if nome:
                agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                run_query("INSERT INTO cortes (cliente, chegada, pago, valor) VALUES (?, ?, ?, ?)", 
                          (nome, agora, False, 35.00))
                st.success(f"Show, {nome}! Você já está na lista do barbeiro.")
                time.sleep(2)
                st.rerun() # Atualiza a tela
            else:
                st.warning("Por favor, digite seu nome.")

# --- INTERFACE: MODO BARBEIRO (ADMIN) ---
def show_admin():
    st.title("✂️ Painel do Barbeiro")
    
    # Equivalente ao TTabControl
    tab1, tab2, tab3 = st.tabs(["💈 Fila & Cortes", "📋 Planos Mensais", "💰 Financeiro"])

    # === ABA 1: CORTES ===
    with tab1:
        st.header("Controle de Atendimentos")
        
        # Carregar dados (Equivalente ao Open do ClientDataSet)
        df_cortes = run_query("SELECT * FROM cortes ORDER BY chegada DESC", return_data=True)
        
        if not df_cortes.empty:
            for index, row in df_cortes.iterrows():
                # Card visual para cada cliente (Loop manual criando componentes)
                with st.container():
                    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                    
                    # Chegada formatada
                    chegada_dt = pd.to_datetime(row['chegada'])
                    hora_chegada = chegada_dt.strftime("%H:%M")
                    dia_chegada = chegada_dt.strftime("%d/%m")
                    
                    with c1:
                        st.markdown(f"**{row['cliente']}**")
                        st.caption(f"Chegou: {dia_chegada} às {hora_chegada}")
                    
                    with c2:
                        if row['saida']:
                            saida_dt = pd.to_datetime(row['saida'])
                            st.write(f"✅ Saiu às {saida_dt.strftime('%H:%M')}")
                        else:
                            if st.button("Finalizar Corte", key=f"fim_{row['id']}"):
                                agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                run_query("UPDATE cortes SET saida = ? WHERE id = ?", (agora, row['id']))
                                st.rerun()

                    with c3:
                        status_pag = "Pago ✅" if row['pago'] else "Pendente ❌"
                        st.write(status_pag)
                    
                    with c4:
                        if not row['pago']:
                            if st.button("Receber", key=f"pag_{row['id']}"):
                                run_query("UPDATE cortes SET pago = ? WHERE id = ?", (True, row['id']))
                                st.rerun()
                    
                    st.divider()
        else:
            st.info("Nenhum cliente registrado hoje.")

    # === ABA 2: PLANOS ===
    with tab2:
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.subheader("Novo Plano")
            with st.form("novo_plano"):
                p_nome = st.text_input("Nome do Cliente")
                p_venc = st.date_input("Data de Vencimento")
                p_status = st.selectbox("Status", ["Ativo", "Cancelado"])
                btn_add_plan = st.form_submit_button("Salvar Plano")
                
                if btn_add_plan and p_nome:
                    run_query("INSERT INTO planos (cliente, vencimento, status) VALUES (?, ?, ?)", 
                              (p_nome, p_venc, p_status))
                    st.success("Plano salvo!")
                    st.rerun()

        with c2:
            st.subheader("Clientes Mensalistas")
            df_planos = run_query("SELECT * FROM planos ORDER BY vencimento ASC", return_data=True)
            
            if not df_planos.empty:
                hoje = date.today()
                
                for i, row in df_planos.iterrows():
                    venc = pd.to_datetime(row['vencimento']).date()
                    dias_restantes = (venc - hoje).days
                    
                    cor_status = "green"
                    msg_status = row['status']
                    
                    # Lógica de cores (Equivalente ao OnGetText ou Styles)
                    if row['status'] == 'Ativo':
                        if dias_restantes < 0:
                            cor_status = "red"
                            msg_status = "ATRASADO"
                        elif dias_restantes <= 3:
                            cor_status = "orange"
                            msg_status = "Vence em Breve"
                    else:
                        cor_status = "gray"
                    
                    cols = st.columns([3, 2, 2, 1])
                    cols[0].write(f"**{row['cliente']}**")
                    cols[1].write(f"Venc: {venc.strftime('%d/%m/%Y')}")
                    cols[2].markdown(f":{cor_status}[{msg_status}]")
                    
                    if cols[3].button("🗑️", key=f"del_plan_{row['id']}"):
                         run_query("DELETE FROM planos WHERE id = ?", (row['id'],))
                         st.rerun()
            else:
                st.write("Nenhum plano cadastrado.")

    # === ABA 3: FINANCEIRO ===
    with tab3:
        st.header("Fluxo de Caixa")
        
        hoje = datetime.now()
        inicio_mes = hoje.replace(day=1, hour=0, minute=0, second=0).strftime("%Y-%m-%d")
        
        # Consultas de Agregação (SUM, COUNT)
        total_cortes_mes = run_query(f"SELECT COUNT(*) FROM cortes WHERE chegada >= '{inicio_mes}'", return_data=True).iloc[0,0]
        faturamento_mes = run_query(f"SELECT SUM(valor) FROM cortes WHERE chegada >= '{inicio_mes}' AND pago = 1", return_data=True).iloc[0,0]
        
        if faturamento_mes is None: faturamento_mes = 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Cortes no Mês", total_cortes_mes)
        m2.metric("Faturamento (Recebido)", f"R$ {faturamento_mes:.2f}")
        m3.metric("Ticket Médio", f"R$ {(faturamento_mes/total_cortes_mes if total_cortes_mes > 0 else 0):.2f}")

        st.subheader("Extrato Detalhado")
        # Equivalente ao TDBGrid
        st.dataframe(run_query("SELECT cliente, chegada, valor, pago FROM cortes WHERE pago = 1 ORDER BY chegada DESC", return_data=True), use_container_width=True)

# --- SIDEBAR: MENU LATERAL (Equivalente ao TMultiView) ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/483/483935.png", width=100)
st.sidebar.title("Menu")
modo = st.sidebar.radio("Selecione o modo:", ["Recepção (Tablet)", "Área do Barbeiro"])

# Controle de fluxo da aplicação
if modo == "Recepção (Tablet)":
    show_kiosk()
else:
    show_admin()