import os
import json
import requests # <--- Importado
import google.generativeai as genai
from fastapi import FastAPI, Request, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv


# --- CONFIGURAÇÃO INICIAL ---
load_dotenv()
# Lê os tokens
_verify_token_bruto = os.getenv("VERIFY_TOKEN")
_gemini_key_bruto = os.getenv("GEMINI_API_KEY")
_wa_token_bruto = os.getenv("WHATSAPP_ACCESS_TOKEN")
_wa_id_bruto = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

MY_VERIFY_TOKEN = _verify_token_bruto.strip() if _verify_token_bruto else None
GEMINI_API_KEY = _gemini_key_bruto.strip() if _gemini_key_bruto else None
WHATSAPP_ACCESS_TOKEN = _wa_token_bruto.strip() if _wa_token_bruto else None
WHATSAPP_PHONE_NUMBER_ID = _wa_id_bruto.strip() if _wa_id_bruto else None

# !!!!!!!!!!!!! ADICIONE ESTAS LINHAS DE DEBUG !!!!!!!!!!!!!
print("--- INICIANDO SERVIDOR - VERIFICANDO TOKENS ---")
print(f"VERIFY_TOKEN: {'CARREGADO' if MY_VERIFY_TOKEN else '!!! NAO CARREGADO !!!'}")
print(f"GEMINI_API_KEY: {'CARREGADO' if GEMINI_API_KEY else '!!! NAO CARREGADO !!!'}")
print(f"WHATSAPP_ACCESS_TOKEN: {'CARREGADO' if WHATSAPP_ACCESS_TOKEN else '!!! NAO CARREGADO !!!'}")
print(f"WHATSAPP_PHONE_NUMBER_ID: {'CARREGADO' if WHATSAPP_PHONE_NUMBER_ID else '!!! NAO CARREGADO !!!'}")
print(f"Valor do ID (para conferir): {WHATSAPP_PHONE_NUMBER_ID}")
print("--------------------------------------------------")
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

app = FastAPI()

# Configura o cliente do Google Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('models/gemini-pro-latest') # <-- Corrigido
    print("API do Gemini configurada com sucesso.")
except Exception as e:
    print(f"ERRO: Falha ao configurar a API do Gemini. Verifique a GEMINI_API_KEY. Erro: {e}")
    model = None

# --- PROMPT DE SISTEMA (Sem alterações) ---
SYSTEM_PROMPT = """
[IDENTIDADE E OBJETIVO PRINCIPAL]
Sua identidade é "Assistente de Clínica (Backend)". Você é um Agente de IA de processamento de linguagem natural. Seu trabalho NÃO é conversar diretamente com o usuário final. Seu trabalho é receber uma string (a mensagem do usuário) e retornar um objeto JSON estruturado que instrui o sistema de backend (Python) sobre qual AÇÃO tomar.

[REGRAS DE COMPORTAMENTO E VALIDAÇÃO (CONSTRUÇÕES)]
1.  **ESCOPO ESTRITO:** Seu único foco é a administração da clínica. Intenções permitidas: 'agendamento', 'cancelamento', 'consulta_horarios', 'consulta_informacoes_clinica', 'saudacao', 'despedida'.
2.  **CLASSIFICAÇÃO DE INTENÇÃO:** Se a intenção não estiver no escopo (ex: "qual a previsão do tempo?"), classifique como 'fora_de_escopo' e determine a `acao_requerida` como 'RESPONDER_AO_USUARIO' com uma mensagem padrão de recusa.
3.  **GERENCIAMENTO DE AMBIGUIDADE:** Se uma solicitação for incompleta (ex: "Quero marcar consulta"), sua `acao_requerida` deve ser 'RESPONDER_AO_USUARIO' e a `resposta_para_usuario` deve ser uma pergunta para obter os dados faltantes (ex: "Claro. Para qual especialidade você gostaria de agendar?").
4.  **TOM DE VOZ (Para Respostas):** As mensagens em `resposta_para_usuario` devem ser profissionais, claras, concisas e amigáveis.

[FERRAMENTAS DISPONÍVEIS (Acesso ao "Script Python")]
Você NÃO executa código. Você solicita a execução de funções pré-definidas pelo backend.
* `tool_consultar_horarios(especialidade: string)`
* `tool_obter_info_clinica(topico: string)` (tópicos: 'endereco', 'horario_funcionamento', 'convenios_aceitos')

[FORMATO DE SAÍDA OBRATÓRIO (JSON)]
Sua resposta DEVE ser um único bloco de código JSON. Não inclua markdown (```json) ou texto antes ou depois.

{
  "status_processamento": "...",
  "intencao_detectada": "...",
  "entidades_extraidas": { "especialidade": null, "topico": null },
  "acao_requerida": "...",
  "payload_acao": {
    "resposta_para_usuario": "...",
    "ferramenta_solicitada": {
      "nome": null,
      "parametros": {}
    }
  },
  "log_para_desenvolvedor": "..."
}
"""
generation_config = { "response_mime_type": "application/json" }

