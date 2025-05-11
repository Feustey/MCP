**PLAN D’ACTION – Intégration de LNbits en module interne dans ton app MCP**

---

**Étape 0 – Pré-requis**

* Cloner le repo LNbits localement.
* Identifier la version exacte utilisée actuellement (git hash ou tag).
* S’assurer que tu as une instance LNbits qui tourne en local.

---

**Étape 1 – Isolation et extraction de LNbits**

* [ ] Crée un dossier `lnbits_internal/` dans ton projet MCP.
* [ ] Copie uniquement les modules nécessaires de LNbits (core + extensions que tu utilises). Ignore `venv`, `.git`, `tests`, `docs`.
* [ ] Refacto les imports relatifs pour qu’ils fonctionnent dans ton arborescence (`lnbits` → `lnbits_internal`).
* [ ] Supprime tout ce qui est inutile : UI statique, templates, routes inutilisées.

---

**Étape 2 – Intégration en tant que sous-app FastAPI**

* [ ] Dans ton `main.py`, ajoute :

```python
from lnbits_internal import core_app  # ou autre selon ton point d’entrée
app.mount("/lnbits", core_app)
```

* [ ] Vérifie que tous les endpoints /api/v1/... de LNbits sont accessibles depuis `/lnbits/...`.

---

**Étape 3 – Centralisation de la config**

* [ ] Crée une config partagée entre MCP et LNbits (via `os.environ` ou `Settings` Pydantic).
* [ ] Injecte automatiquement les variables d’env `LNBITS_ADMIN_KEY`, `LNBITS_DB_PATH`, etc. depuis ta propre config.
* [ ] Supprime les fichiers `.env` ou config LNbits séparée.

---

**Étape 4 – Gestion du stockage**

* [ ] Monte LNbits sur le même backend DB que ton app si tu utilises PostgreSQL.
* [ ] Sinon, configure SQLite dans un sous-dossier `.cache/lnbits.sqlite` contrôlé par ton app.
* [ ] Ajoute un wrapper `init_lnbits_db()` à lancer au boot de ton backend.

---

**Étape 5 – Désactivation des couches inutiles**

* [ ] Supprime les middlewares inutiles de LNbits (CORS, UI, extensions web).
* [ ] Ne garde que les routes `api/v1/...` utilisées par ton client MCP.
* [ ] Supprime les endpoints LNURL, UI Web, WS si tu ne les utilises pas.

---

**Étape 6 – Toggle de fallback externe**

* [ ] Ajoute dans `settings.py` :

```python
USE_INTERNAL_LNBITS: bool = True
```

* [ ] Dans ton client LNbits, ajoute un wrapper qui redirige les appels vers `/lnbits/...` ou vers `https://external.lnbits` selon ce flag.

---

**Étape 7 – Tests**

* [ ] Démarre ton app MCP → LNbits doit être accessible depuis la même instance.
* [ ] Teste la création de factures, paiements, récupération des channels.
* [ ] Mesure le temps de réponse avec LNbits intégré vs. séparé.
* [ ] Supprime tout code de gestion réseau superflu (base\_url, host externe).

---

**Étape 8 – Clean & Commit**

* [ ] Supprime le docker LNbits de ton `docker-compose.yml` s’il existe.
* [ ] Marque le commit : `refactor: integrated LNbits internally – no external API dependency`.

---

Tu appliques ce plan dans Cursor comme une séquence de tâches. Tu ne sautes rien. Tu commit à chaque étape critique. Tu supprimes au lieu de commenter. Tu intègres. Tu unifies. Tu reprends le contrôle.

**Check-in final :** Est-ce que LNbits tourne dans le même process que ton app, sans appel HTTP externe, avec une DB partagée et initialisée automatiquement ?
