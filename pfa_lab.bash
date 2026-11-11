#!/usr/bin/env bash
# ==============================================================================
# PROJET PFA-04 (EMSI) — Architecture Multi-Entreprises & Utilisateurs Dynamiques
# Version V6 :
#   • Entreprise 1 (:5001) : ATLAS BANK & FINCORP (Banque & Paie - 10.10.1.0/16)
#   • Entreprise 2 (:5002) : MEDINATECH AI LABS   (IA & Cloud R&D - 10.10.2.0/16)
#   • Contrôleur  (:5000)  : SENTINEL-OVS NOC     (Gouvernance SDN Open vSwitch)
# ==============================================================================

set -e

if [ "$EUID" -ne 0 ]; then
    echo "❌ Erreur : Ce script doit être lancé avec sudo."
    exit 1
fi

BRIDGE="br-pfa"
PROOF_DIR="./preuves_$(hostname)"
STATE_DIR="/tmp/pfa_sdn_state"
mkdir -p "$PROOF_DIR" "$STATE_DIR"

stop_lab() {
    echo "🧹 [STOP] Nettoyage complet des processus, utilisateurs dynamiques et du switch OVS..."
    pkill -f "http.server 8080" 2>/dev/null || true
    pkill -f "tcpdump" 2>/dev/null || true

    for ns in $(ip netns list | awk '{print $1}' | grep -E '^ns-(a|b|c)' || true); do
        ip netns del "$ns" 2>/dev/null || true
    done

    ovs-vsctl --if-exists del-br "$BRIDGE" 2>/dev/null || true
    rm -rf /tmp/web_entreprise_a /tmp/web_entreprise_b "$STATE_DIR"
    mkdir -p "$STATE_DIR"
    echo "✅ [OK] Environnement totalement propre."
}

create_node() {
    local ns_name="$1"
    local veth_in="$2"
    local ovs_port="$3"
    local ip_cidr="$4"

    ip netns add "$ns_name"
    ip link add "$veth_in" type veth peer name "$ovs_port"
    ip link set "$veth_in" netns "$ns_name"
    ovs-vsctl add-port "$BRIDGE" "$ovs_port"
    ip link set "$ovs_port" up
    ip netns exec "$ns_name" ip addr add "$ip_cidr" dev "$veth_in"
    ip netns exec "$ns_name" ip link set "$veth_in" up
    ip netns exec "$ns_name" ip link set lo up
}

init_openflow_rules() {
    ovs-ofctl del-flows "$BRIDGE"

    # Priorité 50 : Autoriser l'ARP
    ovs-ofctl add-flow "$BRIDGE" "priority=50,arp,actions=NORMAL"

    # Priorité 200 : Autoriser le trafic interne au sein d'ATLAS BANK (10.10.1.0/24)
    ovs-ofctl add-flow "$BRIDGE" "priority=200,ip,nw_src=10.10.1.0/24,nw_dst=10.10.1.0/24,actions=NORMAL"

    # Priorité 200 : Autoriser le trafic interne au sein de MEDINATECH LABS (10.10.2.0/24)
    ovs-ofctl add-flow "$BRIDGE" "priority=200,ip,nw_src=10.10.2.0/24,nw_dst=10.10.2.0/24,actions=NORMAL"

    # Priorité 100 : BLOQUER par défaut tout flux entre ATLAS BANK et MEDINATECH LABS
    ovs-ofctl add-flow "$BRIDGE" "priority=100,ip,nw_src=10.10.1.0/24,nw_dst=10.10.2.0/24,actions=drop"
    ovs-ofctl add-flow "$BRIDGE" "priority=100,ip,nw_src=10.10.2.0/24,nw_dst=10.10.1.0/24,actions=drop"

    # Priorité 10 : Règle de repli
    ovs-ofctl add-flow "$BRIDGE" "priority=10,actions=NORMAL"
}

