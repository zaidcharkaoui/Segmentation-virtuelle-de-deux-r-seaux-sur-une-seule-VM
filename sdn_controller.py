#!/usr/bin/env python3
"""
==============================================================================
PROJET PFA-04 (EMSI) — Contrôleur Web SDN & Dashboard Temps Réel
Scénario : NovaStudio Cloud (DarMarket VLAN 10 vs AtlasPay VLAN 20)
==============================================================================
Ce serveur Python (100% bibliothèque standard, aucun 'pip install' requis)
se branche directement sur les outils Linux de la VM Ubuntu :
  - ip netns (namespaces réseau)
  - ovs-vsctl & ovs-ofctl (Open vSwitch : VLANs & règles OpenFlow)
  - ping & curl (génération de trafic réel)
  - tcpdump (lecture des vraies captures .pcap)

Lancement sur Ubuntu Server :
  sudo python3 sdn_controller.py
Puis ouvrir dans le navigateur du PC :
  http://<IP_DE_LA_VM>:5000
==============================================================================
"""

import http.server
import json
import os
import re
import socket
import subprocess
import time
from urllib.parse import urlparse

PORT = 5000
BRIDGE = "br-pfa"
HOSTNAME = socket.gethostname()
PROOF_DIR = f"./preuves_{HOSTNAME}"
os.makedirs(PROOF_DIR, exist_ok=True)

# Cartographie des namespaces de la VM
NODES = {
    "ns-a1": {"ip": "10.10.0.11", "veth": "veth-a1", "ovs": "ovs-a1", "default_vlan": 10, "group": "A", "role": "Serveur Web DarMarket"},
    "ns-a2": {"ip": "10.10.0.12", "veth": "veth-a2", "ovs": "ovs-a2", "default_vlan": 10, "group": "A", "role": "Client Test DarMarket"},
    "ns-b1": {"ip": "10.10.0.21", "veth": "veth-b1", "ovs": "ovs-b1", "default_vlan": 20, "group": "B", "role": "Serveur API AtlasPay"},
    "ns-b2": {"ip": "10.10.0.22", "veth": "veth-b2", "ovs": "ovs-b2", "default_vlan": 20, "group": "B", "role": "Client Test AtlasPay"},
}

# État courant des permissions pilotées par le contrôleur
STATE = {
    "intraA": True,
    "intraB": True,
    "inter": False,
    "allowed_count": 0,
    "blocked_count": 0,
    "icmp_allowed": 0,
    "http_allowed": 0,
    "icmp_blocked": 0,
    "http_blocked": 0,
    "last_cmd": "sudo ./pfa_lab.sh setup && sudo ./pfa_lab.sh start",
}


def run_cmd(cmd, timeout=5):
    """Exécute une commande shell Linux et retourne (code_retour, stdout, stderr, duree_ms)."""
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        dt_ms = round((time.time() - t0) * 1000, 1)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip(), dt_ms
    except subprocess.TimeoutExpired:
        dt_ms = round((time.time() - t0) * 1000, 1)
        return 124, "", "Timeout expired (100% packet loss / Flux bloqué)", dt_ms


def get_system_status():
    """Récupère l'état réel des namespaces, des ports VLAN OVS et des règles OpenFlow."""
    _, netns_out, _, _ = run_cmd("ip netns list")
    _, ovs_out, _, _ = run_cmd(f"ovs-vsctl show")
    _, flows_out, _, _ = run_cmd(f"ovs-ofctl dump-flows {BRIDGE} 2>/dev/null || true")

    # Vérifier le tag VLAN réel de ovs-b1 pour savoir si l'inter-groupe est ouvert
    _, tag_b1, _, _ = run_cmd("ovs-vsctl get port ovs-b1 tag 2>/dev/null || echo 20")
    STATE["inter"] = (tag_b1.strip() == "10")

    return {
        "hostname": HOSTNAME,
        "bridge_up": BRIDGE in ovs_out,
        "netns_list": [line.split()[0] for line in netns_out.splitlines() if line.strip()],
        "ovs_Flows": flows_out,
        "permissions": {
            "intraA": STATE["intraA"],
            "intraB": STATE["intraB"],
            "inter": STATE["inter"],
        },
        "stats": {
            "allowed": STATE["allowed_count"],
            "blocked": STATE["blocked_count"],
            "icmp_allowed": STATE["icmp_allowed"],
            "http_allowed": STATE["http_allowed"],
            "icmp_blocked": STATE["icmp_blocked"],
            "http_blocked": STATE["http_blocked"],
        },
        "last_cmd": STATE["last_cmd"],
    }


