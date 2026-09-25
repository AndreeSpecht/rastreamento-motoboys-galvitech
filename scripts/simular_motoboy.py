"""Simula o app OwnTracks de um motoboy percorrendo a rota montada no painel.

Envia uma posição a cada INTERVALO segundos para /api/gps/owntracks, seguindo
o traçado calculado pelo OSRM (ou linha reta entre as paradas, se offline).

Uso:
    python scripts/simular_motoboy.py --tid 0
    python scripts/simular_motoboy.py --tid 1 --url http://192.168.0.10:5000 --intervalo 2 --velocidade 35 --token segredo
"""

import argparse
import time

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from radar_tracker.geo import haversine  # noqa: E402


def interpolar(pontos, passo_m):
    """Reamostra o traçado em passos de ~passo_m metros, para um movimento contínuo e realista."""
    saida = []
    for (lat1, lon1), (lat2, lon2) in zip(pontos, pontos[1:]):
        n = max(1, round(haversine(lat1, lon1, lat2, lon2) * 1000 / passo_m))
        saida.extend((lat1 + (lat2 - lat1) * i / n, lon1 + (lon2 - lon1) * i / n) for i in range(n))
    saida.append(pontos[-1])
    return saida


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tid", default="0", help="Tracker ID do motoboy (config/motoboys.json)")
    parser.add_argument("--id", type=int, help="id do motoboy no painel (padrão: igual ao tid)")
    parser.add_argument("--url", default="http://127.0.0.1:5000")
    parser.add_argument("--intervalo", type=float, default=2.0, help="segundos entre posições")
    parser.add_argument("--velocidade", type=float, default=40, help="velocidade simulada em km/h")
    parser.add_argument("--token", default="", help="OWNTRACKS_TOKEN, se configurado no servidor")
    args = parser.parse_args()
    mid = str(args.id if args.id is not None else args.tid)

    estado = requests.get(f"{args.url}/api/estado", timeout=5).json()
    if mid not in estado:
        raise SystemExit(f"Motoboy {mid} não existe no servidor.")
    rota = estado[mid]["rota"]
    if not rota:
        raise SystemExit("Monte uma rota para esse motoboy no painel antes de simular.")

    calc = requests.post(f"{args.url}/api/calc", json={"stops": rota}, timeout=10).json()
    base = (estado[mid]["lat_atual"], estado[mid]["lon_atual"])
    pontos = calc["pontos"] or [base, *[(p["lat"], p["lon"]) for p in rota], base]
    trajeto = interpolar(pontos, passo_m=args.velocidade / 3.6 * args.intervalo)
    auth = ("motoboy", args.token) if args.token else None

    print(f"Simulando {estado[mid]['nome']} com {len(trajeto)} posições ({calc['fonte']}). Ctrl+C para parar.")
    for i, (lat, lon) in enumerate(trajeto, 1):
        msg = {"_type": "location", "tid": args.tid, "lat": lat, "lon": lon, "tst": int(time.time()), "acc": 8, "vel": int(args.velocidade)}
        requests.post(f"{args.url}/api/gps/owntracks", json=msg, auth=auth, timeout=5)
        print(f"\r{i}/{len(trajeto)}  {lat:.5f}, {lon:.5f}", end="", flush=True)
        time.sleep(args.intervalo)
    print("\nTrajeto concluído.")


if __name__ == "__main__":
    main()