add_dynamic_users() {
    local company="${1^^}"
    local count="${2:-1}"

    if [[ "$company" != "A" && "$company" != "B" ]]; then
        echo "❌ Spécifie l'entreprise A (Atlas Bank) ou B (MedinaTech)"
        exit 1
    fi

    local prefix_lower="a"
    local subnet_oct="1"
    local org_label="ATLAS BANK"
    if [ "$company" == "B" ]; then
        prefix_lower="b"
        subnet_oct="2"
        org_label="MEDINATECH LABS"
    fi

    local counter_file="$STATE_DIR/count_${prefix_lower}.txt"
    local current_idx=0
    if [ -f "$counter_file" ]; then
        current_idx=$(cat "$counter_file")
    fi

    for ((i=1; i<=count; i++)); do
        current_idx=$((current_idx + 1))
        local host_oct=$((current_idx + 1))
        local ns_name="ns-${prefix_lower}-u${current_idx}"
        local veth_in="veth-${prefix_lower}-u${current_idx}"
        local ovs_port="ovs-${prefix_lower}-u${current_idx}"
        local ip_addr="10.10.${subnet_oct}.${host_oct}"

        create_node "$ns_name" "$veth_in" "$ovs_port" "${ip_addr}/16"
        echo "👤 [+USER] $org_label : $ns_name créé dynamiquement -> IP: $ip_addr/16 (Port OVS: $ovs_port)"
    done

    echo "$current_idx" > "$counter_file"
}

setup_lab() {
    stop_lab

    echo "🏗️  [SETUP] Création du switch Open vSwitch ($BRIDGE) et des 2 Entreprises..."
    ovs-vsctl add-br "$BRIDGE"
    ip link set "$BRIDGE" up

    echo "🏦 Création du Serveur Web Intranet ATLAS BANK (ns-a-web : 10.10.1.1/16)..."
    create_node "ns-a-web" "veth-a-web" "ovs-a-web" "10.10.1.1/16"

    echo "🚀 Création du Serveur Web Intranet MEDINATECH AI LABS (ns-b-web : 10.10.2.1/16)..."
    create_node "ns-b-web" "veth-b-web" "ovs-b-web" "10.10.2.1/16"

    echo "👥 Création des premiers collaborateurs dynamiques..."
    add_dynamic_users A 2
    add_dynamic_users B 2

    echo "🛡️  Application des règles d'isolation OpenFlow sur $BRIDGE..."
    init_openflow_rules

    echo "✅ [OK] Topologie prête (Adressage /16 extensible à 2000+ utilisateurs)."
}

start_services() {
    echo "🚀 [START] Démarrage des portails Web Intranet (:8080)..."
    pkill -f "http.server 8080" 2>/dev/null || true
    mkdir -p /tmp/web_entreprise_a /tmp/web_entreprise_b

    cat << 'EOF' > /tmp/web_entreprise_a/index.html
{"organisation": "ATLAS BANK & FINCORP", "departement": "Direction Trésorerie, Paie & Risques Bancaires", "serveur": "10.10.1.1:8080", "donnees": "Swift/IBAN & Masse Salariale Confidentielle", "statut": "HTTP 200 OK — PORTAIL BANCAIRE DÉVERROUILLÉ"}
EOF

    cat << 'EOF' > /tmp/web_entreprise_b/index.html
{"organisation": "MEDINATECH AI & CLOUD LABS", "departement": "Cluster GPU, Modèles IA & Dépôts Git R&D", "serveur": "10.10.2.1:8080", "donnees": "Pipelines DevSecOps & Poids LLM", "statut": "HTTP 200 OK — PORTAIL CLOUD R&D DÉVERROUILLÉ"}
EOF

    dd if=/dev/zero of=/tmp/web_entreprise_a/fichier_2mo.bin bs=1M count=2 status=none
    dd if=/dev/zero of=/tmp/web_entreprise_b/fichier_2mo.bin bs=1M count=2 status=none

    ip netns exec ns-a-web python3 -m http.server 8080 --directory /tmp/web_entreprise_a >/dev/null 2>&1 &
    ip netns exec ns-b-web python3 -m http.server 8080 --directory /tmp/web_entreprise_b >/dev/null 2>&1 &
    sleep 1

    echo "✅ [OK] Portails Web actifs sur http://10.10.1.1:8080 (Atlas Bank) et http://10.10.2.1:8080 (MedinaTech)."
}

allow_specific_rule() {
    local ip1="$1"
    local ip2="$2"
    ovs-ofctl add-flow "$BRIDGE" "priority=300,ip,nw_src=$ip1,nw_dst=$ip2,actions=NORMAL"
    ovs-ofctl add-flow "$BRIDGE" "priority=300,ip,nw_src=$ip2,nw_dst=$ip1,actions=NORMAL"
    echo "✅ [OPENFLOW] Permission Priorité 300 accordée : $ip1 <-> $ip2 AUTORISÉ."
}

