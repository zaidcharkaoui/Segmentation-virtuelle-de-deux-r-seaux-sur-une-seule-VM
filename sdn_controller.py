#!/usr/bin/env python3
"""
==============================================================================
PROJET PFA-04 (EMSI) — Plateforme Multi-Ports V6 (Design Sur-Mesure & Logos SVG)
==============================================================================
Trois univers visuels totalement distincts, chacun avec son Logo SVG, sa
direction artistique et sa mise en page propre :

  1. Port :5001 -> ATLAS BANK & FINCORP (Banque Privée & Trésorerie)
     • Design : Thème Clair Prestige « Ivory, Deep Navy & Imperial Gold »
     • Layout : Barre latérale Bancaire + Guichet d'Opérations & Navigateur Intranet
     • Logo SVG : Blason Doré des Montagnes de l'Atlas & Coffre-Fort Numérique

  2. Port :5002 -> MEDINATECH AI & CLOUD LABS (Startup Cyber, IA & DevSecOps)
     • Design : Thème Cyberpunk « Deep Space Violet, Neon Magenta & Cyan Glass »
     • Layout : Grille de Pods Ingénieurs R&D + Terminal DevOps Split-View
     • Logo SVG : Hexagone Neural Lumineux & Circuit Quantique

  3. Port :5000 -> SENTINEL-OVS NOC (Centre de Contrôle SDN de l'Ingénieur Réseau)
     • Design : Thème Radar Tactique « Carbon Black, Radar Emerald & Amber Alert »
     • Layout : Console NOC 3-Panneaux (Permissions OpenFlow, QoS 1000 Kbps, Latence min/avg/max & Audit)
     • Logo SVG : Bouclier Radar SDN & Commutateur Open vSwitch
==============================================================================
"""

import http.server
import json
import os
import re
import socket
import subprocess
import threading
import time
from urllib.parse import urlparse

PORT_CONTROL = 5000
PORT_ENT1 = 5001
PORT_ENT2 = 5002

BRIDGE = "br-pfa"
HOSTNAME = socket.gethostname()
PROOF_DIR = f"./preuves_{HOSTNAME}"
os.makedirs(PROOF_DIR, exist_ok=True)

STATE_LOCK = threading.Lock()
STATE = {
    "global_inter_allowed": False,
    "qos_rate_kbps": 0,
    "custom_rules": [],
    "allowed_count": 0,
    "blocked_count": 0,
    "latency": {"min": "--", "avg": "--", "max": "--", "mdev": "--", "pair": "Aucune mesure"},
    "last_cmd": "sudo ./pfa_lab.sh setup && sudo ./pfa_lab.sh start",
    "logs": [],
}


def run_cmd(cmd, timeout=10):
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        dt_ms = round((time.time() - t0) * 1000, 1)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip(), dt_ms
    except subprocess.TimeoutExpired:
        dt_ms = round((time.time() - t0) * 1000, 1)
        return 124, "", "Timeout (100% Bloqué par le pare-feu Open vSwitch)", dt_ms


def add_log(msg, allowed=True):
    ts = time.strftime("%H:%M:%S")
    with STATE_LOCK:
        STATE["logs"].append({"ts": ts, "text": msg, "allowed": allowed})
        if len(STATE["logs"]) > 100:
            STATE["logs"] = STATE["logs"][-100:]


def discover_live_state():
    _, out, _, _ = run_cmd("ip netns list 2>/dev/null || true")
    ns_names = [line.split()[0] for line in out.splitlines() if line.strip()]

    users_a = []
    users_b = []

    for ns in ns_names:
        if ns.startswith("ns-a-u"):
            uid = ns.replace("ns-a-u", "")
            if uid.isdigit():
                ip = f"10.10.1.{int(uid) + 1}"
                users_a.append({"ns": ns, "ip": ip, "uid": int(uid), "role": f"Banquier #{uid}"})
        elif ns.startswith("ns-b-u"):
            uid = ns.replace("ns-b-u", "")
            if uid.isdigit():
                ip = f"10.10.2.{int(uid) + 1}"
                users_b.append({"ns": ns, "ip": ip, "uid": int(uid), "role": f"Ingénieur IA #{uid}"})

    users_a.sort(key=lambda x: x["uid"])
    users_b.sort(key=lambda x: x["uid"])

    with STATE_LOCK:
        return {
            "hostname": HOSTNAME,
            "ports": {"control": PORT_CONTROL, "ent1": PORT_ENT1, "ent2": PORT_ENT2},
            "servers": {
                "A": {"ns": "ns-a-web", "ip": "10.10.1.1", "url": "http://10.10.1.1:8080", "name": "Portail Core-Banking Atlas Bank (10.10.1.1)"},
                "B": {"ns": "ns-b-web", "ip": "10.10.2.1", "url": "http://10.10.2.1:8080", "name": "Cluster Cloud & IA MedinaTech (10.10.2.1)"},
            },
            "usersA": users_a,
            "usersB": users_b,
            "global_inter_allowed": STATE["global_inter_allowed"],
            "qos_rate_kbps": STATE["qos_rate_kbps"],
            "custom_rules": list(STATE["custom_rules"]),
            "stats": {
                "allowed": STATE["allowed_count"],
                "blocked": STATE["blocked_count"],
            },
            "latency": dict(STATE["latency"]),
            "last_cmd": STATE["last_cmd"],
            "logs": list(STATE["logs"][-40:]),
        }


