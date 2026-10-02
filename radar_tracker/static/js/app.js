/* Painel de rastreamento de motoboys — Galvitech Ltda */
(function () {
  'use strict';

  const INTERVALO_POLL_MS = 2000;
  const $ = (id) => document.getElementById(id);

  // --- Utilitários ---
  function esc(texto) {
    return String(texto ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function api(url, corpo) {
    const opcoes = corpo === undefined ? {} : {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corpo),
    };
    return fetch(url, opcoes).then((r) => r.json());
  }

  function el(tag, attrs, ...filhos) {
    const e = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => {
      if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else if (k === 'className') e.className = v;
      else e.setAttribute(k, v);
    });
    filhos.forEach((f) => e.append(f));
    return e;
  }

  function abrirModal(id) { $(id).classList.add('aberto'); }
  function fecharModal(id) { $(id).classList.remove('aberto'); }

  // --- Mapa ---
  const map = L.map('map', { zoomControl: false }).setView(RADAR.base, 14);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap',
  }).addTo(map);
  L.control.zoom({ position: 'topright' }).addTo(map);
  L.marker(RADAR.base, {
    icon: L.divIcon({ className: 'custom-pin', html: '<div class="pin-base">🏢</div>', iconSize: [30, 30], iconAnchor: [15, 15] }),
  }).addTo(map).bindPopup(`<b>${esc(RADAR.empresa)}</b>`);

  const camadaMotos = L.layerGroup().addTo(map);
  const camadaRota = L.layerGroup().addTo(map);
  const camadaClientes = L.layerGroup().addTo(map);
  const camadaReplay = L.layerGroup().addTo(map);

  function nivelMaisGrave(alertas) { return alertas && alertas.length ? alertas[0].nivel : null; }

  function iconeMoto(m) {
    const velHtml = m.velocidade > 2 ? `<div class="speed-badge">⚡ ${Math.round(m.velocidade)} km/h</div>` : '';
    const bateriaBaixa = (m.alertas || []).some((a) => a.tipo === 'bateria_baixa');
    const batHtml = m.bateria != null
      ? `<div class="bateria-badge${bateriaBaixa ? ' baixa' : ''}">${m.carregando ? '⚡' : '🔋'} ${m.bateria}%</div>` : '';
    const nivel = nivelMaisGrave(m.alertas);
    return L.divIcon({
      className: `moto-icon-container${nivel ? ` com-alerta-${nivel}` : ''}`,
      html: `<div class="moto-label" style="background:${esc(m.cor)}">${esc(m.nome.split(' ')[0])}</div>` +
            `<i class="fas fa-motorcycle moto-icon-svg" style="color:${esc(m.cor)}"></i>${velHtml}${batHtml}`,
      iconSize: [60, 80],
      iconAnchor: [30, 35],
    });
  }

  function iconePino(cor) {
    return L.divIcon({
      className: 'custom-pin',
      html: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 42" width="30" height="42"><path d="M15 0C6.7 0 0 6.7 0 15c0 11 15 27 15 27s15-16 15-27c0-8.3-6.7-15-15-15z" fill="${esc(cor)}" stroke="#333" stroke-width="1"/><circle cx="15" cy="15" r="6" fill="white"/></svg>`,
      iconSize: [30, 42],
      iconAnchor: [15, 42],
      popupAnchor: [0, -40],
    });
  }

  // --- Estado ---
  let motoboys = [];
  let motoId = 0;
  let todosClientes = [];
  let ultimaRotaStr = '';
  let replayData = [];

  function motoAtual() { return motoboys.find((m) => m.id === motoId) || motoboys[0]; }

  // --- Abas de motoboys ---
  function montarAbas() {
    const tabs = $('tabs-container');
    tabs.innerHTML = '';
    motoboys.forEach((m) => {
      tabs.append(el('div', { className: 'tab-item', id: `tab-${m.id}`, onclick: () => mudarMoto(m.id) }, m.nome.split(' ')[0]));
    });
    destacarAba();
  }

  function destacarAba() {
    motoboys.forEach((m) => {
      const aba = $(`tab-${m.id}`);
      const ativa = m.id === motoId;
      aba.classList.toggle('ativa', ativa);
      aba.style.borderBottomColor = ativa ? m.cor : 'transparent';
      aba.style.color = ativa ? m.cor : '';
    });
  }

  function mudarMoto(id) {
    motoId = id;
    ultimaRotaStr = '';
    $('inp-nota').value = '';
    destacarAba();
    $('painel').classList.remove('minimized');
    camadaRota.clearLayers();
    camadaReplay.clearLayers();
    pollEstado();
  }

  // --- Atualização periódica ---
  function pollEstado() {
    api('/api/estado').then((estado) => {
      camadaMotos.clearLayers();
      Object.values(estado).forEach((m) => {
        if (m.lat_atual) L.marker([m.lat_atual, m.lon_atual], { icon: iconeMoto(m) }).addTo(camadaMotos);
      });
      renderizarAlertas(estado);

      const info = estado[motoId];
      if (!info) return;
      renderizarParadas(info);
      renderizarStatus(info);

      const rotaStr = JSON.stringify(info.rota);
      if (rotaStr !== ultimaRotaStr) {
        ultimaRotaStr = rotaStr;
        desenharRota(info.rota, info.cor);
      }
    }).catch(() => { $('status-box').textContent = 'SEM CONEXÃO COM O SERVIDOR'; });
  }

  const ICONE_ALERTA = { sem_sinal: 'fa-signal', parado: 'fa-hourglass-half', bateria_baixa: 'fa-battery-quarter' };
  const ORDEM_NIVEL = { critico: 0, alerta: 1, aviso: 2 };

  function renderizarAlertas(estado) {
    const box = $('alertas-box');
    box.innerHTML = '';
    const todos = [];
    Object.entries(estado).forEach(([mid, m]) => {
      const aba = $(`tab-${mid}`);
      if (aba) {
        aba.querySelectorAll('.tab-badge').forEach((b) => b.remove());
        const nivel = nivelMaisGrave(m.alertas);
        if (nivel) aba.append(el('span', { className: `tab-badge badge-${nivel}`, title: m.alertas.map((a) => a.mensagem).join(' · ') }));
      }
      (m.alertas || []).forEach((a) => todos.push({ ...a, mid: Number(mid), m }));
    });
    // Mais graves primeiro, considerando a frota inteira
    todos.sort((a, b) => ORDEM_NIVEL[a.nivel] - ORDEM_NIVEL[b.nivel]);
    todos.forEach((a) => {
      box.append(el('div', {
        className: `alerta-item nivel-${a.nivel}`,
        title: 'Ver no mapa',
        onclick: () => { mudarMoto(a.mid); map.setView([a.m.lat_atual, a.m.lon_atual], 16); },
      }, el('i', { className: `fas ${ICONE_ALERTA[a.tipo] || 'fa-exclamation-triangle'}` }), el('b', {}, a.m.nome.split(' ')[0]), a.mensagem));
    });
    box.classList.toggle('hidden', todos.length === 0);
  }

  function renderizarParadas(info) {
    const ul = $('lista');
    ul.innerHTML = '';
    info.rota.forEach((p, i) => {
      const remover = info.status === 'LIVRE'
        ? el('i', { className: 'fas fa-times rm', title: 'Remover parada', onclick: () => removerParada(i) })
        : '';
      ul.append(el('li', {}, el('span', {}, `${i + 1}. ${p.nome}`), remover));
    });
    $('msg-vazio').classList.toggle('hidden', info.rota.length > 0);
    $('btn-otimizar').classList.toggle('hidden', !(info.rota.length > 1 && info.status === 'LIVRE'));
  }

  function renderizarStatus(info) {
    const vel = (info.velocidade > 3 ? ` (${Math.round(info.velocidade)} km/h)` : '') +
      (info.bateria != null ? ` · ${info.carregando ? '⚡' : '🔋'}${info.bateria}%` : '');
    const livre = info.status === 'LIVRE';
    $('status-box').className = livre ? 'livre' : 'ocupado';
    $('status-box').textContent = livre ? `DISPONÍVEL${vel}` : `EM ROTA${vel} · Nota: ${info.nota}`;
    $('controles-edicao').classList.toggle('bloqueado', !livre);
    $('btn-iniciar').classList.toggle('hidden', !livre);
    $('btn-voltar').classList.toggle('hidden', livre);
    $('inp-nota').classList.toggle('hidden', !livre);
  }

  function desenharRota(rota, cor) {
    camadaRota.clearLayers();
    $('tempo-fonte').textContent = '';
    if (!rota.length) { $('tempo').textContent = '0 min'; return; }
    $('tempo').textContent = '...';
    api('/api/calc', { stops: rota }).then((d) => {
      $('tempo').textContent = `${d.minutos} min`;
      $('tempo-fonte').textContent = d.fonte === 'osrm'
        ? `${d.distancia_km} km · rota OSRM`
        : `${d.distancia_km} km em linha reta · estimativa offline`;
      if (d.pontos && d.pontos.length) {
        const linha = L.polyline(d.pontos, { color: cor, weight: 6 }).addTo(camadaRota);
        if (window.innerWidth > 768) map.fitBounds(linha.getBounds(), { padding: [50, 50] });
      }
      rota.forEach((p) => {
        L.marker([p.lat, p.lon], { icon: iconePino(cor) })
          .bindTooltip(esc(p.nome), { permanent: true, direction: 'right', offset: [12, -22] })
          .addTo(camadaRota);
      });
    });
  }

  // --- Paradas ---
  function adicionarParada(nome, lat, lon) {
    api('/api/add', { id: motoId, nome, lat, lon }).then(pollEstado);
    api('/api/save_cli', { nome, lat, lon }).then(carregarClientes);
  }

  function removerParada(indice) { api('/api/rm', { id: motoId, idx: indice }).then(pollEstado); }

  function adicionarClientePeloInput() {
    const nome = $('inp-cliente-salvo').value;
    const c = todosClientes.find((x) => x.nome === nome);
    if (c) { adicionarParada(c.nome, c.lat, c.lon); $('inp-cliente-salvo').value = ''; }
  }

  function otimizarRota() {
    api('/api/otimizar', { id: motoId }).then(() => { ultimaRotaStr = ''; pollEstado(); });
  }

  function acao(tipo) {
    const nota = $('inp-nota').value.trim();
    if (tipo === 'iniciar' && !nota) {
      alert('⚠️ Digite o número da nota para sair!');
      $('inp-nota').focus();
      return;
    }
    api(tipo === 'iniciar' ? '/api/start' : '/api/end', { id: motoId, nota }).then(() => {
      if (tipo === 'iniciar') $('inp-nota').value = '';
      pollEstado();
    });
  }

  // --- Busca híbrida: primeiro no cadastro, depois no Nominatim ---
  function buscar() {
    const q = $('inp-busca').value.trim();
    if (!q) return;
    const local = todosClientes.find((c) => c.nome.toLowerCase().includes(q.toLowerCase()));
    if (local) {
      map.setView([local.lat, local.lon], 18);
      const conteudo = el('div', {}, el('b', {}, local.nome), el('br'),
        el('button', { className: 'btn-popup-add', onclick: () => { adicionarParada(local.nome, local.lat, local.lon); map.closePopup(); } }, 'Adicionar à rota'));
      L.popup().setLatLng([local.lat, local.lon]).setContent(conteudo).openOn(map);
      $('inp-busca').value = '';
      return;
    }
    api(`/api/buscar?q=${encodeURIComponent(q)}`).then((d) => {
      if (!d[0]) { alert('Não encontrado no cadastro nem no mapa.'); return; }
      const nome = prompt('Nome do cliente:', d[0].display_name.split(',')[0]);
      if (nome) { adicionarParada(nome.trim(), parseFloat(d[0].lat), parseFloat(d[0].lon)); $('inp-busca').value = ''; }
    });
  }

  // --- Clientes ---
  function carregarClientes() {
    return api('/api/clientes').then((lista) => {
      todosClientes = lista;
      const dl = $('lista-clientes-sugestao');
      dl.innerHTML = '';
      camadaClientes.clearLayers();
      lista.forEach((c) => {
        dl.append(el('option', { value: c.nome }));
        const popup = el('div', {},
          el('b', {}, c.nome),
          el('div', { className: 'popup-row' },
            el('button', { className: 'btn-popup-add', onclick: () => { adicionarParada(c.nome, c.lat, c.lon); map.closePopup(); } }, 'Adicionar'),
            el('button', { className: 'btn-trash', title: 'Apagar cliente', onclick: () => apagarCliente(c.id) }, el('i', { className: 'fas fa-trash' })),
            el('input', { type: 'color', className: 'color-picker-btn', value: c.cor || '#808080', onchange: (e) => mudarCorCliente(c.id, e.target.value) })));
        L.marker([c.lat, c.lon], { icon: iconePino(c.cor || '#808080') })
          .bindPopup(popup)
          .bindTooltip(esc(c.nome), { permanent: true, direction: 'right', offset: [12, -22] })
          .addTo(camadaClientes);
      });
      if ($('modal-gestao-clientes').classList.contains('aberto')) filtrarTabelaClientes();
    });
  }

  function renderizarTabelaClientes(lista) {
    const tbody = document.querySelector('#tabela-clientes tbody');
    tbody.innerHTML = '';
    lista.forEach((c) => {
      tbody.append(el('tr', {},
        el('td', {}, c.nome),
        el('td', {}, c.telefone || '-'),
        el('td', {},
          el('button', { className: 'btn-icon edit-btn', title: 'Editar', onclick: () => editarCliente(c) }, el('i', { className: 'fas fa-pen' })),
          el('button', { className: 'btn-icon del-btn', title: 'Apagar', onclick: () => apagarCliente(c.id) }, el('i', { className: 'fas fa-trash' })))));
    });
  }

  function filtrarTabelaClientes() {
    const termo = $('filtro-cli-lista').value.toLowerCase();
    renderizarTabelaClientes(todosClientes.filter((c) => c.nome.toLowerCase().includes(termo)));
  }

  function editarCliente(c) {
    const nome = prompt('Nome:', c.nome);
    if (nome === null || !nome.trim()) return;
    const telefone = prompt('Telefone:', c.telefone || '');
    if (telefone === null) return;
    api('/api/update_client', { id: c.id, nome: nome.trim(), telefone }).then(carregarClientes);
  }

  function apagarCliente(id) {
    if (!confirm('Apagar este cliente?')) return;
    api('/api/apagar_cliente', { id }).then(() => { map.closePopup(); carregarClientes(); });
  }

  function mudarCorCliente(id, cor) { api('/api/update_color', { id, cor }).then(carregarClientes); }

  map.on('click', (e) => {
    if (!confirm('Cadastrar novo cliente aqui?')) return;
    const nome = prompt('Nome da oficina / cliente:');
    if (nome && nome.trim()) api('/api/save_cli', { nome: nome.trim(), lat: e.latlng.lat, lon: e.latlng.lng }).then(carregarClientes);
  });

  // --- Histórico ---
  function filtrosHistorico() {
    const p = new URLSearchParams();
    if ($('filtro-inicio').value) p.set('inicio', $('filtro-inicio').value);
    if ($('filtro-fim').value) p.set('fim', $('filtro-fim').value);
    return p.toString();
  }

  function carregarHistorico() {
    api(`/api/get_historico?${filtrosHistorico()}`).then((linhas) => {
      const tbody = $('tbody-historico');
      tbody.innerHTML = '';
      if (!linhas.length) tbody.append(el('tr', {}, el('td', { colspan: '6' }, 'Nenhuma viagem no período.')));
      linhas.forEach((r) => {
        tbody.append(el('tr', {}, ...[r.data_viagem, r.motoboy, r.numero_nota || '-', r.destinos, r.hora_saida, r.hora_chegada]
          .map((v) => el('td', {}, v ?? ''))));
      });
    });
  }

  // --- Replay ---
  function carregarTrilha() {
    const data = $('replay-data').value;
    api(`/api/tracklog?id=${motoId}${data ? `&data=${data}` : ''}`).then((pontos) => {
      replayData = pontos;
      camadaReplay.clearLayers();
      if (!pontos.length) { $('replay-time').textContent = '--:--'; alert('Sem posições registradas no período.'); return; }
      L.polyline(pontos.map((p) => [p.lat, p.lon]), { color: motoAtual().cor, weight: 3, dashArray: '6 6' }).addTo(camadaReplay);
      $('replay-slider').value = 0;
      moverReplay(0);
    });
  }

  let marcadorReplay = null;
  function moverReplay(v) {
    if (!replayData.length) return;
    const p = replayData[Math.floor((v / 100) * (replayData.length - 1))];
    if (marcadorReplay) camadaReplay.removeLayer(marcadorReplay);
    marcadorReplay = L.circleMarker([p.lat, p.lon], { radius: 9, color: 'orange', fillOpacity: 0.9 }).addTo(camadaReplay);
    map.panTo([p.lat, p.lon]);
    $('replay-time').textContent = new Date(p.timestamp * 1000).toLocaleTimeString('pt-BR');
  }

  // --- Eventos ---
  $('mobile-toggle').addEventListener('click', () => $('painel').classList.toggle('minimized'));
  $('btn-buscar').addEventListener('click', buscar);
  $('inp-busca').addEventListener('keydown', (e) => { if (e.key === 'Enter') buscar(); });
  $('btn-add-cliente').addEventListener('click', adicionarClientePeloInput);
  $('btn-otimizar').addEventListener('click', otimizarRota);
  $('btn-iniciar').addEventListener('click', () => acao('iniciar'));
  $('btn-voltar').addEventListener('click', () => acao('finalizar'));
  $('btn-relatorio').addEventListener('click', () => { abrirModal('modal-relatorio'); carregarHistorico(); });
  $('btn-filtrar').addEventListener('click', carregarHistorico);
  $('btn-excel').addEventListener('click', () => window.open(`/baixar_excel?${filtrosHistorico()}`));
  $('btn-replay').addEventListener('click', () => abrirModal('modal-replay'));
  $('btn-carregar-trilha').addEventListener('click', carregarTrilha);
  $('replay-slider').addEventListener('input', (e) => moverReplay(e.target.value));
  $('btn-clientes').addEventListener('click', () => { abrirModal('modal-gestao-clientes'); filtrarTabelaClientes(); });
  $('filtro-cli-lista').addEventListener('keyup', filtrarTabelaClientes);
  document.querySelectorAll('[data-fechar]').forEach((x) => x.addEventListener('click', () => fecharModal(x.dataset.fechar)));

  // --- Inicialização ---
  api('/api/motoboys').then((lista) => {
    motoboys = lista;
    motoId = lista.length ? lista[0].id : 0;
    montarAbas();
    carregarClientes();
    pollEstado();
    setInterval(pollEstado, INTERVALO_POLL_MS);
  });
})();
