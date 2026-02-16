import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
from supabase import create_client, Client

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BarberSystem Pro", page_icon="✂️", layout="wide")

# --- CONEXÃO COM SUPABASE ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erro ao configurar Supabase. Verifique se o arquivo .streamlit/secrets.toml existe e está correto.")
    st.stop()

# --- ESTILIZAÇÃO (CSS) ---
st.markdown("""
<style>
    /* Cores principais */
    :root { --primary: #d4af37; }
    .stApp { background-color: #121212; color: #f4f4f4; }
    
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
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #1e1e1e; border-radius: 4px; color: white; }
    .stTabs [aria-selected="true"] { background-color: #d4af37 !important; color: black !important; }
    
    /* Métricas */
    div[data-testid="metric-container"] {
        background-color: #1e1e1e;
        border-left: 5px solid #d4af37;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- INTERFACE: MODO RECEPÇÃO (TABLET) ---
def show_kiosk():
    st.markdown("<h1 style='text-align: center; color: #d4af37;'>💈 Check-in Barbearia 💈</h1>", unsafe_allow_html=True)
    st.write("---")
    
    # --- CALLBACK (A Lógica que roda antes de desenhar a tela) ---
    def realizar_checkin():
        # Pega o valor da sessão (memória)
        nome = st.session_state.kiosk_nome
        
        if nome:
            try:
                agora = datetime.now().isoformat()
                data = {"cliente": nome, "chegada": agora, "pago": False, "valor": 35.00}
                
                # Envia para o Supabase
                supabase.table("cortes").insert(data).execute()
                
                # Feedback visual (Toast)
                st.toast(f"Tudo certo, {nome}! Aguarde ser chamado.", icon='✅')
                
                # Limpa o campo para o próximo cliente
                st.session_state.kiosk_nome = ""
                
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
        else:
            st.toast("Por favor, digite seu nome para continuar.", icon='⚠️')

    # --- LAYOUT VISUAL ---
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.info("👋 Bem-vindo! Coloque seu nome abaixo para entrar na fila.")
        
        # O Input apenas "aponta" para a key no session_state
        st.text_input("Seu Nome Completo", key="kiosk_nome")
        
        # O Botão dispara o callback
        st.button("📍 CHEGUEI (Check-in)", width="stretch", on_click=realizar_checkin)

# --- INTERFACE: MODO BARBEIRO (ADMIN) ---
def show_admin():
    st.title("✂️ Painel do Barbeiro - Supabase Cloud")
    
    tab1, tab2, tab3 = st.tabs(["💈 Fila & Cortes", "📋 Planos Mensais", "💰 Financeiro"])

    # === ABA 1: CORTES ===
    with tab1:
        st.header("Controle de Atendimentos")
        
        # Busca dados no Supabase
        response = supabase.table("cortes").select("*").order("chegada", desc=True).execute()
        df_cortes = pd.DataFrame(response.data)
        
        if not df_cortes.empty:
            df_cortes['chegada'] = pd.to_datetime(df_cortes['chegada'])
            
            for index, row in df_cortes.iterrows():
                with st.container():
                    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                    
                    hora_chegada = row['chegada'].strftime("%H:%M")
                    dia_chegada = row['chegada'].strftime("%d/%m")
                    
                    with c1:
                        st.markdown(f"**{row['cliente']}**")
                        st.caption(f"Chegou: {dia_chegada} às {hora_chegada}")
                    
                    with c2:
                        if row['saida']:
                            saida_dt = pd.to_datetime(row['saida'])
                            st.write(f"✅ Saiu às {saida_dt.strftime('%H:%M')}")
                        else:
                            if st.button("Finalizar Corte", key=f"fim_{row['id']}", width="stretch"):
                                agora = datetime.now().isoformat()
                                supabase.table("cortes").update({"saida": agora}).eq("id", row['id']).execute()
                                st.rerun()

                    with c3:
                        status_pag = "Pago ✅" if row['pago'] else "Pendente ❌"
                        st.write(status_pag)
                    
                    with c4:
                        if not row['pago']:
                            if st.button("Receber", key=f"pag_{row['id']}", width="stretch"):
                                supabase.table("cortes").update({"pago": True}).eq("id", row['id']).execute()
                                st.rerun()
                    
                    st.divider()
        else:
            st.info("Nenhum cliente registrado.")

    # === ABA 2: PLANOS ===
    with tab2:
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.subheader("Novo Plano")
            with st.form("novo_plano"):
                p_nome = st.text_input("Nome do Cliente")
                p_venc = st.date_input("Data de Vencimento", format="DD/MM/YYYY")
                p_status = st.selectbox("Status", ["Ativo", "Cancelado"])
                
                # width="stretch" não funciona dentro de st.form_submit_button ainda em algumas versões, 
                # mas se der erro, remova o argumento width.
                btn_add_plan = st.form_submit_button("Salvar Plano", use_container_width=True) 
                
                if btn_add_plan and p_nome:
                    data = {
                        "cliente": p_nome, 
                        "vencimento": p_venc.isoformat(), 
                        "status": p_status
                    }
                    supabase.table("planos").insert(data).execute()
                    st.success("Plano salvo!")
                    st.rerun()

        with c2:
            st.subheader("Clientes Mensalistas")
            response = supabase.table("planos").select("*").order("vencimento", desc=False).execute()
            df_planos = pd.DataFrame(response.data)
            
            if not df_planos.empty:
                hoje = date.today()
                
                for i, row in df_planos.iterrows():
                    venc = pd.to_datetime(row['vencimento']).date()
                    dias_restantes = (venc - hoje).days
                    
                    cor_status = "green"
                    msg_status = row['status']
                    
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
                         supabase.table("planos").delete().eq("id", row['id']).execute()
                         st.rerun()
            else:
                st.write("Nenhum plano cadastrado.")

    # === ABA 3: FINANCEIRO ===
    with tab3:
        st.header("Fluxo de Caixa")
        
        hoje = datetime.now()
        inicio_mes = hoje.replace(day=1, hour=0, minute=0, second=0).isoformat()
        
        # Métricas
        res_total = supabase.table("cortes").select("*", count="exact").gte("chegada", inicio_mes).execute()
        total_cortes_mes = res_total.count
        
        res_fat = supabase.table("cortes").select("valor").gte("chegada", inicio_mes).eq("pago", True).execute()
        df_fat = pd.DataFrame(res_fat.data)
        faturamento_mes = df_fat['valor'].sum() if not df_fat.empty else 0.0

        m1, m2, m3 = st.columns(3)
        m1.metric("Cortes no Mês", total_cortes_mes)
        m2.metric("Faturamento (Recebido)", f"R$ {faturamento_mes:.2f}")
        ticket_medio = faturamento_mes/total_cortes_mes if total_cortes_mes > 0 else 0
        m3.metric("Ticket Médio", f"R$ {ticket_medio:.2f}")

        st.subheader("Extrato Detalhado")
        
        res_grid = supabase.table("cortes").select("cliente, chegada, valor, pago").eq("pago", True).order("chegada", desc=True).execute()
        df_grid = pd.DataFrame(res_grid.data)
        if not df_grid.empty:
             df_grid['chegada'] = pd.to_datetime(df_grid['chegada'])
        
        # Correção do Warning do Dataframe (use_container_width ainda é o padrão aceito no st.dataframe nas docs atuais, 
        # mas se seu terminal pediu width, tente a linha abaixo comentada se a atual der erro)
        st.dataframe(df_grid, use_container_width=True) 
        # Se o warning persistir, troque a linha acima por: st.dataframe(df_grid, width=1000)

# --- SIDEBAR ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/483/483935.png", width=100)
st.sidebar.title("Menu")
modo = st.sidebar.radio("Selecione o modo:", ["Recepção (Tablet)", "Área do Barbeiro"])

if modo == "Recepção (Tablet)":
    show_kiosk()
else:
    show_admin()