def apply_permission_change(target, allow):
    """Applique réellement la permission sur Open vSwitch dans le noyau Linux."""
    allow = bool(allow)
    if target == "inter":
        if allow:
            cmd = "ovs-vsctl set port ovs-b1 tag=10 && ovs-vsctl set port ovs-b2 tag=10"
        else:
            cmd = "ovs-vsctl set port ovs-b1 tag=20 && ovs-vsctl set port ovs-b2 tag=20"
        run_cmd(cmd)
        STATE["inter"] = allow
        STATE["last_cmd"] = f"sudo {cmd}"

    elif target == "intraA":
        if allow:
            cmd = f"ovs-ofctl del-flows {BRIDGE} 'in_port=ovs-a2'"
        else:
            cmd = f"ovs-ofctl add-flow {BRIDGE} 'priority=200,in_port=ovs-a2,actions=drop'"
        run_cmd(cmd)
        STATE["intraA"] = allow
        STATE["last_cmd"] = f"sudo {cmd}"

    elif target == "intraB":
        if allow:
            cmd = f"ovs-ofctl del-flows {BRIDGE} 'in_port=ovs-b2'"
        else:
            cmd = f"ovs-ofctl add-flow {BRIDGE} 'priority=200,in_port=ovs-b2,actions=drop'"
        run_cmd(cmd)
        STATE["intraB"] = allow
        STATE["last_cmd"] = f"sudo {cmd}"

    return get_system_status()


def execute_real_network_flow(src_ns, dst_ns, proto, pcap_name=None):
    """Exécute un vrai ping ou curl entre deux namespaces Linux avec capture tcpdump réelle."""
    if src_ns not in NODES or dst_ns not in NODES:
        return {"error": "Namespace invalide"}

    dst_info = NODES[dst_ns]
    dst_ip = dst_info["ip"]
    dst_veth = dst_info["veth"]

    pcap_file = os.path.join(PROOF_DIR, pcap_name or "live_capture.pcap")

    # 1. Démarrer une vraie sonde tcpdump en arrière-plan sur l'interface cible
    tcpdump_proc = subprocess.Popen(
        ["ip", "netns", "exec", dst_ns, "tcpdump", "-i", dst_veth, "-nn", "-c", "6", "-w", pcap_file],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.25)

    # 2. Exécuter le vrai flux (ping ou curl) depuis le namespace source
    if proto == "PING":
        real_cmd = f"ip netns exec {src_ns} ping -c 1 -W 1 {dst_ip}"
    else:
        real_cmd = f"ip netns exec {src_ns} curl -s --max-time 2 http://{dst_ip}:8080"

    STATE["last_cmd"] = f"sudo {real_cmd}"
    rc, out, err, duration_ms = run_cmd(real_cmd, timeout=3)

    # 3. Arrêter proprement tcpdump et lire les paquets capturés
    time.sleep(0.25)
    tcpdump_proc.terminate()
    try:
        tcpdump_proc.wait(timeout=1)
    except subprocess.TimeoutExpired:
        tcpdump_proc.kill()

    _, pcap_read, _, _ = run_cmd(f"tcpdump -nn -r {pcap_file} 2>/dev/null || true")
    pcap_size = os.path.getsize(pcap_file) if os.path.exists(pcap_file) else 0

    allowed = (rc == 0)
    if allowed:
        STATE["allowed_count"] += 1
        if proto == "PING":
            STATE["icmp_allowed"] += 1
        else:
            STATE["http_allowed"] += 1
    else:
        STATE["blocked_count"] += 1
        if proto == "PING":
            STATE["icmp_blocked"] += 1
        else:
            STATE["http_blocked"] += 1

    # Extraire la latence exacte si ping a réussi
    latency_str = f"{duration_ms} ms"
    m = re.search(r"time=([0-9.]+)\s*ms", out)
    if m:
        latency_str = f"{m.group(1)} ms"

    if not pcap_read.strip():
        ts = time.strftime("%H:%M:%S")
        pcap_lines = [
            f"{ts} [OVS-DROP] Aucun paquet reçu sur {dst_ns} ({dst_veth}) — Fichier { os.path.basename(pcap_file) } = {pcap_size} octets (100% bloqué par Open vSwitch)"
        ]
    else:
        pcap_lines = [line for line in pcap_read.splitlines() if line.strip()]

    return {
        "allowed": allowed,
        "src": src_ns,
        "dst": dst_ns,
        "proto": proto,
        "command": f"sudo {real_cmd}",
        "output": out if allowed else (err or "100% packet loss / Connection timed out (Bloqué par OVS)"),
        "latency": latency_str if allowed else "Timeout (Drop)",
        "pcap_file": os.path.basename(pcap_file),
        "pcap_size": pcap_size,
        "tcpdump_lines": pcap_lines,
        "status": get_system_status(),
    }


