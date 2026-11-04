# Segmentation virtuelle de deux réseaux avec un contrôleur SDN

## Présentation du projet

Ce projet consiste à mettre en place une infrastructure réseau virtuelle permettant de segmenter deux réseaux distincts au sein d'une seule machine virtuelle Linux.

L'objectif est de contrôler les communications entre les différentes machines virtuelles simulées, d'autoriser les échanges au sein d'un même réseau et de bloquer les communications entre les deux réseaux selon des règles de filtrage.

Un contrôleur web inspiré de l'approche **SDN (Software-Defined Networking)** permet de visualiser et de gérer la segmentation réseau.

## Objectifs

- Créer deux réseaux virtuels indépendants.
- Générer des machines (PCs) virtuelles et leur attribuer des adresses IP.
- Configurer les règles de communication et de blocage par switch virtuel.
- Autoriser les communications au sein d'un même réseau.
- Contrôler et bloquer les communications entre les deux réseaux.
- Visualiser l'état de l'infrastructure à travers une interface web.

## Architecture du projet

L'infrastructure repose sur une seule machine virtuelle Linux qui héberge les composants nécessaires à la simulation de l'environnement réseau.

Les deux réseaux sont organisés de manière à isoler leurs communications :

- **Réseau 1 :** Groupe A — VLAN 10
- **Réseau 2 :** Groupe B — VLAN 20

La segmentation permet de contrôler les flux entre les deux groupes et de tester différentes politiques de communication.

## Technologies utilisées

- **Linux** : environnement d'exécution.
- **Python** : génération des machines virtuelles simulées, attribution des adresses IP et gestion des règles.
- **SDN** : approche de gestion centralisée du réseau.
- **Open vSwitch (OVS)** : gestion des switches virtuels.
- **Bash** : automatisation de la configuration et de la gestion de l'environnement.
- **HTML / CSS / JavaScript** : interface web de visualisation et de contrôle.

## Structure du dépôt

```text
SDN-Network-Segmentation/
│

│sdn_controller
├── pfa_lab.sh
│
├── screenshots/
│   ├── dashboard.png
│   ├── topology.png
│   └── tests.png
│
└── README.md
```



## Fonctionnalités principales

### 1. Génération des machines et attribution des adresses IP
Un script Python permet de générer les machines du réseau et de leur attribuer des adresses IP selon leur groupe.

### 2. Gestion des règles de filtrage
Un autre script Python permet de gérer les règles de blocage au niveau des switches virtuels afin de contrôler les communications entre les réseaux.

### 3. Automatisation de l'infrastructure
Le script `pfa_lab.sh` permet de gérer les différentes opérations de configuration et de test de l'environnement réseau.

### 4. Interface web SDN
Une interface web permet de visualiser l'architecture réseau, de suivre les flux et de présenter les scénarios de segmentation.

## Scénarios de test

Le projet prévoit plusieurs scénarios permettant de vérifier le fonctionnement de la segmentation :

| Scénario | Résultat attendu |
|---|---|
| Communication au sein du même groupe | Autorisée |
| Communication entre deux groupes | Bloquée |
| Modification dynamique des règles | Changement du comportement des communications |


## Environnement d'exécution

## Installation et exécution

### Prérequis

- Une machine virtuelle Linux.
- Python 3.
- Open vSwitch (OVS).
- Les privilèges administrateur (`sudo`).

### 1. Construire et démarrer l'infrastructure réseau

Depuis le répertoire du projet, exécuter :

```bash
sudo ./pfa_lab.sh setup
sudo ./pfa_lab.sh start
```

Ces commandes permettent respectivement de configurer l'environnement réseau virtuel et de démarrer l'infrastructure.

### 2. Tester la segmentation réseau

Pour lancer les tests de communication entre les machines :

```bash
sudo ./pfa_lab.sh test
```

### 3. Démarrer le contrôleur Web SDN

Pour lancer le contrôleur :

```bash
sudo python3 sdn_controller.py
```

Le contrôleur Web SDN permet de visualiser et de gérer l'environnement de segmentation réseau.



Le projet est conçu pour être exécuté dans un environnement Linux disposant des outils nécessaires à la virtualisation réseau et à la gestion des switches virtuels.

Les dépendances et les commandes exactes d'installation et d'exécution seront précisées en fonction de la configuration de l'environnement.

## Auteur

**Zaid Charkaoui**

Étudiant ingénieur en cybersécurité

---

*Projet académique — EMSI | 2025–2026*