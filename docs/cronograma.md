# Cronograma de entregas

> Versão editável em Word: [`Cronograma_Entregas_TCC.docx`](Cronograma_Entregas_TCC.docx)

Entregas **toda sexta-feira** do 8º período, semestre final (2026/2), de 07/08/2026 a 04/12/2026. Uma entrega está concluída quando está no branch `main`, com testes passando no CI e documentação atualizada. As semanas 9 a 18 estão cadastradas como **milestones** no GitHub, com as tarefas em **issues**.

> As entregas das semanas 1 a 8 foram consolidadas e publicadas no repositório em 25/09/2026.

## Marcos

| Marco | Data | Descrição | Status |
|-------|------|-----------|--------|
| M1 | 28/08/2026 | Requisitos e projeto aprovados | ✅ Concluído |
| M2 | 25/09/2026 | v0.8.0: sistema funcional, testado e documentado | ✅ Concluído |
| M3 | 30/10/2026 | v0.9.0: rastreador homologado na Radar Auto Peças | 🔜 Planejado |
| M4 | 20/11/2026 | Avaliação em ambiente real concluída (cronometragem + SUS) | 🔜 Planejado |
| M5 | 04/12/2026 | v1.0.0 e TCC prontos para a defesa | 🔜 Planejado |

## Entregas semanais

| Sem. | Sexta-feira | Fase | Entrega | Evidência | Status |
|:----:|:-----------:|------|---------|-----------|:------:|
| 1 | 07/08/2026 | Requisitos | Levantamento de requisitos com a Galvitech e a Radar Auto Peças (processo atual de despacho). | docs/requisitos.md | ✅ Concluída |
| 2 | 14/08/2026 | Requisitos | Requisitos validados, atores e regras de negócio definidos. | docs/requisitos.md | ✅ Concluída |
| 3 | 21/08/2026 | Projeto | Arquitetura da solução e decisões de projeto documentadas. | docs/arquitetura.md | ✅ Concluída |
| 4 | 28/08/2026 | Projeto | Modelo de dados e contrato da API REST. | docs/banco-de-dados.md, docs/api.md | ✅ Concluída |
| 5 | 04/09/2026 | Rastreamento GPS | Recebimento das posições do OwnTracks e mapa em tempo real (2 s). | radar_tracker/api.py, static/js/app.js | ✅ Concluída |
| 6 | 11/09/2026 | Rastreamento GPS | Tratamento dos dados de GPS, autenticação e simulador. | radar_tracker/frota.py, scripts/simular_motoboy.py | ✅ Concluída |
| 7 | 18/09/2026 | Roteirização | Cálculo de rota via OSRM, modo offline e otimização por vizinho mais próximo. | radar_tracker/roteamento.py, geo.py | ✅ Concluída |
| 8 | 25/09/2026 | Qualidade | Refatoração modular, testes automatizados, CI, documentação e cronograma. | Release v0.8.0 | ✅ Concluída |
| 9 | 02/10/2026 | Rastreamento GPS | Alertas de status do motoboy: sinal perdido, parado por muito tempo e bateria baixa. | Milestone "Semana 09" no GitHub | 🔜 Planejada |
| 10 | 09/10/2026 | Entregas | Confirmação de entrega por parada, com horário de chegada em cada cliente. | Milestone "Semana 10" | 🔜 Planejada |
| 11 | 16/10/2026 | Relatórios | Indicadores de desempenho e melhorias no replay de trilha. | Milestone "Semana 11" | 🔜 Planejada |
| 12 | 23/10/2026 | Segurança | Login de operador no painel e perfis de acesso. | Milestone "Semana 12" | 🔜 Planejada |
| 13 | 30/10/2026 | Testes | Testes de campo e homologação do rastreador na Radar Auto Peças. | Release v0.9.0 | 🔜 Planejada |
| 14 | 06/11/2026 | Avaliação | Cronometragem de base (processo atual) e treinamento da equipe. | Planilha de medições (baseline) | 🔜 Planejada |
| 15 | 13/11/2026 | Avaliação | Piloto em ambiente real com cronometragem usando o sistema. | Planilha de medições (piloto) | 🔜 Planejada |
| 16 | 20/11/2026 | Avaliação | Aplicação do questionário SUS e ajustes finais de usabilidade. | Resultado SUS | 🔜 Planejada |
| 17 | 27/11/2026 | TCC | Análise dos resultados e redação do artigo do TCC. | Artigo (versão para revisão) | 🔜 Planejada |
| 18 | 04/12/2026 | Defesa | Revisão final, versão 1.0.0 e preparação da defesa. | Release v1.0.0 + artigo final | 🔜 Planejada |

