# -*- coding: utf-8 -*-
import os
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL do nosso n8n (o "ramal do assistente")
N8N_WEBHOOK_URL = "https://n8n-production-5bbe.up.railway.app/webhook/gerente-ia"

# Inicialização da aplicação Flask
aplicacao = Flask(__name__)

# --- Configuração do Cliente para a IA (Gemini) ---
try:
    # Pega a chave da variável de ambiente
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    if not GEMINI_API_KEY:
        logger.error("🚨 GEMINI_API_KEY não encontrada nas variáveis de ambiente")
        raise ValueError("GEMINI_API_KEY é obrigatória")
    
    # Configura o Gemini
    genai.configure(api_key=GEMINI_API_KEY)
    cliente_ia = genai.GenerativeModel('gemini-pro')
    
    logger.info("✅ Cliente de IA configurado para conversar com o Gemini.")
    
except Exception as e:
    logger.error(f"🚨 Erro ao configurar o cliente de IA: {e}")
    cliente_ia = None

# --- Prompt personalizado para a Prosper ---
PROMPT_PROSPER = """
Você é a Prosper, uma assistente de IA especializada em ajudar funcionários de uma empresa.

Suas funções:
- Responder dúvidas sobre trabalho e produtividade
- Dar orientações sobre processos
- Oferecer suporte motivacional
- Ajudar com organização e planejamento

Seja sempre profissional, amigável e responda em português brasileiro.
"""

# --- Nova função para criar um ticket usando o n8n ---
def criar_ticket_no_n8n(descricao_problema, usuario="Usuário"):
    """Esta função envia os dados para o webhook do n8n."""
    try:
        # O n8n espera receber os dados em formato JSON
        dados_para_n8n = {
            "descricao": descricao_problema,
            "usuario": usuario
        }
        
        logger.info(f"📋 Criando ticket para: {usuario} - {descricao_problema}")
        
        # Faz a chamada POST para a URL do n8n
        resposta_n8n = requests.post(N8N_WEBHOOK_URL, json=dados_para_n8n, timeout=30)
        
        # Verifica se a chamada para o n8n foi bem-sucedida
        if resposta_n8n.status_code == 200:
            logger.info("✅ Ticket criado com sucesso via n8n.")
            return True
        else:
            logger.error(f"🚨 Erro ao chamar o n8n: Status {resposta_n8n.status_code} - {resposta_n8n.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("🚨 Timeout ao chamar o n8n")
        return False
    except Exception as e:
        logger.error(f"🚨 Erro na função criar_ticket_no_n8n: {e}")
        return False

# --- Função para conversar com a IA ---
def conversar_com_ia(pergunta):
    """Conversa com o Gemini"""
    try:
        # Monta o prompt completo
        prompt_completo = f"{PROMPT_PROSPER}\n\nPergunta do usuário: {pergunta}"
        
        # Gera a resposta
        response = cliente_ia.generate_content(prompt_completo)
        
        if response.text:
            logger.info("✅ Resposta gerada pela IA com sucesso")
            return response.text
        else:
            logger.error("🚨 IA retornou resposta vazia")
            return "Desculpe, não consegui gerar uma resposta adequada. Tente reformular sua pergunta."
            
    except Exception as e:
        logger.error(f"🚨 Erro ao comunicar com o Gemini: {e}")
        return "Desculpe, estou com dificuldades técnicas no momento. Tente novamente em alguns instantes."

# --- Endpoint de saúde ---
@aplicacao.route('/')
def home():
    return jsonify({
        "message": "Backend Prosper funcionando!",
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "ia_disponivel": cliente_ia is not None
    })

@aplicacao.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "Prosper Backend",
        "timestamp": datetime.now().isoformat()
    })

