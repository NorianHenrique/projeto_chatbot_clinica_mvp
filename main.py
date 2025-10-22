import os
import json
import requests
import google.generativeai as genai
from fastapi import FastAPI, Request, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

# --- NOVO: Importando nossas ferramentas do banco de dados ---
from database_tools import tool_obter_info_clinica

# --- CONFIGURAÇÃO INICIAL (Com o .strip() que fizemos) ---
load_dotenv()

_verify_token_bruto = os.getenv("VERIFY_TOKEN")
_gemini_key_bruto = os.getenv("GEMINI_API_KEY")
_wa_token_bruto = os.getenv("WHATSAPP_ACCESS_TOKEN")
_wa_id_bruto = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

MY_VERIFY_TOKEN = _verify_token_bruto.strip() if _verify_token_bruto else None
GEMINI_API_KEY = _gemini_key_bruto.strip() if _gemini_key_bruto else None
WHATSAPP_ACCESS_TOKEN = _wa_token_bruto.strip() if _wa_token_bruto else None
WHATSAPP_PHONE_NUMBER_ID = _wa_id_bruto.strip() if _wa_id_bruto else None

# --- DEBUG: Verificando tokens LIMPOS ---
print("--- INICIANDO SERVIDOR - VERIFICANDO TOKENS (Pós-limpeza) ---")
print(f"VERIFY_TOKEN: {'CARREGADO' if MY_VERIFY_TOKEN else '!!! NAO CARREGADO !!!'}")
print(f"GEMINI_API_KEY: {'CARREGADO' if GEMINI_API_KEY else '!!! NAO CARREGADO !!!'}")
print(f"WHATSAPP_ACCESS_TOKEN: {'CARREGADO' if WHATSAPP_ACCESS_TOKEN else '!!! NAO CARREGADO !!!'}")
print(f"WHATSAPP_PHONE_NUMBER_ID: {'CARREGADO' if WHATSAPP_PHONE_NUMBER_ID else '!!! NAO CARREGADO !!!'}")
print(f"Valor do ID (para conferir): {WHATSAPP_PHONE_NUMBER_ID}")
print("--------------------------------------------------")

app = FastAPI()

# Configura o cliente do Google Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('models/gemini-pro-latest') 
    print("API do Gemini configurada com sucesso.")
except Exception as e:
    print(f"ERRO: Falha ao configurar a API do Gemini. Verifique a GEMINI_API_KEY. Erro: {e}")
    model = None

# --- NOVO: Mapeamento das Ferramentas ---
# Isso permite que o Python saiba qual função chamar
AVAILABLE_TOOLS = {
    "tool_obter_info_clinica": tool_obter_info_clinica,
    # (No futuro, poderíamos adicionar:
    # "tool_consultar_horarios": tool_consultar_horarios
    # )
}

