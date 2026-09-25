import pytest

from radar_tracker import geo


def test_haversine_mesmo_ponto_e_zero():
    assert geo.haversine(-26.5, -49.1, -26.5, -49.1) == 0


def test_haversine_um_grau_de_latitude():
    assert geo.haversine(0, 0, 1, 0) == pytest.approx(111.19, abs=0.1)


def test_velocidade_sem_timestamp_anterior():
    assert geo.velocidade_kmh(0, 0, 0, 0, 1, 100) is None


def test_velocidade_um_km_em_um_minuto():
    lat2 = 1 / 111.19  # ~1 km ao norte
    assert geo.velocidade_kmh(0, 0, 1000, lat2, 0, 1060) == pytest.approx(60, rel=0.01)


def test_vizinho_mais_proximo_ordena_por_proximidade():
    origem = {"lat": 0, "lon": 0}
    paradas = [
        {"nome": "longe", "lat": 0, "lon": 3},
        {"nome": "perto", "lat": 0, "lon": 1},
        {"nome": "meio", "lat": 0, "lon": 2},
    ]
    ordem = [p["nome"] for p in geo.vizinho_mais_proximo(origem, paradas)]
    assert ordem == ["perto", "meio", "longe"]
    assert paradas[0]["nome"] == "longe"  # lista original intacta


def test_distancia_circuito_ida_e_volta():
    origem = {"lat": 0, "lon": 0}
    km = geo.distancia_circuito_km(origem, [{"lat": 1, "lon": 0}])
    assert km == pytest.approx(2 * geo.haversine(0, 0, 1, 0))
