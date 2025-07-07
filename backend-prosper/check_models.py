import os
import google.generativeai as genai

# Pega a chave da variável de ambiente que já configuramos
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("🚨 Chave de API do Gemini não encontrada. Configure a variável de ambiente $env:GEMINI_API_KEY.")
else:
    try:
        genai.configure(api_key=api_key)

        print("✅ Modelos de IA generativa disponíveis que suportam 'generateContent':")

        # Pede ao Google a lista de modelos
        for model in genai.list_models():
            # Verifica se o modelo suporta o método que queremos usar
            if 'generateContent' in model.supported_generation_methods:
                print(model.name)

    except Exception as e:
        print(f"Ocorreu um erro: {e}")