# Durcissement production — Agent commercial ETS Maria

**Date :** 2026-07-20 **Statut : NON implémenté dans la démo — cible de
production.**

Ce document décrit ce qu'il reste à construire pour passer de la démo (POC)
décrite dans
[`2026-07-20-maria-agent-rag-securise-design.md`](2026-07-20-maria-agent-rag-securise-design.md)
à un déploiement en production chez ETS Maria, avec accès en lecture aux données
réelles (Sage 100, base clients, mails, contrats). Rien ci-dessous n'est
construit dans la démo actuelle : c'est la feuille de route de durcissement, pas
un état des lieux.

La démo prouve déjà **3 des 5 axes** de sécurité : isolation réseau (outsider),
capability control au niveau infra (modèle compromis), et egress strictement
contrôlé. Les deux axes restants — protection contre l'insider et le
chiffrement/l'exploitation en continu — sont hors périmètre du POC (YAGNI démo)
et détaillés ici.

## Threat model

### 1. Insider (attaque de l'intérieur)

Dans la démo, l'accès à Open WebUI se fait via un **compte de service unique**
partagé par tous les employés (`WEBUI_AUTH=true`, un seul login). C'est
suffisant pour une démo mais insuffisant en production : n'importe quel
détenteur du compte peut interroger l'intégralité des données indexées, sans
traçabilité individuelle.

Cible de production :