# ==============================================================================
# PAGE 1 (:5001) — ATLAS BANK & FINCORP (THÈME LUXURY BANKING : IVOIRE, OR & NAVY)
# ==============================================================================
ATLAS_BANK_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ATLAS BANK &amp; FINCORP — Espace Collaborateur &amp; Trésorerie (:5001)</title>
  <script src="https://cdn.tailwindcss.com/3.4.17"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f4f1ea; color: #0f172a; }
    .serif-brand { font-family: 'Cinzel', serif; }
    .mono { font-family: 'JetBrains Mono', monospace; }
    .gold-gradient { background: linear-gradient(135deg, #d4af37 0%, #aa7c11 100%); }
    .navy-panel { background: linear-gradient(180deg, #0a192f 0%, #0f2942 100%); }
  </style>
</head>
<body class="min-h-screen flex flex-col">
  <div id="toastBox" class="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"></div>

  <!-- Top Prestige Banking Header -->
  <header class="bg-[#0a192f] text-white border-b-4 border-[#d4af37] shadow-xl sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-5 py-3.5 flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-4">
        <!-- Custom SVG Logo: Atlas Bank Golden Crest & Mountain Vault -->
        <div class="w-12 h-12 rounded-xl bg-[#112240] border-2 border-[#d4af37] flex items-center justify-center shadow-lg">
          <svg viewBox="0 0 64 64" class="w-9 h-9">
            <polygon points="32,4 58,16 58,36 32,60 6,36 6,16" fill="#0a192f" stroke="#d4af37" stroke-width="3.5"/>
            <polygon points="14,40 28,18 40,36 46,26 52,40" fill="#d4af37" opacity="0.9"/>
            <circle cx="32" cy="14" r="3" fill="#f8fafc"/>
          </svg>
        </div>
        <div>
          <div class="flex items-center gap-2.5">
            <span class="serif-brand text-lg sm:text-xl font-extrabold tracking-wider text-[#f5d77f]">ATLAS BANK &amp; FINCORP</span>
            <span class="px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest rounded bg-[#d4af37]/20 text-[#f5d77f] border border-[#d4af37]/50">
               Entreprise 1 • Port :5001
            </span>
          </div>
          <p class="text-xs text-slate-300">Direction Trésorerie, Paie &amp; Risques • Sous-réseau Privé <span class="mono text-[#f5d77f]">10.10.1.0/16</span> (Capacité &gt; 2 000 Banquiers)</p>
        </div>
      </div>

      <!-- Inter-Portal Links -->
      <div class="flex items-center gap-2 text-xs">
        <a id="linkMedina" href="#" target="_blank" class="px-3.5 py-2 rounded-lg font-bold bg-[#112240] hover:bg-[#1d3557] text-purple-300 border border-purple-400/40 transition">
          🚀 Voir MedinaTech (:5002)
        </a>
        <a id="linkSentinel" href="#" target="_blank" class="px-3.5 py-2 rounded-lg font-extrabold gold-gradient text-[#0a192f] shadow transition">
          🛡️ Console SDN Sentinel (:5000)
        </a>
      </div>
    </div>
  </header>

  <!-- Main Banking Layout: Left Sidebar (Directory) + Right Main Desk -->
  <div class="flex-1 max-w-7xl w-full mx-auto px-5 py-6 grid grid-cols-1 lg:grid-cols-12 gap-6">

    <!-- LEFT SIDEBAR (4 cols) : ANNUAIRE DES BANQUIERS & RECRUTEMENT DYNAMIQUE -->
    <aside class="lg:col-span-4 navy-panel text-white rounded-2xl p-5 shadow-2xl border border-[#d4af37]/40 flex flex-col justify-between space-y-4">
      <div class="space-y-4">
        <div class="border-b border-slate-700 pb-3 flex items-center justify-between">
          <div>
            <span class="text-[10px] uppercase tracking-widest text-[#f5d77f] font-bold">Allocation IP Dynamique (/16)</span>
            <h2 class="text-base font-extrabold text-white mt-0.5">👔 Postes Collaborateurs</h2>
          </div>
          <span id="bankUserCount" class="px-3 py-1 rounded-full bg-[#d4af37] text-[#0a192f] font-extrabold text-sm mono">2</span>
        </div>

        <!-- Boutons d'Ajout Dynamique -->
        <div class="space-y-1.5">
          <p class="text-xs text-slate-300">Intégrer de nouveaux banquiers sur le VLAN Finance :</p>
          <div class="grid grid-cols-3 gap-2">
            <button onclick="addBankUsers(1)" class="py-2.5 px-2 rounded-xl gold-gradient text-[#0a192f] font-extrabold text-xs shadow hover:opacity-95 transition">
              +1 Banquier
            </button>
            <button onclick="addBankUsers(5)" class="py-2.5 px-2 rounded-xl bg-[#112240] hover:bg-[#1e3a5f] text-[#f5d77f] border border-[#d4af37]/50 font-bold text-xs transition">
              +5 Banquiers
            </button>
            <button onclick="addBankUsers(10)" class="py-2.5 px-2 rounded-xl bg-[#112240] hover:bg-[#1e3a5f] text-[#f5d77f] border border-[#d4af37]/50 font-bold text-xs transition">
              +10 Banquiers
            </button>
          </div>
        </div>

        <!-- Serveur Core-Banking Interne -->
        <div class="p-3 rounded-xl bg-[#112240] border border-[#d4af37]/40 flex items-center justify-between">
          <div>
            <span class="text-xs font-bold text-[#f5d77f] block">🏦 Serveur Core-Banking</span>
            <span class="mono text-[11px] text-slate-300">http://10.10.1.1:8080 (ns-a-web)</span>
          </div>
          <span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">ACTIF</span>
        </div>

        <!-- Liste des Banquiers -->
        <div>
          <p class="text-xs font-semibold text-slate-300 mb-2">Annuaire IP actif (Atlas Bank) :</p>
          <div id="bankUsersList" class="space-y-1.5 max-h-64 overflow-y-auto pr-1"></div>
        </div>
      </div>

      <div class="p-3 rounded-xl bg-[#071120] border border-slate-800 text-[11px] text-slate-400">
        🔒 <strong>Conformité Bancaire :</strong> L'accès vers <span class="text-white font-semibold">MedinaTech AI Labs</span> est verrouillé par défaut par le pare-feu Open vSwitch.
      </div>
    </aside>

    <!-- RIGHT WORKSPACE (8 cols) : GUICHET D'OPÉRATIONS & NAVIGATEUR INTRANET -->
    <section class="lg:col-span-8 flex flex-col gap-5">

      <!-- Top Status Ribbon (Light Luxury Cards) -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div class="bg-white rounded-2xl p-4 shadow-md border-l-4 border-[#0a192f]">
          <span class="text-[11px] font-bold uppercase text-slate-500">Statut Pare-Feu Inter-Entreprises</span>
          <div id="bankPolicyBadge" class="mt-1.5 text-xs font-extrabold text-rose-700">🔒 CLOISONNEMENT ACTIF</div>
        </div>
        <div class="bg-white rounded-2xl p-4 shadow-md border-l-4 border-[#d4af37]">
          <span class="text-[11px] font-bold uppercase text-slate-500">Politique Bande Passante (QoS)</span>
          <div id="bankQosBadge" class="mt-1.5 text-xs font-extrabold text-emerald-700 mono">Débit Illimité ( Fibre Interne )</div>
        </div>
        <div class="bg-white rounded-2xl p-4 shadow-md border-l-4 border-sky-700">
          <span class="text-[11px] font-bold uppercase text-slate-500">Dernière Latence (min/avg/max)</span>
          <div id="bankLatBadge" class="mt-1.5 text-xs font-extrabold text-sky-900 mono">-- / -- / -- ms</div>
        </div>
      </div>

      <!-- Main Operation Card -->
      <div class="bg-white rounded-2xl p-6 shadow-xl border border-slate-200 space-y-5">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
          <div>
            <h2 class="serif-brand text-base font-extrabold text-[#0a192f]">TERMINAL D'OPÉRATIONS COLLABORATEUR — ATLAS BANK</h2>
            <p class="text-xs text-slate-500">Testez l'accès aux portails Web (`curl`) et l'envoi de paquets (`ping`) vers les autres départements</p>
          </div>
          <span class="px-2.5 py-1 rounded bg-amber-100 text-amber-900 font-bold text-xs mono">VLAN Finance • 10.10.1.x</span>
        </div>

        <!-- Étape 1 : Choix du Banquier -->
        <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
          <label class="block text-xs font-extrabold text-[#0a192f] mb-1">1. Sélectionner le poste Banquier émetteur (Source) :</label>
          <select id="selBankUser" class="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs font-semibold text-slate-900 mono"></select>
        </div>

        <!-- Étape 2 : Connexion Web (Intranet Bancaire vs Cloud MedinaTech) -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button onclick="bankOpenWeb('A')" class="p-3.5 rounded-xl bg-[#0a192f] hover:bg-[#162d4c] text-white text-left shadow-md transition flex items-center justify-between">
            <div>
              <span class="text-xs font-extrabold text-[#f5d77f] block">🏦 Ouvrir Portail Interne Atlas Bank</span>
              <span class="text-[11px] mono text-slate-300">curl http://10.10.1.1:8080</span>
            </div>
            <span class="text-lg">→</span>
          </button>

          <button onclick="bankOpenWeb('B')" class="p-3.5 rounded-xl bg-purple-950 hover:bg-purple-900 text-white text-left shadow-md transition flex items-center justify-between border border-purple-400/40">
            <div>
              <span class="text-xs font-extrabold text-purple-200 block">🌐 Accéder au Portail Externe MedinaTech</span>
              <span class="text-[11px] mono text-purple-300">curl http://10.10.2.1:8080</span>
            </div>
            <span class="text-lg">↗</span>
          </button>
        </div>

        <!-- Étape 3 : Ping & Calcul min/avg/max vers un Ingénieur de MedinaTech + Test Débit 2 Mo -->
        <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
          <label class="block text-xs font-extrabold text-[#0a192f]">2. Contacter un Ingénieur de MedinaTech AI Labs (`ping` &amp; `min/avg/max`) ou tester la QoS :</label>
          <div class="flex flex-wrap gap-2">
            <select id="selTargetMedina" class="flex-1 bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs font-semibold text-slate-900 mono"></select>
            <button onclick="bankPingUser()" class="px-4 py-2 rounded-xl bg-[#0a192f] hover:bg-slate-800 text-white text-xs font-bold shadow">
              💬 Envoyer Ping
            </button>
            <button onclick="bankCalcLatency()" class="px-4 py-2 rounded-xl gold-gradient text-[#0a192f] text-xs font-extrabold shadow">
              📊 Calculer min/avg/max
            </button>
            <button onclick="bankTestSpeed()" class="px-3.5 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold shadow">
              ⬇ Test Débit 2 Mo
            </button>
          </div>
        </div>

        <!-- Fenêtre de Navigateur / Résultat Intégré -->
        <div class="rounded-xl overflow-hidden border-2 border-slate-300 shadow-inner">
          <div class="bg-slate-200 px-3.5 py-2 flex items-center justify-between border-b border-slate-300">
            <div class="flex items-center gap-1.5">
              <span class="w-3 h-3 rounded-full bg-rose-500 inline-block"></span>
              <span class="w-3 h-3 rounded-full bg-amber-500 inline-block"></span>
              <span class="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span>
              <span id="bankBrowserUrl" class="ml-2 px-3 py-0.5 rounded bg-white text-[11px] mono text-slate-700 border border-slate-300">
                https://intranet.atlasbank.ma
              </span>
            </div>
            <span id="bankResTime" class="text-xs font-bold mono text-slate-700">-- ms</span>
          </div>
          <div id="bankBrowserViewport" class="bg-white p-5 min-h-[145px] flex flex-col justify-center">
            <p class="text-xs text-slate-500 text-center">Sélectionnez une opération ci-dessus pour afficher la réponse du serveur ou le verdict du pare-feu Open vSwitch.</p>
          </div>
        </div>

      </div>
    </section>
  </div>

  <script>
    var host = window.location.hostname || "localhost";
    document.getElementById("linkMedina").href = "http://" + host + ":5002";
    document.getElementById("linkSentinel").href = "http://" + host + ":5000";

    function toast(msg, isErr) {
      var box = document.getElementById("toastBox");
      var el = document.createElement("div");
      el.className = "px-4 py-3 rounded-xl border text-xs font-bold shadow-xl " +
        (isErr ? "bg-rose-900 border-rose-400 text-white" : "bg-[#0a192f] border-[#d4af37] text-[#f5d77f]");
      el.textContent = msg;
      box.appendChild(el);
      setTimeout(function() { if (el.parentNode) el.parentNode.removeChild(el); }, 3200);
    }

    function preserveSelect(selEl, htmlStr) {
      var cur = selEl.value;
      selEl.innerHTML = htmlStr;
      if (cur && Array.from(selEl.options).some(function(o) { return o.value === cur; })) {
        selEl.value = cur;
      }
    }

    function renderBankUI(st) {
      document.getElementById("bankUserCount").textContent = st.usersA.length;

      var pol = document.getElementById("bankPolicyBadge");
      if (st.global_inter_allowed) {
        pol.textContent = "🔓 INTERCONNEXION GLOBALE AUTORISÉE";
        pol.className = "mt-1.5 text-xs font-extrabold text-emerald-700";
      } else if (st.custom_rules.length > 0) {
        pol.textContent = "🔑 " + st.custom_rules.length + " DÉROGATION(S) OPENFLOW ACTIVE(S)";
        pol.className = "mt-1.5 text-xs font-extrabold text-amber-700";
      } else {
        pol.textContent = "🔒 CLOISONNEMENT BANCAIRE STRICT";
        pol.className = "mt-1.5 text-xs font-extrabold text-rose-700";
      }

      var qos = document.getElementById("bankQosBadge");
      if (st.qos_rate_kbps > 0) {
        qos.textContent = "⚡ Bridé à " + st.qos_rate_kbps + " Kbps (1 Mbps)";
        qos.className = "mt-1.5 text-xs font-extrabold text-amber-700 mono";
      } else {
        qos.textContent = "Débit Illimité (Fibre Interne)";
        qos.className = "mt-1.5 text-xs font-extrabold text-emerald-700 mono";
      }

      if (st.latency && st.latency.avg !== "--") {
        document.getElementById("bankLatBadge").textContent =
          st.latency.min + " / " + st.latency.avg + " / " + st.latency.max + " ms";
      }

      document.getElementById("bankUsersList").innerHTML = st.usersA.map(function(u) {
        return "<div class='px-3 py-2 rounded-lg bg-[#112240] border border-slate-700 flex items-center justify-between text-xs'>" +
          "<div><span class='font-bold text-[#f5d77f] block'>👔 " + u.role + "</span><span class='text-[10px] text-slate-400 mono'>" + u.ns + "</span></div>" +
          "<span class='mono text-xs text-white bg-[#0a192f] px-2 py-0.5 rounded border border-[#d4af37]/40'>" + u.ip + "</span></div>";
      }).join("");

      preserveSelect(document.getElementById("selBankUser"), st.usersA.map(function(u) {
        return "<option value='" + u.ns + "|" + u.ip + "'>👔 " + u.role + " (" + u.ns + " — IP : " + u.ip + ")</option>";
      }).join(""));

      preserveSelect(document.getElementById("selTargetMedina"), st.usersB.map(function(u) {
        return "<option value='" + u.ns + "|" + u.ip + "'>🧑‍💻 " + u.role + " [MedinaTech] (" + u.ns + " — " + u.ip + ")</option>";
      }).join(""));
    }

    function showBankViewport(allowed, urlStr, title, bodyText, timing) {
      document.getElementById("bankBrowserUrl").textContent = urlStr;
      document.getElementById("bankResTime").textContent = timing || "";
      var vp = document.getElementById("bankBrowserViewport");
      if (allowed) {
        vp.className = "bg-emerald-50/70 p-5 min-h-[145px] flex flex-col justify-center border-l-8 border-emerald-600";
        vp.innerHTML = "<div class='text-emerald-900 font-extrabold text-sm mb-1'>✅ " + title + "</div>" +
          "<div class='p-3 rounded-lg bg-white border border-emerald-300 text-slate-800 text-xs mono shadow-sm break-all'>" + bodyText + "</div>";
      } else {
        vp.className = "bg-rose-50 p-5 min-h-[145px] flex flex-col justify-center border-l-8 border-rose-600";
        vp.innerHTML = "<div class='text-rose-800 font-extrabold text-sm mb-1'>🚫 " + title + "</div>" +
          "<div class='p-3 rounded-lg bg-white border border-rose-300 text-rose-700 text-xs mono shadow-sm'>" + bodyText + "</div>";
      }
    }

    async function addBankUsers(n) {
      toast("Création dynamique de +" + n + " Banquier(s) dans Atlas Bank...", false);
      var res = await fetch("/api/add_user", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company: "A", count: n })
      });
      renderBankUI(await res.json());
      toast("+" + n + " Banquier(s) ajouté(s) avec IP dynamique !", false);
    }

    async function bankOpenWeb(targetComp) {
      var u = document.getElementById("selBankUser").value.split("|");
      var dstIp = targetComp === "A" ? "10.10.1.1" : "10.10.2.1";
      var label = targetComp === "A" ? "Portail Core-Banking Atlas Bank" : "Portail Cloud MedinaTech Labs";
      var res = await fetch("/api/test_flow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ src_ns: u[0], src_ip: u[1], dst_ip: dstIp, proto: "CURL", dst_label: label })
      });
      var data = await res.json();
      showBankViewport(
        data.allowed,
        "http://" + dstIp + ":8080/index.html",
        data.allowed ? label + " — Accès Autorisé" : " Pare-Feu Sentinel-OVS : Accès Interdit vers " + label,
        data.output,
        data.latency
      );
      renderBankUI(data.state);
    }

    async function bankPingUser() {
      var u = document.getElementById("selBankUser").value.split("|");
      var t = document.getElementById("selTargetMedina").value.split("|");
      var res = await fetch("/api/test_flow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ src_ns: u[0], src_ip: u[1], dst_ip: t[1], proto: "PING", dst_label: t[0] + " (" + t[1] + ")" })
      });
      var data = await res.json();
      showBankViewport(
        data.allowed,
        "icmp://" + u[1] + " -> " + t[1],
        data.allowed ? "Paquets ICMP Echo Reply reçus de " + t[0] : "Paquets ICMP bloqués par Open vSwitch vers " + t[0],
        data.output,
        data.latency
      );
      renderBankUI(data.state);
    }

    async function bankCalcLatency() {
      var u = document.getElementById("selBankUser").value.split("|");
      var t = document.getElementById("selTargetMedina").value.split("|");
      toast("Calcul min/avg/max vers " + t[0] + "...", false);
      var res = await fetch("/api/latency", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ src_ns: u[0], dst_ip: t[1], label: u[0] + " → " + t[0] })
      });
      var data = await res.json();
      showBankViewport(
        data.allowed,
        "benchmark://" + u[0] + " -> " + t[0],
        data.allowed ? "Statistiques de Latence (" + data.pair + ")" : "Calcul Impossible : Communication Interdite",
        data.summary,
        data.allowed ? ("avg = " + data.avg + " ms") : "Bloqué"
      );
      renderBankUI(data.state);
    }

    async function bankTestSpeed() {
      var u = document.getElementById("selBankUser").value.split("|");
      toast("Téléchargement du fichier de 2 Mo en cours...", false);
      var res = await fetch("/api/qos_speed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ src_ns: u[0], dst_ip: "10.10.1.1" })
      });
      var data = await res.json();
      showBankViewport(true, "http://10.10.1.1:8080/fichier_2mo.bin", "Test de Débit Téléchargement (" + data.qos_mode + ")", data.detail, data.duration);
      renderBankUI(data.state);
    }

    async function poll() {
      try {
        var res = await fetch("/api/status");
        renderBankUI(await res.json());
      } catch (e) {}
    }

    window.addEventListener("DOMContentLoaded", function() {
      poll();
      setInterval(poll, 1500);
    });
  </script>