## Detalhamento

### Semana 01 · 07/08/2026 · Requisitos

**Entrega:** Levantamento de requisitos com a Galvitech e a Radar Auto Peças (processo atual de despacho).

- Entrevistas com o operador de expedição e com os motoboys
- Mapeamento do processo atual (manual / WhatsApp)
- Lista inicial de requisitos funcionais e não funcionais

**Evidência:** docs/requisitos.md · **Status:** Concluída

### Semana 02 · 14/08/2026 · Requisitos

**Entrega:** Requisitos validados, atores e regras de negócio definidos.

- Validação dos RF/RNF com a Galvitech
- Definição das regras de negócio (nota obrigatória, rota travada em entrega)
- Priorização das funcionalidades

**Evidência:** docs/requisitos.md · **Status:** Concluída

### Semana 03 · 21/08/2026 · Projeto

**Entrega:** Arquitetura da solução e decisões de projeto documentadas.

- Diagrama de componentes (OwnTracks, Flask, SQLite, OSRM, Leaflet)
- Máquina de estados da entrega
- Registro das decisões e alternativas

**Evidência:** docs/arquitetura.md · **Status:** Concluída

### Semana 04 · 28/08/2026 · Projeto

**Entrega:** Modelo de dados e contrato da API REST.

- Modelo ER (clientes, histórico, tracklog)
- Especificação dos endpoints
- Linha de base: protótipo V79 versionado

**Evidência:** docs/banco-de-dados.md, docs/api.md · **Status:** Concluída

### Semana 05 · 04/09/2026 · Rastreamento GPS

**Entrega:** Recebimento das posições do OwnTracks e mapa em tempo real (2 s).

- Endpoint /api/gps/owntracks
- Mapa Leaflet com ícone, nome e velocidade de cada motoboy
- Gravação da trilha (tracklog)

**Evidência:** radar_tracker/api.py, static/js/app.js · **Status:** Concluída

### Semana 06 · 11/09/2026 · Rastreamento GPS

**Entrega:** Tratamento dos dados de GPS, autenticação e simulador.

- Filtro de precisão, ordem temporal e saltos
- Token opcional no endpoint
- Simulador do OwnTracks para demonstrações

**Evidência:** radar_tracker/frota.py, scripts/simular_motoboy.py · **Status:** Concluída

### Semana 07 · 18/09/2026 · Roteirização

**Entrega:** Cálculo de rota via OSRM, modo offline e otimização por vizinho mais próximo.

- Integração com o OSRM (traçado + tempo)
- Fallback offline (Haversine + velocidade média)
- Otimização da ordem das paradas

**Evidência:** radar_tracker/roteamento.py, geo.py · **Status:** Concluída

### Semana 08 · 25/09/2026 · Qualidade

**Entrega:** Refatoração modular, testes automatizados, CI, documentação e cronograma.

- Pacote radar_tracker em camadas + correção de 7 bugs do protótipo
- 29 testes pytest + GitHub Actions (Windows/Ubuntu)
- README, docs/ e instaladores para qualquer PC

**Evidência:** Release v0.8.0 · **Status:** Concluída

### Semana 09 · 02/10/2026 · Rastreamento GPS

**Entrega:** Alertas de status do motoboy: sinal perdido, parado por muito tempo e bateria baixa.

- Detectar motoboy sem sinal (última posição antiga)
- Alerta de parada prolongada fora de um cliente
- Nível de bateria enviado pelo OwnTracks (campo batt)

