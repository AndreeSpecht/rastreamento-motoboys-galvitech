import time


def posicao(tid="0", lat=-26.5085, lon=-49.1054, **extra):
    return {"_type": "location", "tid": tid, "lat": lat, "lon": lon, "tst": int(time.time()), **extra}


def test_posicao_atualiza_mapa_e_trilha(client):
    assert client.post("/api/gps/owntracks", json=posicao(acc=5)).json == []
    estado = client.get("/api/estado").json["0"]
    assert estado["lat_atual"] == -26.5085
    trilha = client.get("/api/tracklog?id=0").json
    assert len(trilha) == 1 and trilha[0]["lat"] == -26.5085


def test_tid_personalizado_mapeia_para_motoboy(client):
    client.post("/api/gps/owntracks", json=posicao(tid="b1", lat=-26.49))
    assert client.get("/api/estado").json["1"]["lat_atual"] == -26.49


def test_mensagens_ignoradas(client):
    assert client.post("/api/gps/owntracks", json={"_type": "transition"}).json == []
    assert client.post("/api/gps/owntracks", json=posicao(tid="desconhecido")).json == []
    assert client.post("/api/gps/owntracks", json=posicao(lat=None)).json == []
    assert client.post("/api/gps/owntracks", data="lixo").json == []


def test_leitura_imprecisa_nao_vai_para_trilha(client):
    client.post("/api/gps/owntracks", json=posicao(acc=900))
    assert client.get("/api/tracklog?id=0").json == []


def test_token_obrigatorio_quando_configurado(app, client):
    app.extensions["radar"]["config"].OWNTRACKS_TOKEN = "segredo"
    assert client.post("/api/gps/owntracks", json=posicao()).status_code == 401
    ok = client.post("/api/gps/owntracks", json=posicao(), auth=("motoboy", "segredo"))
    assert ok.status_code == 200
    ok = client.post("/api/gps/owntracks", json=posicao(), headers={"X-Token": "segredo"})
    assert ok.status_code == 200