</body>
</html>
"""


# ==============================================================================
# PAGE 2 (:5002) — MEDINATECH AI & CLOUD LABS (THÈME CYBERPUNK / NEON AI LAB)
# ==============================================================================
MEDINATECH_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MEDINATECH AI &amp; CLOUD LABS — Engineering &amp; DevSecOps Hub (:5002)</title>
  <script src="https://cdn.tailwindcss.com/3.4.17"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    body {
      font-family: 'Space Grotesk', sans-serif;
      background-color: #070312;
      background-image: radial-gradient(circle at 15% 20%, rgba(168, 85, 247, 0.16) 0%, transparent 40%),
                        radial-gradient(circle at 85% 80%, rgba(6, 182, 212, 0.14) 0%, transparent 40%);
      color: #f3e8ff;
    }
    .mono { font-family: 'JetBrains Mono', monospace; }
    .cyber-card {
      background: rgba(17, 10, 38, 0.82);
      border: 1px solid rgba(168, 85, 247, 0.35);
      box-shadow: 0 0 25px rgba(168, 85, 247, 0.1);
    }
    .neon-btn {
      background: linear-gradient(90deg, #9333ea 0%, #db2777 50%, #0891b2 100%);
    }
  </style>
</head>
<body class="min-h-screen flex flex-col">
  <div id="toastBox" class="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"></div>

  <!-- Top Cyber-AI Header -->
  <header class="bg-[#0d0620]/90 border-b border-fuchsia-500/40 backdrop-blur sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-5 py-3.5 flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-4">
        <!-- Custom SVG Logo: MedinaTech Neural Hexagon & Quantum Core -->
        <div class="w-12 h-12 rounded-2xl bg-[#1a0b38] border-2 border-cyan-400 flex items-center justify-center shadow-lg shadow-fuchsia-500/30">
          <svg viewBox="0 0 64 64" class="w-9 h-9">
            <polygon points="32,4 56,18 56,46 32,60 8,46 8,18" fill="none" stroke="#22d3ee" stroke-width="3"/>
            <polygon points="32,14 46,22 46,42 32,50 18,42 18,22" fill="#a855f7" opacity="0.35" stroke="#ec4899" stroke-width="2"/>
            <circle cx="32" cy="32" r="5" fill="#22d3ee"/>
            <line x1="32" y1="14" x2="32" y2="27" stroke="#f472b6" stroke-width="2"/>
            <line x1="46" y1="42" x2="36" y2="35" stroke="#22d3ee" stroke-width="2"/>
            <line x1="18" y1="42" x2="28" y2="35" stroke="#22d3ee" stroke-width="2"/>
          </svg>
        </div>
        <div>
          <div class="flex items-center gap-2.5">
            <span class="text-lg sm:text-xl font-extrabold tracking-wide bg-gradient-to-r from-cyan-300 via-fuchsia-400 to-purple-300 bg-clip-text text-transparent">
              MEDINATECH AI &amp; CLOUD LABS
            </span>
            <span class="px-2.5 py-0.5 text-[10px] font-bold uppercase rounded-full bg-fuchsia-500/20 text-fuchsia-300 border border-fuchsia-400/50 mono">
              Entreprise 2 • Port :5002
            </span>
          </div>
          <p class="text-xs text-purple-300/80">Cluster GPU, R&amp;D &amp; DevSecOps • Pool IP Dynamique <span class="mono text-cyan-300">10.10.2.0/16</span> (Scalabilité &gt; 2 000 Ingénieurs)</p>
        </div>
      </div>

      <div class="flex items-center gap-2 text-xs">
        <a id="linkAtlas" href="#" target="_blank" class="px-3.5 py-2 rounded-xl font-bold bg-[#1a0b38] hover:bg-purple-900 text-amber-300 border border-amber-400/40 transition">
          🏦 Voir Atlas Bank (:5001)
        </a>
        <a id="linkSentinel" href="#" target="_blank" class="px-3.5 py-2 rounded-xl font-extrabold neon-btn text-white shadow-lg transition">
          🛡️ Console SDN Sentinel (:5000)
        </a>
      </div>
    </div>
  </header>

  <main class="flex-1 max-w-7xl w-full mx-auto px-5 py-6 space-y-6">

    <!-- Top Section : Spawner Dynamique de Pods Ingénieurs (Grid Layout) -->
    <section class="cyber-card rounded-2xl p-5 space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-4 border-b border-purple-500/30 pb-3">
        <div>
          <span class="text-[10px] uppercase tracking-widest text-cyan-300 font-bold mono">Orchestrateur de Namespaces R&amp;D</span>
          <h2 class="text-base font-extrabold text-white">⚡ Pods Ingénieurs IA Connectés (<span id="medinaCount" class="text-cyan-300 mono">2</span> actifs sur 10.10.2.x/16)</h2>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button onclick="spawnEngineers(1)" class="px-3.5 py-2 rounded-xl neon-btn text-white font-extrabold text-xs shadow-lg hover:opacity-90 transition">
            ⚡ Spawner +1 Ingénieur
          </button>
          <button onclick="spawnEngineers(5)" class="px-3 py-2 rounded-xl bg-purple-950/80 hover:bg-purple-900 text-cyan-300 border border-cyan-400/40 font-bold text-xs transition">
            ⚡ +5 Ingénieurs
          </button>
          <button onclick="spawnEngineers(10)" class="px-3 py-2 rounded-xl bg-purple-950/80 hover:bg-purple-900 text-fuchsia-300 border border-fuchsia-400/40 font-bold text-xs transition">
            ⚡ +10 Ingénieurs
          </button>
        </div>
      </div>

      <!-- Grille horizontale de cartes ingénieurs (Différente de la sidebar d'Atlas Bank !) -->
      <div id="medinaGrid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5 max-h-44 overflow-y-auto pr-1"></div>
    </section>

    <!-- Bottom Split-View : Left Action Console + Right Cyber Terminal -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

      <!-- Left (6 cols) : Commandes DevOps & Accès Web -->
      <div class="lg:col-span-6 cyber-card rounded-2xl p-5 space-y-4">
        <div class="flex items-center justify-between border-b border-purple-500/30 pb-3">
          <h3 class="text-sm font-extrabold text-cyan-300 uppercase tracking-wider">🧑‍💻 Console d'Exécution Ingénieur R&amp;D</h3>
          <span id="medinaQosTag" class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 mono">QoS : Illimité</span>
        </div>

        <div>
          <label class="block text-xs font-bold text-purple-200 mb-1">Sélectionner le Pod Ingénieur actif (Source MedinaTech) :</label>
          <select id="selMedinaUser" class="w-full bg-[#090414] border border-purple-500/50 rounded-xl px-3 py-2 text-xs text-cyan-200 mono"></select>
        </div>

        <!-- Boutons Web -->
        <div class="space-y-2">
          <span class="text-xs font-bold text-fuchsia-300 block">1. Explorer les Portails Web HTTP (:8080) :</span>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <button onclick="medinaWeb('B')" class="p-3 rounded-xl bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-400/50 text-cyan-200 text-xs font-bold text-left">
              🚀 Ouvrir Cluster Interne MedinaTech
              <span class="block text-[10px] mono text-cyan-300/80 mt-0.5">http://10.10.2.1:8080</span>
            </button>
            <button onclick="medinaWeb('A')" class="p-3 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-400/50 text-amber-200 text-xs font-bold text-left">
              🏦 Tenter Accès Serveur Atlas Bank
              <span class="block text-[10px] mono text-amber-300/80 mt-0.5">http://10.10.1.1:8080</span>
            </button>
          </div>
        </div>

        <!-- Ping & Latence vers un Banquier d'Atlas Bank -->
        <div class="space-y-2 pt-2 border-t border-purple-500/30">
          <span class="text-xs font-bold text-fuchsia-300 block">2. Tester un Flux vers un Banquier d'Atlas Bank (`ping` &amp; `min/avg/max`) :</span>
          <select id="selTargetAtlas" class="w-full bg-[#090414] border border-purple-500/50 rounded-xl px-3 py-2 text-xs text-amber-200 mono"></select>
          <div class="grid grid-cols-3 gap-2 pt-1">
            <button onclick="medinaPing()" class="py-2 px-3 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold shadow">
              💬 Ping Banquier
            </button>
            <button onclick="medinaLatency()" class="py-2 px-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold shadow">
              📊 min/avg/max
            </button>
            <button onclick="medinaSpeed()" class="py-2 px-3 rounded-xl bg-pink-600 hover:bg-pink-500 text-white text-xs font-bold shadow">
              ⬇ Débit 2 Mo
            </button>
          </div>
        </div>
      </div>

      <!-- Right (6 cols) : Cyber Telemetry Screen -->
      <div class="lg:col-span-6 cyber-card rounded-2xl p-5 flex flex-col justify-between space-y-4">
        <div class="flex items-center justify-between border-b border-purple-500/30 pb-3">
          <span class="text-sm font-extrabold text-fuchsia-300 uppercase tracking-wider">📡 Télémétrie &amp; Réponse Réseau Live</span>
          <span id="medinaPolTag" class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-500/20 text-rose-300 mono">🔒 ISOLÉ D'ATLAS BANK</span>
        </div>

        <div id="medinaScreen" class="bg-[#05020c] border-2 border-purple-500/40 rounded-xl p-4 flex-1 flex flex-col justify-center min-h-[190px] mono text-xs">
          <p class="text-purple-300/60 text-center">En attente d'exécution d'un appel HTTP curl ou d'une sonde ICMP ping...</p>
        </div>

        <div class="grid grid-cols-3 gap-2 text-center bg-[#090414] p-2.5 rounded-xl border border-purple-500/30 mono text-xs">
          <div><span class="text-[10px] text-purple-400 block">MIN</span><span id="mLatMin" class="font-bold text-cyan-300">-- ms</span></div>
          <div><span class="text-[10px] text-purple-400 block">AVG</span><span id="mLatAvg" class="font-bold text-fuchsia-300">-- ms</span></div>
          <div><span class="text-[10px] text-purple-400 block">MAX</span><span id="mLatMax" class="font-bold text-amber-300">-- ms</span></div>
        </div>
      </div>

    </div>
  </main>

  <script>
    var host = window.location.hostname || "localhost";
    document.getElementById("linkAtlas").href = "http://" + host + ":5001";
    document.getElementById("linkSentinel").href = "http://" + host + ":5000";

    function toast(msg, isErr) {
      var box = document.getElementById("toastBox");
      var el = document.createElement("div");
      el.className = "px-4 py-3 rounded-xl border text-xs font-bold shadow-xl " +
        (isErr ? "bg-rose-950 border-rose-500 text-rose-200" : "bg-[#1a0b38] border-cyan-400 text-cyan-200");
      el.textContent = msg;
      box.appendChild(el);
      setTimeout(function() { if (el.parentNode) el.parentNode.removeChild(el); }, 3200);
    }

    function preserveSelect(selEl, htmlStr) {
      var cur = selEl.value;
      selEl.innerHTML = htmlStr;
      if (cur && Array.from(selEl.options).some(function(o) { return o.value === cur; })) {
        selEl.value = cur;
      }
    }

    function renderMedinaUI(st) {
      document.getElementById("medinaCount").textContent = st.usersB.length;

      var pol = document.getElementById("medinaPolTag");
      if (st.global_inter_allowed) {
        pol.textContent = "🔓 ACCÈS INTER-ENTREPRISES OUVERT";
        pol.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 mono";
      } else if (st.custom_rules.length > 0) {
        pol.textContent = "🔑 " + st.custom_rules.length + " RÈGLE(S) OPENFLOW ACTIVE(S)";
        pol.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-300 mono";
      } else {
        pol.textContent = "🔒 ISOLÉ D'ATLAS BANK";
        pol.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-500/20 text-rose-300 mono";
      }

      var qos = document.getElementById("medinaQosTag");
      if (st.qos_rate_kbps > 0) {
        qos.textContent = "⚡ QoS : Bridé " + st.qos_rate_kbps + " Kbps";
        qos.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-300 mono";
      } else {
        qos.textContent = "QoS : Illimité";
        qos.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 mono";
      }

      if (st.latency) {
        document.getElementById("mLatMin").textContent = st.latency.min + " ms";
        document.getElementById("mLatAvg").textContent = st.latency.avg + " ms";
        document.getElementById("mLatMax").textContent = st.latency.max + " ms";
      }

      document.getElementById("medinaGrid").innerHTML = st.usersB.map(function(u) {
        return "<div class='p-2.5 rounded-xl bg-[#090414] border border-cyan-500/40 flex flex-col justify-between'>" +
          "<div class='flex items-center justify-between'><span class='text-[11px] font-bold text-cyan-300'>🧑‍💻 " + u.role + "</span>" +
          "<span class='w-2 h-2 rounded-full bg-emerald-400'></span></div>" +
          "<span class='mono text-[11px] text-fuchsia-300 mt-1'>" + u.ip + "/16</span>" +
          "<span class='mono text-[10px] text-slate-400'>" + u.ns + "</span></div>";
      }).join("");

      preserveSelect(document.getElementById("selMedinaUser"), st.usersB.map(function(u) {
        return "<option value='" + u.ns + "|" + u.ip + "'>🧑‍💻 " + u.role + " (" + u.ns + " — " + u.ip + ")</option>";
      }).join(""));

      preserveSelect(document.getElementById("selTargetAtlas"), st.usersA.map(function(u) {
        return "<option value='" + u.ns + "|" + u.ip + "'>👔 " + u.role + " [Atlas Bank] (" + u.ns + " — " + u.ip + ")</option>";
      }).join(""));
    }

    function showMedinaScreen(allowed, header, body, timing) {
      var scr = document.getElementById("medinaScreen");
      if (allowed) {
        scr.className = "bg-emerald-950/30 border-2 border-emerald-400 rounded-xl p-4 flex-1 flex flex-col justify-center min-h-[190px] mono text-xs";
        scr.innerHTML = "<div class='flex justify-between text-emerald-300 font-bold mb-2'><span>✓ " + header + "</span><span>" + (timing || "") + "</span></div>" +
          "<div class='p-3 rounded bg-[#05020c] border border-emerald-500/40 text-cyan-200 break-all'>" + body + "</div>";
      } else {
        scr.className = "bg-rose-950/30 border-2 border-rose-500 rounded-xl p-4 flex-1 flex flex-col justify-center min-h-[190px] mono text-xs";
        scr.innerHTML = "<div class='flex justify-between text-rose-400 font-bold mb-2'><span>✕ " + header + "</span><span>DROP OVS</span></div>" +
          "<div class='p-3 rounded bg-[#05020c] border border-rose-500/40 text-rose-300 break-all'>" + body + "</div>";
      }
    }

    async function spawnEngineers(n) {
      toast("Déploiement dynamique de +" + n + " Pod(s) Ingénieur R&D...", false);
      var res = await fetch("/api/add_user", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company: "B", count: n })
      });
      renderMedinaUI(await res.json());
      toast("+" + n + " Ingénieur(s) ajouté(s) sur le pool 10.10.2.x/16 !", false);
    }

    async function medinaWeb(targetComp) {
      var u = document.getElementById("selMedinaUser").value.split("|");
      var dstIp = targetComp === "B" ? "10.10.2.1" : "10.10.1.1";
      var label = targetComp === "B" ? "Cluster Cloud MedinaTech" : "Portail Financier Atlas Bank";
      var res = await fetch("/api/test_flow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ src_ns: u[0], src_ip: u[1], dst_ip: dstIp, proto: "CURL", dst_label: label })
      });
      var data = await res.json();
      showMedinaScreen(data.allowed, label + " (http://" + dstIp + ":8080)", data.output, data.latency);
      renderMedinaUI(data.state);
    }

    async function medinaPing() {
      var u = document.getElementById("selMedinaUser").value.split("|");
      var t = document.getElementById("selTargetAtlas").value.split("|");
      var res = await fetch("/api/test_flow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ src_ns: u[0], src_ip: u[1], dst_ip: t[1], proto: "PING", dst_label: t[0] + " (" + t[1] + ")" })
      });
      var data = await res.json();
      showMedinaScreen(data.allowed, "ICMP PING " + u[0] + " -> " + t[0], data.output, data.latency);
      renderMedinaUI(data.state);
    }

    async function medinaLatency() {
      var u = document.getElementById("selMedinaUser").value.split("|");
      var t = document.getElementById("selTargetAtlas").value.split("|");
      toast("Mesure min/avg/max vers " + t[0] + "...", false);
      var res = await fetch("/api/latency", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ src_ns: u[0], dst_ip: t[1], label: u[0] + " → " + t[0] })
      });
      var data = await res.json();
      showMedinaScreen(data.allowed, "LATENCE MIN/AVG/MAX (" + data.pair + ")", data.summary, data.allowed ? ("avg=" + data.avg + "ms") : "Bloqué");
      renderMedinaUI(data.state);
    }

    async function medinaSpeed() {
      var u = document.getElementById("selMedinaUser").value.split("|");
      toast("Test de débit 2 Mo sur le cluster...", false);
      var res = await fetch("/api/qos_speed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ src_ns: u[0], dst_ip: "10.10.2.1" })
      });
      var data = await res.json();
      showMedinaScreen(true, "TÉLÉCHARGEMENT 2 Mo (" + data.qos_mode + ")", data.detail, data.duration);
      renderMedinaUI(data.state);
    }

    async function poll() {
      try {
        var res = await fetch("/api/status");
        renderMedinaUI(await res.json());
      } catch (e) {}
    }

    window.addEventListener("DOMContentLoaded", function() {
      poll();
      setInterval(poll, 1500);
    });
  </script>
</body>
</html>
"""


