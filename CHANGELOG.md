# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). O projeto usa [versionamento semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

Planejado (ver [cronograma](docs/cronograma.md)): alertas de status, confirmação de entrega por parada, indicadores, login de operador, homologação e avaliação em ambiente real.

## [0.8.0] - 2026-09-25 (entrega da semana 8)

### Adicionado
- Pacote `radar_tracker` em camadas (config, banco, frota, geo, roteamento, API, frontend).
- Filtro de leituras GPS por precisão, ordem temporal e saltos de velocidade. A velocidade informada pelo aparelho tem preferência.
- Token opcional no endpoint do OwnTracks (`OWNTRACKS_TOKEN`, via HTTP Basic ou `X-Token`).
- Identificação do motoboy pelo Tracker ID configurável em `config/motoboys.json`.
- Filtro de datas no histórico, que também vale para a exportação Excel.
- Replay de trilha com seleção de dia e traçado completo no mapa.
- Endpoints `/api/health` e `/api/motoboys`, e distância e origem (OSRM/offline) no cálculo de rota.
- Configuração por `.env`; scripts `instalar`/`iniciar` para Windows e Linux/macOS; servidor `waitress`.
- `scripts/seed_demo.py` (clientes fictícios) e `scripts/simular_motoboy.py` (simulador do OwnTracks).
- 29 testes automatizados e CI no GitHub Actions (Windows e Ubuntu).
- Documentação completa em `docs/` e cronograma de entregas em Word e Markdown.

### Corrigido
- Rota `/api/rm` registrada em duplicidade.
- Finalizar uma rota apagava nome e cor do motoboy da sessão.
- Nomes de clientes com aspas quebravam o painel (injeção de HTML).
- Termo de busca de endereço não era codificado na URL.
- Filtro de datas do relatório não tinha efeito.
- Leituras de GPS no mesmo segundo eram descartadas.

### Alterado
- Exportação Excel usa `openpyxl` diretamente (sem `pandas`).
- Leaflet atualizado para 1.9.4.
- Binários, bancos de dados e domínio do ngrok removidos do repositório.

## [0.1.0] - 2026-01-28 (protótipo V79)

### Adicionado
- Protótipo monolítico (`app_radar_pro.py`) em uso na Radar Auto Peças: rastreamento via OwnTracks, rotas OSRM com fallback, vizinho mais próximo, clientes, histórico com nota, replay e Excel.
