import pytest
import requests

from radar_tracker import create_app
from radar_tracker.config import Config

MOTOBOYS = [
    {"id": 0, "nome": "Ana Teste", "cor": "#e74c3c", "tid": "0"},
    {"id": 1, "nome": "Bruno Teste", "cor": "#3498db", "tid": "b1"},
]


@pytest.fixture
def cfg(tmp_path):
    class ConfigTeste(Config):
        PASTA_DADOS = tmp_path
        DB_PATH = tmp_path / "teste.db"
        ARQUIVO_SESSAO = tmp_path / "sessao.json"
        OWNTRACKS_TOKEN = ""

    return ConfigTeste


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Nenhum teste acessa OSRM/Nominatim de verdade: simula serviço fora do ar."""

    def falhar(*_args, **_kwargs):
        raise requests.ConnectionError("rede desabilitada nos testes")

    monkeypatch.setattr(requests, "get", falhar)


@pytest.fixture
def app(cfg):
    return create_app(cfg, motoboys=[dict(m) for m in MOTOBOYS])


@pytest.fixture
def client(app):
    return app.test_client()
