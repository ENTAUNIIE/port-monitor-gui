# Cisco Network Monitoring GUI

Cette application permet de surveiller en temps réel l'état des interfaces réseau sur des équipements Cisco (switches, routeurs) via une interface graphique.

## Fonctionnalités

- Surveillance multi-appareils avec un onglet par équipement.
- Affichage du statut des ports : UP, DOWN, administratively shutdown avec couleurs.
- Filtres : UP, DOWN, SHUTDOWN, VLAN, TRUNK.
- Résumé VLAN / Trunk / Ports UP par appareil.
- Synthèse globale exportable en CSV.
- Ajout et suppression d'appareils avec double confirmation.
- Rafraîchissement automatique toutes les 7 secondes.

## Installation

1. Cloner le dépôt :

```bash
git clone https://github.com/ton-utilisateur/port-monitor-gui.git
cd port-monitor-gui
```

2. Installer les dépendances :

```bash
pip install -r requirements.txt
```

## Lancement

```bash
python int.py
```

## Fichiers

- `int.py` : Script principal.
- `devices.json` : Liste des équipements (généré automatiquement).
- `icon.png` : Icône de l'application.
- `requirements.txt` : Dépendances.
- `README.md` : Documentation.
