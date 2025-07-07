# -*- coding: utf-8 -*-
import os
import requests # Importamos a nova ferramenta para fazer chamadas
from flask import Flask, request, jsonify
from openai import OpenAI

# URL do nosso n8n (o "ramal do assistente")
# Vamos preencher isso com a sua URL real no próximo passo.
N8N_WEBHOOK_URL = "https://alexgranja.app.n8n.cloud/webhook/gerente-ia"

# Inicialização da aplicação Flask
aplicacao = Flask(__name__)

# --- Configuração do Cliente para a IA Local (Ollama) ---
try:
    cliente_ia = OpenAI(
        base_url='http://localhost:11434/v1',
        api_key='ollama',
    )
    print("✅ Cliente de IA configurado para conversar com o Ollama.")
except Exception as e:
    print(f"🚨 Erro ao configurar o cliente de IA: {e}")
    cliente_ia = None

# --- Nova função para criar um ticket usando o n8n ---
def criar_ticket_no_n8n(descricao_problema):
    """Esta função envia os dados para o webhook do n8n."""
    try:
        # O n8n espera receber os dados em formato JSON
        dados_para_n8n = {"descricao": descricao_problema}
        
        # Faz a chamada POST para a URL do n8n
        resposta_n8n = requests.post(N8N_WEBHOOK_URL, json=dados_para_n8n)
        
        # Verifica se a chamada para o n8n foi bem-sucedida
        if resposta_n8n.status_code == 200:
            print("✅ Ticket criado com sucesso via n8n.")
            return True
        else:
            print(f"🚨 Erro ao chamar o n8n: {resposta_n8n.text}")
            return False
    except Exception as e:
        print(f"🚨 Erro na função criar_ticket_no_n8n: {e}")
        return False

# --- Nosso endpoint principal ---
@aplicacao.route('/api/ask-local-ai', methods=['GET'])
def perguntar_ia_local():
    if not cliente_ia:
        return jsonify({"erro": "O cliente de IA não foi inicializado."}), 500

    pergunta_usuario = request.args.get('pergunta')
    if not pergunta_usuario:
        return jsonify({"erro": "O parâmetro 'pergunta' é obrigatório."}), 400

    # --- Nova Lógica de Decisão ---
    # Por enquanto, uma lógica simples: se a pergunta contém "impressora" ou "computador", criamos um ticket.
    if "impressora" in pergunta_usuario.lower() or "computador" in pergunta_usuario.lower():
        
        sucesso_ticket = criar_ticket_no_n8n(pergunta_usuario)
        
        if sucesso_ticket:
            return jsonify({"resposta": "Entendido. Abri um chamado para o seu problema. A equipe de TI entrará em contato em breve."})
        else:
            return jsonify({"resposta": "Entendi seu problema, mas não consegui criar o chamado no sistema. Por favor, tente novamente mais tarde."})

    else:
        # Se não for um problema técnico, apenas conversamos com a IA
        try:
            resposta_chat = cliente_ia.chat.completions.create(
                model="gemma:2b",
                messages=[ {"role": "user", "content": pergunta_usuario} ]
            )
            resposta_final = resposta_chat.choices[0].message.content
            return jsonify({"resposta": resposta_final})
        except Exception as e:
            print(f"🚨 Erro ao comunicar com o Ollama: {e}")
            return jsonify({"erro": "Não foi possível conectar com a IA local."}), 500

# Ponto de entrada da aplicação
if __name__ == '__main__':
    aplicacao.run(debug=True, host='0.0.0.0', port=5000)