**Evidência:** Milestone "Semana 09" no GitHub · **Status:** Planejada

### Semana 10 · 09/10/2026 · Entregas

**Entrega:** Confirmação de entrega por parada, com horário de chegada em cada cliente.

- Marcar cada parada como entregue no painel
- Registrar o horário de chegada por cliente
- Histórico detalhado por parada

**Evidência:** Milestone "Semana 10" · **Status:** Planejada

### Semana 11 · 16/10/2026 · Relatórios

**Entrega:** Indicadores de desempenho e melhorias no replay de trilha.

- Entregas por motoboy, tempo médio de rota e km rodados
- Replay com velocidade e paradas
- Exportação Excel com indicadores

**Evidência:** Milestone "Semana 11" · **Status:** Planejada

### Semana 12 · 23/10/2026 · Segurança

**Entrega:** Login de operador no painel e perfis de acesso.

- Autenticação de usuários do painel
- Perfis de acesso (operador / gestor)
- Proteção das rotas da API e acesso externo via HTTPS

**Evidência:** Milestone "Semana 12" · **Status:** Planejada

### Semana 13 · 30/10/2026 · Testes

**Entrega:** Testes de campo e homologação do rastreador na Radar Auto Peças.

- Testes de campo com os motoboys
- Homologação com o operador de expedição
- Correções e versão v0.9.0

**Evidência:** Release v0.9.0 · **Status:** Planejada

### Semana 14 · 06/11/2026 · Avaliação

**Entrega:** Cronometragem de base (processo atual) e treinamento da equipe.

- Medir o tempo de planejamento de rotas sem o sistema
- Treinamento dos operadores e motoboys
- Configuração do OwnTracks nos celulares

**Evidência:** Planilha de medições (baseline) · **Status:** Planejada

### Semana 15 · 13/11/2026 · Avaliação

**Entrega:** Piloto em ambiente real com cronometragem usando o sistema.

- Operação real por uma semana
- Medir o tempo de planejamento com o sistema
- Registro de incidentes e ajustes

**Evidência:** Planilha de medições (piloto) · **Status:** Planejada

### Semana 16 · 20/11/2026 · Avaliação

**Entrega:** Aplicação do questionário SUS e ajustes finais de usabilidade.

- Aplicar o SUS aos usuários
- Calcular o escore (meta ≥ 71, "bom")
- Ajustes de interface

**Evidência:** Resultado SUS · **Status:** Planejada

### Semana 17 · 27/11/2026 · TCC

**Entrega:** Análise dos resultados e redação do artigo do TCC.

- Comparar tempos antes/depois
- Discutir a hipótese e a pergunta de pesquisa
- Redação das seções de resultados e conclusão

**Evidência:** Artigo (versão para revisão) · **Status:** Planejada

### Semana 18 · 04/12/2026 · Defesa

**Entrega:** Revisão final, versão 1.0.0 e preparação da defesa.

- Revisão com a professora
- Release v1.0.0 no GitHub
- Slides, vídeo e ensaio da apresentação

**Evidência:** Release v1.0.0 + artigo final · **Status:** Planejada

## Riscos e mitigação

| Risco | Probabilidade | Mitigação |
|-------|:-------------:|-----------|
| Instabilidade do OSRM público | Média | Fallback offline já implementado; opção de hospedar OSRM próprio (OSRM_URL). |
| Qualidade do GPS nos celulares | Alta | Filtro de precisão/saltos; uso da velocidade do aparelho; orientação sobre economia de bateria. |
| Queda de internet ou do computador da loja | Média | Sessão gravada em disco e retomada no reinício; modo offline de rotas; backup da pasta data/. |
| Baixa adesão dos motoboys ao app | Média | Treinamento na semana 14; OwnTracks com configuração única e uso passivo. |
| Amostra pequena para o SUS | Alta | Incluir operadores, gestor e motoboys; registrar como limitação no TCC. |
| Atraso em alguma entrega semanal | Média | Folga nas semanas 11 e 17; escopo de relatórios pode ser reduzido sem afetar a avaliação. |
