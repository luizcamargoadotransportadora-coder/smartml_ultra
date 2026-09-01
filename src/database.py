"""
SmartML Ultra - Camada de Persistência Local (SQLite)
Garante rastreabilidade, histórico de análises e auditoria de campo.
"""
from __future__ import annotations
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.getcwd(), "smartml_ultra.db")

def conectar():
    """Cria e retorna a conexão com o banco SQLite local."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_banco():
    """Cria as tabelas principais do sistema se não existirem."""
    conn = conectar()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora TEXT NOT NULL,
        titulo_original TEXT NOT NULL,
        titulo_encontrado TEXT,
        custo_base REAL NOT NULL,
        moeda TEXT DEFAULT 'BRL',
        menor_preco_concorrente REAL,
        link_concorrente TEXT,
        lucro_classico REAL,
        margem_classico REAL,
        lucro_premium REAL,
        margem_premium REAL,
        status_veredicto TEXT,
        origem TEXT DEFAULT 'AppSheet',
        confianca TEXT DEFAULT 'ALTA'
    )
    """)
    
    conn.commit()
    conn.close()

def salvar_analise(dados: dict) -> int:
    """Salva uma nova auditoria concluída no banco local."""
    inicializar_banco()
    conn = conectar()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO analises (
        data_hora, titulo_original, titulo_encontrado, custo_base, moeda,
        menor_preco_concorrente, link_concorrente, lucro_classico, margem_classico,
        lucro_premium, margem_premium, status_veredicto, origem, confianca
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        dados.get("titulo_original", ""),
        dados.get("titulo_encontrado", ""),
        dados.get("custo_base", 0.0),
        dados.get("moeda", "BRL"),
        dados.get("menor_preco", 0.0),
        dados.get("link", ""),
        dados.get("classico", {}).get("lucro", 0.0),
        dados.get("classico", {}).get("margem", 0.0),
        dados.get("premium", {}).get("lucro", 0.0),
        dados.get("premium", {}).get("margem", 0.0),
        dados.get("status", "E"),
        dados.get("origem", "AppSheet"),
        dados.get("confianca", "ALTA")
    ))
    
    conn.commit()
    novo_id = cursor.lastrowid
    conn.close()
    return novo_id

# Inicializa o banco automaticamente ao importar o módulo
inicializar_banco()