# ==============================================================================
# INTERFACE WEB HTML SERVIE DIRECTEMENT PAR LE CONTRÔLEUR PYTHON
# ==============================================================================
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NovaStudio SDN Controller — Connecté en Direct à Ubuntu Server</title>
  <script src="https://cdn.tailwindcss.com/3.4.17"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    body { font-family: 'Inter', sans-serif; background-color: #0b1120; color: #e2e8f0; }
    .mono { font-family: 'JetBrains Mono', monospace; }
    .custom-scroll::-webkit-scrollbar { width: 6px; height: 6px; }
    .custom-scroll::-webkit-scrollbar-track { background: #0f172a; }
    .custom-scroll::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
  </style>
</head>
<body class="min-h-screen flex flex-col">
  <div id="toastBox" class="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"></div>

  <header class="bg-slate-900/95 border-b border-slate-800 sticky top-0 z-40 backdrop-blur">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-blue-600 flex items-center justify-center font-extrabold text-white text-lg shadow-lg">
          SDN
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-base sm:text-lg font-extrabold text-white">NovaStudio Cloud — Contrôleur SDN Temps Réel</h1>
            <span id="vmHostBadge" class="px-2.5 py-0.5 text-[11px] font-bold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 mono">
              ● CONNECTÉ À LA VM
            </span>
          </div>
          <p class="text-xs text-slate-400">Pilotage réel du noyau Linux (<span class="mono text-slate-300">ip netns</span> • <span class="mono text-slate-300">Open vSwitch</span> • <span class="mono text-slate-300">tcpdump</span>)</p>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button onclick="runLabAction('setup')" class="px-3 py-1.5 rounded-lg text-xs font-bold bg-teal-600 hover:bg-teal-500 text-white transition shadow">
          🔄 Réinitialiser Topologie (Setup + Start)
        </button>
      </div>
    </div>
  </header>

  <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-5 space-y-5">

    <!-- KPI Row -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
      <div class="bg-slate-900 border border-emerald-500/30 rounded-2xl p-4 flex items-center justify-between">
        <div>
          <p class="text-xs font-medium text-slate-400 uppercase">Flux Autorisés (Réels)</p>
          <span id="kpiAllowed" class="text-3xl font-extrabold text-emerald-400 mono">0</span>
          <p class="text-[11px] text-slate-400 mt-1">Code retour Linux = 0 (OK)</p>
        </div>
        <div class="w-11 h-11 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-lg">✓</div>
      </div>

      <div class="bg-slate-900 border border-rose-500/30 rounded-2xl p-4 flex items-center justify-between">
        <div>
          <p class="text-xs font-medium text-slate-400 uppercase">Flux Stoppés (Bloqués OVS)</p>
          <span id="kpiBlocked" class="text-3xl font-extrabold text-rose-400 mono">0</span>
          <p class="text-[11px] text-slate-400 mt-1">100% Packet Loss / Timeout</p>
        </div>
        <div class="w-11 h-11 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400 font-bold text-lg">✕</div>
      </div>

      <div id="kpiInterCard" class="bg-slate-900 border border-rose-500/40 rounded-2xl p-4 flex items-center justify-between">
        <div>
          <p class="text-xs font-medium text-slate-400 uppercase">État Règle Inter-Groupe</p>
          <div class="mt-1">
            <span id="kpiInterBadge" class="inline-flex px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40">
              🔒 INTERDIT (VLAN 10 ≠ 20)
            </span>
          </div>
          <p class="text-[11px] text-slate-400 mt-1">DarMarket ↔ AtlasPay</p>
        </div>
        <button onclick="togglePerm('inter')" class="px-3 py-2 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-white border border-slate-700">
          Basculer
        </button>
      </div>

      <div class="bg-slate-900 border border-sky-500/30 rounded-2xl p-4 flex items-center justify-between">
        <div>
          <p class="text-xs font-medium text-slate-400 uppercase">Dernière Latence Mesurée</p>
          <span id="kpiLatency" class="text-2xl font-extrabold text-sky-400 mono">-- ms</span>
          <p id="kpiBridgeState" class="text-[11px] text-emerald-400 mt-1 font-medium">● Switch br-pfa actif</p>
        </div>
        <div class="w-11 h-11 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-400 font-bold text-xs mono">LIVE</div>
      </div>
    </section>

    <!-- Main Control & Topology Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">

      <!-- Left Column: Permissions & Real Tests -->
      <div class="lg:col-span-5 space-y-4">

        <!-- Permissions Box -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
          <div class="border-b border-slate-800 pb-2">
            <h2 class="text-sm font-bold text-white">🛡️ Contrôle des Permissions en Direct (Open vSwitch)</h2>
            <p class="text-xs text-slate-400">Chaque clic exécute réellement <span class="mono text-teal-300">ovs-vsctl</span> / <span class="mono text-teal-300">ovs-ofctl</span> sur votre VM</p>
          </div>

          <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
            <div>
              <span class="text-xs font-bold text-white">Flux Intra-Groupe A (DarMarket VLAN 10)</span>
              <p class="text-[11px] text-slate-400 mono">ns-a2 (10.10.0.12) ↔ ns-a1 (10.10.0.11)</p>
            </div>
            <button id="btnIntraA" onclick="togglePerm('intraA')" class="px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
              ✓ PERMIS
            </button>
          </div>

          <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
            <div>
              <span class="text-xs font-bold text-white">Flux Intra-Groupe B (AtlasPay VLAN 20)</span>
              <p class="text-[11px] text-slate-400 mono">ns-b2 (10.10.0.22) ↔ ns-b1 (10.10.0.21)</p>
            </div>
            <button id="btnIntraB" onclick="togglePerm('intraB')" class="px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
              ✓ PERMIS
            </button>
          </div>

          <div id="boxInter" class="p-3.5 rounded-xl bg-rose-950/25 border border-rose-500/40 flex items-center justify-between">
            <div>
              <span class="text-xs font-bold text-white">Flux Inter-Groupe (DarMarket ↔ AtlasPay)</span>
              <p id="descInter" class="text-[11px] text-rose-200/80">Isolation VLAN 10 ≠ VLAN 20 active sur la VM</p>
            </div>
            <button id="btnInter" onclick="togglePerm('inter')" class="px-3.5 py-2 rounded-lg text-xs font-extrabold bg-rose-600 text-white shadow">
              ✕ INTERDIT
            </button>
          </div>

          <div class="bg-slate-950 rounded-xl p-2.5 border border-slate-800">
            <span class="text-[10px] text-slate-400 block mb-1">COMMANDE LINUX EXÉCUTÉE SUR LA VM :</span>
            <code id="cmdDisplay" class="text-[11px] mono text-teal-300 break-all">sudo ./pfa_lab.sh setup</code>
          </div>
        </div>

        <!-- Tests Launcher Box -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
          <div class="border-b border-slate-800 pb-2">
            <h2 class="text-sm font-bold text-white">🚀 Lancer les Vrais Tests sur la VM Ubuntu</h2>
            <p class="text-xs text-slate-400">Exécute <span class="mono">ip netns exec</span> + <span class="mono">tcpdump</span> et affiche le vrai résultat</p>
          </div>

          <div class="grid grid-cols-3 gap-2">
            <button onclick="runRealTest(1)" class="p-2.5 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-left">
              <span class="text-xs font-extrabold text-emerald-300 block">TEST 1 (Intra)</span>
              <span class="text-[10px] text-slate-300">ns-a2 → ns-a1</span>
            </button>
            <button onclick="runRealTest(2)" class="p-2.5 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/40 text-left">
              <span class="text-xs font-extrabold text-rose-300 block">TEST 2 (Inter)</span>
              <span class="text-[10px] text-slate-300">ns-a2 → ns-b1</span>
            </button>
            <button onclick="runRealTest(3)" class="p-2.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-left">
              <span class="text-xs font-extrabold text-amber-300 block">TEST 3 (Cycle)</span>
              <span class="text-[10px] text-slate-300">Ouvrir → Bloquer</span>
            </button>
          </div>

          <div class="pt-2 border-t border-slate-800 grid grid-cols-3 gap-2">
            <select id="selSrc" class="bg-slate-950 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-white">
              <option value="ns-a2">De: ns-a2 (.12)</option>
              <option value="ns-b2">De: ns-b2 (.22)</option>
              <option value="ns-a1">De: ns-a1 (.11)</option>
            </select>
            <select id="selDst" class="bg-slate-950 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-white">
              <option value="ns-a1">Vers: ns-a1 (.11)</option>
              <option value="ns-b1">Vers: ns-b1 (.21)</option>
              <option value="ns-b2">Vers: ns-b2 (.22)</option>
            </select>
            <select id="selProto" class="bg-slate-950 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-white">
              <option value="CURL">HTTP curl :8080</option>
              <option value="PING">ICMP ping</option>
            </select>
          </div>

          <button onclick="sendCustomRealFlow()" class="w-full py-2 rounded-xl bg-gradient-to-r from-teal-600 to-blue-600 hover:from-teal-500 hover:to-blue-500 text-white font-bold text-xs shadow">
            ⚡ Exécuter ce Flux sur la VM maintenant
          </button>
        </div>
      </div>

      <!-- Right Column: Visual Topology & Live Server Response -->
      <div class="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col justify-between">
        <div class="flex items-center justify-between border-b border-slate-800 pb-2.5">
          <div>
            <h2 class="text-sm font-bold text-white">🌐 Topologie Réseau en Direct (<span id="topoHostTitle" class="mono text-teal-300">Ubuntu VM</span>)</h2>
            <p class="text-xs text-slate-400">Animation synchronisée avec le vrai résultat de la commande Linux</p>
          </div>
        </div>

        <div class="my-3 bg-slate-950 rounded-xl border border-slate-800 p-2">
          <svg viewBox="0 0 760 365" class="w-full h-auto">
            <!-- Group A -->
            <rect x="20" y="15" width="335" height="175" rx="12" fill="#0284c7" fill-opacity="0.08" stroke="#0284c7" stroke-width="1.6" stroke-dasharray="5,3"/>
            <text x="187" y="36" text-anchor="middle" fill="#38bdf8" font-size="11.5" font-weight="700">GROUPE A — DarMarket (VLAN 10)</text>

            <rect x="36" y="50" width="142" height="95" rx="9" fill="#0f172a" stroke="#38bdf8" stroke-width="2"/>
            <text x="107" y="72" text-anchor="middle" fill="#fff" font-size="11" font-weight="700">ns-a1 (Serveur)</text>
            <text x="107" y="90" text-anchor="middle" fill="#7dd3fc" font-size="10" font-family="monospace">10.10.0.11:8080</text>
            <text x="107" y="112" text-anchor="middle" fill="#94a3b8" font-size="9.5" font-family="monospace">veth-a1</text>

            <rect x="196" y="50" width="142" height="95" rx="9" fill="#0f172a" stroke="#38bdf8" stroke-width="2"/>
            <text x="267" y="72" text-anchor="middle" fill="#fff" font-size="11" font-weight="700">ns-a2 (Client)</text>
            <text x="267" y="90" text-anchor="middle" fill="#7dd3fc" font-size="10" font-family="monospace">10.10.0.12/24</text>
            <text x="267" y="112" text-anchor="middle" fill="#94a3b8" font-size="9.5" font-family="monospace">veth-a2</text>

            <!-- Group B -->
            <rect x="405" y="15" width="335" height="175" rx="12" fill="#0d9488" fill-opacity="0.08" stroke="#0d9488" stroke-width="1.6" stroke-dasharray="5,3"/>
            <text x="572" y="36" text-anchor="middle" fill="#2dd4bf" font-size="11.5" font-weight="700">GROUPE B — AtlasPay (VLAN 20)</text>

            <rect x="422" y="50" width="142" height="95" rx="9" fill="#0f172a" stroke="#2dd4bf" stroke-width="2"/>
            <text x="493" y="72" text-anchor="middle" fill="#fff" font-size="11" font-weight="700">ns-b1 (API FinTech)</text>
            <text x="493" y="90" text-anchor="middle" fill="#5eead4" font-size="10" font-family="monospace">10.10.0.21:8080</text>
            <text x="493" y="112" text-anchor="middle" fill="#94a3b8" font-size="9.5" font-family="monospace">veth-b1</text>

            <rect x="582" y="50" width="142" height="95" rx="9" fill="#0f172a" stroke="#2dd4bf" stroke-width="2"/>
            <text x="653" y="72" text-anchor="middle" fill="#fff" font-size="11" font-weight="700">ns-b2 (Client)</text>
            <text x="653" y="90" text-anchor="middle" fill="#5eead4" font-size="10" font-family="monospace">10.10.0.22/24</text>
            <text x="653" y="112" text-anchor="middle" fill="#94a3b8" font-size="9.5" font-family="monospace">veth-b2</text>

            <!-- Cables -->
            <line x1="107" y1="145" x2="107" y2="240" stroke="#38bdf8" stroke-width="3"/>
            <line x1="267" y1="145" x2="267" y2="240" stroke="#38bdf8" stroke-width="3"/>
            <line x1="493" y1="145" x2="493" y2="240" stroke="#2dd4bf" stroke-width="3"/>
            <line x1="653" y1="145" x2="653" y2="240" stroke="#2dd4bf" stroke-width="3"/>

            <!-- OVS Switch -->
            <rect x="35" y="240" width="690" height="95" rx="12" fill="#1e293b" stroke="#475569" stroke-width="2"/>
            <text x="380" y="263" text-anchor="middle" fill="#fff" font-size="12" font-weight="800">Open vSwitch « br-pfa » (Noyau Linux Ubuntu)</text>

            <rect id="svgIntraA" x="55" y="275" width="185" height="44" rx="8" fill="#064e3b" stroke="#10b981" stroke-width="1.5"/>
            <text x="147" y="293" text-anchor="middle" fill="#a7f3d0" font-size="10" font-weight="700">VLAN 10 (DarMarket)</text>
            <text id="svgTxtA" x="147" y="309" text-anchor="middle" fill="#34d399" font-size="9.5" font-family="monospace" font-weight="700">PERMIS</text>

            <rect id="svgInter" x="265" y="273" width="230" height="48" rx="8" fill="#4c0519" stroke="#f43f5e" stroke-width="2"/>
            <text x="380" y="292" text-anchor="middle" fill="#fecdd3" font-size="10" font-weight="800">PARE-FEU INTER-GROUPE (10 ↔ 20)</text>
            <text id="svgTxtInter" x="380" y="310" text-anchor="middle" fill="#fb7185" font-size="10" font-family="monospace" font-weight="700">🔒 ISOLÉ (DROP)</text>

            <rect id="svgIntraB" x="520" y="275" width="185" height="44" rx="8" fill="#064e3b" stroke="#10b981" stroke-width="1.5"/>
            <text x="612" y="293" text-anchor="middle" fill="#a7f3d0" font-size="10" font-weight="700">VLAN 20 (AtlasPay)</text>
            <text id="svgTxtB" x="612" y="309" text-anchor="middle" fill="#34d399" font-size="9.5" font-family="monospace" font-weight="700">PERMIS</text>

            <!-- Animated Packet -->
            <g id="pktNode" style="display:none;">
              <circle id="pktCircle" cx="267" cy="145" r="9" fill="#10b981" stroke="#fff" stroke-width="2"/>
            </g>
          </svg>
        </div>

        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
          <div class="flex items-center justify-between">
            <span id="resBadge" class="px-2 py-0.5 rounded text-xs font-bold bg-slate-800 text-slate-300 mono">EN ATTENTE</span>
            <span id="resPcapInfo" class="text-[11px] mono text-sky-400">Fichier .pcap : --</span>
          </div>
          <p id="resOutput" class="text-xs mono text-slate-300 break-all pt-1">Cliquez sur un test à gauche pour exécuter la commande sur votre VM.</p>
        </div>
      </div>
    </div>

    <!-- Bottom Row: Live Charts & Real tcpdump Output -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">
      <div class="lg:col-span-4 bg-slate-900 border border-slate-800 rounded-2xl p-4">
        <h3 class="text-xs font-bold uppercase text-white mb-2">Graphique 1 — Historique des Flux Réels</h3>
        <div class="relative h-52"><canvas id="chartHistory"></canvas></div>
      </div>

      <div class="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-2xl p-4">
        <h3 class="text-xs font-bold uppercase text-white mb-2">Graphique 2 — Bilan par Protocole</h3>
        <div class="relative h-52"><canvas id="chartProto"></canvas></div>
      </div>

      <div class="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-xs font-bold uppercase text-white">Sonde <span class="mono text-sky-400">tcpdump -nn -r capture.pcap</span> (Vraies Trames VM)</h3>
        </div>
        <div id="pcapConsole" class="bg-slate-950 border border-slate-800 rounded-xl p-3 h-52 overflow-y-auto custom-scroll mono text-[11px] space-y-1 text-slate-300">
          <div class="text-slate-500"># Prêt à lire les captures .pcap générées sur la VM...</div>
        </div>
      </div>
    </div>

  </main>

  <script>
    var COORDS = {
      "ns-a1": { x: 107, y: 145, group: "A" },
      "ns-a2": { x: 267, y: 145, group: "A" },
      "ns-b1": { x: 493, y: 145, group: "B" },
      "ns-b2": { x: 653, y: 145, group: "B" }
    };
    var currentPerms = { intraA: true, intraB: true, inter: false };
    var chartHist = null;
    var chartProto = null;

    function toast(msg, isErr) {
      var box = document.getElementById("toastBox");
      var el = document.createElement("div");
      el.className = "px-4 py-2.5 rounded-xl border text-xs font-bold shadow-xl " +
        (isErr ? "bg-rose-950 border-rose-500 text-rose-100" : "bg-slate-900 border-emerald-500 text-emerald-100");
      el.textContent = msg;
      box.appendChild(el);
      setTimeout(function() { if (el.parentNode) el.parentNode.removeChild(el); }, 3000);
    }

    function initCharts() {
      chartHist = new Chart(document.getElementById("chartHistory").getContext("2d"), {
        type: "bar",
        data: {
          labels: [],
          datasets: [
            { label: "Autorisé (OK)", data: [], backgroundColor: "#10b981", borderRadius: 4 },
            { label: "Stoppé (Drop)", data: [], backgroundColor: "#f43f5e", borderRadius: 4 }
          ]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          scales: { y: { beginAtZero: true, ticks: { stepSize: 1, color: "#94a3b8" } }, x: { ticks: { color: "#94a3b8", font: { size: 9 } } } },
          plugins: { legend: { labels: { color: "#cbd5e1", font: { size: 10 } } } }
        }
      });

      chartProto = new Chart(document.getElementById("chartProto").getContext("2d"), {
        type: "doughnut",
        data: {
          labels: ["ICMP Autorisé", "HTTP Autorisé", "ICMP Stoppé", "HTTP Stoppé"],
          datasets: [{ data: [1, 1, 1, 1], backgroundColor: ["#10b981", "#0ea5e9", "#f43f5e", "#f59e0b"], borderWidth: 0 }]
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: "60%",
          plugins: { legend: { position: "bottom", labels: { color: "#cbd5e1", font: { size: 10 }, boxWidth: 10 } } }
        }
      });
    }

    function applyStatusUI(st) {
      if (!st) return;
      document.getElementById("vmHostBadge").textContent = "● VM : " + st.hostname;
      document.getElementById("topoHostTitle").textContent = "VM " + st.hostname;
      document.getElementById("kpiAllowed").textContent = st.stats.allowed;
      document.getElementById("kpiBlocked").textContent = st.stats.blocked;
      document.getElementById("cmdDisplay").textContent = st.last_cmd;

      currentPerms = st.permissions;

      // Intra A
      var btnA = document.getElementById("btnIntraA");
      btnA.textContent = currentPerms.intraA ? "✓ PERMIS" : "✕ INTERDIT";
      btnA.className = currentPerms.intraA
        ? "px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
        : "px-3 py-1.5 rounded-lg text-xs font-bold bg-rose-600 text-white";
      document.getElementById("svgTxtA").textContent = currentPerms.intraA ? "PERMIS" : "BLOQUÉ (DROP)";

      // Intra B
      var btnB = document.getElementById("btnIntraB");
      btnB.textContent = currentPerms.intraB ? "✓ PERMIS" : "✕ INTERDIT";
      btnB.className = currentPerms.intraB
        ? "px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
        : "px-3 py-1.5 rounded-lg text-xs font-bold bg-rose-600 text-white";
      document.getElementById("svgTxtB").textContent = currentPerms.intraB ? "PERMIS" : "BLOQUÉ (DROP)";

      // Inter A <-> B
      var inter = currentPerms.inter;
      var btnInter = document.getElementById("btnInter");
      var kpiBadge = document.getElementById("kpiInterBadge");
      var svgInter = document.getElementById("svgInter");
      var svgTxtInter = document.getElementById("svgTxtInter");

      if (inter) {
        btnInter.textContent = "✓ PERMIS (OUVERT)";
        btnInter.className = "px-3.5 py-2 rounded-lg text-xs font-extrabold bg-emerald-600 text-white shadow";
        kpiBadge.textContent = "🔓 PERMIS (VLAN PARTAGÉ)";
        kpiBadge.className = "inline-flex px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40";
        svgInter.setAttribute("fill", "#064e3b");
        svgInter.setAttribute("stroke", "#10b981");
        svgTxtInter.textContent = "🔓 OUVERT (FLUX A↔B AUTORISÉ)";
        svgTxtInter.setAttribute("fill", "#34d399");
      } else {
        btnInter.textContent = "✕ INTERDIT";
        btnInter.className = "px-3.5 py-2 rounded-lg text-xs font-extrabold bg-rose-600 text-white shadow";
        kpiBadge.textContent = "🔒 INTERDIT (VLAN 10 ≠ 20)";
        kpiBadge.className = "inline-flex px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40";
        svgInter.setAttribute("fill", "#4c0519");
        svgInter.setAttribute("stroke", "#f43f5e");
        svgTxtInter.textContent = "🔒 ISOLÉ (DROP)";
        svgTxtInter.setAttribute("fill", "#fb7185");
      }

      var s = st.stats;
      if ((s.icmp_allowed + s.http_allowed + s.icmp_blocked + s.http_blocked) > 0 && chartProto) {
        chartProto.data.datasets[0].data = [s.icmp_allowed, s.http_allowed, s.icmp_blocked, s.http_blocked];
        chartProto.update();
      }
    }

    function animateDot(srcId, dstId, allowed) {
      var s = COORDS[srcId];
      var d = COORDS[dstId];
      var g = document.getElementById("pktNode");
      var c = document.getElementById("pktCircle");
      c.setAttribute("fill", allowed ? "#10b981" : "#f43f5e");
      g.style.display = "block";

      var pts = [{ x: s.x, y: 145 }, { x: s.x, y: 260 }];
      if (allowed) {
        pts.push({ x: d.x, y: 260 }, { x: d.x, y: 145 });
      } else {
        pts.push({ x: 380, y: 260 });
      }

      var idx = 0, p = 0;
      function step() {
        p += 0.1;
        if (p >= 1) {
          p = 0; idx++;
          if (idx >= pts.length - 1) {
            setTimeout(function() { g.style.display = "none"; }, 300);
            return;
          }
        }
        var x = pts[idx].x + (pts[idx+1].x - pts[idx].x) * p;
        var y = pts[idx].y + (pts[idx+1].y - pts[idx].y) * p;
        c.setAttribute("cx", x);
        c.setAttribute("cy", y);
        requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    }

    async function togglePerm(target) {
      var nextVal = !currentPerms[target];
      var res = await fetch("/api/permission", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target: target, allow: nextVal })
      });
      var data = await res.json();
      applyStatusUI(data);
      toast("Permission " + target + " mise à jour sur Open vSwitch !", !nextVal);
    }

    async function triggerFlowAPI(src, dst, proto, pcapName, label) {
      var res = await fetch("/api/flow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ src: src, dst: dst, proto: proto, pcap_name: pcapName })
      });
      var data = await res.json();
      animateDot(src, dst, data.allowed);
      applyStatusUI(data.status);

      document.getElementById("kpiLatency").textContent = data.latency;
      var badge = document.getElementById("resBadge");
      badge.textContent = data.allowed ? "✓ AUTORISÉ (PASS)" : "✕ STOPPÉ (DROP OVS)";
      badge.className = data.allowed
        ? "px-2.5 py-0.5 rounded text-xs font-bold bg-emerald-500/20 text-emerald-300 mono"
        : "px-2.5 py-0.5 rounded text-xs font-bold bg-rose-500/20 text-rose-300 mono";

      document.getElementById("resPcapInfo").textContent = data.pcap_file + " (" + data.pcap_size + " octets)";
      document.getElementById("resOutput").textContent = data.command + "  ==>  " + data.output;

      var term = document.getElementById("pcapConsole");
      data.tcpdump_lines.forEach(function(line) {
        var d = document.createElement("div");
        d.className = data.allowed ? "text-emerald-300" : "text-rose-400 font-semibold";
        d.textContent = line;
        term.appendChild(d);
      });
      term.scrollTop = term.scrollHeight;

      if (chartHist) {
        chartHist.data.labels.push(label || (src + "→" + dst));
        chartHist.data.datasets[0].data.push(data.allowed ? 1 : 0);
        chartHist.data.datasets[1].data.push(data.allowed ? 0 : 1);
        if (chartHist.data.labels.length > 8) {
          chartHist.data.labels.shift();
          chartHist.data.datasets[0].data.shift();
          chartHist.data.datasets[1].data.shift();
        }
        chartHist.update();
      }
      return data;
    }

    async function sendCustomRealFlow() {
      var s = document.getElementById("selSrc").value;
      var d = document.getElementById("selDst").value;
      var p = document.getElementById("selProto").value;
      await triggerFlowAPI(s, d, p, "custom_flow.pcap", s + "→" + d);
    }

    async function runRealTest(num) {
      if (num === 1) {
        toast("Exécution réelle du Test 1 (Intragroupe) sur la VM...", false);
        await triggerFlowAPI("ns-a2", "ns-a1", "CURL", "test1_intra.pcap", "Test 1 (Intra)");
      } else if (num === 2) {
        if (currentPerms.inter) await togglePerm("inter");
        toast("Exécution réelle du Test 2 (Intergroupe bloqué) sur la VM...", true);
        await triggerFlowAPI("ns-a2", "ns-b1", "CURL", "test2_inter_bloque.pcap", "Test 2 (Bloqué)");
      } else if (num === 3) {
        toast("Test 3 (Étape 3A) : Ouverture de la règle sur Open vSwitch...", false);
        if (!currentPerms.inter) await togglePerm("inter");
        await triggerFlowAPI("ns-a2", "ns-b1", "CURL", "test3_dynamique.pcap", "Test 3A (Ouvert)");
        setTimeout(async function() {
          toast("Test 3 (Étape 3B) : Rétablissement de l'isolation sur Open vSwitch...", true);
          if (currentPerms.inter) await togglePerm("inter");
          await triggerFlowAPI("ns-a2", "ns-b1", "CURL", "test3_bloque.pcap", "Test 3B (Rétabli)");
        }, 1200);
      }
    }

    async function runLabAction(act) {
      toast("Réinitialisation de la topologie via pfa_lab.sh...", false);
      var res = await fetch("/api/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: act })
      });
      var data = await res.json();
      applyStatusUI(data);
      toast("Topologie et serveurs HTTP prêts !", false);
    }

    window.addEventListener("DOMContentLoaded", async function() {
      initCharts();
      var res = await fetch("/api/status");
      var st = await res.json();
      applyStatusUI(st);
    });
  </script>
