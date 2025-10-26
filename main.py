from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field # Importa Field
import json
import uuid # <-- NOVO: Para gerar IDs únicos

# Importa nossas funções refatoradas
from agent import handle_message
from telegram_utils import parse_webhook_data, send_telegram_message

# Inicializa o FastAPI
app = FastAPI()

# --- Configuração do CORS (Idêntica) ---
origins = ["*"] 
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# --- Modelos Pydantic ATUALIZADOS para o endpoint /chat ---
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None # <-- NOVO: Session ID opcional vindo do frontend

class ChatResponse(BaseModel):
    reply: str
    session_id: str # <-- NOVO: Sempre retornamos um session_id

# --- ROTA DE WEBHOOK TELEGRAM (Idêntica à anterior) ---
@app.post("/webhook/telegram")
async def webhook_telegram(request: Request, background_tasks: BackgroundTasks):
    request_data = {}
    try:
        request_data = await request.json()
        # print("--- Telegram Webhook Recebido (Payload Bruto) ---") 
        # print(json.dumps(request_data, indent=2, ensure_ascii=False))

        user_chat_id, user_message = parse_webhook_data(request_data)

        if user_chat_id and user_message:
            print(f"--- Delegando para o Agente (Telegram) em Segundo Plano (Chat ID: {user_chat_id}) ---")

            def process_and_send(chat_id, message):
                bot_reply = handle_message(chat_id, message)
                if bot_reply:
                    send_telegram_message(chat_id, bot_reply)
                else:
                    print("handle_message não retornou resposta para enviar (Telegram).")

            background_tasks.add_task(process_and_send, user_chat_id, user_message)
            return {"status": "ok, processando em segundo plano"}
        else:
            print("Webhook recebido (Telegram), mas não é uma mensagem de texto. Ignorando.")
            return {"status": "ok, ignorado"}

    except json.JSONDecodeError:
        print("Erro: Não foi possível decodificar o JSON recebido (Telegram).")
        raise HTTPException(status_code=400, detail="Payload inválido.")
    except Exception as e:
        print(f"Erro inesperado na Rota Telegram: {e}")
        return {"status": "ok, erro interno no processamento"}

# --- ROTA PARA O FRONTEND WEB (ATUALIZADA COM SESSÕES) ---
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request_data: ChatRequest):
    """
    Recebe a mensagem do frontend web, gerencia a sessão e retorna a resposta.
    """
    user_message = request_data.message
    session_id = request_data.session_id

    # --- Lógica de Gerenciamento de Sessão ---
    if not session_id:
        # Se o frontend não enviou um ID, gera um novo
        session_id = str(uuid.uuid4()) # Gera um ID único universal
        print(f"--- Nova Sessão Web Iniciada --- ID: {session_id}")
    else:
        print(f"--- Sessão Web Existente --- ID: {session_id}")

    print(f"Mensagem Recebida (Web): {user_message}")

    # Chama a lógica do agente USANDO o session_id como chave da memória
    bot_reply = handle_message(session_id, user_message)

    if bot_reply is None:
        bot_reply = "Desculpe, ocorreu um erro ao processar sua mensagem."

    print(f"--- Resposta /chat enviada (Sessão: {session_id}) ---")
    print(f"Reply: {bot_reply}")

    # Retorna a resposta E o session_id para o frontend
    return ChatResponse(reply=bot_reply, session_id=session_id)


# --- ROTA HEALTH CHECK (Idêntica) ---
@app.get("/")
async def root():
    return {"status": "Servidor do Chatbot (Refatorado v2) está rodando!"}