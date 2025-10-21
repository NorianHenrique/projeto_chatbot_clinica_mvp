# 🤖 Chatbot de Clínica Médica com IA (MVP)

Este é um projeto de MVP (Minimum Viable Product) para um chatbot de atendimento de clínica médica, utilizando a API do WhatsApp, FastAPI e a IA do Google (Gemini) para processamento de linguagem natural.

O objetivo é criar um agente de IA capaz de entender as solicitações do usuário (como agendamentos, cancelamentos e consultas de informação) e, futuramente, interagir com um banco de dados para fornecer respostas e executar ações.

## 🚀 Status Atual do Projeto

O projeto está atualmente no final da **Fase 3**. O "cérebro" do chatbot está funcional, mas o "braço" (envio de mensagens) está bloqueado por um bug na conta de teste da API da Meta.

### O que JÁ Fizemos (Funcional):

* **Fase 0: Ambiente**
    * Configuração do ambiente virtual Python (`venv`).
    * Instalação das dependências (FastAPI, Uvicorn, Google-GenerativeAI, Requests, DotEnv).

* **Fase 1: Webhook (Ouvir)**
    * O backend em **FastAPI** está rodando.
    * O `ngrok` está expondo o servidor local para a web.
    * O Webhook da API do WhatsApp (Meta) está **verificado e configurado** com sucesso.
    * Nosso servidor recebe e processa corretamente os payloads `POST` (mensagens) e `GET` (verificação) da Meta.

* **Fase 2: IA (Pensar)**
    * A API do Google **Gemini** está integrada.
    * Um **Prompt de Sistema** robusto foi desenvolvido para instruir a IA a agir como um agente de backend, forçando-a a responder em **JSON estruturado**.
    * A IA consegue classificar intenções (`agendamento`, `consulta_info`, `fora_de_escopo`), extrair entidades (`topico: "endereco"`) e decidir qual ação o Python deve tomar (`RESPONDER_AO_USUARIO` ou `EXECUTAR_FERRAMENTA`).
    * Nosso script Python consegue analisar o JSON da IA com sucesso.

### O que Falta Fazer (Próximas Etapas):

* **Fase 3: Ação (Responder) - ⚠️ BLOQUEADO**
    * A lógica para *tentar* enviar a resposta está implementada.
    * **PROBLEMA ATUAL:** A API de teste da Meta está retornando um erro `400 Bad Request` persistente em todas as tentativas de envio de mensagem (seja texto simples ou templates). Isso foi validado como um **bug da conta de teste da Meta**, pois a própria ferramenta de "Enviar Mensagem" da UI da Meta também falha (diz que envia, mas a mensagem não chega).
    * **Decisão:** Vamos pausar a depuração do envio e focar na lógica de backend (Fase 4), assumindo que o envio funcionará em um ambiente de produção.

* **Fase 4: Conexão com Banco de Dados (SQLite)**
    * Implementar as "ferramentas" (`tools`) que a IA pode solicitar.
    * Conectar o FastAPI ao **SQLite** para buscar dados reais (ex: buscar o endereço da clínica quando a IA pedir `tool_obter_info_clinica`).
    * Implementar o fluxo de **RAG (Retrieval-Augmented Generation)**: (Usuário pergunta -> IA pede ferramenta -> Python busca no DB -> Python chama a IA de novo com o dado -> IA gera a resposta final).

* **Fase 5: MVP Funcional**
    * Implementar as ferramentas de escrita no banco (Agendamento, Cancelamento).

## 🛠️ Stack de Tecnologia

* **Backend:** FastAPI (Python)
* **Servidor:** Uvicorn
* **IA (LLM):** Google Gemini (via `google-generativeai`)
* **Canal (API):** API Oficial do WhatsApp Business (Meta)
* **Banco de Dados:** SQLite
* **Túnel (Testes):** ngrok

## 🏁 Como Executar (Para Colegas)

1.  **Clone este repositório:**
    ```bash
    git clone [URL_DO_SEU_REPOSITORIO]
    cd [NOME_DA_PASTA]
    ```

2.  **Crie e ative o ambiente virtual:**
    ```bash
    python -m venv venv
    # No Windows:
    .\venv\Scripts\activate
    # No macOS/Linux:
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Crie seu arquivo de "segredos":**
    * Crie um arquivo chamado `.env` na raiz do projeto.
    * Copie o conteúdo do `env.example` para dentro do `.env`.
    * Preencha com suas próprias chaves (obtenha as chaves da Meta e do Google AI Studio).

5.  **Configure o Banco de Dados (Uma vez):**
    ```bash
    python database_setup.py
    ```

6.  **Inicie o servidor FastAPI (Terminal 1):**
    ```bash
    uvicorn main:app --reload
    ```

7.  **Inicie o túnel ngrok (Terminal 2):**
    ```bash
    ngrok http 8000
    ```

8.  **Configure o Webhook na Meta:**
    * Copie a URL `https...` do ngrok.
    * Cole-a no painel do seu App da Meta (WhatsApp > Configuração da API > Webhook), adicionando `/webhook/whatsapp` no final.
    * Adicione seu `VERIFY_TOKEN` (do `.env`) na plataforma.
    * Assine o evento `messages`.