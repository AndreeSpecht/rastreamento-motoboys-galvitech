import time

import pytest


def test_pagina_inicial(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Radar Auto Peças" in r.get_data(as_text=True)


def test_health_e_motoboys(client):
    assert client.get("/api/health").json == {"status": "ok"}
    nomes = [m["nome"] for m in client.get("/api/motoboys").json]
    assert nomes == ["Ana Teste", "Bruno Teste"]


def test_fluxo_de_entrega_gera_historico(client):
    assert client.post("/api/add", json={"id": 0, "nome": "Oficina X", "lat": -26.49, "lon": -49.08}).json["ok"] == 1
    assert client.post("/api/start", json={"id": 0, "nota": "NF-999"}).json["ok"] == 1
    assert client.get("/api/estado").json["0"]["status"] == "EM_ROTA"
    assert client.post("/api/end", json={"id": 0}).json["ok"] == 1

    hist = client.get("/api/get_historico").json
    assert len(hist) == 1
    assert hist[0]["numero_nota"] == "NF-999" and hist[0]["motoboy"] == "Ana Teste"


def test_filtro_de_historico_por_data(client):
    client.post("/api/add", json={"id": 0, "nome": "A", "lat": -26.49, "lon": -49.08})
    client.post("/api/start", json={"id": 0, "nota": "1"})
    client.post("/api/end", json={"id": 0})
    assert len(client.get("/api/get_historico?inicio=2000-01-01&fim=2000-01-02").json) == 0
    hoje = time.strftime("%Y-%m-%d")
    assert len(client.get(f"/api/get_historico?inicio={hoje}&fim={hoje}").json) == 1


def test_motoboy_inexistente_retorna_404(client):
    r = client.post("/api/add", json={"id": 99, "nome": "A", "lat": 0, "lon": 0})
    assert r.status_code == 404


@pytest.mark.parametrize(
    "corpo",
    [{}, {"id": 0, "nome": "", "lat": 0, "lon": 0}, {"id": 0, "nome": "A", "lat": "x", "lon": 0}],
)
def test_validacao_de_entrada(client, corpo):
    assert client.post("/api/add", json=corpo).status_code == 400


def test_otimizar_rota(client):
    for nome, lon in [("Longe", -49.0), ("Perto", -49.09)]:
        client.post("/api/add", json={"id": 0, "nome": nome, "lat": -26.508484936938192, "lon": lon})
    client.post("/api/otimizar", json={"id": 0})
    assert [p["nome"] for p in client.get("/api/estado").json["0"]["rota"]] == ["Perto", "Longe"]


def test_calc_usa_fallback_offline(client):
    d = client.post("/api/calc", json={"stops": [{"lat": -26.49, "lon": -49.08}]}).json
    assert d["fonte"] == "offline"
    assert d["minutos"] > 0 and d["pontos"] == []


def test_crud_de_clientes(client):
    nome = "Oficina O'Brien <b>"
    cid = client.post("/api/save_cli", json={"nome": nome, "lat": -26.4, "lon": -49.0}).json["id"]
    # mesmo nome (sem diferenciar maiúsculas) não duplica o cadastro
    assert client.post("/api/save_cli", json={"nome": nome.lower(), "lat": 0, "lon": 0}).json["id"] == cid
    client.post("/api/update_client", json={"id": cid, "nome": "Oficina Nova", "telefone": "47 9999-0000"})
    client.post("/api/update_color", json={"id": cid, "cor": "#123456"})
    c = client.get("/api/clientes").json[0]
    assert (c["nome"], c["telefone"], c["cor"]) == ("Oficina Nova", "47 9999-0000", "#123456")
    assert client.post("/api/update_color", json={"id": cid, "cor": "red"}).status_code == 400
    client.post("/api/apagar_cliente", json={"id": cid})
    assert client.get("/api/clientes").json == []


def test_exportacao_excel(client):
    r = client.get("/baixar_excel")
    assert r.status_code == 200
    assert r.data[:2] == b"PK"  # arquivo .xlsx é um zip
