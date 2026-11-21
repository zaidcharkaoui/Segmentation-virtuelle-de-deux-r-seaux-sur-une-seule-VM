#!/usr/bin/env bash
# ==============================================================================
# PROJET PFA-04 (EMSI) — Segmentation virtuelle de deux réseaux sur une seule VM
# Scénario Métier : NovaStudio Cloud (Équipe A DarMarket vs Équipe B AtlasPay)
# ==============================================================================
# Commandes disponibles (conformes au cahier des charges du professeur) :
#   sudo ./pfa_lab.sh setup   -> Crée les 4 namespaces, les câbles veth et le switch OVS
#   sudo ./pfa_lab.sh start   -> Démarre les 2 petits serveurs web (DarMarket & AtlasPay)
#   sudo ./pfa_lab.sh test    -> Exécute automatiquement les 3 tests + captures tcpdump
#   sudo ./pfa_lab.sh allow   -> Ouvre manuellement la porte entre A et B (VLAN 10 <-> 20)
#   sudo ./pfa_lab.sh block   -> Referme la porte entre A et B (Isolation stricte)
#   sudo ./pfa_lab.sh status  -> Affiche l'état actuel des namespaces et du switch
#   sudo ./pfa_lab.sh stop    -> Nettoie tout proprement (aucun résidu sur la VM)
# ==============================================================================

set -e

# Vérification des droits administrateur (root) requis par ip netns et Open vSwitch
if [ "$EUID" -ne 0 ]; then
    echo "❌ Erreur : Ce script doit être lancé avec sudo."
    echo "👉 Tape : sudo ./pfa_lab.sh ${1:-setup}"
    exit 1
fi

BRIDGE="br-pfa"
PROOF_DIR="./preuves_$(hostname)"
mkdir -p "$PROOF_DIR"

# ------------------------------------------------------------------------------
# 1. FONCTION STOP : Nettoyage complet et idempotent
# ------------------------------------------------------------------------------
stop_lab() {
    echo "🧹 [STOP] Nettoyage de l'environnement virtuel..."

    # Arrêt des petits serveurs web et des sondes tcpdump éventuelles
    pkill -f "http.server 8080" 2>/dev/null || true
    pkill -f "tcpdump" 2>/dev/null || true

    # Suppression des 4 bulles réseau (namespaces)
    for ns in ns-a1 ns-a2 ns-b1 ns-b2; do
        ip netns del "$ns" 2>/dev/null || true
    done

    # Suppression du switch virtuel Open vSwitch
    ovs-vsctl --if-exists del-br "$BRIDGE" 2>/dev/null || true

    # Nettoyage des petits fichiers temporaires des serveurs web
    rm -rf /tmp/site_darmarket /tmp/site_atlaspay

    echo "✅ [OK] La VM est totalement propre."
}

# ------------------------------------------------------------------------------
# 2. FONCTION SETUP : Construction des 4 PC virtuels et du Switch Open vSwitch
# ------------------------------------------------------------------------------
setup_lab() {
    # Idempotence : on nettoie toujours avant de créer pour éviter les erreurs "File exists"
    stop_lab

    echo "🏗️  [SETUP] Création du switch central Open vSwitch ($BRIDGE)..."
    ovs-vsctl add-br "$BRIDGE"
    ip link set "$BRIDGE" up

    # Création et câblage des 4 namespaces :
    # Format = "nom_court : dernier_octet_IP : numéro_VLAN : équipe"
    for item in "a1:11:10:DarMarket-Serveur" "a2:12:10:DarMarket-Client" "b1:21:20:AtlasPay-Serveur" "b2:22:20:AtlasPay-Client"; do
        IFS=":" read -r name oct vlan role <<< "$item"

        echo "   -> Création de ns-$name ($role) | IP: 10.10.0.$oct/24 | VLAN: $vlan"

        # 1) Créer la bulle réseau (le petit PC virtuel)
        ip netns add "ns-$name"

        # 2) Créer le câble virtuel (veth-X côté PC <-> ovs-X côté Switch)
        ip link add "veth-$name" type veth peer name "ovs-$name"

        # 3) Brancher une extrémité dans le PC virtuel
        ip link set "veth-$name" netns "ns-$name"

        # 4) Brancher l'autre extrémité sur le switch Open vSwitch avec son étiquette VLAN
        ovs-vsctl add-port "$BRIDGE" "ovs-$name" tag="$vlan"
        ip link set "ovs-$name" up

        # 5) Configurer l'adresse IP et allumer la carte réseau dans le PC virtuel
        ip netns exec "ns-$name" ip addr add "10.10.0.$oct/24" dev "veth-$name"
        ip netns exec "ns-$name" ip link set "veth-$name" up
        ip netns exec "ns-$name" ip link set lo up
    done

    echo "✅ [OK] Topologie créée et isolée :"
    echo "   • Équipe A (DarMarket - VLAN 10) : ns-a1 (10.10.0.11) et ns-a2 (10.10.0.12)"
    echo "   • Équipe B (AtlasPay  - VLAN 20) : ns-b1 (10.10.0.21) et ns-b2 (10.10.0.22)"
}