# --- Nosso endpoint principal ---
@aplicacao.route('/api/ask-local-ai', methods=['GET', 'POST'])
def perguntar_ia_local():
    if not cliente_ia:
        return jsonify({"erro": "O cliente de IA não foi inicializado."}), 500

    # Pega a pergunta do request (GET ou POST)
    if request.method == 'GET':
        pergunta_usuario = request.args.get('pergunta')
        usuario = request.args.get('usuario', 'Usuário')
    else:
        data = request.get_json()
        pergunta_usuario = data.get('pergunta', '') if data else ''
        usuario = data.get('usuario', 'Usuário') if data else 'Usuário'

    if not pergunta_usuario:
        return jsonify({"erro": "O parâmetro 'pergunta' é obrigatório."}), 400

    logger.info(f"📝 Pergunta recebida de {usuario}: {pergunta_usuario}")

    # --- Lógica de Decisão Melhorada ---
    # Palavras-chave que indicam problemas técnicos
    palavras_tecnicas = [
        "impressora", "computador", "problema", "lento", "quebrado", 
        "não funciona", "travou", "erro", "internet", "sistema",
        "software", "hardware", "mouse", "teclado", "monitor",
        "email", "outlook", "excel", "word", "powerpoint", "windows",
        "mac", "linux", "rede", "wifi", "cabo", "impressão",
        "scanner", "telefone", "ramal", "equipamento"
    ]
    
    # Verifica se é um problema técnico
    eh_problema_tecnico = any(palavra in pergunta_usuario.lower() for palavra in palavras_tecnicas)
    
    if eh_problema_tecnico:
        # Cria ticket no n8n
        sucesso_ticket = criar_ticket_no_n8n(pergunta_usuario, usuario)
        
        if sucesso_ticket:
            resposta = f"Entendido, {usuario}! 🎫 Abri um chamado para o seu problema técnico. A equipe de TI entrará em contato em breve para resolver a questão."
        else:
            resposta = "Entendi seu problema técnico, mas não consegui criar o chamado no sistema no momento. Por favor, tente novamente mais tarde ou entre em contato diretamente com o suporte."
            
        return jsonify({
            "resposta": resposta,
            "tipo": "ticket_criado",
            "timestamp": datetime.now().isoformat()
        })
    
    else:
        # Se não for um problema técnico, conversa com a IA
        resposta_ia = conversar_com_ia(pergunta_usuario)
        
        return jsonify({
            "resposta": resposta_ia,
            "tipo": "resposta_ia",
            "timestamp": datetime.now().isoformat()
        })

# --- Endpoint para webhook (compatibilidade com n8n) ---
@aplicacao.route('/api/webhook', methods=['POST'])
def webhook():
    """Endpoint específico para integração com n8n"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400
        
        descricao = data.get('descricao', '')
        usuario = data.get('usuario', 'Usuário')
        
        if not descricao:
            return jsonify({"erro": "Descrição é obrigatória"}), 400
        
        logger.info(f"🔗 Webhook recebido de {usuario}: {descricao}")
        
        # Usa a mesma lógica do endpoint principal
        palavras_tecnicas = [
            "impressora", "computador", "problema", "lento", "quebrado", 
            "não funciona", "travou", "erro", "internet", "sistema"
        ]
        
        eh_problema_tecnico = any(palavra in descricao.lower() for palavra in palavras_tecnicas)
        
        if eh_problema_tecnico:
            sucesso_ticket = criar_ticket_no_n8n(descricao, usuario)
            resposta = "Chamado criado com sucesso! A equipe de TI entrará em contato." if sucesso_ticket else "Erro ao criar chamado. Tente novamente."
        else:
            resposta = conversar_com_ia(descricao)
        
        return jsonify({
            "resposta": resposta,
            "usuario": usuario,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"🚨 Erro no webhook: {e}")
        return jsonify({
            "erro": "Erro interno",
            "resposta": "Desculpe, ocorreu um erro ao processar sua solicitação."
        }), 500

# --- Endpoint para testar conexão com n8n ---
@aplicacao.route('/api/test-n8n', methods=['GET'])
def testar_n8n():
    """Testa se o n8n está funcionando"""
    try:
        sucesso = criar_ticket_no_n8n("Teste de conexão", "Sistema")
        
        if sucesso:
            return jsonify({
                "status": "success",
                "message": "Conexão com n8n funcionando!",
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Erro ao conectar com n8n",
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Erro: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

# Ponto de entrada da aplicação
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    aplicacao.run(debug=False, host='0.0.0.0', port=port)