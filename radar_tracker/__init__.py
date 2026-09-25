"""Módulo de rastreamento em tempo real de motoboys — Galvitech Ltda."""

import logging

from flask import Flask

from .config import Config, carregar_motoboys
from .db import Banco
from .frota import Frota

__version__ = "0.8.0"


def create_app(config=None, motoboys=None):
    """Cria a aplicação Flask. `config` pode ser uma classe/objeto que sobrescreve `Config`."""
    cfg = config or Config
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    cfg.PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    banco = Banco(cfg.DB_PATH)
    banco.inicializar()

    frota = Frota(
        motoboys or carregar_motoboys(),
        cfg.BASE_LAT,
        cfg.BASE_LON,
        cfg.ARQUIVO_SESSAO,
        precisao_max_m=cfg.GPS_PRECISAO_MAX_M,
        velocidade_max_kmh=cfg.GPS_VELOCIDADE_MAX_KMH,
    )
    frota.carregar()

    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.extensions["radar"] = {"config": cfg, "banco": banco, "frota": frota}

    from .api import bp

    app.register_blueprint(bp)
    return app
