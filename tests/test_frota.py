from radar_tracker.frota import EM_ROTA, LIVRE, Frota

from .conftest import MOTOBOYS


def nova_frota(tmp_path):
    return Frota([dict(m) for m in MOTOBOYS], -26.5, -49.1, tmp_path / "s.json")


def test_ciclo_completo_preserva_nome_e_cor(tmp_path):
    f = nova_frota(tmp_path)
    assert f.adicionar_parada(0, "Cliente A", -26.49, -49.08)
    assert f.iniciar(0, "12345")
    assert f.estado[0]["status"] == EM_ROTA
    assert not f.adicionar_parada(0, "Cliente B", -26.4, -49.0)  # rota travada em andamento

    viagem = f.finalizar(0)
    assert viagem["motoboy"] == "Ana Teste"
    assert viagem["destinos"] == "Cliente A"
    assert viagem["nota"] == "12345"
    snap = f.snapshot()["0"]
    assert snap["status"] == LIVRE and snap["rota"] == []
    assert snap["nome"] == "Ana Teste" and snap["cor"] == "#e74c3c"


def test_nao_inicia_sem_nota_ou_sem_rota(tmp_path):
    f = nova_frota(tmp_path)
    assert not f.iniciar(0, "123")
    f.adicionar_parada(0, "Cliente A", -26.49, -49.08)
    assert not f.iniciar(0, "")


def test_remover_parada_indice_invalido(tmp_path):
    f = nova_frota(tmp_path)
    f.adicionar_parada(0, "A", -26.49, -49.08)
    assert not f.remover_parada(0, 5)
    assert f.remover_parada(0, 0)


def test_sessao_persiste_entre_instancias(tmp_path):
    f = nova_frota(tmp_path)
    f.adicionar_parada(1, "Cliente X", -26.49, -49.08)
    g = nova_frota(tmp_path)
    g.carregar()
    assert g.estado[1]["rota"][0]["nome"] == "Cliente X"


def test_filtro_gps(tmp_path):
    f = nova_frota(tmp_path)
    assert f.atualizar_posicao(0, -26.5, -49.1, ts=1000, precisao_m=10) == 0
    assert f.atualizar_posicao(0, -26.5, -49.1, ts=1010, precisao_m=500) is None  # impreciso
    assert f.atualizar_posicao(0, -26.5, -49.1, ts=900) is None  # fora de ordem
    assert f.atualizar_posicao(0, -26.0, -49.1, ts=1020) is None  # salto de ~55 km em 20 s
    vel = f.atualizar_posicao(0, -26.5 + 0.00225, -49.1, ts=1030)  # ~250 m em 30 s = ~30 km/h
    assert 25 < vel < 35
    assert f.atualizar_posicao(0, -26.5, -49.1, ts=1040, vel_dispositivo=42) == 42
    assert f.atualizar_posicao(0, -26.5001, -49.1, ts=1040) == 42  # mesmo segundo: aceita e mantém velocidade


def test_tid_personalizado(tmp_path):
    f = nova_frota(tmp_path)
    assert f.id_por_tid("b1") == 1
    assert f.id_por_tid("zz") is None
