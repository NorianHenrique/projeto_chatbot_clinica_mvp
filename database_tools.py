import sqlite3

DATABASE_FILE = 'clinic.db'

def tool_obter_info_clinica(topic: str) -> str:
    """
    Busca no banco de dados a informação com base no tópico.
    """
    if not topic:
        return "Tópico não fornecido."

    print(f"--- FERRAMENTA DB: Buscando pelo tópico: {topic} ---")

    try:
        # Conecta ao DB
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Busca o valor (usamos 'topic = ?' para evitar SQL Injection)
        cursor.execute("SELECT value FROM info WHERE topic = ?", (topic,))
        result = cursor.fetchone() # Pega o primeiro resultado

        conn.close()

        if result:
            # result é uma tupla (ex: ('Rua das Flores...',)), 
            # então pegamos o primeiro item
            print(f"--- FERRAMENTA DB: Informação encontrada: {result[0]} ---")
            return result[0]
        else:
            print("--- FERRAMENTA DB: Tópico não encontrado no banco. ---")
            return f"Informação sobre '{topic}' não encontrada."

    except Exception as e:
        print(f"--- FERRAMENTA DB: ERRO ao acessar o SQLite: {e} ---")
        return "Ocorreu um erro ao consultar o banco de dados."