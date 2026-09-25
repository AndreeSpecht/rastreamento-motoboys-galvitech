"""Popula o banco com clientes fictícios para demonstração.

Uso:
    python scripts/seed_demo.py            # só insere se o cadastro estiver vazio
    python scripts/seed_demo.py --forcar   # insere mesmo com clientes existentes
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from radar_tracker.config import Config  # noqa: E402
from radar_tracker.db import Banco  # noqa: E402

# Nomes fictícios; coordenadas em bairros de Jaraguá do Sul/SC
CLIENTES_DEMO = [
    ("Oficina Mecânica Centro (demo)", -26.4851, -49.0713),
    ("Auto Center Vila Nova (demo)", -26.4935, -49.0889),
    ("Funilaria Czerniewicz (demo)", -26.4702, -49.0937),
    ("Mecânica Barra do Rio Cerro (demo)", -26.4562, -49.1238),
    ("Retífica Jaraguá Esquerdo (demo)", -26.4903, -49.0980),
    ("Oficina Três Rios do Sul (demo)", -26.5155, -49.1152),
    ("Auto Elétrica Amizade (demo)", -26.4659, -49.0764),
    ("Moto Peças Nereu Ramos (demo)", -26.5012, -49.0585),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--forcar", action="store_true", help="insere mesmo que já existam clientes")
    args = parser.parse_args()

    Config.PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    banco = Banco(Config.DB_PATH)
    banco.inicializar()
    if banco.listar_clientes() and not args.forcar:
        print("Cadastro já possui clientes; nada a fazer (use --forcar para inserir mesmo assim).")
        return
    for nome, lat, lon in CLIENTES_DEMO:
        banco.salvar_cliente(nome, lat, lon)
    print(f"{len(CLIENTES_DEMO)} clientes de demonstração disponíveis em {Config.DB_PATH}")


if __name__ == "__main__":
    main()
