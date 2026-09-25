import sqlite3
import pandas as pd
from flask import Flask, render_template_string, request, jsonify, send_file
import requests
import polyline
import webbrowser
from threading import Timer
from datetime import datetime
import os
import json
import io
import math
import time

# --- CONFIGURAÇÃO ---
app = Flask(__name__)
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(PASTA_ATUAL, "oficinas.db")
ARQUIVO_SESSAO = os.path.join(PASTA_ATUAL, "sessao_atual.json")
FATOR_ATRASO = 1.6 

BASE_LAT = -26.508484936938192
BASE_LON = -49.10542231274289

# --- UTILITÁRIOS ---
def haversine(lat1, lon1, lat2, lon2):
    try:
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c 
    except: return 0

# --- SESSÃO ---
status_frota = {}

def carregar_sessao():
    global status_frota
    if os.path.exists(ARQUIVO_SESSAO):
        try:
            with open(ARQUIVO_SESSAO, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                status_frota = {int(k): v for k, v in dados.items()}
        except: resetar_frota()
    else: resetar_frota()

def salvar_sessao():
    try:
        with open(ARQUIVO_SESSAO, 'w', encoding='utf-8') as f:
            json.dump(status_frota, f, ensure_ascii=False, indent=4)
    except: pass

def resetar_frota():
    global status_frota
    status_frota = {
        0: {'nome': 'Guilherme Silva', 'cor': '#e74c3c', 'status':'LIVRE', 'rota':[], 'lat_atual': BASE_LAT, 'lon_atual': BASE_LON, 'velocidade': 0, 'last_ts': 0}, 
        1: {'nome': 'Victor Santos',   'cor': '#3498db', 'status':'LIVRE', 'rota':[], 'lat_atual': BASE_LAT, 'lon_atual': BASE_LON, 'velocidade': 0, 'last_ts': 0}, 
        2: {'nome': 'Juliano Costa',   'cor': '#2ecc71', 'status':'LIVRE', 'rota':[], 'lat_atual': BASE_LAT, 'lon_atual': BASE_LON, 'velocidade': 0, 'last_ts': 0}, 
        3: {'nome': 'Rafael Souza',    'cor': '#9b59b6', 'status':'LIVRE', 'rota':[], 'lat_atual': BASE_LAT, 'lon_atual': BASE_LON, 'velocidade': 0, 'last_ts': 0}
    }

# --- BANCO DE DADOS ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, lat REAL, lon REAL, cor TEXT DEFAULT "#808080", telefone TEXT DEFAULT "", obs TEXT DEFAULT "")''')
        c.execute('''CREATE TABLE IF NOT EXISTS tracklog (id INTEGER PRIMARY KEY AUTOINCREMENT, moto_id INTEGER, lat REAL, lon REAL, velocidade REAL, timestamp INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS entregas (id INTEGER PRIMARY KEY AUTOINCREMENT, motoboy TEXT, cliente_nome TEXT, status TEXT, data_hora TEXT, assinatura_img TEXT, nota_fiscal TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS historico (id INTEGER PRIMARY KEY AUTOINCREMENT, motoboy TEXT, data_viagem TEXT, hora_saida TEXT, hora_chegada TEXT, destinos TEXT, numero_nota TEXT DEFAULT "")''')
        try: c.execute("ALTER TABLE clientes ADD COLUMN telefone TEXT DEFAULT ''")
        except: pass
        try: c.execute("ALTER TABLE clientes ADD COLUMN obs TEXT DEFAULT ''")
        except: pass
        conn.commit()

def salvar_historico_db(moto, saida, chegada, dest, nota):
    with sqlite3.connect(DB_NAME) as conn:
        conn.cursor().execute("INSERT INTO historico (motoboy, data_viagem, hora_saida, hora_chegada, destinos, numero_nota) VALUES (?,?,?,?,?,?)", 
        (moto, datetime.now().strftime("%d/%m/%Y"), saida, chegada, dest, nota))

# --- BACKEND LOGIC ---
def processar_gps(moto_id, lat, lon, ts):
    if moto_id not in status_frota: return
    moto = status_frota[moto_id]
    if not ts: ts = int(time.time())
    
    dist = haversine(moto['lat_atual'] or BASE_LAT, moto['lon_atual'] or BASE_LON, lat, lon)
    tempo_s = ts - moto['last_ts']
    vel_kmh = 0
    if tempo_s > 0 and moto['last_ts'] > 0:
        vel_kmh = (dist / (tempo_s/3600))
        if vel_kmh > 120 or vel_kmh < 1: vel_kmh = 0 
    
    moto['lat_atual'] = lat
    moto['lon_atual'] = lon
    moto['velocidade'] = vel_kmh
    moto['last_ts'] = ts
    
    with sqlite3.connect(DB_NAME) as conn:
        conn.cursor().execute("INSERT INTO tracklog (moto_id, lat, lon, velocidade, timestamp) VALUES (?,?,?,?,?)", (moto_id, lat, lon, vel_kmh, ts))
    salvar_sessao()

carregar_sessao()
init_db()

# --- INTERFACE ---
HTML_MAPA = """
<!DOCTYPE html>
<html>
<head>
    <title>Radar Peças - V79 (Gestão Clientes)</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body, html { margin: 0; padding: 0; height: 100vh; width: 100vw; overflow: hidden; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        #map { height: 100vh; width: 100vw; background: #e5e5e5; position: absolute; top: 0; left: 0; z-index: 1; cursor: crosshair; }
        
        .moto-icon-container { background: transparent; text-align: center; }
        .moto-icon-svg { filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.6)); font-size: 32px; z-index: 1000; margin-bottom: -5px; }
        .moto-label { background: rgba(0,0,0,0.8); color: white; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: bold; white-space: nowrap; border: 1px solid white; margin-bottom: 2px; }
        .speed-badge { background: #2c3e50; color: #f1c40f; border-radius: 10px; padding: 1px 6px; font-size: 10px; font-weight: 800; box-shadow: 0 2px 4px rgba(0,0,0,0.4); white-space: nowrap; margin-top: 2px; border: 1px solid #fff; }
        
        .leaflet-tooltip { background: #ffffff; border: 1px solid #aaa; box-shadow: 0 2px 5px rgba(0,0,0,0.2); border-radius: 4px; padding: 2px 6px; color: #000; font-size: 11px; font-weight: bold; font-family: sans-serif; white-space: nowrap; }
        .custom-pin { background: transparent; }

        #painel { position: absolute; top: 10px; left: 10px; bottom: 10px; width: 380px; background: white; z-index: 9999; display: flex; flex-direction: column; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); transition: height 0.3s; overflow: hidden; }
        @media (max-width: 768px) { #painel { top: auto; bottom: 10px; left: 2.5%; width: 95%; height: auto; max-height: 60vh; border-radius: 15px; } #painel.minimized { height: 60px !important; } #mobile-toggle { display: flex !important; } }
        
        .tabs { display: flex; background: #f0f0f0; border-radius: 5px 5px 0 0; flex-shrink: 0; }
        .tab-item { flex: 1; text-align: center; padding: 12px 10px; cursor: pointer; font-weight: bold; font-size: 0.85em; border-bottom: 4px solid transparent; }
        .active-0 { border-color: red; color: red; background: white;} .active-1 { border-color: blue; color: blue; background: white;} .active-2 { border-color: green; color: green; background: white;} .active-3 { border-color: purple; color: purple; background: white;}
        
        #mobile-toggle { display: none; justify-content: center; align-items: center; background: #e0e0e0; height: 30px; cursor: pointer; }
        #status-box { text-align: center; padding: 12px; color: white; font-weight: bold; margin: 10px; border-radius: 6px; font-size: 0.9em; flex-shrink: 0; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .livre { background: linear-gradient(135deg, #27ae60, #2ecc71); } .ocupado { background: linear-gradient(135deg, #c0392b, #e74c3c); }
        
        .conteudo-principal { flex: 1; overflow-y: auto; padding: 0 15px; }
        ul { list-style: none; padding: 0; } li { background: #f9f9f9; padding: 8px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; font-size: 0.9em; }
        
        .btn-full { width: 100%; padding: 12px; border: none; font-weight: bold; color: white; cursor: pointer; border-radius: 6px; margin-top: 5px; font-size: 1em; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
        .btn-go { background: linear-gradient(135deg, #f39c12, #f1c40f); } 
        .btn-end { background: linear-gradient(135deg, #2ecc71, #27ae60); }
        
        .action-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
        .modern-btn { border: none; padding: 10px; border-radius: 8px; color: white; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 5px; font-size: 0.85em; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .btn-report { background: linear-gradient(135deg, #2980b9, #3498db); } 
        .btn-replay { background: linear-gradient(135deg, #8e44ad, #9b59b6); }
        .btn-manage { background: linear-gradient(135deg, #34495e, #2c3e50); grid-column: span 2; }
        
        .bloqueado { opacity: 0.5; pointer-events: none; }
        input, select { padding: 10px; border-radius: 5px; border: 1px solid #ccc; width: 100%; box-sizing: border-box; }
        #inp-nota { border: 2px solid #f39c12; background: #fffbf0; font-weight: bold; text-align: center; margin-bottom: 5px; }
        .popup-row { display: flex; gap: 5px; align-items: center; margin-top: 8px; }
        .btn-popup-add { background: #27ae60; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; flex-grow: 1; font-weight: bold; font-size: 0.9em;}
        .btn-trash { background: #c0392b; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; }
        .color-picker-btn { width: 30px; height: 30px; border: none; padding: 0; background: none; cursor: pointer; }
        input[type="color"]::-webkit-color-swatch-wrapper { padding: 0; } input[type="color"]::-webkit-color-swatch { border: 2px solid #ddd; border-radius: 50%; }

        .modal-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.8); z-index: 20000; display: none; justify-content: center; align-items: center; }
        .modal-box { background: white; width: 90%; max-width: 700px; border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; max-height: 90vh; }
        .modal-header { padding: 15px; background: #2c3e50; color: white; display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
        .modal-body { padding: 15px; overflow-y: auto; }
        
        .btn-opt { background: linear-gradient(90deg, #8e44ad, #3498db); color: white; width: 100%; border: none; padding: 10px; margin-bottom: 10px; cursor: pointer; font-weight: bold; border-radius: 6px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        
        /* Tabela de Clientes */
        .cli-table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
        .cli-table th, .cli-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .cli-table th { background: #f2f2f2; }
        .btn-icon { border:none; background:none; cursor:pointer; font-size:1.1em; }
        .edit-btn { color: #f39c12; } .del-btn { color: #c0392b; }
    </style>
</head>
<body>
<div id="map"></div>
<div id="painel">
    <div id="mobile-toggle" onclick="togglePainel()"><i class="fas fa-chevron-down" id="toggle-icon"></i></div>
    <div class="tabs" id="tabs-container"></div>
    <div id="status-box" class="livre">DISPONÍVEL</div>
    <div class="conteudo-principal">
        <div id="controles-edicao">
            <div style="display:flex; gap:5px; margin-bottom:15px;"><input type="text" id="inp-busca" placeholder="Buscar cliente ou endereço..." style="flex:1;" onkeydown="if(event.key==='Enter') buscar()"><button onclick="buscar()">🔍</button></div>
            <div style="display:flex; gap:5px; margin-bottom:10px;"><input list="lista-clientes-sugestao" id="inp-cliente-salvo" placeholder="Cliente salvo..." style="flex:1;"><datalist id="lista-clientes-sugestao"></datalist><button onclick="adicionarClientePeloInput()" style="background:#27ae60; color:white;">＋</button></div>
        </div>
        <button id="btn-otimizar" class="btn-opt" onclick="otimizarRotaAtual()" style="display:none;">⚡ Otimizar Rota (IA)</button>
        <ul id="lista"></ul>
        <div id="msg-vazio" style="text-align:center; color:#aaa; font-size:0.8em;">Vazio</div>
    </div>
    <div class="footer-btns" style="padding:15px; background:#f4f4f4; border-top:1px solid #ddd; flex-shrink: 0;">
        <div style="text-align:center; margin-bottom:5px;"><b>Tempo Estimado: <span id="tempo" style="font-size:1.1em; color:#2c3e50;">0 min</span></b></div>
        <input type="text" id="inp-nota" placeholder="Nº NOTA / PEDIDO" />
        <button id="btn-iniciar" class="btn-full btn-go" onclick="acao('iniciar')">🚀 SAIR PARA ENTREGA</button>
        <button id="btn-voltar" class="btn-full btn-end" onclick="acao('finalizar')" style="display:none;">🏁 FINALIZAR ROTA</button>
        
        <div class="action-grid">
            <button class="modern-btn btn-report" onclick="abrirRelatorio()"><i class="fas fa-file-alt"></i> Relatório</button>
            <button class="modern-btn btn-replay" onclick="abrirReplay()"><i class="fas fa-history"></i> Replay</button>
            <button class="modern-btn btn-manage" onclick="abrirGestaoClientes()"><i class="fas fa-users"></i> Gerenciar Clientes</button>
        </div>
    </div>
</div>

<div class="modal-overlay" id="modal-gestao-clientes">
    <div class="modal-box">
        <div class="modal-header">Gerenciar Clientes <span onclick="document.getElementById('modal-gestao-clientes').style.display='none'" style="cursor:pointer;">X</span></div>
        <div class="modal-body">
            <input type="text" id="filtro-cli-lista" placeholder="Filtrar por nome..." onkeyup="filtrarTabelaClientes()" style="margin-bottom:10px;">
            <div style="overflow-y:auto; max-height:400px;">
                <table class="cli-table" id="tabela-clientes">
                    <thead><tr><th>Nome</th><th>Telefone</th><th>Ações</th></tr></thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<div class="modal-overlay" id="modal-relatorio">
    <div class="modal-box">
        <div class="modal-header">Histórico <span onclick="document.getElementById('modal-relatorio').style.display='none'" style="cursor:pointer;">X</span></div>
        <div class="modal-body">
            <div style="display:flex; gap:10px; margin-bottom:10px;">
                <input type="date" id="filtro-inicio"> <input type="date" id="filtro-fim">
                <button onclick="carregarHistoricoFiltrado()" style="padding:8px;">Filtrar</button>
                <button onclick="baixarExcel()" style="background:#27ae60; color:white; border:none; padding:8px; cursor:pointer;">Excel</button>
            </div>
            <div style="max-height:400px; overflow-y:auto;">
                <table style="width:100%; border-collapse:collapse; font-size:0.85em;">
                    <thead><tr style="background:#ddd; text-align:left;"><th>Data</th><th>Moto</th><th>Nota</th><th>Destinos</th><th>Saída</th><th>Chegada</th></tr></thead>
                    <tbody id="tbody-historico"></tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<div class="modal-overlay" id="modal-replay">
    <div class="modal-box" style="width: 500px;">
        <div class="modal-header" style="background:#8e44ad;">🎥 Replay de Rota <span onclick="document.getElementById('modal-replay').style.display='none'" style="cursor:pointer;">X</span></div>
        <div class="modal-body">
            <div style="background:#f8f9fa; padding:20px; border-radius:8px; text-align:center;">
                <p>Veja o rastro do motoboy:</p>
                <input type="range" id="replay-slider" min="0" max="100" value="0" style="width:100%; margin: 15px 0;" oninput="moverReplay(this.value)">
                <h2 id="replay-time" style="color:#2c3e50;">--:--</h2>
                <button onclick="carregarTracklog()" style="background:#8e44ad; color:white; padding:12px; border:none; border-radius:6px; cursor:pointer; width:100%;">Carregar Trilha</button>
            </div>
        </div>
    </div>
</div>

<script>
    var map = L.map('map', {zoomControl: false}).setView([{{ base_lat }}, {{ base_lon }}], 14);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution: ''}).addTo(map);
    L.control.zoom({position: 'topright'}).addTo(map);
    L.marker([{{ base_lat }}, {{ base_lon }}], {icon: L.divIcon({className: 'custom-pin', html: '<div style="font-size:30px; filter:drop-shadow(2px 2px 2px rgba(0,0,0,0.5));">🏢</div>', iconSize: [30,30], iconAnchor: [15,15]})}).addTo(map).bindPopup("<b>RADAR AUTO PEÇAS</b>");
    
    var camadaMotos = L.layerGroup().addTo(map);
    var camadaRota = L.layerGroup().addTo(map);
    var camadaClientes = L.layerGroup().addTo(map);
    var camadaReplay = L.layerGroup().addTo(map);
    
    var motoId = 0;
    var motoboys = [{id: 0, nome: "Guilherme Silva", cor: "red"}, {id: 1, nome: "Victor Santos", cor: "blue"}, {id: 2, nome: "Juliano Costa", cor: "green"}, {id: 3, nome: "Rafael Souza", cor: "purple"}];
    var todosClientes = [];
    var replayData = [];
    var ultimaRotaStr = "";

    var tabs = document.getElementById('tabs-container');
    motoboys.forEach((m, i) => { var d=document.createElement('div'); d.className=`tab-item ${i===0?'active-0':''}`; d.innerText=m.nome.split(' ')[0]; d.onclick=()=>mudarMoto(i); d.id=`tab-${i}`; tabs.appendChild(d); });
    
    function createMotoIcon(color, nome, vel) { 
        var velHtml = vel > 2 ? `<div class="speed-badge">⚡ ${Math.round(vel)} km/h</div>` : '';
        return L.divIcon({className: 'moto-icon-container', html: `<div class="moto-label" style="background:${color};">${nome.split(' ')[0]}</div><i class="fas fa-motorcycle moto-icon-svg" style="color:${color};"></i>${velHtml}`, iconSize: [60, 70], iconAnchor: [30, 35]}); 
    }
    
    function createPinIcon(color) { 
        return L.divIcon({className: 'custom-pin', html: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 42" width="30" height="42"><path d="M15 0C6.7 0 0 6.7 0 15c0 11 15 27 15 27s15-16 15-27c0-8.3-6.7-15-15-15z" fill="${color}" stroke="#333" stroke-width="1"/><circle cx="15" cy="15" r="6" fill="white"/></svg>`, iconSize: [30, 42], iconAnchor: [15, 42], popupAnchor: [0, -40]}); 
    }

    function togglePainel() { document.getElementById('painel').classList.toggle('minimized'); }
    function mudarMoto(id) { motoId = id; ultimaRotaStr = ""; motoboys.forEach(m=>document.getElementById(`tab-${m.id}`).className='tab-item'); document.getElementById(`tab-${id}`).classList.add(`active-${id}`); document.getElementById('painel').classList.remove('minimized'); camadaRota.clearLayers(); pollEstado(); }

    function pollEstado() {
        fetch('/api/estado').then(r=>r.json()).then(d => {
            camadaMotos.clearLayers();
            for(var mid in d) {
                var m = d[mid];
                if(m.lat_atual) L.marker([m.lat_atual, m.lon_atual], {icon: createMotoIcon(motoboys[mid].cor, motoboys[mid].nome, m.velocidade)}).addTo(camadaMotos);
            }
            var info = d[motoId];
            var ul = document.getElementById('lista'); ul.innerHTML = "";
            document.getElementById('msg-vazio').style.display = info.rota.length ? 'none' : 'block';
            document.getElementById('btn-otimizar').style.display = (info.rota.length > 1 && info.status === 'LIVRE') ? 'block' : 'none';

            info.rota.forEach((p, i) => { 
                ul.innerHTML += `<li><span>${i+1}. ${p.nome}</span><i class="fas fa-times" style="color:red; cursor:pointer;" onclick="rmParada(${i})"></i></li>`; 
            });
            
            var velTexto = info.velocidade > 3 ? ` (${Math.round(info.velocidade)} km/h)` : "";
            if(info.status === 'LIVRE') {
                document.getElementById('status-box').className='livre'; document.getElementById('status-box').innerText="DISPONÍVEL" + velTexto;
                document.getElementById('controles-edicao').classList.remove('bloqueado');
                document.getElementById('btn-iniciar').style.display='block'; document.getElementById('btn-voltar').style.display='none';
                document.getElementById('inp-nota').style.display = 'block'; if(!document.getElementById('inp-nota').value) document.getElementById('inp-nota').value = info.nota || "";
            } else {
                document.getElementById('status-box').className='ocupado'; document.getElementById('status-box').innerText=`EM ROTA${velTexto} - Nota: ${info.nota}`;
                document.getElementById('controles-edicao').classList.add('bloqueado');
                document.getElementById('btn-iniciar').style.display='none'; document.getElementById('btn-voltar').style.display='block';
                document.getElementById('inp-nota').style.display = 'none';
            }
            
            var rotaAtualStr = JSON.stringify(info.rota);
            if (rotaAtualStr !== ultimaRotaStr) { desenharRota(info.rota, motoboys[motoId].cor); ultimaRotaStr = rotaAtualStr; }
        });
    }

    function desenharRota(rota, cor) {
        camadaRota.clearLayers();
        if(!rota.length) { document.getElementById('tempo').innerText = "0 min"; return; }
        document.getElementById('tempo').innerText = "...";
        fetch('/api/calc', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({stops:rota})}).then(r=>r.json()).then(d => {
            document.getElementById('tempo').innerText = d.minutos + " min";
            if(d.pontos && d.pontos.length) {
                var linha = L.polyline(d.pontos, {color: cor, weight: 6}).addTo(camadaRota);
                if(window.innerWidth > 768) map.fitBounds(linha.getBounds(), {padding: [50, 50]});
            }
            rota.forEach((p, idx) => L.marker([p.lat, p.lon], {icon: createPinIcon(cor)}).bindTooltip(`<div class='rotulo-mapa'>${p.nome}</div>`, {permanent: true, direction: 'right', offset: [12, -22]}).addTo(camadaRota));
        });
    }

    function carregarClientes() {
        fetch('/api/clientes').then(r=>r.json()).then(d=>{
            todosClientes = d;
            var dl = document.getElementById('lista-clientes-sugestao'); dl.innerHTML = '';
            camadaClientes.clearLayers();
            d.forEach(c => {
                var o = document.createElement('option'); o.value = c.nome; dl.appendChild(o);
                var btnHtml = `<div class="popup-row">
                    <button class="btn-popup-add" onclick="addParada('${c.nome}', ${c.lat}, ${c.lon})">Adicionar</button>
                    <button class="btn-trash" onclick="apagarCliente(${c.id})"><i class="fas fa-trash"></i></button>
                    <input type="color" class="color-picker-btn" value="${c.cor||'#808080'}" onchange="mudarCorCliente(${c.id}, this.value)">
                </div>`;
                L.marker([c.lat, c.lon], {icon: createPinIcon(c.cor||'#808080')})
                 .bindPopup(`<b>${c.nome}</b><br>${btnHtml}`)
                 .bindTooltip(`<div class='rotulo-mapa'>${c.nome}</div>`, {permanent: true, direction: 'right', offset: [12, -22]})
                 .addTo(camadaClientes);
            });
        });
    }
    
    // --- GESTÃO DE CLIENTES (NOVO) ---
    function abrirGestaoClientes() {
        document.getElementById('modal-gestao-clientes').style.display = 'flex';
        renderizarTabelaClientes(todosClientes);
    }
    
    function renderizarTabelaClientes(lista) {
        var tbody = document.querySelector('#tabela-clientes tbody');
        tbody.innerHTML = "";
        lista.forEach(c => {
            tbody.innerHTML += `
                <tr>
                    <td>${c.nome}</td>
                    <td>${c.telefone || '-'}</td>
                    <td>
                        <button class="btn-icon edit-btn" onclick="editarCliente(${c.id}, '${c.nome}', '${c.telefone||''}')"><i class="fas fa-pen"></i></button>
                        <button class="btn-icon del-btn" onclick="apagarClienteLista(${c.id})"><i class="fas fa-trash"></i></button>
                    </td>
                </tr>`;
        });
    }
    
    function filtrarTabelaClientes() {
        var termo = document.getElementById('filtro-cli-lista').value.toLowerCase();
        var filtrados = todosClientes.filter(c => c.nome.toLowerCase().includes(termo));
        renderizarTabelaClientes(filtrados);
    }
    
    function editarCliente(id, nomeAtual, telAtual) {
        var novoNome = prompt("Novo nome:", nomeAtual);
        if(novoNome !== null) {
            var novoTel = prompt("Novo telefone:", telAtual);
            if(novoTel !== null) {
                fetch('/api/update_client', {method:'POST',headers:{'Content-Type':'application/json'}, body:JSON.stringify({id:id, nome:novoNome, telefone:novoTel})})
                .then(() => { carregarClientes(); setTimeout(abrirGestaoClientes, 500); });
            }
        }
    }
    
    function apagarClienteLista(id) {
        if(confirm("Apagar este cliente?")) {
            fetch('/api/apagar_cliente', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id:id})})
            .then(() => { carregarClientes(); setTimeout(abrirGestaoClientes, 500); });
        }
    }

    map.on('click', function(e) {
        if(confirm("Cadastrar novo cliente aqui?")) {
            var nome = prompt("Nome da Oficina:");
            if(nome) {
                fetch('/api/save_cli', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nome:nome,lat:e.latlng.lat,lon:e.latlng.lng})})
                .then(() => carregarClientes());
            }
        }
    });

    window.apagarCliente = function(id) {
        if(confirm("Apagar cliente?")) {
            fetch('/api/apagar_cliente', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id:id})})
            .then(() => { map.closePopup(); carregarClientes(); });
        }
    }

    function otimizarRotaAtual() {
        fetch('/api/otimizar', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id: motoId})})
        .then(() => { alert("Rota otimizada!"); pollEstado(); });
    }

    function abrirRelatorio() { document.getElementById('modal-relatorio').style.display = 'flex'; carregarHistoricoFiltrado(); }
    function abrirReplay() { document.getElementById('modal-replay').style.display = 'flex'; }
    
    function carregarTracklog() {
        fetch(`/api/tracklog?id=${motoId}`).then(r=>r.json()).then(d => {
            replayData = d; if(!d.length) return alert("Sem dados hoje");
            document.getElementById('replay-slider').value = 0; moverReplay(0);
        });
    }
    function moverReplay(v) {
        if(!replayData.length) return;
        var i = Math.floor((v/100)*(replayData.length-1));
        var p = replayData[i];
        camadaReplay.clearLayers();
        L.circleMarker([p.lat, p.lon], {color:'orange'}).addTo(camadaReplay);
        document.getElementById('replay-time').innerText = new Date(p.timestamp*1000).toLocaleTimeString();
    }
    function carregarHistoricoFiltrado() {
        fetch('/api/get_historico').then(r=>r.json()).then(d => {
            var t = document.getElementById('tbody-historico'); t.innerHTML = "";
            d.forEach(r => t.innerHTML += `<tr><td style='border:1px solid #ddd; padding:5px;'>${r.data_viagem}</td><td style='border:1px solid #ddd; padding:5px;'>${r.motoboy}</td><td style='border:1px solid #ddd; padding:5px;'>${r.numero_nota||'-'}</td><td style='border:1px solid #ddd; padding:5px;'>${r.destinos}</td><td style='border:1px solid #ddd; padding:5px;'>${r.hora_saida}</td><td style='border:1px solid #ddd; padding:5px;'>${r.hora_chegada}</td></tr>`);
        });
    }
    function baixarExcel() { window.open('/baixar_excel'); }

    window.mudarCorCliente = function(id, novaCor) { fetch('/api/update_color', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id: id, cor: novaCor})}).then(() => { carregarClientes(); }); }
    
    // --- BUSCA HÍBRIDA CORRIGIDA (PRIMEIRO BANCO, DEPOIS API) ---
    function buscar() { 
        var q = document.getElementById('inp-busca').value; 
        if(!q) return;
        
        // 1. Tenta achar no banco local
        var localMatch = todosClientes.find(c => c.nome.toLowerCase().includes(q.toLowerCase()));
        
        if (localMatch) {
            // Se achou, foca nele
            map.setView([localMatch.lat, localMatch.lon], 18);
            L.popup().setLatLng([localMatch.lat, localMatch.lon]).setContent(`<b>${localMatch.nome}</b><br><button onclick="addParada('${localMatch.nome}', ${localMatch.lat}, ${localMatch.lon})">Adicionar</button>`).openOn(map);
            document.getElementById('inp-busca').value = "";
        } else {
            // 2. Se não achou, vai pra API
            fetch(`/api/buscar?q=${q}`).then(r=>r.json()).then(d=>{ 
                if(d[0]) { 
                    var n=prompt("Nome:", d[0].display_name.split(',')[0]); 
                    if(n) { addParada(n, d[0].lat, d[0].lon); document.getElementById('inp-busca').value=""; } 
                } else {
                    alert("Não encontrado no cadastro nem no mapa.");
                }
            }); 
        }
    }
    
    function addParada(n,la,lo) { fetch('/api/add', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:motoId,nome:n,lat:la,lon:lo})}).then(pollEstado); salvarCliente(n,la,lo); }
    function salvarCliente(n,la,lo) { fetch('/api/save_cli', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nome:n,lat:la,lon:lo})}).then(carregarClientes); }
    function rmParada(i) { fetch('/api/rm', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:motoId,idx:i})}).then(pollEstado); }
    
    function acao(t) { 
        var n = document.getElementById('inp-nota').value.trim();
        if (t === 'iniciar' && !n) {
            alert("⚠️ Digite o número da nota para sair!");
            document.getElementById('inp-nota').focus();
            return;
        }
        fetch(`/api/${t === 'iniciar' ? 'start' : 'end'}`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:motoId, nota:n})}).then(pollEstado); 
    }
    
    function adicionarClientePeloInput() { var n=document.getElementById('inp-cliente-salvo').value; var c=todosClientes.find(x=>x.nome===n); if(c) { addParada(c.nome, c.lat, c.lon); document.getElementById('inp-cliente-salvo').value=""; } }

    carregarClientes();
    setInterval(pollEstado, 2000);
</script>
</body>
</html>
"""

# --- API ROUTES ---
@app.route('/')
def index(): return render_template_string(HTML_MAPA, base_lat=BASE_LAT, base_lon=BASE_LON)

@app.route('/api/estado')
def st(): return jsonify(status_frota)

@app.route('/api/add', methods=['POST'])
def add():
    d=request.json; i=d['id']
    if status_frota[i]['status']=='LIVRE': status_frota[i]['rota'].append({'nome':d['nome'], 'lat':float(d['lat']), 'lon':float(d['lon'])}); salvar_sessao()
    return jsonify({'ok':1})

@app.route('/api/rm', methods=['POST'])
def rm():
    d=request.json; i=d['id']
    if status_frota[i]['status']=='LIVRE': status_frota[i]['rota'].pop(d['idx']); salvar_sessao()
    return jsonify({'ok':1})

@app.route('/api/otimizar', methods=['POST'])
def otimizar():
    mid = request.json['id']; rota = status_frota[mid]['rota']
    if not rota: return jsonify({'ok':0})
    atual = {'lat': status_frota[mid]['lat_atual'] or BASE_LAT, 'lon': status_frota[mid]['lon_atual'] or BASE_LON}
    nova = []
    while rota:
        mais_perto = min(rota, key=lambda p: haversine(atual['lat'], atual['lon'], p['lat'], p['lon']))
        nova.append(mais_perto); rota.remove(mais_perto); atual = mais_perto
    status_frota[mid]['rota'] = nova; salvar_sessao()
    return jsonify({'ok':1})

@app.route('/api/start', methods=['POST'])
def start():
    d=request.json; i=d['id']
    if status_frota[i]['rota']: status_frota[i].update({'status':'EM_ROTA', 'hora_saida':datetime.now().strftime("%H:%M"), 'nota': d.get('nota', '')}); salvar_sessao()
    return jsonify({'ok':1})

@app.route('/api/end', methods=['POST'])
def end():
    i=request.json['id']
    if status_frota[i]['status']=='EM_ROTA':
        chegada=datetime.now().strftime("%H:%M")
        motos=["Guilherme Silva","Victor Santos","Juliano Costa","Rafael Souza"]
        dest= ", ".join([p['nome'] for p in status_frota[i]['rota']])
        salvar_historico_db(motos[i], status_frota[i]['hora_saida'], chegada, dest, status_frota[i].get('nota', ''))
        status_frota[i] = {'status':'LIVRE', 'rota':[], 'nota': '', 'lat_atual': status_frota[i]['lat_atual'], 'lon_atual': status_frota[i]['lon_atual'], 'velocidade':0, 'last_ts':0}
        salvar_sessao()
    return jsonify({'ok':1})

@app.route('/api/gps/owntracks', methods=['POST'])
def gps_owntracks():
    try:
        data = request.json
        if data.get('_type') == 'location':
            lat = data.get('lat'); lon = data.get('lon'); tid = data.get('tid')
            ts = data.get('tst', int(time.time()))
            if lat and lon and tid:
                try: moto_id = int(tid)
                except: moto_id = -1
                if moto_id in status_frota:
                    processar_gps(moto_id, float(lat), float(lon), ts)
                    print(f"[SUCESSO] Moto {moto_id}: {lat}, {lon}")
        return jsonify([])
    except Exception as e: print(e); return jsonify([])

@app.route('/api/calc', methods=['POST'])
def calc():
    stops = request.json.get('stops', [])
    coords = [f"{BASE_LON},{BASE_LAT}"] + [f"{s['lon']},{s['lat']}" for s in stops] + [f"{BASE_LON},{BASE_LAT}"]
    try:
        # Tenta OSRM (Online)
        r = requests.get(f"http://router.project-osrm.org/route/v1/driving/{';'.join(coords)}?overview=full", timeout=2).json()
        duration = r['routes'][0]['duration']
        geometry = r['routes'][0]['geometry']
        minutes = int((duration * FATOR_ATRASO) / 60)
        return jsonify({'pontos': polyline.decode(geometry), 'minutos': minutes, 'erro':0})
    except:
        # Fallback Matemática (Offline)
        total_km = 0
        last = {'lat': BASE_LAT, 'lon': BASE_LON}
        for s in stops:
            total_km += haversine(last['lat'], last['lon'], s['lat'], s['lon'])
            last = s
        total_km += haversine(last['lat'], last['lon'], BASE_LAT, BASE_LON)
        minutes_est = int((total_km / 25) * 60) + (len(stops) * 5)
        return jsonify({'pontos': [], 'minutos': minutes_est, 'erro':0})

@app.route('/api/buscar')
def search():
    try: return jsonify(requests.get("https://nominatim.openstreetmap.org/search", params={'q':f"{request.args.get('q')}, Jaraguá do Sul", 'format':'json', 'limit':1}, headers={'User-Agent':'AppV79'}).json())
    except: return jsonify([])

@app.route('/api/clientes')
def clis():
    with sqlite3.connect(DB_NAME) as conn: conn.row_factory=sqlite3.Row; return jsonify([dict(r) for r in conn.cursor().execute("SELECT * FROM clientes ORDER BY nome").fetchall()])

@app.route('/api/save_cli', methods=['POST'])
def sv_cli():
    d=request.json
    with sqlite3.connect(DB_NAME) as conn: 
        c = conn.cursor()
        c.execute("SELECT id FROM clientes WHERE nome = ?", (d['nome'],))
        if not c.fetchone(): c.execute("INSERT INTO clientes (nome, lat, lon, cor) VALUES (?, ?, ?, ?)", (d['nome'], d['lat'], d['lon'], 'grey'))
    return jsonify({'ok':1})

@app.route('/api/update_client', methods=['POST'])
def upd_cli():
    d=request.json
    with sqlite3.connect(DB_NAME) as conn:
        conn.cursor().execute("UPDATE clientes SET nome=?, telefone=? WHERE id=?", (d['nome'], d['telefone'], d['id']))
    return jsonify({'ok':1})

@app.route('/api/update_color', methods=['POST'])
def upd_color():
    d=request.json
    with sqlite3.connect(DB_NAME) as conn: conn.cursor().execute("UPDATE clientes SET cor = ? WHERE id = ?", (d['cor'], d['id']))
    return jsonify({'ok':1})

@app.route('/api/apagar_cliente', methods=['POST'])
def del_cli():
    d=request.json
    with sqlite3.connect(DB_NAME) as conn: conn.cursor().execute("DELETE FROM clientes WHERE id = ?", (d['id'],))
    return jsonify({'ok':1})

@app.route('/api/rm', methods=['POST'])
def del_stop():
    d=request.json; i=d['id']
    if status_frota[i]['status']=='LIVRE': status_frota[i]['rota'].pop(d['idx']); salvar_sessao()
    return jsonify({'ok':1})

@app.route('/api/get_historico')
def get_hist():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        h1 = [dict(r) for r in conn.cursor().execute("SELECT * FROM historico ORDER BY id DESC").fetchall()]
        return jsonify(h1)

@app.route('/api/tracklog')
def tracklog():
    mid = request.args.get('id', 0); ts_limit = int(time.time()) - 86400
    with sqlite3.connect(DB_NAME) as conn: conn.row_factory = sqlite3.Row; return jsonify([dict(r) for r in conn.cursor().execute("SELECT lat, lon, timestamp FROM tracklog WHERE moto_id=? AND timestamp > ? ORDER BY timestamp ASC", (mid, ts_limit)).fetchall()])

@app.route('/baixar_excel')
def xls():
    conn = sqlite3.connect(DB_NAME); df = pd.read_sql_query("SELECT * FROM historico", conn); conn.close()
    output = io.BytesIO(); 
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="relatorio.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == '__main__':
    Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(host='0.0.0.0', port=5000)