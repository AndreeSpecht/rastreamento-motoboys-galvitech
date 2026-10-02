# Referência da API REST

Base: `http://<servidor>:5000`. Todas as requisições `POST` usam `Content-Type: application/json`.
Erros de validação retornam **400** `{"ok": 0, "erro": "..."}` e motoboy inexistente retorna **404**.

## Sistema

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Painel web. |
| GET | `/api/health` | `{"status": "ok"}`, usado para monitoramento. |
| GET | `/api/motoboys` | Lista `[{id, nome, cor}]` configurada em `config/motoboys.json`. |

## Frota e rotas

| Método | Rota | Corpo | Resposta |
|--------|------|-------|----------|
| GET | `/api/estado` | — | Objeto indexado pelo id do motoboy: `status`, `rota[]`, `nota`, `hora_saida`, `lat_atual`, `lon_atual`, `velocidade`, `last_ts`, `bateria`, `carregando`, `recebido_em`, `inicio_ts`, `parado_desde`, `nome`, `cor` e `alertas[]` (ver abaixo). |
| POST | `/api/add` | `{id, nome, lat, lon}` | `{ok}`: adiciona parada (só com status `LIVRE`). |
| POST | `/api/rm` | `{id, idx}` | `{ok}`: remove a parada da posição `idx`. |
| POST | `/api/otimizar` | `{id}` | `{ok}`: reordena as paradas pelo vizinho mais próximo (mínimo de 2). |
| POST | `/api/start` | `{id, nota}` | `{ok}`: inicia a entrega (exige paradas e nota). |
| POST | `/api/end` | `{id}` | `{ok}`: finaliza e grava no histórico. |
| POST | `/api/calc` | `{stops: [{lat, lon}]}` | `{pontos: [[lat, lon]], minutos, distancia_km, fonte: "osrm" \| "offline"}` |
| GET | `/api/buscar?q=texto` | — | Resultado do Nominatim (lista), limitado à `CIDADE_BUSCA`. |

## Alertas

Cada motoboy em `/api/estado` traz a lista `alertas`, e `GET /api/alertas` devolve os alertas de toda a frota, do mais grave ao mais leve:

```json
[
  { "tipo": "sem_sinal", "nivel": "critico", "mensagem": "Sem sinal há 4 min", "minutos": 4, "moto_id": 0, "motoboy": "Motoboy Um" },
  { "tipo": "parado", "nivel": "alerta", "mensagem": "Parado há 12 min fora de um cliente", "minutos": 12, "moto_id": 1, "motoboy": "Motoboy Dois" },
  { "tipo": "bateria_baixa", "nivel": "aviso", "mensagem": "Bateria do celular em 14%", "bateria": 14, "moto_id": 2, "motoboy": "Motoboy Três" }
]
```

| Tipo | Nível | Regra (padrões configuráveis no `.env`) |
|------|-------|------------------------------------------|
| `sem_sinal` | crítico | Em entrega e sem mensagem do celular há `ALERTA_SEM_SINAL_MIN` (3 min), contando desde a saída se nunca enviou. |
| `parado` | alerta | Em entrega, sem sair de um raio de `ALERTA_RAIO_PARADO_M` (50 m) há `ALERTA_PARADO_MIN` (10 min) e a mais de `ALERTA_RAIO_CLIENTE_M` (100 m) de clientes, paradas e loja. Não aparece junto com `sem_sinal`. |
| `bateria_baixa` | aviso | `batt` abaixo de `ALERTA_BATERIA_MIN` (20%) e celular fora da tomada. Vale mesmo fora da entrega. |

## GPS (OwnTracks)

`POST /api/gps/owntracks`: recebe o [payload de localização do OwnTracks](https://owntracks.org/booklet/tech/json/#_typelocation).

```json
{ "_type": "location", "tid": "0", "lat": -26.5085, "lon": -49.1054, "tst": 1790364807, "acc": 8, "vel": 32 }
```

| Campo | Uso |
|-------|-----|
| `tid` | Tracker ID → identifica o motoboy (campo `tid` em `config/motoboys.json`). |
| `lat`, `lon` | Posição. |
| `tst` | Timestamp Unix da leitura (se ausente, usa a hora do servidor). |
| `acc` | Precisão em metros. Leituras acima de `GPS_PRECISAO_MAX_M` são descartadas. |
| `vel` | Velocidade em km/h informada pelo aparelho (preferida quando presente). |
| `batt` | Bateria do celular em % (alerta de bateria baixa). |
| `bs` | Estado da bateria: `1` desconectado, `2` carregando, `3` carga completa. Com 2 ou 3 o alerta de bateria é ignorado. |

Resposta sempre `[]` (o OwnTracks espera uma lista). Se `OWNTRACKS_TOKEN` estiver definido, envie-o como **senha** do HTTP Basic Auth (o usuário pode ser qualquer um) ou no header `X-Token`. Sem o token, a resposta é **401**.

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/tracklog?id=0[&data=AAAA-MM-DD]` | Pontos `[{lat, lon, velocidade, timestamp}]` do dia informado ou das últimas 24 h. |

## Clientes

| Método | Rota | Corpo | Resposta |
|--------|------|-------|----------|
| GET | `/api/clientes` | — | `[{id, nome, lat, lon, cor, telefone, obs}]` em ordem alfabética. |
| POST | `/api/save_cli` | `{nome, lat, lon}` | `{ok, id}`. Se já existir um cliente com o mesmo nome, devolve o id existente. |
| POST | `/api/update_client` | `{id, nome, telefone}` | `{ok}` |
| POST | `/api/update_color` | `{id, cor: "#rrggbb"}` | `{ok}` |
| POST | `/api/apagar_cliente` | `{id}` | `{ok}` |

## Histórico e relatórios

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/get_historico[?inicio=AAAA-MM-DD&fim=AAAA-MM-DD]` | Viagens (mais recentes primeiro). |
| GET | `/baixar_excel[?inicio=...&fim=...]` | Planilha `.xlsx` com o mesmo filtro. |

## Exemplo com `curl`

```bash
curl -X POST localhost:5000/api/add -H "Content-Type: application/json" \
     -d '{"id":0,"nome":"Oficina Centro","lat":-26.4851,"lon":-49.0713}'
curl -X POST localhost:5000/api/start -H "Content-Type: application/json" -d '{"id":0,"nota":"NF-1001"}'
curl -X POST localhost:5000/api/gps/owntracks -H "Content-Type: application/json" \
     -d '{"_type":"location","tid":"0","lat":-26.50,"lon":-49.10,"acc":10}'
curl -X POST localhost:5000/api/end -H "Content-Type: application/json" -d '{"id":0}'
```