# ---
# FUNÇÃO DE ENVIO DE MENSAGEM (NOVO!)
# ---
def send_whatsapp_message(to_phone_number, message_text):
    """
    Envia uma mensagem de texto simples para o usuário via API da Meta.
    """
    url = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone_number,
        "type": "text",
        "text": {"body": message_text},
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status() # Lança um erro se a resposta for 4xx ou 5xx
        
        print(f"--- Mensagem enviada para {to_phone_number} ---")
        print(f"Conteúdo: {message_text}")
        print(f"Resposta da Meta: {response.json()}")
        print("-----------------------------------------")
        
    except requests.exceptions.RequestException as e:
        print(f"================================================================")
        print(f"ERRO FATAL AO TENTAR ENVIAR MENSAGEM (requests.exceptions.RequestException):")
        print(f"Tipo exato do Erro: {type(e)}")
        print(f"Mensagem de Erro completa: {e}")
        print(f"================================================================")
        print(f"Payload que tentamos enviar: {payload}")
        print(f"URL que tentamos acessar: {url}")
# ---
# ROTA 1: Verificação do Webhook (GET) - (Sem alterações)
# ---
@app.get("/webhook/whatsapp")
async def verify_webhook(
    request: Request,
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
):
    print("Recebendo requisição de verificação...")
    if hub_mode == "subscribe" and hub_verify_token == MY_VERIFY_TOKEN:
        print("Verificação do Webhook bem-sucedida!")
        return PlainTextResponse(content=hub_challenge, status_code=200)
    else:
        print(f"Falha na verificação. Token recebido: {hub_verify_token}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token de verificação inválido.",
        )

# ---
# ROTA 2: Recebimento de Mensagens (POST) - (Atualizada)
# ---
@app.post("/webhook/whatsapp")
async def receive_message(request: Request):
    
    request_data = {}
    try:
        request_data = await request.json()
        print("--- Nova Mensagem Recebida (Payload Completo) ---")
        print(json.dumps(request_data, indent=2, ensure_ascii=False))
        
        user_message = "Mensagem não encontrada"
        user_phone_number = None # <-- NOVO: Precisamos saber para quem responder
        
        if (
            "entry" in request_data and request_data["entry"] and
            "changes" in request_data["entry"][0] and request_data["entry"][0]["changes"] and
            "value" in request_data["entry"][0]["changes"][0] and
            "messages" in request_data["entry"][0]["changes"][0]["value"] and request_data["entry"][0]["changes"][0]["value"]["messages"] and
            "text" in request_data["entry"][0]["changes"][0]["value"]["messages"][0] and
            "body" in request_data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]
        ):
            user_message = request_data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
            user_phone_number = request_data["entry"][0]["changes"][0]["value"]["messages"][0]["from"] # <-- NOVO: Captura o número do usuário
            
            print(f"--- Mensagem do Usuário Extraída ---")
            print(f"De: {user_phone_number}")
            print(f"Texto: {user_message}")
            print("-----------------------------------")
            
            if not model:
                raise HTTPException(status_code=500, detail="API do Gemini não configurada.")
            
            print("Enviando para o Gemini...")
            
            chat = model.start_chat(history=[
                {"role": "user", "parts": [SYSTEM_PROMPT]},
                {"role": "model", "parts": ["OK. Estou pronto para receber a mensagem do usuário."]}
            ])
            response = chat.send_message(user_message, generation_config=generation_config)
            
            ai_json_response_str = response.text
            print("--- Resposta JSON do Gemini Recebida ---")
            print(ai_json_response_str)
            print("--------------------------------------")
            
            # --- LÓGICA DA FASE 3 (NOVO!) ---
            try:
                # Converte a string JSON em um objeto Python
                ai_data = json.loads(ai_json_response_str)
                
                # O "Cérebro" do Agente: Decide o que fazer
                if ai_data.get("acao_requerida") == "RESPONDER_AO_USUARIO":
                    resposta_texto = ai_data["payload_acao"]["resposta_para_usuario"]
                    
                    # Chama nossa nova função!
                    if user_phone_number:
                        send_whatsapp_message(user_phone_number, resposta_texto)
                    else:
                        print("ERRO: JSON do Gemini OK, mas número do usuário não foi encontrado.")
                        
                elif ai_data.get("acao_requerida") == "EXECUTAR_FERRAMENTA":
                    # FASE 4 (Ainda não implementada):
                    # Aqui é onde chamaríamos o SQLite.
                    # Por enquanto, vamos apenas avisar o usuário.
                    print("AÇÃO: A IA solicitou dados do DB (Fase 4).")
                    send_whatsapp_message(user_phone_number, "Entendi, estou consultando os dados... (Função em desenvolvimento)")
                    
                else:
                    print(f"Ação desconhecida recebida da IA: {ai_data.get('acao_requerida')}")
                    
            except json.JSONDecodeError:
                print("ERRO FATAL: Gemini retornou um JSON inválido. Não foi possível processar a ação.")
                print(ai_json_response_str) # Imprime o JSON quebrado
            
        else:
            print("Webhook recebido, mas não é uma mensagem de texto do usuário. Ignorando.")

        return {"status": "ok"}
    
    except Exception as e:
        print(f"Erro inesperado ao processar a mensagem: {e}")
        print("Payload bruto que causou o erro:")
        print(request_data)
        return {"status": "ok_with_error"}

# ---
# ROTA 3: Health check (Sem alterações)
# ---
@app.get("/")
async def root():
    return {"status": "Servidor do Chatbot está rodando!"}