"""Estado em memória da frota de motoboys, persistido em JSON entre reinícios."""

import json
import os
import threading
import time
from datetime import datetime

from . import geo

LIVRE = "LIVRE"
EM_ROTA = "EM_ROTA"


class MotoboyNaoEncontrado(KeyError):
    pass


class Frota:
    def __init__(self, motoboys, base_lat, base_lon, arquivo_sessao, precisao_max_m=100, velocidade_max_kmh=150,
                 raio_parado_m=50):
        self.motoboys = {m["id"]: m for m in motoboys}
        self.por_tid = {str(m["tid"]): m["id"] for m in motoboys}
        self.base = {"lat": base_lat, "lon": base_lon}
        self.arquivo_sessao = str(arquivo_sessao)
        self.precisao_max_m = precisao_max_m
        self.velocidade_max_kmh = velocidade_max_kmh
        self.raio_parado_m = raio_parado_m
        self._lock = threading.RLock()
        self.estado = {mid: self._estado_inicial() for mid in self.motoboys}

    def _estado_inicial(self):
        return {
            "status": LIVRE,
            "rota": [],
            "nota": "",
            "hora_saida": "",
            "lat_atual": self.base["lat"],
            "lon_atual": self.base["lon"],
            "velocidade": 0,
            "last_ts": 0,
            # Monitoramento (alertas)
            "inicio_ts": 0,  # hora (servidor) em que saiu para a entrega
            "recebido_em": 0,  # hora (servidor) da última mensagem do celular
            "bateria": None,  # % informado pelo OwnTracks
            "carregando": False,
            "parado_desde": 0,  # início do período parado no mesmo lugar
            "parado_lat": None,
            "parado_lon": None,
        }

    # --- Persistência ---
    def carregar(self):
        if not os.path.exists(self.arquivo_sessao):
            return
        try:
            with open(self.arquivo_sessao, encoding="utf-8") as f:
                salvo = json.load(f)
        except (OSError, ValueError):
            return
        with self._lock:
            for chave, dados in salvo.items():
                mid = int(chave)
                if mid in self.estado and isinstance(dados, dict):
                    for campo in self.estado[mid]:
                        if campo in dados:
                            self.estado[mid][campo] = dados[campo]

    def salvar(self):
        with self._lock:
            conteudo = json.dumps(self.estado, ensure_ascii=False, indent=2)
        os.makedirs(os.path.dirname(self.arquivo_sessao) or ".", exist_ok=True)
        temporario = self.arquivo_sessao + ".tmp"
        with open(temporario, "w", encoding="utf-8") as f:
            f.write(conteudo)
        os.replace(temporario, self.arquivo_sessao)  # gravação atômica

    # --- Consultas ---
    def _moto(self, mid):
        try:
            return self.estado[int(mid)]
        except (KeyError, TypeError, ValueError):
            raise MotoboyNaoEncontrado(mid) from None

    def id_por_tid(self, tid):
        return self.por_tid.get(str(tid))

    def snapshot(self):
        with self._lock:
            return {
                str(mid): {**dados, "nome": self.motoboys[mid]["nome"], "cor": self.motoboys[mid]["cor"],
                           "rota": list(dados["rota"])}
                for mid, dados in self.estado.items()
            }

    # --- Montagem da rota ---
    def adicionar_parada(self, mid, nome, lat, lon):
        with self._lock:
            moto = self._moto(mid)
            if moto["status"] != LIVRE:
                return False
            moto["rota"].append({"nome": nome, "lat": float(lat), "lon": float(lon)})
        self.salvar()
        return True

    def remover_parada(self, mid, indice):
        with self._lock:
            moto = self._moto(mid)
            if moto["status"] != LIVRE or not 0 <= indice < len(moto["rota"]):
                return False
            moto["rota"].pop(indice)
        self.salvar()
        return True

    def otimizar(self, mid):
        with self._lock:
            moto = self._moto(mid)
            if moto["status"] != LIVRE or len(moto["rota"]) < 2:
                return False
            origem = {"lat": moto["lat_atual"] or self.base["lat"], "lon": moto["lon_atual"] or self.base["lon"]}
            moto["rota"] = geo.vizinho_mais_proximo(origem, moto["rota"])
        self.salvar()
        return True

    # --- Ciclo da entrega ---
    def iniciar(self, mid, nota):
        with self._lock:
            moto = self._moto(mid)
            if moto["status"] != LIVRE or not moto["rota"] or not nota:
                return False
            agora = int(time.time())
            moto.update(status=EM_ROTA, nota=nota, hora_saida=datetime.now().strftime("%H:%M"),
                        inicio_ts=agora, parado_desde=agora,
                        parado_lat=moto["lat_atual"], parado_lon=moto["lon_atual"])
        self.salvar()
        return True

    def finalizar(self, mid):
        """Encerra a rota e devolve os dados da viagem para o histórico (ou None)."""
        with self._lock:
            moto = self._moto(mid)
            if moto["status"] != EM_ROTA:
                return None
            viagem = {
                "moto_id": int(mid),
                "motoboy": self.motoboys[int(mid)]["nome"],
                "hora_saida": moto["hora_saida"],
                "hora_chegada": datetime.now().strftime("%H:%M"),
                "destinos": ", ".join(p["nome"] for p in moto["rota"]),
                "nota": moto["nota"],
            }
            moto.update(status=LIVRE, rota=[], nota="", hora_saida="", inicio_ts=0)
        self.salvar()
        return viagem

    # --- GPS ---
    def registrar_contato(self, mid, bateria=None, carregando=None, agora=None):
        """Marca que o celular se comunicou, mesmo que a posição venha a ser descartada."""
        with self._lock:
            moto = self._moto(mid)
            moto["recebido_em"] = int(agora or time.time())
            if bateria is not None:
                moto["bateria"] = max(0, min(100, int(bateria)))
            if carregando is not None:
                moto["carregando"] = bool(carregando)

    def atualizar_posicao(self, mid, lat, lon, ts=None, precisao_m=None, vel_dispositivo=None):
        """Aplica uma leitura de GPS após filtrá-la.

        Descarta leituras com precisão pior que `precisao_max_m`, fora de ordem
        (timestamp anterior ao último aceito) ou que impliquem um salto acima de
        `velocidade_max_kmh`. Retorna a velocidade (km/h) ou None se descartada.
        """
        ts = int(ts or time.time())
        with self._lock:
            moto = self._moto(mid)
            if precisao_m is not None and precisao_m > self.precisao_max_m:
                return None
            if moto["last_ts"] and ts < moto["last_ts"]:
                return None
            if moto["last_ts"] and ts == moto["last_ts"]:
                vel = moto["velocidade"]  # mesma marca de tempo: mantém a última velocidade
            else:
                vel = geo.velocidade_kmh(moto["lat_atual"], moto["lon_atual"], moto["last_ts"], lat, lon, ts)
                if vel is not None and vel > self.velocidade_max_kmh:
                    return None
            if vel_dispositivo is not None and vel_dispositivo >= 0:
                vel = float(vel_dispositivo)  # velocidade medida pelo próprio GPS é mais fiel
            if vel is None or vel < 1:
                vel = 0.0
            moto.update(lat_atual=lat, lon_atual=lon, velocidade=round(vel, 1), last_ts=ts)
            self._atualizar_parado(moto, lat, lon, ts)
        self.salvar()
        return vel

    def _atualizar_parado(self, moto, lat, lon, ts):
        """Reinicia a contagem de "parado" quando o motoboy sai do raio do ponto de referência."""
        if moto["parado_lat"] is None or geo.haversine(moto["parado_lat"], moto["parado_lon"], lat, lon) * 1000 > self.raio_parado_m:
            moto.update(parado_desde=ts, parado_lat=lat, parado_lon=lon)
