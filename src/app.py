import streamlit as st
import pandas as pd
import json
import os
from openai import OpenAI

# Configuração da Página
st.set_page_config(page_title="Agente Financeiro Inteligente", page_icon="💰")

st.title("🤖 BIA - Agente Financeiro Pessoal")

# 1. Configuração da API Key (Pode usar .env ou input lateral)
api_key = st.sidebar.text_input("Insira sua OpenAI API Key", type="password")
client = None
if api_key:
    client = OpenAI(api_key=api_key)

# 2. Função para Carregar a Base de Conhecimento
@st.cache_data
def carregar_dados():
    # Caminhos relativos baseados na estrutura do seu repositório
    base_path = os.path.join(os.path.dirname(__file__), '..', 'data')
    
    dados = {}
    try:
        # Carregar Perfil
        with open(os.path.join(base_path, 'perfil_investidor.json'), 'r', encoding='utf-8') as f:
            dados['perfil'] = json.load(f)
            
        # Carregar Produtos
        with open(os.path.join(base_path, 'produtos_financeiros.json'), 'r', encoding='utf-8') as f:
            dados['produtos'] = json.load(f)
            
        # Carregar Transações e Histórico (CSV)
        dados['transacoes'] = pd.read_csv(os.path.join(base_path, 'transacoes.csv'))
        dados['historico'] = pd.read_csv(os.path.join(base_path, 'historico_atendimento.csv'))
        
        return dados
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None

dados_cliente = carregar_dados()

# Visualização dos dados na barra lateral (para debug/demonstração)
if dados_cliente:
    with st.sidebar.expander("📂 Ver Dados do Cliente"):
        st.write("Perfil:", dados_cliente['perfil']['nome'])
        st.write("Saldo Atual:", dados_cliente['perfil']['renda_mensal']) # Exemplo
        st.write("Transações:", dados_cliente['transacoes'].head())

# 3. Construção do System Prompt (Engenharia de Prompt)
def construir_prompt_sistema(dados):
    if not dados:
        return "Você é um assistente financeiro útil."
    
    perfil = dados['perfil']
    produtos = json.dumps(dados['produtos'], ensure_ascii=False)
    
    # Resumir transações para não estourar contexto (últimas 5)
    transacoes_recentes = dados['transacoes'].tail(10).to_string(index=False)
    
    prompt = f"""
    Você é um Agente Financeiro Pessoal experiente e consultivo.
    
    SEU OBJETIVO:
    Ajudar o cliente {perfil['nome']} a gerir suas finanças, atingir a meta de '{perfil['objetivo_principal']}' e responder dúvidas sobre investimentos.
    
    PERFIL DO CLIENTE:
    - Idade: {perfil['idade']}
    - Perfil de Risco: {perfil['perfil_investidor']}
    - Renda Mensal: R$ {perfil['renda_mensal']}
    - Património Total: R$ {perfil['patrimonio_total']}
    
    HISTÓRICO RECENTE DE TRANSAÇÕES:
    {transacoes_recentes}
    
    PRODUTOS FINANCEIROS DISPONÍVEIS NA INSTITUIÇÃO:
    {produtos}
    
    REGRAS DE CONDUTA (IMPORTANTE):
    1. Baseie-se APENAS nos dados fornecidos. Se não souber, admita.
    2. Seja empático e use uma linguagem adequada ao nível de conhecimento do cliente.
    3. Para este cliente ({perfil['perfil_investidor']}), recomende apenas produtos adequados ao risco.
    4. Analise as transações para dar conselhos práticos de economia.
    5. Nunca invente valores ou rentabilidades que não estejam na lista de produtos.
    """
    return prompt

# 4. Interface de Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibir histórico de mensagens
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Captura de input do utilizador
if prompt := st.chat_input("Como posso ajudar com as suas finanças hoje?"):
    if not client:
        st.info("Por favor, insira a sua API Key da OpenAI na barra lateral para começar.")
        st.stop()

    # Adicionar mensagem do utilizador ao histórico
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gerar resposta do Agente
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model="gpt-4o-mini", # Ou gpt-3.5-turbo
            messages=[
                {"role": "system", "content": construir_prompt_sistema(dados_cliente)}
            ] + [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        )
        response = st.write_stream(stream)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
