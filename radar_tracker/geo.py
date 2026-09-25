"""Funções geográficas puras: distância, velocidade e ordenação de paradas."""

import math

RAIO_TERRA_KM = 6371.0


def haversine(lat1, lon1, lat2, lon2):
    """Distância em km entre dois pontos (fórmula de Haversine)."""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return RAIO_TERRA_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def velocidade_kmh(lat1, lon1, ts1, lat2, lon2, ts2):
    """Velocidade média entre duas leituras. Retorna None se não for calculável."""
    if not ts1 or ts2 <= ts1:
        return None
    horas = (ts2 - ts1) / 3600
    return haversine(lat1, lon1, lat2, lon2) / horas


def vizinho_mais_proximo(origem, paradas):
    """Ordena as paradas pela heurística do vizinho mais próximo.

    origem: dict com 'lat' e 'lon'. paradas: lista de dicts com 'lat' e 'lon'.
    Retorna uma nova lista; a original não é alterada.
    """
    restantes = list(paradas)
    atual = origem
    ordenadas = []
    while restantes:
        proxima = min(restantes, key=lambda p: haversine(atual["lat"], atual["lon"], p["lat"], p["lon"]))
        ordenadas.append(proxima)
        restantes.remove(proxima)
        atual = proxima
    return ordenadas


def distancia_circuito_km(origem, paradas):
    """Distância em linha reta de origem → paradas → origem."""
    total = 0.0
    atual = origem
    for p in paradas:
        total += haversine(atual["lat"], atual["lon"], p["lat"], p["lon"])
        atual = p
    return total + haversine(atual["lat"], atual["lon"], origem["lat"], origem["lon"])
