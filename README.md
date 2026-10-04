# iBroadcast Sync — app menu bar

Petite application macOS, dans la barre de menu, qui pilote le projet
[`ibroadcast-sync`](https://github.com/Jeromearsene/ibroadcast-sync) sans
avoir à ouvrir un terminal : lancer une synchro, voir quand la dernière
s'est terminée (et avec quel résultat), et activer/désactiver une
synchro planifiée (via `launchd`).

Ce projet est un **compagnon** de `ibroadcast-sync`, pas un fork ni une
réécriture : il ne fait qu'appeler le CLI existant. `ibroadcast-sync`
reste utilisable seul, en ligne de commande, exactement comme avant.

## Pourquoi un projet séparé

- Cycle de vie différent : `ibroadcast-sync` est un outil CLI testé sur
  plusieurs versions de Python (3.9 → 3.12, voir sa CI) ; cette app est
  spécifiquement macOS (rumps/PyObjC), et n'a pas de sens ailleurs.
- Dépendances différentes et volontairement très légères (voir
  "Pourquoi la performance" plus bas) - les mélanger dans un seul
  `pyproject.toml` aurait fait porter requests/rich/pytest-cov etc. à
  cette petite app sans raison.

## Pourquoi la performance (RAM, pas de lag)

Ce process tourne **en permanence** dans la barre de menu, donc son
empreinte doit rester minimale et constante, que la bibliothèque fasse
50 ou 50 000 morceaux. Deux décisions font tout le travail :

1. **La vraie synchro tourne toujours dans un sous-processus**
   (`sync_runner.py` : `scripts/run.sh` du projet `ibroadcast-sync`),
   jamais importée dans ce process. `requests`, `rich`,
   `oauth_client.py`, le pont JXA vers Music.app... rien de tout ça
   n'est jamais chargé ici - seulement le temps du sous-processus, qui
   se termine et libère sa mémoire.
2. **Ce process ne lit jamais la bibliothèque musicale** : il se
   contente de relire un tout petit fichier JSON
   (`data/ibroadcast_sync_status.json`, écrit par le CLI après chaque
   synchro réelle - voir le patch correspondant dans le projet
   principal) pour afficher "dernière synchro : ...". Pas de parsing de
   logs, pas de requête réseau depuis l'app elle-même.

Résultat : au repos, cette app ne fait qu'un `rumps.Timer` qui se
réveille toutes les 30 secondes pour relire ce petit fichier - rien
d'autre.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancer en développement

```bash
python3 -m ibroadcast_sync_menubar
```

La première chose à faire, dans le menu qui apparaît dans la barre de
menu : **Dossier du projet…**, pour indiquer où se trouve ton clone de
`ibroadcast-sync` (celui qui contient `scripts/run.sh`).

## Construire l'app (`.app` autonome)

```bash
python3 setup.py py2app -A   # build "alias" : rapide, pour développer
python3 setup.py py2app      # vrai build, dans dist/ - celui à copier
                              # dans ~/Applications
```

## Où sont stockés les réglages

`~/Library/Application Support/ibroadcast-sync-menubar/config.json`
(indépendant du `.env` du projet `ibroadcast-sync` : cette app passe ce
qu'il faut au CLI explicitement, via variables d'environnement et
flags, à chaque appel).

## Organisation du code

| Fichier | Rôle |
|---|---|
| `app.py` | L'app `rumps` elle-même : menu, minuteries, callbacks. |
| `settings_window.py` | Le seul bout d'AppKit "brut" : le sélecteur de dossier natif (`NSOpenPanel`). |
| `config.py` | Lecture/écriture de `config.json` (écriture atomique). |
| `status.py` | Lecture du `ibroadcast_sync_status.json` du CLI + formatage de la ligne affichée dans le menu. |
| `sync_runner.py` | Construit la commande/l'environnement pour lancer une synchro manuelle. |
| `launchd_manager.py` | Génère le `.plist` et appelle `launchctl` pour la synchro planifiée. |

## Tests

```bash
pip install pytest ruff mypy
pytest
ruff check . && ruff format --check .
mypy ibroadcast_sync_menubar tests
```

Comme pour le pont JXA de `ibroadcast-sync` lui-même, le code
AppKit/rumps (`app.py`, `settings_window.py`) n'est **pas** couvert par
les tests : il n'y a pas d'environnement macOS/PyObjC dans lequel
l'exécuter ici. Il reste vérifié par `python -m py_compile` (syntaxe) et
par `mypy` (le reste de la logique de ces deux fichiers - les imports
`rumps`/`AppKit` sont déclarés `Any`, voir `pyproject.toml`). Tout le
reste (`config.py`, `status.py`, `sync_runner.py`,
`launchd_manager.py` - la logique pure, sans AppKit) est testé
normalement.