- **Comptes RBAC par employé**, fin des comptes de service partagés. Chaque
  employé a son identité propre dans Open WebUI (ou un IdP externe en SSO), avec
  des rôles/permissions adaptés à son périmètre métier (ex. : un technicien n'a
  pas besoin de voir les conditions commerciales négociées d'un gros compte).
- **Audit log** : qui a requêté quoi, quand, avec quel résultat retourné.
  Nécessaire pour la conformité et pour détecter un usage abusif ou une fuite
  (ex. : un employé qui exfiltre méthodiquement tout le catalogue clients via
  des requêtes RAG répétées).
- **Données en lecture seule** pour tous les rôles non-admin : aucun chemin
  d'écriture depuis l'agent vers les systèmes sources (déjà vrai en démo au
  niveau des montages `:ro`, à étendre à un vrai contrôle d'accès applicatif
  côté connecteurs).

### 2. Outsider (attaque de l'extérieur)

**Déjà démontré en démo** : isolation réseau (`net_internal` sans route
internet, `net_egress` réservé au seul `egress-proxy`), authentification sur
l'unique port publié (`WEBUI_AUTH` sur `open-webui:3000`), et egress zéro en
dehors de l'allowlist du proxy. Ces invariants sont conçus pour tenir tels quels
en production ; le travail restant est opérationnel (TLS, rotation de clés,
durcissement de l'hôte), traité en section « Exploitation » ci-dessous.

### 3. Modèle compromis (via injection de prompt ou autre)

**Déjà démontré en démo** : le principe directeur — _on ne fait pas confiance au
modèle, on contrôle ses capacités au niveau de l'infrastructure_ — est déjà
appliqué. Le toolset du modèle (`platform_toolsets.api_server`) est limité à
`[skills, todo, memory]`, sans tool `web`/`file`/`terminal` : un mail client
collé contenant une injection de prompt n'a aucun outil à détourner pour sortir
des données, et même le réseau ne le permettrait pas (aucun egress direct pour
`ollama`/`hermes`). Ce modèle de défense ne change pas en production ; il doit
être **maintenu** à mesure que de nouveaux connecteurs (Sage 100, etc.) sont
ajoutés : tout nouveau connecteur doit suivre le même principe (lecture seule,
aucun accès donné en tool direct au modèle, tout passe par un index RAG
intermédiaire).

## Limites connues de la démo à durcir en prod

- **Exfiltration DNS** : `net_internal` (`internal: true`) bloque le routage IP
  direct vers internet pour `ollama`/`hermes`, mais le résolveur DNS interne
  fourni par Docker peut, selon la configuration de l'hôte, relayer des requêtes
  DNS émises depuis un réseau interne vers l'extérieur. Le tunneling DNS
  (exfiltration de données encodées dans des sous-domaines de requêtes de
  résolution) est un canal **indépendant** du proxy HTTP/HTTPS et n'est **pas**
  couvert par l'allowlist `proxy/filter`. À tester au bring-up :
  `docker compose exec hermes nslookup <domaine-arbitraire>` doit échouer (ou à
  défaut ne renvoyer aucune résolution exploitable). Durcissement prod :
  résolveur DNS local restreint à une allowlist explicite, ou suppression pure
  et simple du besoin de résolution DNS sortante pour `hermes`/`ollama`.
- **Image `hermes-agent:local`** : construite en local
  (`docker build -t
  hermes-agent:local ~/.local/opt/hermes-agent`), ce tag
  dépend du contenu du répertoire d'installation au moment du `build` — non
  versionné, non reproductible au sens strict (deux builds à des instants
  différents peuvent produire des images différentes sans que le tag change). En
  production : publier une image Hermes dans un registre, taguée par version
  sémantique ou par digest de contenu, pour garantir traçabilité et
  reproductibilité du déploiement.

## Chiffrement at-rest

- **Volumes chiffrés** : LUKS (au niveau disque/partition) ou gocryptfs (au
  niveau répertoire) pour les volumes contenant l'index RAG, les mémoires Hermes
  (`~/.hermes/memories/`), et tout cache local de données Maria.
- **Réplica en lecture seule de Sage 100** : si un miroir/replica local de la
  base Sage 100 est nécessaire pour la synchronisation RAG (voir ci-dessous), il
  doit lui aussi résider sur un volume chiffré, jamais en clair sur disque.
- **Secrets dans un gestionnaire dédié**, pas dans `.env` : Docker secrets ou
  HashiCorp Vault (ou équivalent) pour `MARIA_API_KEY`, les identifiants du
  connecteur Sage 100, et toute clé d'API tierce (moteur de recherche web,
  etc.). Le `.env` de la démo est acceptable pour un POC de courte durée, pas
  pour une exploitation continue.

## RBAC + audit

- Intégration à un IdP (SSO d'entreprise si disponible) ou à défaut un annuaire
  de comptes nominatifs dans Open WebUI, avec rôles : `admin`, `commercial`,
  `technicien`, etc.
- Journalisation systématique : requête (prompt), documents RAG retournés,
  réponse du modèle, identité de l'employé, horodatage. Rétention définie par la
  politique de conformité de l'entreprise.
- Revue périodique des accès (qui a quel rôle, désactivation des comptes
  employés partis).

## Connecteur Sage 100 (lecture seule) + synchronisation RAG

- **Utilisateur DB dédié, lecture seule**, sans aucun droit d'écriture ni de DDL
  sur la base Sage 100. Aucune credential admin ne doit transiter par l'agent.
- **Synchronisation planifiée** (ex. : job nocturne) qui extrait les données
  pertinentes (catalogue, stocks, prix) de Sage 100 et met à jour l'index RAG
  local (la collection Knowledge, ou son équivalent en prod). Le modèle ne
  requête **jamais** Sage 100 directement — toujours via cet index
  intermédiaire, qui rejoue le principe de capability control de la Section 1 du
  design (aucun tool DB direct donné au modèle).
- **Jamais de chemin d'écriture** de l'agent vers Sage 100, à aucun niveau (ni
  via un tool, ni via le connecteur de synchronisation, qui doit être
  strictement unidirectionnel Sage 100 → index RAG).

## Exploitation (TLS, DLP, backup, monitoring)

- **TLS de bout en bout** : certificat sur `open-webui` (reverse proxy TLS
  devant le port 3000, ou terminaison TLS directe), et TLS entre les conteneurs
  internes si l'hébergement s'étend au-delà d'un hôte unique.
- **DLP (Data Loss Prevention) sur le proxy egress** : au-delà de l'allowlist de
  domaines déjà en place (`proxy/filter`), inspection du contenu sortant vers
  les domaines autorisés (ex. : détection de motifs ressemblant à des données
  clients dans les requêtes du web search) pour couvrir le cas où un domaine
  allowlisté serait lui-même compromis ou détourné.
- **Rétention et rotation des logs** : politique définie (durée de conservation,
  rotation, accès restreint aux logs d'audit).
- **Backup / DR (disaster recovery)** : sauvegarde régulière des volumes (index
  RAG, mémoires Hermes, config), testée en restauration, avec un plan de reprise
  documenté.
- **Monitoring** : santé des conteneurs, alerte sur tentative d'egress hors
  allowlist (le proxy doit logguer et idéalement alerter sur les refus), et
  disponibilité du service pour les employés.

## Hors périmètre de ce document

Ce document couvre le _quoi_ et le _pourquoi_ du durcissement ; il ne fixe pas
de calendrier ni de choix d'outillage définitif (ex. : Vault vs. Docker secrets,
SSO spécifique). Ces arbitrages se font au moment du passage en production, en
fonction de l'infrastructure existante chez ETS Maria.
