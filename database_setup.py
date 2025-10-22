import sqlite3

def setup_database():
    # Conecta (e cria) ao arquivo de banco de dados
    conn = sqlite3.connect('clinic.db')
    cursor = conn.cursor()

    # --- Cria a tabela de informações ---
    # (IF NOT EXISTS garante que não vai quebrar se rodarmos de novo)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL UNIQUE,
        value TEXT NOT NULL
    )
    ''')
    print("Tabela 'info' criada com sucesso (ou já existia).")

    # --- Insere os dados do nosso MVP ---
    # (IGNORE OR REPLACE garante que não vai duplicar)
    info_data = [
        ('endereco', 'Nosso endereço é Rua das Flores, 123 - Centro.'),
        ('horario_funcionamento', 'Atendemos de Segunda a Sexta, das 08:00 às 18:00.'),
        ('convenios_aceitos', 'Aceitamos os convênios Unimed, Bradesco Saúde e SulAmérica.')
    ]

    # Usamos 'INSERT OR IGNORE' para não dar erro se o 'topic' já existir
    cursor.executemany("INSERT OR IGNORE INTO info (topic, value) VALUES (?, ?)", info_data)

    print(f"{cursor.rowcount} novas informações inseridas.")

    # Salva (commit) as mudanças e fecha a conexão
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("Iniciando setup do banco de dados...")
    setup_database()
    print("Banco de dados 'clinic.db' está pronto.")