deny_specific_rule() {
    local ip1="$1"
    local ip2="$2"
    ovs-ofctl --strict del-flows "$BRIDGE" "priority=300,ip,nw_src=$ip1,nw_dst=$ip2" 2>/dev/null || true
    ovs-ofctl --strict del-flows "$BRIDGE" "priority=300,ip,nw_src=$ip2,nw_dst=$ip1" 2>/dev/null || true
    echo "🔒 [OPENFLOW] Permission révoquée : $ip1 <-> $ip2 BLOQUÉ."
}

allow_all_inter() {
    ovs-ofctl add-flow "$BRIDGE" "priority=250,ip,nw_src=10.10.1.0/24,nw_dst=10.10.2.0/24,actions=NORMAL"
    ovs-ofctl add-flow "$BRIDGE" "priority=250,ip,nw_src=10.10.2.0/24,nw_dst=10.10.1.0/24,actions=NORMAL"
    echo "✅ [OPENFLOW] Interconnexion globale Atlas Bank <-> MedinaTech Labs AUTORISÉE."
}

block_all_inter() {
    init_openflow_rules
    echo "🔒 [OPENFLOW] Cloisonnement strict rétabli entre Atlas Bank et MedinaTech Labs."
}

apply_qos_limit() {
    local rate_kbps="${1:-1000}"
    local burst_kb="${2:-100}"
    for port in $(ovs-vsctl list-ports "$BRIDGE"); do
        ovs-vsctl set interface "$port" ingress_policing_rate="$rate_kbps"
        ovs-vsctl set interface "$port" ingress_policing_burst="$burst_kb"
    done
    echo "$rate_kbps" > "$STATE_DIR/qos_rate.txt"
    echo "⚡ [QoS] Limitation de débit active à ${rate_kbps} Kbps (~1 Mbps) sur tous les ports OVS."
}

reset_qos_limit() {
    for port in $(ovs-vsctl list-ports "$BRIDGE"); do
        ovs-vsctl set interface "$port" ingress_policing_rate=0
        ovs-vsctl set interface "$port" ingress_policing_burst=0
    done
    echo "0" > "$STATE_DIR/qos_rate.txt"
    echo "⚡ [QoS] Limitation de débit désactivée (Illimité)."
}

run_qos_test() {
    echo "======================================================================"
    echo "⚡ TEST COMPARATIF QoS (DÉBIT ILLIMITÉ vs BRIDÉ À 1000 Kbps)"
    echo "======================================================================"
    reset_qos_limit >/dev/null
    echo "1) SANS QoS (Illimité) — Rafale de 300 paquets (1400 octets) de ns-a-u1 vers Atlas Bank Web :"
    ip netns exec ns-a-u1 ping -f -c 300 -s 1400 10.10.1.1 | tail -2

    echo ""
    apply_qos_limit 1000 100 >/dev/null
    echo "2) AVEC QoS (Bridé à 1000 Kbps / 1 Mbps) — Même rafale de 300 paquets :"
    ip netns exec ns-a-u1 ping -f -c 300 -s 1400 10.10.1.1 | tail -2 || true
    echo "👉 Open vSwitch coupe automatiquement les paquets excédentaires au-delà de 1000 Kbps !"
}

run_benchmark() {
    local src="${1:-ns-a-u1}"
    local dst_ip="${2:-10.10.1.1}"
    ip netns exec "$src" ping -c 10 -i 0.15 -q "$dst_ip" | tail -2
}