# --- PROMPT DE SISTEMA (ATUALIZADO) ---
SYSTEM_PROMPT = """
[IDENTIDADE E OBJETIVO PRINCIPAL]
Sua identidade é "Assistente de Clínica (Backend)". Você é um Agente de IA de processamento de linguagem natural. Seu trabalho NÃO é conversar diretamente com o usuário final. Seu trabalho é receber uma string (a mensagem do usuário) e retornar um objeto JSON estruturado que instrui o sistema de backend (Python) sobre qual AÇÃO tomar.

[REGRAS DE COMPORTAMENTO E VALIDAÇÃO (CONSTRUÇÕES)]
1.  **ESCOPO ESTRITO:** Seu único foco é a administração da clínica. Intenções permitidas: 'agendamento', 'cancelamento', 'consulta_horarios', 'consulta_informacoes_clinica', 'saudacao', 'despedida'.
2.  **CLASSIFICAÇÃO DE INTENÇÃO:** Se a intenção não estiver no escopo (ex: "qual a previsão do tempo?"), classifique como 'fora_de_escopo' e determine a `acao_requerida` como 'RESPONDER_AO_USUARIO' com uma mensagem padrão de recusa.
3.  **GERENCIAMENTO DE AMBIGUIDADE:** Se uma solicitação for incompleta (ex: "Quero marcar consulta"), sua `acao_requerida` deve ser 'RESPONDER_AO_USUARIO' e a `resposta_para_usuario` deve ser uma pergunta para obter os dados faltantes (ex: "Claro. Para qual especialidade você gostaria de agendar?").
4.  **TOM DE VOZ (Para Respostas):** As mensagens em `resposta_para_usuario` devem ser profissionais, claras, concisas e amigáveis.
5.  **--- ATUALIZADO: FLUXO RAG (Retrieval-Augmented Generation) ---**
    Se sua `acao_requerida` for `EXECUTAR_FERRAMENTA`, o sistema Python irá rodar a ferramenta e te devolver o resultado em uma nova mensagem (ex: "OK, a ferramenta foi executada. O resultado é: 'Rua das Flores, 123'"). Sua próxima tarefa é usar *apenas* essa informação para gerar a resposta final para o usuário, com `acao_requerida: "RESPONDER_AO_USUARIO"`.

[FERRAMENTAS DISPONÍVEIS (Acesso ao "Script Python")]
Você NÃO executa código. Você solicita a execução de funções pré-definidas pelo backend.
* `tool_obter_info_clinica(topic: str)` (tópicos: 'endereco', 'horario_funcionamento', 'convenios_aceitos')

[FORMATO DE SAÍDA OBRATÓRIO (JSON)]
(O formato JSON continua o mesmo)
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
    # A URL está correta, usando o ID do número de telefone
    url = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "messaging_product": "whatsapp",
        # O número de destino deve estar no formato internacional, sem o '+'
        "to": to_phone_number, 
        "type": "text",
        "text": {"body": message_text},
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload )
        response.raise_for_status() # Lança um erro se a resposta for 4xx ou 5xx
        
        print(f"--- Mensagem enviada para {to_phone_number} ---")
        print(f"Conteúdo: {message_text}")
        print(f"Resposta da Meta: {response.json()}")
        print("-----------------------------------------")
        
    except requests.exceptions.HTTPError as http_err:
        # Captura o erro 400 e tenta extrair a mensagem de erro detalhada da Meta
        try:
            error_details = response.json( )
            error_message = error_details.get("error", {}).get("message", "Detalhes do erro não disponíveis.")
            error_code = error_details.get("error", {}).get("code", "N/A")
            
            print(f"================================================================")
            print(f"ERRO FATAL AO TENTAR ENVIAR MENSAGEM (HTTP {http_err.response.status_code} ):")
            print(f"CÓDIGO DE ERRO DA META: {error_code}")
            print(f"MENSAGEM DE ERRO DETALHADA: {error_message}")
            print(f"================================================================")
            print(f"Payload que tentamos enviar: {payload}")
            print(f"URL que tentamos acessar: {url}")
            
        except Exception:
            # Se não conseguir ler o JSON de erro
            print(f"================================================================")
            print(f"ERRO FATAL AO TENTAR ENVIAR MENSAGEM (requests.exceptions.HTTPError):")
            print(f"Mensagem de Erro completa: {http_err}" )
            print(f"================================================================")
            print(f"Payload que tentamos enviar: {payload}")
            print(f"URL que tentamos acessar: {url}")
            
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
    # --- ESTE É O CÓDIGO QUE FALTAVA ---
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
# ROTA 2: Recebimento de Mensagens (POST) - (ATUALIZADA COM RAG)
# ---

@app.post("/webhook/whatsapp")
async def receive_message(request: Request):
    
    request_data = {}
    try:
        request_data = await request.json()
        print("--- Nova Mensagem Recebida (Payload Completo) ---")
        print(json.dumps(request_data, indent=2, ensure_ascii=False))
        
        user_message = "Mensagem não encontrada"
        user_phone_number = None
        
        if (
            "entry" in request_data and request_data["entry"] and
            "changes" in request_data["entry"][0] and request_data["entry"][0]["changes"] and
            "value" in request_data["entry"][0]["changes"][0] and
            "messages" in request_data["entry"][0]["changes"][0]["value"] and request_data["entry"][0]["changes"][0]["value"]["messages"] and
            "text" in request_data["entry"][0]["changes"][0]["value"]["messages"][0] and
            "body" in request_data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]
        ):
            user_message = request_data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
            user_phone_number = request_data["entry"][0]["changes"][0]["value"]["messages"][0]["from"]
            
            print(f"--- Mensagem do Usuário Extraída ---")
            print(f"De: {user_phone_number}")
            print(f"Texto: {user_message}")
            print("-----------------------------------")
            
            if not model:
                raise HTTPException(status_code=500, detail="API do Gemini não configurada.")
            
            print("Enviando para o Gemini (Chamada 1)...")
            
            # Inicia o "chat" com o Prompt de Sistema
            chat = model.start_chat(history=[
                {"role": "user", "parts": [SYSTEM_PROMPT]},
                {"role": "model", "parts": ["OK. Estou pronto para receber a mensagem do usuário."]}
            ])
            
            # Envia a mensagem do usuário
            response = chat.send_message(user_message, generation_config=generation_config)
            
            ai_json_response_str = response.text
            print("--- Resposta JSON (Chamada 1) do Gemini Recebida ---")
            print(ai_json_response_str)
            print("--------------------------------------------------")
            
            # --- LÓGICA DE AÇÃO (ATUALIZADA) ---
            try:
                ai_data = json.loads(ai_json_response_str)
                
                if ai_data.get("acao_requerida") == "RESPONDER_AO_USUARIO":
                    # A IA respondeu diretamente (ex: "Olá!", "Fora de escopo")
                    resposta_texto = ai_data["payload_acao"]["resposta_para_usuario"]
                    print(f"--- Ação: Responder Diretamente ---")
                    send_whatsapp_message(user_phone_number, resposta_texto)
                        
                elif ai_data.get("acao_requerida") == "EXECUTAR_FERRAMENTA":
                    # --- LÓGICA RAG (FASE 4) ---
                    print("--- Ação: Executar Ferramenta (RAG) ---")
                    
                    # 1. Extrair detalhes da ferramenta
                    tool_request = ai_data.get("payload_acao", {}).get("ferramenta_solicitada", {})
                    tool_name = tool_request.get("nome")
                    tool_params = tool_request.get("parametros", {})

                    if tool_name and tool_name in AVAILABLE_TOOLS:
                        # 2. Chamar a ferramenta correta do database_tools.py
                        print(f"--- Executando Ferramenta: {tool_name} com params: {tool_params} ---")
                        tool_function = AVAILABLE_TOOLS[tool_name]
                        db_result = tool_function(**tool_params) # ex: tool_obter_info_clinica(topic="endereco")
                        
                        # 3. Enviar o resultado de volta para a IA (Segunda chamada)
                        print("--- Enviando para o Gemini (Chamada 2 - RAG)... ---")
                        rag_prompt = f"OK, a ferramenta {tool_name} foi executada. O resultado é: '{db_result}'. Com base *apenas* nesse resultado, gere a resposta final para o usuário."
                        
                        response_rag = chat.send_message(rag_prompt, generation_config=generation_config)
                        final_ai_json_str = response_rag.text
                        
                        print("--- Resposta JSON Final (RAG) do Gemini Recebida ---")
                        print(final_ai_json_str)
                        print("--------------------------------------------------")
                        
                        # 4. Processar a *nova* resposta da IA
                        final_ai_data = json.loads(final_ai_json_str)
                        
                        if final_ai_data.get("acao_requerida") == "RESPONDER_AO_USUARIO":
                            final_response_text = final_ai_data["payload_acao"]["resposta_para_usuario"]
                            print(f"--- Ação: Responder com dados do DB ---")
                            send_whatsapp_message(user_phone_number, final_response_text)
                        else:
                            print("ERRO RAG: A IA não gerou uma resposta final, mesmo após os dados do DB.")
                            send_whatsapp_message(user_phone_number, "Desculpe, tive um problema ao processar sua solicitação após consultar os dados.")

                    else:
                        print(f"ERRO: A IA solicitou uma ferramenta desconhecida: {tool_name}")
                        send_whatsapp_message(user_phone_number, "Desculpe, a IA pediu uma ferramenta que eu não conheço.")
                    
                else:
                    print(f"Ação desconhecida recebida da IA: {ai_data.get('acao_requerida')}")
                    
            except json.JSONDecodeError:
                print("ERRO FATAL: Gemini retornou um JSON inválido. Não foi possível processar a ação.")
                print(ai_json_response_str) 
            
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