# ==============================================================================
# PAGE 3 (:5000) — SENTINEL-OVS NOC (CENTRE DE CONTRÔLE DE L'INGÉNIEUR RÉSEAU)
# ==============================================================================
CONTROL_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SENTINEL-OVS NOC — Centre de Contrôle SDN &amp; Open vSwitch (:5000)</title>
  <script src="https://cdn.tailwindcss.com/3.4.17"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    body { font-family: 'Inter', sans-serif; background-color: #060a0e; color: #e2e8f0; }
    .mono { font-family: 'JetBrains Mono', monospace; }
  </style>
</head>
<body class="min-h-screen flex flex-col">
  <div id="toastBox" class="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"></div>

  <header class="bg-[#0b1219] border-b border-emerald-500/40 sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-5 py-3.5 flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-3.5">
        <!-- Custom SVG Logo: Sentinel-OVS Radar Shield -->
        <div class="w-12 h-12 rounded-xl bg-emerald-950 border-2 border-emerald-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
          <svg viewBox="0 0 64 64" class="w-9 h-9">
            <path d="M32 6 L56 16 L56 34 C56 48 45 56 32 60 C19 56 8 48 8 34 L8 16 Z" fill="#064e3b" stroke="#10b981" stroke-width="3"/>
            <circle cx="32" cy="32" r="12" fill="none" stroke="#34d399" stroke-width="2" stroke-dasharray="4,2"/>
            <circle cx="32" cy="32" r="4" fill="#10b981"/>
            <line x1="32" y1="32" x2="42" y2="22" stroke="#6ee7b7" stroke-width="2.5"/>
          </svg>
        </div>
        <div>
          <div class="flex items-center gap-2.5">
            <h1 class="text-base sm:text-lg font-extrabold tracking-wider text-white">SENTINEL-OVS — NOC &amp; SDN SECURITY CONTROLLER</h1>
            <span class="px-2.5 py-0.5 text-[10px] font-bold uppercase rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 mono">
              Ingénieur Réseau • :5000
            </span>
          </div>
          <p class="text-xs text-slate-400">Supervision en Temps Réel : <strong class="text-amber-300">Atlas Bank (:5001)</strong> ↔ <strong class="text-fuchsia-300">MedinaTech Labs (:5002)</strong> • QoS 1000 Kbps • Calcul min/avg/max</p>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2 text-xs">
        <a id="navEnt1" href="#" target="_blank" class="px-3 py-2 rounded-lg font-bold bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40">
          🏦 Ouvrir Atlas Bank (:5001)
        </a>
        <a id="navEnt2" href="#" target="_blank" class="px-3 py-2 rounded-lg font-bold bg-fuchsia-500/20 hover:bg-fuchsia-500/30 text-fuchsia-300 border border-fuchsia-500/40">
          🚀 Ouvrir MedinaTech (:5002)
        </a>
        <button onclick="runAutomatedSuite()" class="px-3.5 py-2 rounded-lg font-extrabold bg-emerald-600 hover:bg-emerald-500 text-white shadow">
          ▶ Exécuter les 3 Tests Automatisés (.pcap)
        </button>
        <button onclick="resetAll()" class="px-3 py-2 rounded-lg font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700">
          🔄 Réinitialiser Tout
        </button>
      </div>
    </div>
  </header>

  <main class="flex-1 max-w-7xl w-full mx-auto px-5 py-5 space-y-5">

    <!-- Synoptic KPI Row -->
    <section class="grid grid-cols-2 lg:grid-cols-5 gap-3">
      <div class="bg-[#0b1219] border border-amber-500/30 rounded-2xl p-3.5">
        <p class="text-[11px] font-semibold text-amber-300 uppercase">🏦 Atlas Bank (:5001)</p>
        <span id="ctrlCountA" class="text-2xl font-extrabold text-white mono">2</span>
        <span class="text-xs text-slate-400 ml-1">banquiers (10.10.1.x)</span>
      </div>

      <div class="bg-[#0b1219] border border-fuchsia-500/30 rounded-2xl p-3.5">
        <p class="text-[11px] font-semibold text-fuchsia-300 uppercase">🚀 MedinaTech (:5002)</p>
        <span id="ctrlCountB" class="text-2xl font-extrabold text-white mono">2</span>
        <span class="text-xs text-slate-400 ml-1">ingénieurs (10.10.2.x)</span>
      </div>

      <div class="bg-[#0b1219] border border-emerald-500/30 rounded-2xl p-3.5">
        <p class="text-[11px] font-semibold text-slate-400 uppercase">Flux Autorisés (Live)</p>
        <span id="ctrlAllowed" class="text-2xl font-extrabold text-emerald-400 mono">0</span>
        <span class="text-xs text-slate-400 ml-1">passés</span>
      </div>

      <div class="bg-[#0b1219] border border-rose-500/30 rounded-2xl p-3.5">
        <p class="text-[11px] font-semibold text-slate-400 uppercase">Flux Stoppés (OVS Drop)</p>
        <span id="ctrlBlocked" class="text-2xl font-extrabold text-rose-400 mono">0</span>
        <span class="text-xs text-slate-400 ml-1">bloqués</span>
      </div>

      <div class="bg-[#0b1219] border border-amber-500/40 rounded-2xl p-3.5">
        <p class="text-[11px] font-semibold text-slate-400 uppercase">Bride Débit QoS</p>
        <span id="ctrlQosKpi" class="text-base font-extrabold text-emerald-400 mono block mt-1">ILLIMITÉ</span>
      </div>
    </section>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">

      <!-- Left (5 cols) : Règles OpenFlow (Permettre / Interdire) -->
      <div class="lg:col-span-5 bg-[#0b1219] border border-slate-800 rounded-2xl p-5 space-y-4">
        <div class="border-b border-slate-800 pb-2.5">
          <h2 class="text-sm font-extrabold text-white">🛡️ 1. Règles de Sécurité OpenFlow (Permettre / Interdire)</h2>
          <p class="text-xs text-slate-400">Agissez en temps réel sur le commutateur central <span class="mono text-emerald-400">br-pfa</span></p>
        </div>

        <div class="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between gap-2">
          <div>
            <span class="text-xs font-bold text-white block">Flux Global Atlas Bank ↔ MedinaTech</span>
            <span id="globStatusText" class="text-[11px] text-rose-400 font-bold">🔒 INTERDIT PAR DÉFAUT (Isolation stricte)</span>
          </div>
          <button id="btnGlobToggle" onclick="toggleGlobal()" class="px-3.5 py-2 rounded-xl text-xs font-extrabold bg-rose-600 hover:bg-rose-500 text-white shadow shrink-0">
            Permettre Tout
          </button>
        </div>

        <div class="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2.5">
          <span class="text-xs font-bold text-emerald-400 block">🔑 Autoriser un Employé ou un Portail Web Spécifique :</span>
          <div>
            <label class="block text-[10px] uppercase text-amber-300 mb-1">Côté ATLAS BANK (Serveur Web ou Banquier) :</label>
            <select id="selRuleA" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white mono"></select>
          </div>
          <div>
            <label class="block text-[10px] uppercase text-fuchsia-300 mb-1">Côté MEDINATECH LABS (Serveur Web ou Ingénieur) :</label>
            <select id="selRuleB" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white mono"></select>
          </div>
          <button onclick="allowPair()" class="w-full py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-extrabold shadow transition">
            ✓ Permettre cette Connexion (Priorité 300)
          </button>

          <div class="pt-2">
            <span class="text-[11px] font-semibold text-slate-400 block mb-1">Exceptions OpenFlow actives :</span>
            <div id="activeRulesList" class="space-y-1.5 max-h-36 overflow-y-auto"></div>
          </div>
        </div>
      </div>

      <!-- Right (7 cols) : QoS 1000 Kbps, Latence min/avg/max & Console Audit -->
      <div class="lg:col-span-7 flex flex-col gap-4">

        <div class="bg-[#0b1219] border border-slate-800 rounded-2xl p-5 space-y-3">
          <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
            <div>
              <h2 class="text-sm font-extrabold text-white">⚡ 2. Limitation de Débit QoS (<span class="mono text-amber-300">1000 Kbps = 1 Mbps</span>)</h2>
              <p class="text-xs text-slate-400">Police le trafic entrant sur les ports du switch (<span class="mono">ingress_policing_rate=1000</span>)</p>
            </div>
            <div class="flex gap-2">
              <button id="btnQosToggle" onclick="toggleQos()" class="px-3.5 py-2 rounded-xl text-xs font-extrabold bg-amber-600 hover:bg-amber-500 text-white shadow">
                ⚡ Activer Limitation 1000 Kbps
              </button>
              <button onclick="runQosCompare()" class="px-3 py-2 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/40">
                🧪 Test Comparatif QoS
              </button>
            </div>
          </div>
          <div id="qosResultBanner" class="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs mono text-slate-300">
            Débit illimité. Cliquez sur « Activer Limitation 1000 Kbps » ou « Test Comparatif QoS ».
          </div>
        </div>

        <div class="bg-[#0b1219] border border-slate-800 rounded-2xl p-5 space-y-3">
          <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
            <div>
              <h2 class="text-sm font-extrabold text-white">📊 3. Calculateur de Latence (<span class="mono text-sky-300">min / avg / max / mdev</span>)</h2>
              <p class="text-xs text-slate-400">Mesure précise sur salve ICMP entre les namespaces</p>
            </div>
            <button onclick="calculateLatency()" class="px-3.5 py-2 rounded-xl text-xs font-extrabold bg-sky-600 hover:bg-sky-500 text-white shadow">
              📊 Calculer min / avg / max
            </button>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 text-center">
              <span class="text-[10px] uppercase text-slate-400 block">MIN</span>
              <span id="latMin" class="text-lg font-extrabold text-emerald-400 mono">-- ms</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 text-center">
              <span class="text-[10px] uppercase text-slate-400 block">AVG (Moy)</span>
              <span id="latAvg" class="text-lg font-extrabold text-sky-400 mono">-- ms</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 text-center">
              <span class="text-[10px] uppercase text-slate-400 block">MAX</span>
              <span id="latMax" class="text-lg font-extrabold text-amber-400 mono">-- ms</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 text-center">
              <span class="text-[10px] uppercase text-slate-400 block">MDEV (Jitter)</span>
              <span id="latMdev" class="text-lg font-extrabold text-purple-400 mono">-- ms</span>
            </div>
          </div>
        </div>

        <div class="bg-[#0b1219] border border-slate-800 rounded-2xl p-4 flex-1 flex flex-col justify-between">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs font-bold uppercase text-white">Journal d'Audit Temps Réel (<span class="mono text-emerald-400">Atlas Bank :5001 • MedinaTech :5002 • Preuves .pcap</span>)</span>
            <code id="ctrlLastCmd" class="text-[11px] mono text-teal-300">Prêt</code>
          </div>
          <div id="ctrlLogs" class="bg-slate-950 border border-slate-800 rounded-xl p-3 h-40 overflow-y-auto mono text-[11px] space-y-1 text-slate-300"></div>
        </div>

      </div>
    </div>
  </main>

  <script>
    var currentState = null;
    var host = window.location.hostname || "localhost";
    document.getElementById("navEnt1").href = "http://" + host + ":5001";
    document.getElementById("navEnt2").href = "http://" + host + ":5002";

    function toast(msg, isErr) {
      var box = document.getElementById("toastBox");
      var el = document.createElement("div");
      el.className = "px-4 py-2.5 rounded-xl border text-xs font-bold shadow-xl " +
        (isErr ? "bg-rose-950 border-rose-500 text-rose-100" : "bg-slate-900 border-emerald-500 text-emerald-100");
      el.textContent = msg;
      box.appendChild(el);
      setTimeout(function() { if (el.parentNode) el.parentNode.removeChild(el); }, 3200);
    }

    function preserveSelect(selEl, htmlStr) {
      var cur = selEl.value;
      selEl.innerHTML = htmlStr;
      if (cur && Array.from(selEl.options).some(function(o) { return o.value === cur; })) {
        selEl.value = cur;
      }
    }

    function renderControl(st) {
      currentState = st;
      document.getElementById("ctrlCountA").textContent = st.usersA.length;
      document.getElementById("ctrlCountB").textContent = st.usersB.length;
      document.getElementById("ctrlAllowed").textContent = st.stats.allowed;
      document.getElementById("ctrlBlocked").textContent = st.stats.blocked;
      document.getElementById("ctrlLastCmd").textContent = st.last_cmd;

      var qosKpi = document.getElementById("ctrlQosKpi");
      var btnQos = document.getElementById("btnQosToggle");
      if (st.qos_rate_kbps > 0) {
        qosKpi.textContent = "BRIDÉ (" + st.qos_rate_kbps + " Kbps)";
        qosKpi.className = "text-sm font-extrabold text-amber-400 mono block mt-1";
        btnQos.textContent = "🔓 Désactiver QoS (Illimité)";
        btnQos.className = "px-3.5 py-2 rounded-xl text-xs font-extrabold bg-rose-600 hover:bg-rose-500 text-white shadow";
      } else {
        qosKpi.textContent = "ILLIMITÉ";
        qosKpi.className = "text-sm font-extrabold text-emerald-400 mono block mt-1";
        btnQos.textContent = "⚡ Activer Limitation 1000 Kbps";
        btnQos.className = "px-3.5 py-2 rounded-xl text-xs font-extrabold bg-amber-600 hover:bg-amber-500 text-white shadow";
      }

      if (st.latency) {
        document.getElementById("latMin").textContent = st.latency.min + " ms";
        document.getElementById("latAvg").textContent = st.latency.avg + " ms";
        document.getElementById("latMax").textContent = st.latency.max + " ms";
        document.getElementById("latMdev").textContent = st.latency.mdev + " ms";
      }

      var globTxt = document.getElementById("globStatusText");
      var btnGlob = document.getElementById("btnGlobToggle");
      if (st.global_inter_allowed) {
        globTxt.textContent = "🔓 AUTORISÉ GLOBALEMENT (Atlas Bank ↔ MedinaTech)";
        globTxt.className = "text-[11px] text-emerald-400 font-bold";
        btnGlob.textContent = "Interdire Tout";
        btnGlob.className = "px-3.5 py-2 rounded-xl text-xs font-extrabold bg-emerald-600 hover:bg-emerald-500 text-white shadow shrink-0";
      } else {
        globTxt.textContent = "🔒 INTERDIT PAR DÉFAUT (Isolation stricte)";
        globTxt.className = "text-[11px] text-rose-400 font-bold";
        btnGlob.textContent = "Permettre Tout";
        btnGlob.className = "px-3.5 py-2 rounded-xl text-xs font-extrabold bg-rose-600 hover:bg-rose-500 text-white shadow shrink-0";
      }

      var optsA = "<option value='10.10.1.1'>🏦 Serveur Web Atlas Bank (10.10.1.1)</option>" +
        st.usersA.map(function(u) { return "<option value='" + u.ip + "'>👔 " + u.role + " (" + u.ns + " • " + u.ip + ")</option>"; }).join("");
      var optsB = "<option value='10.10.2.1'>🚀 Serveur Web MedinaTech (10.10.2.1)</option>" +
        st.usersB.map(function(u) { return "<option value='" + u.ip + "'>🧑‍💻 " + u.role + " (" + u.ns + " • " + u.ip + ")</option>"; }).join("");

      preserveSelect(document.getElementById("selRuleA"), optsA);
      preserveSelect(document.getElementById("selRuleB"), optsB);

      var rBox = document.getElementById("activeRulesList");
      if (st.custom_rules.length === 0) {
        rBox.innerHTML = "<p class='text-[11px] text-slate-500 italic'>Aucune dérogation active.</p>";
      } else {
        rBox.innerHTML = st.custom_rules.map(function(r) {
          return "<div class='px-2.5 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-500/40 flex items-center justify-between text-xs'>" +
            "<span class='mono text-emerald-300'>✓ " + r.ip1 + " ↔ " + r.ip2 + "</span>" +
            "<button onclick=\"denyPair('" + r.ip1 + "','" + r.ip2 + "')\" class='px-2 py-0.5 rounded bg-rose-600 text-white font-bold text-[10px]'>✕ Interdire</button></div>";
        }).join("");
      }

      var lBox = document.getElementById("ctrlLogs");
      lBox.innerHTML = st.logs.map(function(l) {
        var col = l.allowed ? "text-emerald-300" : "text-rose-400 font-semibold";
        return "<div class='" + col + "'>" + l.ts + " " + l.text + "</div>";
      }).join("");
      lBox.scrollTop = lBox.scrollHeight;
    }

    async function toggleGlobal() {
      var nextVal = !(currentState && currentState.global_inter_allowed);
      var res = await fetch("/api/global_inter", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ allow: nextVal })
      });
      renderControl(await res.json());
      toast(nextVal ? "Interconnexion Globale PERMISE" : "Isolation Globale RÉTABLIE", !nextVal);
    }

    async function allowPair() {
      var ip1 = document.getElementById("selRuleA").value;
      var ip2 = document.getElementById("selRuleB").value;
      var res = await fetch("/api/rule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "allow", ip1: ip1, ip2: ip2 })
      });
      renderControl(await res.json());
      toast("Permission accordée : " + ip1 + " ↔ " + ip2, false);
    }

    async function denyPair(ip1, ip2) {
      var res = await fetch("/api/rule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "deny", ip1: ip1, ip2: ip2 })
      });
      renderControl(await res.json());
      toast("Permission révoquée : " + ip1 + " ↔ " + ip2, true);
    }

    async function toggleQos() {
      var activate = (currentState && currentState.qos_rate_kbps === 0);
      var res = await fetch("/api/qos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enable: activate, rate: 1000 })
      });
      var data = await res.json();
      document.getElementById("qosResultBanner").textContent = data.message;
      renderControl(data.state);
      toast(data.message, !activate);
    }

    async function runQosCompare() {
      toast("Test comparatif QoS (Illimité vs 1000 Kbps)...", false);
      var res = await fetch("/api/qos_compare", { method: "POST" });
      var data = await res.json();
      document.getElementById("qosResultBanner").innerHTML = "<pre class='whitespace-pre-wrap text-amber-200 text-[11px]'>" + data.output + "</pre>";
      renderControl(data.state);
      toast("Test comparatif QoS terminé !", false);
    }

    async function calculateLatency() {
      toast("Calcul de latence min/avg/max/mdev...", false);
      var res = await fetch("/api/latency", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ src_ns: "ns-a-u1", dst_ip: "10.10.1.1", label: "ns-a-u1 → Atlas Bank Web" })
      });
      var data = await res.json();
      renderControl(data.state);
      toast("Latence calculée : avg = " + data.avg + " ms", false);
    }

    async function runAutomatedSuite() {
      toast("Lancement des 3 Tests Automatisés (.pcap)...", false);
      var res = await fetch("/api/run_suite", { method: "POST" });
      var data = await res.json();
      document.getElementById("qosResultBanner").innerHTML = "<pre class='whitespace-pre-wrap text-emerald-300 text-[11px]'>" + data.report + "</pre>";
      renderControl(data.state);
      toast("Les 3 Tests Obligatoires sont validés !", false);
    }

    async function resetAll() {
      toast("Réinitialisation complète...", false);
      var res = await fetch("/api/reset", { method: "POST" });
      renderControl(await res.json());
      toast("Laboratoire réinitialisé !", false);
    }

    async function poll() {
      try {
        var res = await fetch("/api/status");
        renderControl(await res.json());
      } catch (e) {}
    }

    window.addEventListener("DOMContentLoaded", function() {
      poll();
      setInterval(poll, 1500);
    });
  </script>