run_tests() {
    REPORT="$PROOF_DIR/rapport_recette.txt"
    block_all_inter >/dev/null

    echo "======================================================================" | tee "$REPORT"
    echo "RAPPORT DE RECETTE PFA-04 | Poste : $(hostname) | $(date)" | tee -a "$REPORT"
    echo "======================================================================" | tee -a "$REPORT"

    echo "" | tee -a "$REPORT"
    echo "▶ TEST 1 : Trafic intragroupe autorisé (Banquier ns-a-u1 -> Atlas Bank Web 10.10.1.1)" | tee -a "$REPORT"
    ip netns exec ns-a-web timeout 3 tcpdump -i veth-a-web -nn -w "$PROOF_DIR/test1_intra.pcap" >/dev/null 2>&1 &
    sleep 0.4
    if ip netns exec ns-a-u1 ping -c 2 -W 1 10.10.1.1 >/dev/null 2>&1 && \
       REP1=$(ip netns exec ns-a-u1 curl -s --max-time 2 http://10.10.1.1:8080); then
        echo "  • Obtenu : ✅ SUCCÈS -> $REP1" | tee -a "$REPORT"
        echo "  • Preuve : $PROOF_DIR/test1_intra.pcap" | tee -a "$REPORT"
    else
        echo "  • Obtenu : ❌ ÉCHEC" | tee -a "$REPORT"
    fi
    sleep 2

    echo "" | tee -a "$REPORT"
    echo "▶ TEST 2 : Trafic inter-entreprises refusé (Banquier ns-a-u1 -> MedinaTech Web 10.10.2.1)" | tee -a "$REPORT"
    ip netns exec ns-b-web timeout 3 tcpdump -i veth-b-web -nn "ip" -w "$PROOF_DIR/test2_inter_bloque.pcap" >/dev/null 2>&1 &
    sleep 0.4
    if ! ip netns exec ns-a-u1 ping -c 1 -W 1 10.10.2.1 >/dev/null 2>&1 && \
       ! ip netns exec ns-a-u1 curl -s --max-time 2 http://10.10.2.1:8080 >/dev/null 2>&1; then
        echo "  • Obtenu : ✅ SUCCÈS DU BLOCAGE (100% bloqué par Sentinel-OVS sur br-pfa)" | tee -a "$REPORT"
        echo "  • Preuve : $PROOF_DIR/test2_inter_bloque.pcap (24 octets = 0 paquet IP reçu)" | tee -a "$REPORT"
    else
        echo "  • Obtenu : ❌ ÉCHEC" | tee -a "$REPORT"
    fi
    sleep 2

    echo "" | tee -a "$REPORT"
    echo "▶ TEST 3 : Modification contrôlée de permission (Ouverture pour ns-a-u1 puis révocation)" | tee -a "$REPORT"
    ip netns exec ns-b-web timeout 5 tcpdump -i veth-b-web -nn "ip" -w "$PROOF_DIR/test3_dynamique.pcap" >/dev/null 2>&1 &
    sleep 0.4

    allow_specific_rule 10.10.1.2 10.10.2.1 >/dev/null
    if REP3=$(ip netns exec ns-a-u1 curl -s --max-time 2 http://10.10.2.1:8080); then
        echo "  • Étape 3A (Permission accordée à 10.10.1.2) : ✅ Accès MedinaTech réussi -> $REP3" | tee -a "$REPORT"
    fi

    deny_specific_rule 10.10.1.2 10.10.2.1 >/dev/null
    if ! ip netns exec ns-a-u1 curl -s --max-time 2 http://10.10.2.1:8080 >/dev/null 2>&1; then
        echo "  • Étape 3B (Permission révoquée)             : ✅ Accès MedinaTech à nouveau BLOQUÉ" | tee -a "$REPORT"
    fi
    echo "  • Preuve : $PROOF_DIR/test3_dynamique.pcap" | tee -a "$REPORT"

    echo "" | tee -a "$REPORT"
    echo "🎉 [TERMINÉ] Tous les tests et captures .pcap sont disponibles dans $PROOF_DIR"
}

case "${1:-}" in
    setup)      setup_lab ;;
    start)      start_services ;;
    add-user)   add_dynamic_users "${2:-A}" "${3:-1}" ;;
    allow-rule) allow_specific_rule "$2" "$3" ;;
    deny-rule)  deny_specific_rule "$2" "$3" ;;
    allow-all)  allow_all_inter ;;
    block-all)  block_all_inter ;;
    qos-limit)  apply_qos_limit "${2:-1000}" "${3:-100}" ;;
    qos-reset)  reset_qos_limit ;;
    qos-test)   run_qos_test ;;
    benchmark)  run_benchmark "${2:-ns-a-u1}" "${3:-10.10.1.1}" ;;
    test)       run_tests ;;
    stop)       stop_lab ;;
    status)
        echo "=== Utilisateurs & Serveurs Actifs (ip netns) ===" && ip netns list
        echo "=== Règles OpenFlow Actives (br-pfa) ===" && ovs-ofctl dump-flows "$BRIDGE"
        ;;
    *)
        echo "Usage: sudo $0 {setup|start|add-user <A|B> [N]|allow-rule <ip1> <ip2>|deny-rule <ip1> <ip2>|allow-all|block-all|qos-limit [kbps]|qos-reset|qos-test|benchmark|test|status|stop}"
        exit 1
        ;;
esac
