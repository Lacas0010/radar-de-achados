import sqlite3
import hashlib
from datetime import datetime
from contextlib import contextmanager
from typing import List, Tuple, Optional, Dict, Any
from models.item import Anuncio

DB_PATH = "achados.db"

@contextmanager
def get_db(db_path: str = DB_PATH):
    """Context manager para conexão SQLite segura que sempre fecha a conexão."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db(db_path: str = DB_PATH):
    """Inicializa as tabelas no banco de dados SQLite com suporte a histórico de preços."""
    with get_db(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS anuncios (
                id TEXT PRIMARY KEY,
                url TEXT UNIQUE,
                titulo TEXT,
                preco REAL,
                preco_anterior REAL,
                variacao_preco REAL,
                localizacao TEXT,
                plataforma TEXT,
                imagem_url TEXT,
                data_publicacao TEXT,
                desconto_percentual REAL,
                classificacao TEXT,
                primeira_vez_visto TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultima_vez_visto TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de Histórico de Variações de Preço
        conn.execute("""
            CREATE TABLE IF NOT EXISTS historico_precos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad_id TEXT,
                plataforma TEXT,
                preco REAL,
                data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ad_id) REFERENCES anuncios(id)
            )
        """)

        # Índices
        conn.execute("CREATE INDEX IF NOT EXISTS idx_anuncios_url ON anuncios(url)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_anuncios_plataforma ON anuncios(plataforma)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hist_ad_id ON historico_precos(ad_id)")
        
        # Migração defensiva: adiciona colunas caso o banco já existisse
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(anuncios)")
        colunas = [c["name"] for c in cursor.fetchall()]
        if "preco_anterior" not in colunas:
            cursor.execute("ALTER TABLE anuncios ADD COLUMN preco_anterior REAL")
        if "variacao_preco" not in colunas:
            cursor.execute("ALTER TABLE anuncios ADD COLUMN variacao_preco REAL")
            
        conn.commit()

def gerar_id_anuncio(url: str) -> str:
    """Gera um hash determinístico curto para o anúncio com base na URL."""
    clean_url = url.split("?")[0].rstrip("/")
    return hashlib.sha256(clean_url.encode("utf-8")).hexdigest()[:16]

def processar_e_salvar_anuncios(
    anuncios: List[Anuncio],
    db_path: str = DB_PATH
) -> Tuple[List[Anuncio], int]:
    """
    Verifica no SQLite quais anúncios já foram vistos anteriormente.
    Detecta reduções de preço (ex: baixou R$ 250) e registra no histórico.
    Atualiza 'is_novo', 'preco_anterior' e 'variacao_preco'.
    Retorna (lista_anuncios, total_novos).
    """
    init_db(db_path)
    total_novos = 0
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db(db_path) as conn:
        cursor = conn.cursor()

        for a in anuncios:
            item_id = a.id or gerar_id_anuncio(a.url)
            a.id = item_id

            # Consulta se a URL ou ID já existe no banco
            cursor.execute("SELECT id, preco, preco_anterior, variacao_preco FROM anuncios WHERE url = ? OR id = ?", (a.url, item_id))
            row = cursor.fetchone()

            if row:
                # Anúncio já existente no banco de dados
                a.is_novo = False
                preco_antigo = float(row["preco"]) if row["preco"] else a.preco
                
                # Detectar redução de preço
                if a.preco < preco_antigo:
                    queda = round(preco_antigo - a.preco, 2)
                    a.preco_anterior = preco_antigo
                    a.variacao_preco = queda
                    print(f"[Preço Baixou!] Anúncio '{a.titulo[:35]}...' baixou de R$ {preco_antigo:.2f} para R$ {a.preco:.2f} (-R$ {queda:.2f})")
                    
                    # Registrar no histórico de preços
                    cursor.execute("""
                        INSERT INTO historico_precos (ad_id, plataforma, preco, data_registro)
                        VALUES (?, ?, ?, ?)
                    """, (item_id, a.plataforma, a.preco, agora))
                else:
                    a.preco_anterior = row["preco_anterior"]
                    a.variacao_preco = row["variacao_preco"]

                cursor.execute("""
                    UPDATE anuncios 
                    SET preco = ?, preco_anterior = ?, variacao_preco = ?,
                        ultima_vez_visto = ?, desconto_percentual = ?, classificacao = ?
                    WHERE id = ?
                """, (a.preco, a.preco_anterior, a.variacao_preco, agora, a.desconto_percentual, a.classificacao, row["id"]))

            else:
                # Anúncio novo / nunca visto antes
                a.is_novo = True
                total_novos += 1
                cursor.execute("""
                    INSERT INTO anuncios (
                        id, url, titulo, preco, preco_anterior, variacao_preco,
                        localizacao, plataforma, imagem_url, data_publicacao,
                        desconto_percentual, classificacao, primeira_vez_visto, ultima_vez_visto
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item_id, a.url, a.titulo, a.preco, None, None,
                    a.localizacao, a.plataforma, a.imagem_url, a.data_publicacao,
                    a.desconto_percentual, a.classificacao, agora, agora
                ))

                # Histórico inicial
                cursor.execute("""
                    INSERT INTO historico_precos (ad_id, plataforma, preco, data_registro)
                    VALUES (?, ?, ?, ?)
                """, (item_id, a.plataforma, a.preco, agora))

        conn.commit()

    return anuncios, total_novos

def obter_estatisticas_banco(db_path: str = DB_PATH) -> dict:
    """Retorna contadores gerais do banco de dados SQLite."""
    init_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM anuncios")
        total = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) as total_olx FROM anuncios WHERE plataforma = 'OLX'")
        total_olx = cursor.fetchone()["total_olx"]

        cursor.execute("SELECT COUNT(*) as total_fb FROM anuncios WHERE plataforma LIKE '%Facebook%'")
        total_fb = cursor.fetchone()["total_fb"]

        cursor.execute("SELECT COUNT(*) as total_drops FROM anuncios WHERE variacao_preco > 0")
        total_drops = cursor.fetchone()["total_drops"]

    return {
        "total_anuncios_armazenados": total,
        "total_olx": total_olx,
        "total_facebook": total_fb,
        "total_quedas_preco": total_drops
    }