</body>
</html>
"""


def make_handler_for_role(role):
    class RoleHandler(http.server.BaseHTTPRequestHandler):
        def _send_json(self, obj, code=200):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/api/status":
                self._send_json(discover_live_state())
                return

            if role == "ENT1":
                html = ATLAS_BANK_HTML
            elif role == "ENT2":
                html = MEDINATECH_HTML
            else:
                html = CONTROL_HTML

            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            data = json.loads(raw)

            if self.path == "/api/add_user":
                comp = data.get("company", "A")
                cnt = int(data.get("count", 1))
                cmd = f"./pfa_lab.sh add-user {comp} {cnt}"
                run_cmd(cmd, timeout=15)
                with STATE_LOCK:
                    STATE["last_cmd"] = f"sudo {cmd}"
                org = "ATLAS BANK" if comp == "A" else "MEDINATECH LABS"
                add_log(f"[+USERS] {org} : +{cnt} collaborateur(s) ajouté(s) avec IP dynamique (/16)", True)
                self._send_json(discover_live_state())

            elif self.path == "/api/test_flow":
                src_ns = data.get("src_ns", "ns-a-u1")
                src_ip = data.get("src_ip", "10.10.1.2")
                dst_ip = data.get("dst_ip", "10.10.1.1")
                proto = data.get("proto", "CURL")
                dst_label = data.get("dst_label", dst_ip)

                if proto == "PING":
                    cmd = f"ip netns exec {src_ns} ping -c 1 -W 1 {dst_ip}"
                else:
                    cmd = f"ip netns exec {src_ns} curl -s --max-time 2 http://{dst_ip}:8080"

                rc, out, err, dt_ms = run_cmd(cmd, timeout=4)
                allowed = (rc == 0)

                with STATE_LOCK:
                    STATE["last_cmd"] = f"sudo {cmd}"
                    if allowed:
                        STATE["allowed_count"] += 1
                    else:
                        STATE["blocked_count"] += 1

                add_log(
                    f"[{'AUTORISÉ' if allowed else 'STOPPÉ OVS'}] {src_ns} ({src_ip}) -> {dst_label} ({proto}) : {'200 OK / Reply' if allowed else '100% Bloqué'}",
                    allowed
                )

                self._send_json({
                    "allowed": allowed,
                    "src_ns": src_ns,
                    "src_ip": src_ip,
                    "dst_label": dst_label,
                    "latency": f"{dt_ms} ms",
                    "output": out if allowed else "100% Packet Loss / Connection Timed Out — Rejeté par le pare-feu Sentinel-OVS (br-pfa)",
                    "state": discover_live_state(),
                })

            elif self.path == "/api/rule":
                act = data.get("action")
                ip1 = data.get("ip1")
                ip2 = data.get("ip2")
                if act == "allow":
                    cmd = f"./pfa_lab.sh allow-rule {ip1} {ip2}"
                    run_cmd(cmd)
                    with STATE_LOCK:
                        STATE["last_cmd"] = f"sudo {cmd}"
                        pair = {"ip1": ip1, "ip2": ip2}
                        if pair not in STATE["custom_rules"]:
                            STATE["custom_rules"].append(pair)
                    add_log(f"[PERMISSION ACCORDÉE] OpenFlow Prio 300 : {ip1} <-> {ip2} AUTORISÉ", True)
                else:
                    cmd = f"./pfa_lab.sh deny-rule {ip1} {ip2}"
                    run_cmd(cmd)
                    with STATE_LOCK:
                        STATE["last_cmd"] = f"sudo {cmd}"
                        STATE["custom_rules"] = [r for r in STATE["custom_rules"] if not (r["ip1"] == ip1 and r["ip2"] == ip2)]
                    add_log(f"[PERMISSION RÉVOQUÉE] {ip1} <-> {ip2} est à nouveau INTERDIT", False)
                self._send_json(discover_live_state())

            elif self.path == "/api/global_inter":
                allow = bool(data.get("allow"))
                cmd = "./pfa_lab.sh allow-all" if allow else "./pfa_lab.sh block-all"
                run_cmd(cmd)
                with STATE_LOCK:
                    STATE["global_inter_allowed"] = allow
                    if not allow:
                        STATE["custom_rules"] = []
                    STATE["last_cmd"] = f"sudo {cmd}"
                add_log(f"[POLITIQUE GLOBALE] Atlas Bank <-> MedinaTech Labs : {'AUTORISÉ' if allow else 'ISOLÉ (BLOQUÉ)'}", allow)
                self._send_json(discover_live_state())

            elif self.path == "/api/qos":
                enable = bool(data.get("enable"))
                rate = int(data.get("rate", 1000)) if enable else 0
                cmd = f"./pfa_lab.sh qos-limit {rate}" if enable else "./pfa_lab.sh qos-reset"
                run_cmd(cmd)
                with STATE_LOCK:
                    STATE["qos_rate_kbps"] = rate
                    STATE["last_cmd"] = f"sudo {cmd}"
                msg = f"Limitation de débit QoS ACTIVÉE à {rate} Kbps (~1 Mbps)" if enable else "Limitation QoS DÉSACTIVÉE (Débit Illimité)"
                add_log(f"[QoS OVS] {msg}", True)
                self._send_json({"message": msg, "state": discover_live_state()})

            elif self.path == "/api/qos_compare":
                cmd = "./pfa_lab.sh qos-test"
                _, out, _, _ = run_cmd(cmd, timeout=20)
                with STATE_LOCK:
                    STATE["qos_rate_kbps"] = 1000
                    STATE["last_cmd"] = f"sudo {cmd}"
                add_log("[QoS TEST] Démonstration comparative Sans QoS vs Avec QoS 1000 Kbps effectuée", True)
                self._send_json({"output": out, "state": discover_live_state()})

            elif self.path == "/api/qos_speed":
                src_ns = data.get("src_ns", "ns-a-u1")
                dst_ip = data.get("dst_ip", "10.10.1.1")
                cmd = f"ip netns exec {src_ns} curl -s -w 'Temps total: %{{time_total}}s | Vitesse moyenne: %{{speed_download}} octets/s' -o /dev/null http://{dst_ip}:8080/fichier_2mo.bin"
                t0 = time.time()
                _, out, _, _ = run_cmd(cmd, timeout=25)
                with STATE_LOCK:
                    q_rate = STATE["qos_rate_kbps"]
                    STATE["last_cmd"] = f"sudo {cmd}"
                mode_str = f"Bridé à {q_rate} Kbps (~125 Ko/s)" if q_rate > 0 else "Débit Illimité"
                add_log(f"[TEST DÉBIT 2 Mo] {src_ns} -> {dst_ip} ({mode_str}) : {out}", True)
                self._send_json({
                    "qos_mode": mode_str,
                    "detail": out,
                    "duration": f"{round(time.time() - t0, 2)} s",
                    "state": discover_live_state(),
                })

            elif self.path == "/api/latency":
                src_ns = data.get("src_ns", "ns-a-u1")
                dst_ip = data.get("dst_ip", "10.10.1.1")
                label = data.get("label", f"{src_ns} -> {dst_ip}")
                cmd = f"ip netns exec {src_ns} ping -c 6 -i 0.15 -W 1 -q {dst_ip}"
                rc, out, _, _ = run_cmd(cmd, timeout=6)
                allowed = (rc == 0)
                m = re.search(r"=\s*([0-9.]+)/([0-9.]+)/([0-9.]+)/([0-9.]+)", out)
                if allowed and m:
                    l_min, l_avg, l_max, l_mdev = m.group(1), m.group(2), m.group(3), m.group(4)
                    with STATE_LOCK:
                        STATE["latency"] = {"min": l_min, "avg": l_avg, "max": l_max, "mdev": l_mdev, "pair": label}
                        STATE["last_cmd"] = f"sudo {cmd}"
                    summary = f"min = {l_min} ms | avg = {l_avg} ms | max = {l_max} ms | mdev = {l_mdev} ms"
                    add_log(f"[LATENCE] {label} -> {summary}", True)
                    self._send_json({"allowed": True, "pair": label, "min": l_min, "avg": l_avg, "max": l_max, "mdev": l_mdev, "summary": summary, "state": discover_live_state()})
                else:
                    add_log(f"[LATENCE BLOQUÉE] {label} : 100% packet loss (Bloqué par OVS)", False)
                    self._send_json({"allowed": False, "pair": label, "avg": "--", "summary": "100% Packet Loss (Flux bloqué entre ces deux points)", "state": discover_live_state()})

            elif self.path == "/api/run_suite":
                cmd = "./pfa_lab.sh test"
                _, out, _, _ = run_cmd(cmd, timeout=25)
                with STATE_LOCK:
                    STATE["global_inter_allowed"] = False
                    STATE["custom_rules"] = []
                    STATE["last_cmd"] = f"sudo {cmd}"
                add_log("[RECETTE AUTO] Les 3 Tests Obligatoires (.pcap) ont été exécutés avec succès", True)
                self._send_json({"report": out, "state": discover_live_state()})

            elif self.path == "/api/reset":
                cmd = "./pfa_lab.sh setup && ./pfa_lab.sh start"
                run_cmd(cmd, timeout=20)
                with STATE_LOCK:
                    STATE["global_inter_allowed"] = False
                    STATE["qos_rate_kbps"] = 0
                    STATE["custom_rules"] = []
                    STATE["last_cmd"] = f"sudo {cmd}"
                add_log("[RESET] Laboratoire réinitialisé", True)
                self._send_json(discover_live_state())

            else:
                self._send_json({"error": "Not found"}, 404)

        def log_message(self, fmt, *args):
            return

    return RoleHandler


def start_server_on_port(port, role):
    handler_cls = make_handler_for_role(role)
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", port), handler_cls)
    srv.serve_forever()


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("❌ Lance ce script avec sudo : sudo python3 sdn_controller.py")
        raise SystemExit(1)

    _, ns_out, _, _ = run_cmd("ip netns list")
    if "ns-a-web" not in ns_out:
        print("⚙️  Initialisation automatique de la topologie (setup + start)...")
        run_cmd("./pfa_lab.sh setup && ./pfa_lab.sh start", timeout=20)

    threading.Thread(target=start_server_on_port, args=(PORT_ENT1, "ENT1"), daemon=True).start()
    threading.Thread(target=start_server_on_port, args=(PORT_ENT2, "ENT2"), daemon=True).start()

    print("==========================================================================")
    print(f"🚀 PLATEFORME MULTI-UNIVERS SDN V6 ACTIVE SUR LA VM '{HOSTNAME}'")
    print("==========================================================================")
    print(f"  🏦 Port 5001 — ATLAS BANK & FINCORP      : http://<IP_DE_TA_VM>:{PORT_ENT1}")
    print(f"  🚀 Port 5002 — MEDINATECH AI & CLOUD LABS: http://<IP_DE_TA_VM>:{PORT_ENT2}")
    print(f"  🛡️  Port 5000 — SENTINEL-OVS NOC (Admin)  : http://<IP_DE_TA_VM>:{PORT_CONTROL}")
    print("==========================================================================")

    try:
        start_server_on_port(PORT_CONTROL, "CONTROL")
    except KeyboardInterrupt:
        print("\nArrêt des 3 serveurs.")