</body>
</html>
"""


class SDNRequestHandler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self._send_json(get_system_status())
        else:
            body = DASHBOARD_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        data = json.loads(raw)

        if self.path == "/api/permission":
            st = apply_permission_change(data.get("target"), data.get("allow"))
            self._send_json(st)
        elif self.path == "/api/flow":
            res = execute_real_network_flow(
                data.get("src", "ns-a2"),
                data.get("dst", "ns-a1"),
                data.get("proto", "CURL"),
                data.get("pcap_name"),
            )
            self._send_json(res)
        elif self.path == "/api/action":
            run_cmd("./pfa_lab.sh setup && ./pfa_lab.sh start", timeout=15)
            STATE["intraA"] = True
            STATE["intraB"] = True
            STATE["inter"] = False
            self._send_json(get_system_status())
        else:
            self._send_json({"error": "Not found"}, status=404)

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("❌ Erreur : Lance ce contrôleur avec sudo pour piloter ip netns et Open vSwitch :")
        print("👉 sudo python3 sdn_controller.py")
        raise SystemExit(1)

    print("======================================================================")
    print(f"🚀 Contrôleur Web SDN NovaStudio actif sur la VM '{HOSTNAME}'")
    print(f"👉 Ouvre ton navigateur sur : http://<IP_DE_TA_VM>:{PORT}")
    print("======================================================================")
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), SDNRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du contrôleur SDN.")