# ------------------------------------------------------------------------------
# 3. FONCTION START : Démarrage des 2 petits services web (pour tester curl)
# ------------------------------------------------------------------------------
start_services() {
    echo "🚀 [START] Démarrage des services web dans ns-a1 (DarMarket) et ns-b1 (AtlasPay)..."

    pkill -f "http.server 8080" 2>/dev/null || true
    mkdir -p /tmp/site_darmarket /tmp/site_atlaspay

    # Page web du serveur A1 (DarMarket E-Commerce)
    cat << 'EOF' > /tmp/site_darmarket/index.html
{"equipe": "Groupe A - DarMarket", "vlan": 10, "service": "Catalogue E-Commerce", "statut": "ACCES AUTORISE"}
EOF

    # Page web du serveur B1 (AtlasPay FinTech)
    cat << 'EOF' > /tmp/site_atlaspay/index.html
{"equipe": "Groupe B - AtlasPay", "vlan": 20, "service": "API Paiement Confidentielle", "statut": "ACCES AUTORISE"}
EOF

    # Lancement des serveurs HTTP Python sur le port 8080 à l'intérieur des bulles
    ip netns exec ns-a1 python3 -m http.server 8080 --directory /tmp/site_darmarket >/dev/null 2>&1 &
    ip netns exec ns-b1 python3 -m http.server 8080 --directory /tmp/site_atlaspay >/dev/null 2>&1 &
    sleep 1

    echo "✅ [OK] Services actifs :"
    echo "   • Serveur DarMarket (ns-a1) écoute sur http://10.10.0.11:8080"
    echo "   • Serveur AtlasPay  (ns-b1) écoute sur http://10.10.0.21:8080"
}

# ------------------------------------------------------------------------------
# 4. FONCTIONS ALLOW / BLOCK : Ouvrir ou fermer la porte entre l'Équipe A et B
# ------------------------------------------------------------------------------
allow_intergroup() {
    echo "🔓 [PERMISSION] Ouverture du passage entre l'Équipe A et l'Équipe B..."
    ovs-vsctl set port ovs-b1 tag=10
    ovs-vsctl set port ovs-b2 tag=10
    echo "✅ [OK] Les deux équipes sont temporairement dans le même VLAN (flux autorisé)."
}

block_intergroup() {
    echo "🔒 [PERMISSION] Rétablissement du mur d'isolation entre l'Équipe A et l'Équipe B..."
    ovs-vsctl set port ovs-b1 tag=20
    ovs-vsctl set port ovs-b2 tag=20
    echo "✅ [OK] Équipe A = VLAN 10 | Équipe B = VLAN 20 (flux intergroupe bloqué)."
}

