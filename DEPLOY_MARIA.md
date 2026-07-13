# Guide de déploiement — Agent commercial local sur VM Debian 12 (site ETS Maria)

Ce guide décrit, étape par étape, la remise en place complète de l'agent sur une
**VM Debian 12** hébergée sur le serveur Windows d'ETS Maria (Hyper-V supposé).
Il est écrit pour être suivi seul, sans assistance.

**Principe retenu** : l'installation nécessite un accès internet **ponctuel**
(téléchargement d'Ollama, du modèle, de Hermes Agent et des paquets). Une fois
installé, l'agent fonctionne intégralement hors ligne ; l'accès internet de la
VM peut être coupé. Une variante 100 % hors-ligne est décrite en annexe A —
avec ses limites réelles.

## 0. Architecture déployée

```
Navigateur (poste employé)
        │ http://<ip-vm>:8321                    ← seul port exposé au LAN
        ▼
Proxy FastAPI  agent/app.py  (uvicorn, service maria-agent)
        │  sert l'UI + enrichit chaque demande : instruction de tâche,
        │  fiche entreprise (agent/data/entreprise.md),
        │  extraits catalogue (agent/data/catalogue_mock.csv, recherche lexicale),
        │  client + devis sélectionnés (agent/data/maria.db, SQLite local —
        │  seedée automatiquement depuis les CSV mock au premier démarrage)
        ▼ 127.0.0.1:8642  (/v1/chat/completions, clé API locale)
Gateway Hermes Agent  (service hermes-gateway)
        │  system prompt : ~/.hermes/SOUL.md + skill mails-commerciaux
        │  mémoire persistante locale (SQLite, ~/.hermes/)
        ▼ 127.0.0.1:11434  (API OpenAI-compatible)
Ollama  (service ollama, OLLAMA_NO_CLOUD=1)
        └─ qwen3:4b-instruct-2507-q4_K_M  (≈ 2,5 Go, contexte 64k)
```

Trois services systemd, démarrés dans cet ordre : `ollama` → `hermes-gateway`
→ `maria-agent`. Hermes et Ollama n'écoutent que sur 127.0.0.1.

**Hermétisme (audité sur Hermes Agent 0.18.2, install git)** :
- le gateway headless (`hermes gateway`) ne fait **aucun appel réseau sortant** :
  modèle, mémoire, skills et « curator » passent tous par l'endpoint local ;
- la vérification de mise à jour (fichier `~/.hermes/.update_check`) n'est
  déclenchée que par le CLI interactif / TUI / dashboard — jamais par le
  gateway — et échoue silencieusement sans réseau ;
- le Skills Hub n'est contacté que sur commande explicite
  (`hermes skills install …`) — ne jamais la lancer sur la VM ;
- la config `hermes/config.yaml.example` du dépôt ne référence aucun provider
  cloud (pas de Nous Portal, pas d'OpenRouter) et désactive le STT.

## 1. Dimensionnement de la VM

| Ressource | Minimum | Recommandé | Pourquoi |
|---|---|---|---|
| vCPU | 4 | 6–8 | l'inférence CPU est parallélisée |
| RAM | 10 Go **statique** | 16 Go | modèle ≈ 2,5 Go + KV cache 64k quantisé ≈ 2,7 Go + gateway Hermes ≈ 0,5 Go + système. Désactiver la mémoire dynamique Hyper-V : le ballooning fait s'effondrer les perfs |
| Disque | 30 Go | 40 Go | système ≈ 5 Go, Ollama ≈ 5 Go, modèle 2,5 Go, Hermes Agent ≈ 1 Go (repo + venv + caches), marge |
| GPU | aucun | — | pas de passthrough GPU simple sous Hyper-V ; on assume du CPU-only |

**Vérification indispensable avant d'aller plus loin** — le CPU du serveur doit exposer AVX2 :

```bash
lscpu | grep -o avx2 | head -1    # doit afficher : avx2
```

Sans AVX2, Ollama tournera très lentement ou pas du tout → changer de machine hôte.

**Performances à attendre en CPU-only** : la génération tourne à ~5–15 tokens/s
selon le CPU (réf. : la machine de dev fait ~60 tok/s sur GPU GTX 1080). Hermes
ajoute un system prompt volumineux (SOUL + skills + mémoire) : la **première
génération** après démarrage inclut son traitement complet et peut prendre
**2 à 5 min sur CPU**. Ollama réutilise ensuite ce préfixe en cache (prompt
caching) : les demandes suivantes retombent à ~30 s–2 min par mail. C'est
acceptable pour la démo ; le Mac mini M4 prévu ensuite ramènera ça à quelques
secondes (voir ROADMAP). Mesuré sur dev/GPU : ~40 s par mail, premier compris.

## 2. Préparation du système (root ou sudo)

```bash
apt update && apt install -y curl git python3 python3-venv ca-certificates xz-utils
```

Debian 12 fournit Python 3.11 : suffisant pour le proxy (testé 3.11+ ; dev
validé en 3.14) **et** compatible Hermes Agent (exige 3.11 ≤ Python < 3.14 —
son installeur embarque de toute façon son propre Python via `uv`).

Créer l'utilisateur applicatif (avec home : Hermes stocke tout dans `~/.hermes`) :

```bash
useradd -r -m -d /opt/maria-agent -s /bin/bash maria-agent
```

Note : shell `/bin/bash` (et non `nologin`) car l'installeur Hermes et son CLI
s'exécutent sous cet utilisateur (`su - maria-agent`). Verrouiller le mot de
passe : `passwd -l maria-agent`.

## 3. Installation d'Ollama (service systemd officiel)

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Le script crée l'utilisateur `ollama` et le service `ollama.service`.
**Durcissement hermétique + contexte 64k** (obligatoire — Hermes exige un
contexte de 64k minimum ; sans KV quantisé, le cache passerait de ~2,7 à ~9 Go) :

```bash
systemctl edit ollama
```

Ajouter dans l'éditeur qui s'ouvre :

```ini
[Service]
Environment="OLLAMA_NO_CLOUD=1"
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_CONTEXT_LENGTH=65536"
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q4_0"
```

Puis :

```bash
systemctl daemon-reload && systemctl restart ollama
curl -s http://127.0.0.1:11434/api/version   # doit répondre {"version":"..."}
```

- `OLLAMA_NO_CLOUD=1` désactive toute fonction cloud d'Ollama (versions ≥ 0.31).
- `OLLAMA_HOST=127.0.0.1` : Ollama n'est joignable que depuis la VM elle-même.
  Ne jamais mettre `0.0.0.0` ici.
- `OLLAMA_KV_CACHE_TYPE=q4_0` requiert `OLLAMA_FLASH_ATTENTION=1`. Validé sur
  la machine de dev (GPU) ; si les logs Ollama indiquent que flash attention
  est désactivée sur le CPU cible, le KV repasse en f16 → prévoir 16 Go de RAM.

Télécharger le modèle (≈ 2,5 Go — le plus gros téléchargement) :

```bash
ollama pull qwen3:4b-instruct-2507-q4_K_M
ollama list    # le modèle doit apparaître
```

## 4. Installation de Hermes Agent (utilisateur maria-agent)

```bash
su - maria-agent
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

L'installeur clone le dépôt Hermes, crée son venv (via `uv`) et installe la
commande `hermes` dans `~/.local/bin`. À la fin, **ignorer/quitter toute
proposition de configuration de provider cloud** — la config vient du dépôt :

```bash
# toujours sous maria-agent, depuis /opt/maria-agent/app (dépôt cloné au §5) :
mkdir -p ~/.hermes/skills
cp hermes/config.yaml.example ~/.hermes/config.yaml
cp hermes/SOUL.md             ~/.hermes/SOUL.md
cp -r hermes/skills/mails-commerciaux ~/.hermes/skills/

# Clé API du gateway (protège le port 8642 local) :
sed -i "s/__CLE_API_GATEWAY__/$(openssl rand -hex 24)/" ~/.hermes/config.yaml
```

(Si le dépôt n'est pas encore cloné, faire le §5 d'abord puis revenir ici —
l'ordre §4/§5 est indifférent, seuls les fichiers `hermes/` du dépôt comptent.)

Test manuel du gateway :

```bash
~/.local/bin/hermes gateway   # laisser tourner
# Depuis un autre terminal de la VM :
curl -s http://127.0.0.1:8642/health    # doit répondre 200
# Ctrl+C pour arrêter, le service systemd prendra le relais (§6).
```

**Règles d'exploitation hermétique** (voir audit §0) :
- ne jamais lancer `hermes update`, `hermes skills install` ni le dashboard
  web sur la VM — ce sont les seuls chemins qui sortent sur internet ;
- le CLI `hermes` interactif tente une vérification de version au lancement :
  sans réseau elle échoue silencieusement, aucun impact.

## 5. Installation de l'agent (proxy + UI)

Récupérer le dépôt (depuis Git, ou copie par clé USB/scp du dossier complet) :

```bash
git clone <url-du-depot> /opt/maria-agent/app
# — ou — scp -r MariaAgent/ maria-agent@<ip-vm>:/opt/maria-agent/app
cd /opt/maria-agent/app
python3 -m venv .venv
.venv/bin/pip install -r agent/requirements.txt
chown -R maria-agent: /opt/maria-agent
```

**Avant la mise en service** : compléter `agent/data/entreprise.md`
(tous les champs `[À COMPLÉTER]` : téléphone, adresse, conditions commerciales…).
C'est la source de vérité du modèle — champs vides = brouillons avec des trous,
champs remplis = brouillons complets.

**Base clients/devis** : aucune dépendance système nouvelle (SQLite via la
stdlib Python). `agent/data/maria.db` est créée et seedée automatiquement au
premier démarrage depuis les CSV mock (`clients_mock.csv`,
`documents_mock.csv`, `document_lignes_mock.csv`). Après modification de ces
CSV (ou pour repartir propre) :

```bash
sudo -u maria-agent /opt/maria-agent/app/.venv/bin/python /opt/maria-agent/app/agent/seed_db.py --force
```

Test manuel rapide (Ollama démarré §3, gateway démarré §4) :

```bash
sudo -u maria-agent MARIA_HOST=127.0.0.1 /opt/maria-agent/app/.venv/bin/uvicorn app:app \
  --app-dir /opt/maria-agent/app/agent --port 8321
# Depuis un autre terminal de la VM :
curl -s http://127.0.0.1:8321/api/health
# attendu : {"hermes":true,"ollama":true,"model":"qwen3:4b-instruct-2507-q4_K_M","model_ready":true,"ready":true}
# Ctrl+C pour arrêter, on passe aux services.
```

Le proxy lit la clé API du gateway directement dans
`~maria-agent/.hermes/config.yaml` (même utilisateur) — rien à configurer.

## 6. Services systemd

Créer `/etc/systemd/system/hermes-gateway.service` :

```ini
[Unit]
Description=Gateway Hermes Agent (ETS Maria)
After=network-online.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=maria-agent
WorkingDirectory=/opt/maria-agent
Environment="HOME=/opt/maria-agent"
ExecStart=/opt/maria-agent/.local/bin/hermes gateway
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Créer `/etc/systemd/system/maria-agent.service` :

```ini
[Unit]
Description=Agent commercial local ETS Maria (UI + proxy)
After=network-online.target hermes-gateway.service
Wants=hermes-gateway.service

[Service]
Type=simple
User=maria-agent
WorkingDirectory=/opt/maria-agent/app
Environment="MARIA_HOST=0.0.0.0"
Environment="MARIA_PORT=8321"
Environment="MARIA_MODEL=qwen3:4b-instruct-2507-q4_K_M"
ExecStart=/opt/maria-agent/app/.venv/bin/uvicorn app:app --app-dir /opt/maria-agent/app/agent --host ${MARIA_HOST} --port ${MARIA_PORT}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now hermes-gateway maria-agent
systemctl status ollama hermes-gateway maria-agent
```

`MARIA_HOST=0.0.0.0` expose l'UI sur le réseau d'entreprise — c'est voulu :
les employés y accèdent via `http://<ip-de-la-vm>:8321`. Le gateway Hermes
(8642) et Ollama (11434) restent en 127.0.0.1.

## 7. Pare-feu (recommandé)

```bash
apt install -y ufw
ufw default deny incoming
ufw allow from 192.168.0.0/16 to any port 8321 proto tcp   # adapter au plan d'adressage local
ufw allow from 192.168.0.0/16 to any port 22 proto tcp     # SSH admin si utilisé
ufw enable
```

Adapter `192.168.0.0/16` au sous-réseau réel d'ETS Maria (demander à Kévin ou
vérifier `ip route` sur un poste).

## 8. Recette (checklist de validation)

1. `systemctl status ollama hermes-gateway maria-agent` → les trois `active (running)`.
2. `curl -s http://127.0.0.1:8321/api/health` → `"ready":true` (les trois maillons).
3. Depuis un **poste employé** : ouvrir `http://<ip-vm>:8321`, pastille verte
   « Modèle local prêt ».
4. Tâche « Répondre à un client », coller un mail de test avec une demande de pompe →
   le brouillon cite une référence `PMP-…` du catalogue avec le bon prix, et ne contient
   ni prix inventé, ni délai chiffré non fourni (référence de recette validée en dev :
   demande « pompe piscine 50 m³ » → `PMP-HAY-SP050` à 539,00 € HT, délai laissé
   « à confirmer », signature avec `[À COMPLÉTER : téléphone]` tant que la fiche
   n'est pas remplie).
5. Bouton « Affiner » avec « plus court » → version raccourcie cohérente.
6. Débrancher/couper l'accès internet de la VM → refaire le test 4 : tout doit
   fonctionner à l'identique. Prévoir le préchauffage : première génération après
   redémarrage = chargement du modèle + traitement du system prompt Hermes
   (jusqu'à quelques minutes sur CPU), ensuite fluide.

## 9. Différences dev ↔ production (à ne pas oublier)

| Sujet | Machine de dev (ce qui a été fait) | VM Maria (ce guide) |
|---|---|---|
| Ollama | install manuelle user-space (`~/.local/opt/ollama`, pas de sudo dispo) | script officiel + service systemd + user `ollama` |
| Hermes Agent | install git user-space (`~/.local/opt/hermes-agent`, v0.18.2) | installeur officiel sous `maria-agent` + service systemd |
| Inférence | GPU GTX 1080 (≈ 60 tok/s) | CPU-only (≈ 5–15 tok/s) — prévenir les utilisateurs |
| Exposition | `127.0.0.1` uniquement | UI sur `0.0.0.0:8321` ; gateway et Ollama sur `127.0.0.1` |
| Lancement | `scripts/run.sh` (session : Ollama + gateway + proxy) | trois services systemd persistants |
| Hermétique | `OLLAMA_NO_CLOUD=1` dans `run.sh`, config Hermes sans provider cloud | idem, dans les overrides/units systemd |

## 10. Points de vigilance

- **Hyper-V, mémoire dynamique : OFF.** Fixer la RAM. Le ballooning + un modèle chargé
  = latences catastrophiques.
- **AVX2** vérifié avant tout (section 1).
- **Snapshots/checkpoints Hyper-V** : en faire un après la recette — retour arrière trivial.
- **RAM chargée ≈ 6 Go** (modèle + KV cache 64k quantisé) + gateway Hermes ≈ 0,5 Go.
  Avec 10 Go ça passe ; ne rien co-héberger d'autre sur cette VM (Peep a son
  propre serveur Docker).
- **Contexte 64k obligatoire** : minimum imposé par Hermes Agent. Ne pas le
  réduire dans `config.yaml` ou l'override Ollama pour « gagner de la RAM » —
  le gateway refuserait de démarrer ou tronquerait ses prompts.
- **`keep_alive`** : Ollama garde le modèle chargé après usage. Première requête
  du matin = chargement + system prompt Hermes (le plus long sur CPU), ensuite fluide.
- **Mémoire Hermes** : le gateway accumule une mémoire locale
  (`~maria-agent/.hermes/`, SQLite). 100 % local, mais penser à l'inclure dans
  les sauvegardes si on veut la conserver, et à la purger si on veut repartir à zéro.
- **Mises à jour** : rien n'est automatique (voulu — hermétique). Mise à jour
  modèle, Ollama ou Hermes (`hermes update`) = opération manuelle ponctuelle
  avec internet réactivé, suivie d'un re-test de recette complet (§8).
- **Sauvegardes** : `agent/data/` (fiche + catalogue), `~maria-agent/.hermes/`
  (config + clé + SOUL + skills + mémoire) et d'éventuelles modifs de code ;
  tout le reste se réinstalle avec ce guide.
- **RGPD / confidentialité** : aucune donnée ne sort. C'est l'argument central face à
  Limova — le démontrer en coupant internet pendant la démo (test 8.6).

## 11. Exploitation courante

```bash
journalctl -u maria-agent -f          # logs du proxy/UI
journalctl -u hermes-gateway -f       # logs de l'agent Hermes
journalctl -u ollama -f               # logs d'inférence
systemctl restart hermes-gateway      # redémarrage de l'agent (mémoire conservée)
ollama ps                             # modèle chargé ? CPU/GPU ? mémoire ?
```

Changer de modèle plus tard (ex. machine plus puissante) :

```bash
ollama pull <nouveau-modele>
# 1. ~maria-agent/.hermes/config.yaml : model.default = <nouveau-modele>
# 2. systemctl edit maria-agent → Environment="MARIA_MODEL=<nouveau-modele>"
systemctl daemon-reload && systemctl restart hermes-gateway maria-agent
```

---

## Annexe A — Variante 100 % hors-ligne (si la VM n'a jamais internet)

**Recommandation honnête** : l'installeur Hermes est conçu pour un poste avec
internet (clone git + résolution de dépendances). La voie la plus fiable reste
un **accès internet temporaire** (partage 4G, VLAN dédié le temps de l'install),
coupé définitivement après la recette §8.6. Si c'est impossible :

1. **Ollama** : télécharger sur une machine connectée le tarball Linux
   `https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tar.zst`
   (format `.tar.zst` depuis 2026 — paquet `zstd` requis), l'extraire dans
   `/usr/local`, créer le service systemd à la main (section `[Service]`
   identique au §3).
2. **Modèle** : copier `~/.ollama/models` (blobs + manifests) de la machine
   connectée vers `/usr/share/ollama/.ollama/models` (propriétaire `ollama:`).
3. **Proxy** : `pip download -r agent/requirements.txt -d wheels/
   --python-version 3.11 --only-binary=:all:` sur la machine connectée, puis
   `pip install --no-index --find-links wheels/ -r agent/requirements.txt` sur la VM.
4. **Hermes Agent** — le point délicat. Deux options :
   - *Miroir d'installation* : reproduire sur une **machine de transfert** la
     même arborescence que la VM (même chemin `/opt/maria-agent`, même version
     de Python), y lancer l'installeur officiel, puis copier `~/.local/opt/hermes-agent`
     et `~/.local/bin/hermes` sur la VM. ⚠️ Le venv embarque des chemins absolus :
     la copie ne fonctionne que si le chemin du home est identique.
   - *Install pip hors-ligne* : depuis le clone du dépôt Hermes sur la machine
     connectée, `pip download` de ses dépendances (`pyproject.toml`), transfert,
     puis venv + `pip install --no-index` sur la VM. Plus propre mais non testé —
     prévoir une demi-journée d'ajustements.
5. Reprendre au §4 (copie de `hermes/config.yaml.example`, SOUL, skill), puis §5.

## Annexe B — Dépannage

| Symptôme | Cause probable | Remède |
|---|---|---|
| Pastille rouge « Moteur IA arrêté » | Ollama ou gateway down | `systemctl restart ollama hermes-gateway`, puis `journalctl -u hermes-gateway -n 50` |
| `/api/health` : `"hermes":false` | gateway down ou clé changée | `journalctl -u hermes-gateway -n 50` ; vérifier que le proxy et le gateway lisent le même `~/.hermes/config.yaml` |
| « Modèle non installé » | pull manquant/interrompu | `ollama pull qwen3:4b-instruct-2507-q4_K_M` |
| Le gateway répond 401 au proxy | clé API régénérée après démarrage du proxy | `systemctl restart maria-agent` (il relit la clé au démarrage) |
| Générations très lentes (> 5 min/mail) | mémoire dynamique Hyper-V, swap, AVX2 absent, ou KV f16 (flash attention inactive) | fixer la RAM, `free -h`, `lscpu \| grep avx2`, `journalctl -u ollama` (chercher `flash attention`) |
| Gateway ne démarre pas | config.yaml invalide ou contexte < 64k | `journalctl -u hermes-gateway -n 50` ; re-partir de `hermes/config.yaml.example` |
| HTTP 500 au démarrage du proxy | venv incomplet | relancer `pip install -r agent/requirements.txt` et lire `journalctl -u maria-agent` |
| Page inaccessible depuis un poste | pare-feu / mauvais host | vérifier `MARIA_HOST=0.0.0.0`, règles ufw, `ip a` sur la VM |
