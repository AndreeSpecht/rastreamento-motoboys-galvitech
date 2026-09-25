"""Acesso ao banco SQLite: esquema, migrações leves e consultas."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime

COR_PADRAO_CLIENTE = "#808080"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    cor TEXT DEFAULT '#808080',
    telefone TEXT DEFAULT '',
    obs TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS tracklog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    moto_id INTEGER,
    lat REAL,
    lon REAL,
    velocidade REAL,
    timestamp INTEGER
);
CREATE INDEX IF NOT EXISTS idx_tracklog_moto_ts ON tracklog (moto_id, timestamp);
CREATE TABLE IF NOT EXISTS historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    motoboy TEXT,
    data_viagem TEXT,
    hora_saida TEXT,
    hora_chegada TEXT,
    destinos TEXT,
    numero_nota TEXT DEFAULT ''
);
"""

# Colunas acrescentadas após a primeira versão do banco (protótipo V79)
MIGRACOES = {
    "clientes": {"cor": "TEXT DEFAULT '#808080'", "telefone": "TEXT DEFAULT ''", "obs": "TEXT DEFAULT ''"},
    "historico": {"numero_nota": "TEXT DEFAULT ''", "data_iso": "TEXT", "moto_id": "INTEGER"},
}


class Banco:
    def __init__(self, caminho):
        self.caminho = str(caminho)

    @contextmanager
    def conexao(self):
        conn = sqlite3.connect(self.caminho)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def inicializar(self):
        with self.conexao() as conn:
            conn.executescript(ESQUEMA)
            for tabela, colunas in MIGRACOES.items():
                existentes = {r["name"] for r in conn.execute(f"PRAGMA table_info({tabela})")}
                for coluna, tipo in colunas.items():
                    if coluna not in existentes:
                        conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
            # Preenche data_iso em registros antigos (data_viagem em dd/mm/aaaa)
            for r in conn.execute("SELECT id, data_viagem FROM historico WHERE data_iso IS NULL").fetchall():
                try:
                    iso = datetime.strptime(r["data_viagem"], "%d/%m/%Y").strftime("%Y-%m-%d")
                except (TypeError, ValueError):
                    continue
                conn.execute("UPDATE historico SET data_iso = ? WHERE id = ?", (iso, r["id"]))
            conn.execute("UPDATE clientes SET cor = ? WHERE cor IS NULL OR cor NOT LIKE '#%'", (COR_PADRAO_CLIENTE,))

    # --- Clientes ---
    def listar_clientes(self):
        with self.conexao() as conn:
            rows = conn.execute(
                "SELECT id, nome, lat, lon, cor, telefone, obs FROM clientes ORDER BY nome COLLATE NOCASE"
            ).fetchall()
            return [dict(r) for r in rows]

    def salvar_cliente(self, nome, lat, lon):
        """Insere o cliente se ainda não existir um com o mesmo nome. Retorna o id."""
        with self.conexao() as conn:
            existente = conn.execute(
                "SELECT id FROM clientes WHERE nome = ? COLLATE NOCASE", (nome,)
            ).fetchone()
            if existente:
                return existente["id"]
            cur = conn.execute(
                "INSERT INTO clientes (nome, lat, lon, cor) VALUES (?, ?, ?, ?)",
                (nome, lat, lon, COR_PADRAO_CLIENTE),
            )
            return cur.lastrowid

    def atualizar_cliente(self, cliente_id, nome, telefone):
        with self.conexao() as conn:
            conn.execute("UPDATE clientes SET nome = ?, telefone = ? WHERE id = ?", (nome, telefone, cliente_id))

    def atualizar_cor_cliente(self, cliente_id, cor):
        with self.conexao() as conn:
            conn.execute("UPDATE clientes SET cor = ? WHERE id = ?", (cor, cliente_id))

    def apagar_cliente(self, cliente_id):
        with self.conexao() as conn:
            conn.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))

    # --- Rastreamento ---
    def registrar_posicao(self, moto_id, lat, lon, velocidade, ts):
        with self.conexao() as conn:
            conn.execute(
                "INSERT INTO tracklog (moto_id, lat, lon, velocidade, timestamp) VALUES (?, ?, ?, ?, ?)",
                (moto_id, lat, lon, velocidade, ts),
            )

    def trilha(self, moto_id, ts_inicio, ts_fim):
        with self.conexao() as conn:
            rows = conn.execute(
                "SELECT lat, lon, velocidade, timestamp FROM tracklog "
                "WHERE moto_id = ? AND timestamp >= ? AND timestamp < ? ORDER BY timestamp",
                (moto_id, ts_inicio, ts_fim),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Histórico ---
    def registrar_viagem(self, moto_id, motoboy, hora_saida, hora_chegada, destinos, nota, quando=None):
        quando = quando or datetime.now()
        with self.conexao() as conn:
            conn.execute(
                "INSERT INTO historico (moto_id, motoboy, data_viagem, data_iso, hora_saida, hora_chegada, "
                "destinos, numero_nota) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    moto_id,
                    motoboy,
                    quando.strftime("%d/%m/%Y"),
                    quando.strftime("%Y-%m-%d"),
                    hora_saida,
                    hora_chegada,
                    destinos,
                    nota,
                ),
            )

    def historico(self, inicio=None, fim=None):
        """Viagens mais recentes primeiro. inicio/fim no formato AAAA-MM-DD (inclusivos)."""
        sql = (
            "SELECT id, data_viagem, motoboy, numero_nota, destinos, hora_saida, hora_chegada "
            "FROM historico WHERE 1=1"
        )
        params = []
        if inicio:
            sql += " AND data_iso >= ?"
            params.append(inicio)
        if fim:
            sql += " AND data_iso <= ?"
            params.append(fim)
        sql += " ORDER BY id DESC"
        with self.conexao() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