# ------------------------------------------------------------------------------
# 5. FONCTION TEST : Les 3 Tests Obligatoires + Preuves tcpdump automatiques
# ------------------------------------------------------------------------------
run_tests() {
    REPORT="$PROOF_DIR/rapport_recette.txt"
    echo "======================================================================" | tee "$REPORT"
    echo "RAPPORT DE RECETTE PFA-04 | Poste : $(hostname) | Date : $(date)" | tee -a "$REPORT"
    echo "======================================================================" | tee -a "$REPORT"

    # --- TEST 1 : Flux intragroupe autorisé (ns-a2 -> ns-a1) ---
    echo "" | tee -a "$REPORT"
    echo "▶ TEST 1 : Trafic autorisé au sein du même groupe (ns-a2 -> ns-a1)" | tee -a "$REPORT"
    echo "  • Action   : ping 10.10.0.11 + curl http://10.10.0.11:8080 depuis ns-a2" | tee -a "$REPORT"
    echo "  • Attendu  : Succès (0% packet loss et réponse JSON DarMarket)" | tee -a "$REPORT"

    # Démarrage de la caméra tcpdump dans ns-a1 pendant 3 secondes
    ip netns exec ns-a1 timeout 3 tcpdump -i veth-a1 -nn -w "$PROOF_DIR/test1_intra.pcap" >/dev/null 2>&1 &
    sleep 0.5

    if ip netns exec ns-a2 ping -c 2 -W 1 10.10.0.11 >/dev/null 2>&1 && \
       REP1=$(ip netns exec ns-a2 curl -s --max-time 2 http://10.10.0.11:8080); then
        echo "  • Obtenu   : ✅ SUCCÈS -> $REP1" | tee -a "$REPORT"
        echo "  • Preuve   : $PROOF_DIR/test1_intra.pcap" | tee -a "$REPORT"
    else
        echo "  • Obtenu   : ❌ ÉCHEC (Vérifie que tu as bien lancé: sudo ./pfa_lab.sh start)" | tee -a "$REPORT"
    fi
    sleep 2

    # --- TEST 2 : Flux intergroupe refusé (ns-a2 -> ns-b1) ---
    echo "" | tee -a "$REPORT"
    echo "▶ TEST 2 : Trafic intergroupe non autorisé (ns-a2 DarMarket -> ns-b1 AtlasPay)" | tee -a "$REPORT"
    echo "  • Action   : ping 10.10.0.21 + curl http://10.10.0.21:8080 depuis ns-a2" | tee -a "$REPORT"
    echo "  • Attendu  : Échec de connexion (Flux bloqué par l'isolation VLAN 10 != 20)" | tee -a "$REPORT"

    ip netns exec ns-b1 timeout 3 tcpdump -i veth-b1 -nn -w "$PROOF_DIR/test2_inter_bloque.pcap" >/dev/null 2>&1 &
    sleep 0.5

    if ! ip netns exec ns-a2 ping -c 1 -W 1 10.10.0.21 >/dev/null 2>&1 && \
       ! ip netns exec ns-a2 curl -s --max-time 2 http://10.10.0.21:8080 >/dev/null 2>&1; then
        echo "  • Obtenu   : ✅ SUCCÈS DU BLOCAGE (100% packet loss, aucun accès à AtlasPay)" | tee -a "$REPORT"
        echo "  • Preuve   : $PROOF_DIR/test2_inter_bloque.pcap (0 paquet reçu sur ns-b1)" | tee -a "$REPORT"
    else
        echo "  • Obtenu   : ❌ ÉCHEC (Le flux est passé alors qu'il devait être bloqué)" | tee -a "$REPORT"
    fi
    sleep 2

    # --- TEST 3 : Modification contrôlée de la règle puis rétablissement ---
    echo "" | tee -a "$REPORT"
    echo "▶ TEST 3 : Modification contrôlée de la règle (Ouverture puis Rétablissement)" | tee -a "$REPORT"
    echo "  • Action   : 1) Autoriser A<->B et tester curl | 2) Bloquer A<->B et retester curl" | tee -a "$REPORT"
    echo "  • Attendu  : Étape 3A = Succès | Étape 3B = Bloqué à nouveau" | tee -a "$REPORT"

    ip netns exec ns-b1 timeout 5 tcpdump -i veth-b1 -nn -w "$PROOF_DIR/test3_dynamique.pcap" >/dev/null 2>&1 &
    sleep 0.5

    # Étape 3A : On ouvre la porte
    allow_intergroup >/dev/null
    if REP3=$(ip netns exec ns-a2 curl -s --max-time 2 http://10.10.0.21:8080); then
        echo "  • Obtenu 3A (Porte ouverte)  : ✅ Flux passe -> $REP3" | tee -a "$REPORT"
    else
        echo "  • Obtenu 3A (Porte ouverte)  : ❌ Échec" | tee -a "$REPORT"
    fi

    # Étape 3B : On referme la porte immédiatement
    block_intergroup >/dev/null
    if ! ip netns exec ns-a2 curl -s --max-time 2 http://10.10.0.21:8080 >/dev/null 2>&1; then
        echo "  • Obtenu 3B (Porte refermée) : ✅ Flux à nouveau BLOQUÉ (Isolation rétablie)" | tee -a "$REPORT"
    else
        echo "  • Obtenu 3B (Porte refermée) : ❌ Échec" | tee -a "$REPORT"
    fi
    echo "  • Preuve   : $PROOF_DIR/test3_dynamique.pcap" | tee -a "$REPORT"
    sleep 1

    echo "" | tee -a "$REPORT"
    echo "🎉 [TERMINÉ] Tous les tests et captures sont enregistrés dans le dossier : $PROOF_DIR/"
}

# ------------------------------------------------------------------------------
# 6. FONCTION STATUS : Voir l'état du laboratoire
# ------------------------------------------------------------------------------
show_status() {
    echo "=== Bulles réseau (ip netns) présentes ==="
    ip netns list
    echo ""
    echo "=== Configuration du Switch Open vSwitch ($BRIDGE) ==="
    ovs-vsctl show
}

case "${1:-}" in
    setup)  setup_lab ;;
    start)  start_services ;;
    test)   run_tests ;;
    allow)  allow_intergroup ;;
    block)  block_intergroup ;;
    status) show_status ;;
    stop)   stop_lab ;;
    *)
        echo "Usage : sudo ./pfa_lab.sh {setup|start|test|allow|block|status|stop}"
        exit 1
        ;;
esac