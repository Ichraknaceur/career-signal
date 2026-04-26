"""
Page 0 — Documentation de CareerSignal.

Vue d'ensemble, architecture, guide d'utilisation et bonnes pratiques.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

import streamlit as st

st.set_page_config(
    page_title="Documentation — CareerSignal",
    page_icon="📚",
    layout="wide",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
  .doc-hero {
    background: linear-gradient(135deg, #4338CA 0%, #7C3AED 100%);
    color: white;
    border-radius: 16px;
    padding: 36px 40px;
    margin-bottom: 28px;
  }
  .doc-hero h1 { color: white; margin: 0 0 8px 0; font-size: 2rem; }
  .doc-hero p  { color: rgba(255,255,255,0.85); margin: 0; font-size: 1.05rem; }

  .phase-card {
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 12px;
    border-left: 4px solid;
  }
  .phase-1 { background: #f0fdf4; border-color: #16a34a; }
  .phase-2 { background: #eff6ff; border-color: #2563eb; }
  .phase-3 { background: #fdf4ff; border-color: #9333ea; }
  .phase-4 { background: #fff7ed; border-color: #ea580c; }

  .phase-card h3 { margin: 0 0 6px 0; font-size: 1.05rem; }
  .phase-card p  { margin: 0; color: #475569; font-size: 0.92rem; }

  .arch-box {
    background: #1e1e2e;
    color: #cdd6f4;
    border-radius: 12px;
    padding: 24px;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.7;
  }
  .arch-box .green  { color: #a6e3a1; }
  .arch-box .blue   { color: #89dceb; }
  .arch-box .purple { color: #cba6f7; }
  .arch-box .yellow { color: #f9e2af; }
  .arch-box .red    { color: #f38ba8; }
  .arch-box .orange { color: #fab387; }

  .tip-box {
    background: #fefce8;
    border: 1px solid #fde68a;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
  }
  .warn-box {
    background: #fff1f2;
    border: 1px solid #fecdd3;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
  }
  .info-box {
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
  }
  .file-badge {
    background: #1e1e2e;
    color: #a6e3a1;
    border-radius: 6px;
    padding: 2px 8px;
    font-family: monospace;
    font-size: 12px;
  }
  .status-badge {
    border-radius: 8px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 600;
    display: inline-block;
    margin: 2px;
  }
  .s-pending  { background:#fef9c3; color:#854d0e; }
  .s-approved { background:#dcfce7; color:#166534; }
  .s-sent     { background:#dbeafe; color:#1e40af; }
  .s-accepted { background:#f0fdf4; color:#15803d; }
</style>
""",
    unsafe_allow_html=True,
)


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="doc-hero">
  <h1>📚 CareerSignal</h1>
  <p>
    Système multi-agents IA de bout en bout pour automatiser la présence professionnelle en ligne.<br>
    Génération de contenu · Planification LinkedIn · Outreach automatisé · Veille IA
  </p>
</div>
""",
    unsafe_allow_html=True,
)


# ── Tabs de la doc ────────────────────────────────────────────────────────────
tab_ov, tab_arch, tab_phases, tab_setup, tab_tips = st.tabs(
    [
        "🗺 Vue d'ensemble",
        "🏗 Architecture",
        "📖 Guide par phase",
        "⚙️ Configuration",
        "💡 Bonnes pratiques",
    ]
)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — Vue d'ensemble
# ════════════════════════════════════════════════════════════════════════════════
with tab_ov:
    st.markdown("## 🎯 Qu'est-ce que ce système ?")
    st.markdown("""
**CareerSignal** est une plateforme multi-agents IA qui automatise l'ensemble
du workflow de personal branding pour les professionnels de l'IA.

Il repose sur le principe **Human-in-the-Loop** : chaque action critique (publication,
envoi de connexion) passe par une validation manuelle avant d'être exécutée.
""")

    col1, col2, col3, col4 = st.columns(4)
    for col, icon, title, desc, cls in [
        (col1, "✍️", "Phase 1", "Génération articles Medium avec SEO", "phase-1"),
        (col2, "📅", "Phase 2", "Planification & publication LinkedIn", "phase-2"),
        (col3, "🤝", "Phase 3", "Outreach automatisé LinkedIn", "phase-3"),
        (col4, "📡", "Phase 4", "Veille IA & suggestions de posts", "phase-4"),
    ]:
        with col:
            st.markdown(
                f"<div class='phase-card {cls}'><h3>{icon} {title}</h3><p>{desc}</p></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("## 🔄 Flux de travail global")

    st.markdown("""
```
┌─────────────────────────────────────────────────────────────────┐
│                     CONTENT AGENT SYSTEM                        │
│                                                                 │
│  [Phase 4: Veille]  ──► Articles scrappés + résumés LLM        │
│         │                                                       │
│         ▼                                                       │
│  [Phase 1: Medium]  ──► Article complet SEO-optimisé           │
│         │                                                       │
│         ▼                                                       │
│  [Phase 2: Scheduler] ──► Posts LinkedIn planifiés             │
│         │                                                       │
│         ▼                                                       │
│  [Phase 3: Outreach] ──► Connexions LinkedIn personnalisées    │
│         │                                                       │
│         ▼                                                       │
│     Human Review ──► Approbation → Publication / Envoi         │
└─────────────────────────────────────────────────────────────────┘
```
""")

    st.markdown("## 📊 Stack technique")

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown("**🤖 IA & LLM**")
        st.markdown("""
- Anthropic Claude (claude-sonnet-4-6)
- OpenAI GPT-4o-mini
- Switch provider dynamique via UI
- Agents spécialisés (BaseAgent)
""")
    with col_s2:
        st.markdown("**🌐 Automation**")
        st.markdown("""
- Playwright (Chrome headless/non-headless)
- Session persistante (cookies JSON)
- Anti-détection (délais humains, webdriver spoof)
- RSS/Atom parsing + BeautifulSoup
""")
    with col_s3:
        st.markdown("**🖥 Interface & Infra**")
        st.markdown("""
- Streamlit multi-pages
- Stockage JSON local (data/)
- Docker + docker-compose
- Rate limiting (15 connexions/jour)
""")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — Architecture
# ════════════════════════════════════════════════════════════════════════════════
with tab_arch:
    st.markdown("## 🏗 Structure du projet")

    st.markdown(
        """<div class="arch-box">
<span class="blue">career-signal/</span><br>
│<br>
├── <span class="green">agents/</span>               <span style="color:#6c7086"># Agents LLM spécialisés</span><br>
│   ├── <span class="yellow">base_agent.py</span>     <span style="color:#6c7086"># Agentic loop multi-provider (Anthropic / OpenAI)</span><br>
│   ├── <span class="yellow">medium_agent.py</span>   <span style="color:#6c7086"># Rédaction d'articles Medium</span><br>
│   ├── <span class="yellow">seo_agent.py</span> / <span class="yellow">qa_judge_agent.py</span> / <span class="yellow">revision_agent.py</span><br>
│   ├── <span class="yellow">outreach_agent.py</span> <span style="color:#6c7086"># Notes de connexion LinkedIn ≤ 300 chars</span><br>
│   └── <span class="yellow">veille_agent.py</span>   <span style="color:#6c7086"># Résumés + posts LinkedIn depuis articles</span><br>
│<br>
├── <span class="green">pipelines/</span>            <span style="color:#6c7086"># Orchestration des agents</span><br>
│   ├── <span class="yellow">medium_pipeline.py</span>            <span style="color:#6c7086"># Phase 1</span><br>
│   ├── <span class="yellow">linkedin_scheduling_pipeline.py</span> <span style="color:#6c7086"># Phase 2</span><br>
│   ├── <span class="yellow">outreach_pipeline.py</span>          <span style="color:#6c7086"># Phase 3 (+ check_acceptances)</span><br>
│   └── <span class="yellow">veille_pipeline.py</span>            <span style="color:#6c7086"># Phase 4</span><br>
│<br>
├── <span class="green">tools/</span>                <span style="color:#6c7086"># Outils & persistance</span><br>
│   ├── <span class="yellow">linkedin_scraper.py</span>  <span style="color:#6c7086"># Login, search, enrich, send_connection, check_acceptance</span><br>
│   ├── <span class="yellow">linkedin_poster.py</span>   <span style="color:#6c7086"># Publication de posts via Playwright</span><br>
│   ├── <span class="yellow">outreach_store.py</span>   <span style="color:#6c7086"># CRUD JSON profils outreach</span><br>
│   ├── <span class="yellow">scheduler_tools.py</span>  <span style="color:#6c7086"># CRUD JSON posts planifiés</span><br>
│   ├── <span class="yellow">veille_store.py</span>     <span style="color:#6c7086"># CRUD JSON sources + articles</span><br>
│   └── <span class="yellow">rss_fetcher.py</span>      <span style="color:#6c7086"># Parseur RSS/Atom + scraping direct</span><br>
│<br>
├── <span class="green">core/</span>                 <span style="color:#6c7086"># Infrastructure commune</span><br>
│   ├── <span class="yellow">client.py</span>    <span style="color:#6c7086"># get_provider() + clear_provider_cache()</span><br>
│   ├── <span class="yellow">config.py</span>    <span style="color:#6c7086"># Settings (modèles, limites)</span><br>
│   └── <span class="yellow">memory.py</span>    <span style="color:#6c7086"># ContentPipelineState (état partagé)</span><br>
│<br>
├── <span class="green">ui/pages/</span>             <span style="color:#6c7086"># Interface Streamlit</span><br>
│   ├── <span class="purple">00_Documentation.py</span>    <span style="color:#6c7086"># ← Cette page</span><br>
│   ├── <span class="purple">02_LinkedIn_Scheduling.py</span><br>
│   ├── <span class="purple">03_LinkedIn_Outreach.py</span><br>
│   └── <span class="purple">04_Veille_IA.py</span><br>
│<br>
├── <span class="green">data/</span>                 <span style="color:#6c7086"># Stockage JSON (gitignored)</span><br>
│   ├── <span class="red">linkedin_cookies.json</span>  <span style="color:#6c7086"># Session LinkedIn persistante</span><br>
│   ├── <span class="red">outreach.json</span>          <span style="color:#6c7086"># Profils outreach</span><br>
│   ├── <span class="red">schedule.json</span>          <span style="color:#6c7086"># Posts planifiés</span><br>
│   ├── <span class="red">veille_sources.json</span>    <span style="color:#6c7086"># Sources RSS</span><br>
│   └── <span class="red">veille_articles.json</span>   <span style="color:#6c7086"># Articles + résumés + posts</span><br>
│<br>
├── <span class="orange">Dockerfile</span> / <span class="orange">docker-compose.yml</span><br>
├── <span class="orange">pyproject.toml</span>  <span style="color:#6c7086"># Dépendances du projet</span><br>
└── <span class="orange">.env</span>            <span style="color:#6c7086"># Clés API (ne jamais committer)</span><br>
</div>""",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("## 🔀 Pattern d'architecture : BaseAgent + Agentic Loop")
    st.code(
        """
# Chaque agent hérite de BaseAgent
class VeilleAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="VeilleAgent", system_prompt=SYSTEM_PROMPT)
        self._tools = [WRITE_SUMMARY_TOOL]   # Tools LLM

    def handle_write_summary(self, summary: str) -> dict:
        self._result = summary               # Handler appelé par le LLM
        return {"success": True}

    def summarize(self, article) -> str:
        self._agentic_loop([{"role": "user", "content": prompt}])
        return self._result

# Provider switché dynamiquement via LLM_PROVIDER env var
os.environ["LLM_PROVIDER"] = "openai"       # ou "anthropic"
clear_provider_cache()
agent = VeilleAgent()                        # Lit le provider au __init__
""",
        language="python",
    )


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — Guide par phase
# ════════════════════════════════════════════════════════════════════════════════
with tab_phases:
    # ── Phase 1 ───────────────────────────────────────────────────────────────
    with st.expander("✍️ Phase 1 — Génération d'articles Medium", expanded=True):
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown("""
**Objectif** : Générer un article complet, SEO-optimisé, prêt à publier sur Medium.

**Workflow :**
1. Renseigner le sujet / thème de l'article
2. L'agent `MediumAgent` génère titre + intro + corps + conclusion
3. L'agent `SEOAgent` optimise les keywords, meta description et structure
4. L'agent `QAJudgeAgent` évalue la qualité (score 0-10)
5. Si score < seuil → `RevisionAgent` améliore l'article
6. Export Markdown ou publication directe

**Agents impliqués :**
""")
            st.markdown("""
| Agent | Rôle |
|-------|------|
| `MediumAgent` | Rédaction complète |
| `SEOAgent` | Optimisation SEO |
| `QAJudgeAgent` | Contrôle qualité |
| `RevisionAgent` | Révision si besoin |
""")
        with col2:
            st.markdown(
                """<div class="info-box">
💡 <strong>Tip</strong> : Donne un contexte précis au lancement :<br><br>
<em>"Article technique sur les RAG pipelines pour des ingénieurs ML débutants,
1500 mots, style accessible, avec exemples de code Python"</em>
</div>
<div class="tip-box">
✅ Le pipeline MediumPipeline utilise <strong>max_revisions=2</strong> par défaut.
Tu peux augmenter pour plus de qualité (au coût de plus d'appels LLM).
</div>""",
                unsafe_allow_html=True,
            )

    # ── Phase 2 ───────────────────────────────────────────────────────────────
    with st.expander("📅 Phase 2 — Planification LinkedIn"):
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown("""
**Objectif** : Planifier et publier des posts LinkedIn depuis un calendrier éditorial.

**Workflow :**
1. L'agent génère des posts LinkedIn depuis un article Medium (ou de zéro)
2. Les posts apparaissent dans le **calendrier hebdomadaire**
3. Review manuelle : ✅ Approuver / ❌ Rejeter / ✏️ Éditer
4. Clic "Publier" → Playwright ouvre Chrome et publie le post

**Statuts des posts :**
""")
            for s, label, cls in [
                ("draft", "Brouillon généré", "s-pending"),
                ("approved", "Approuvé, prêt à publier", "s-approved"),
                ("published", "Publié sur LinkedIn", "s-sent"),
                ("rejected", "Rejeté", "s-accepted"),
            ]:
                st.markdown(
                    f"<span class='status-badge {cls}'>{s}</span> → {label}",
                    unsafe_allow_html=True,
                )
        with col2:
            st.markdown(
                """<div class="warn-box">
⚠️ <strong>Important</strong> : Renseigne tes credentials LinkedIn dans la sidebar
avant de publier. La session est persistée via cookies (tu n'as à te connecter
qu'une seule fois).
</div>
<div class="tip-box">
💡 Mode <strong>Headless = OFF</strong> recommandé pour la publication
(LinkedIn détecte plus facilement les navigateurs headless).
</div>""",
                unsafe_allow_html=True,
            )

    # ── Phase 3 ───────────────────────────────────────────────────────────────
    with st.expander("🤝 Phase 3 — LinkedIn Outreach"):
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown("""
**Objectif** : Trouver, enrichir et contacter des profils LinkedIn avec des notes personnalisées.

**Workflow en 5 étapes :**
1. **Search** : Playwright scrape les résultats de recherche LinkedIn
2. **Enrich** : Visite de chaque profil pour extraire les infos complètes
3. **Generate** : `OutreachAgent` génère une note ≤ 300 chars par profil
4. **Review** : Approuver / Rejeter / Éditer les notes dans l'UI
5. **Send** : Envoi des connexions approuvées (max 15/jour)

**Cycle de vie d'un profil :**
""")
            st.markdown("""
```
pending → approved → sent → accepted
         ↓
       rejected
```
""")
            st.markdown("""
**Suivi des acceptations :**
Bouton "🔍 Vérifier les acceptations" → visite chaque profil "sent"
et détecte si le badge de degré est passé à **1er** (= accepté).
""")
        with col2:
            st.markdown(
                """<div class="info-box">
ℹ️ <strong>Note de connexion</strong> : LinkedIn limite à <strong>300 caractères</strong>.
Le LLM est instruit de respecter cette limite strictement.
</div>
<div class="tip-box">
💡 Configure ton <strong>contexte expéditeur</strong> dans la sidebar :<br>
<em>"Je suis en fin de thèse industrielle en IA, travaux LLM/RAG..."</em><br>
Ce contexte est injecté dans chaque note générée.
</div>
<div class="warn-box">
⚠️ <strong>Limite LinkedIn</strong> : Max 15-20 connexions/jour recommandé
pour éviter la restriction de compte.
</div>""",
                unsafe_allow_html=True,
            )

    # ── Phase 4 ───────────────────────────────────────────────────────────────
    with st.expander("📡 Phase 4 — Veille IA"):
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown("""
**Objectif** : Surveiller les flux RSS IA/LLM/RAG, générer des résumés et proposer des posts LinkedIn.

**Workflow :**
1. **Sources** : 7 flux RSS pré-configurés (TDS, HuggingFace, The Batch, OpenAI, LangChain…)
2. **Fetch** : Récupération des nouveaux articles (déduplication par URL)
3. **Summarize** : Résumé LLM en français (~150 mots) par article
4. **Suggest** : Post LinkedIn engageant avec hook + contenu + hashtags
5. **Review** : Éditer et envoyer directement au **Scheduler** (Phase 2)

**Sources par défaut :**
""")
            for name in [
                "Towards Data Science",
                "The Batch (DeepLearning.AI)",
                "Hugging Face Blog",
                "OpenAI Blog",
                "LangChain Blog",
                "Google AI Blog",
                "Sebastian Raschka",
            ]:
                st.markdown(f"- {name}")
        with col2:
            st.markdown(
                """<div class="tip-box">
💡 Tu peux ajouter n'importe quel flux RSS personnalisé depuis
l'onglet <strong>Sources</strong> de la Page 4.
</div>
<div class="info-box">
🔗 <strong>Intégration Phase 2</strong> : Le bouton "📅 → Scheduler"
envoie directement le post suggéré dans le calendrier LinkedIn
(statut "approved", planifié pour demain à 9h).
</div>""",
                unsafe_allow_html=True,
            )


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — Configuration
# ════════════════════════════════════════════════════════════════════════════════
with tab_setup:
    st.markdown("## ⚙️ Configuration du système")

    st.markdown("### 1. Variables d'environnement (`.env`)")
    st.code(
        """
# ── LLM Provider ──────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...      # Clé Anthropic (Claude)
OPENAI_API_KEY=sk-...             # Clé OpenAI (GPT-4o-mini)
LLM_PROVIDER=openai               # "anthropic" ou "openai"

# ── Modèles (optionnel — valeurs par défaut) ──────────────────
# ANTHROPIC_AGENT_MODEL=claude-sonnet-4-6
# OPENAI_AGENT_MODEL=gpt-4o-mini

# ── Medium (optionnel) ────────────────────────────────────────
MEDIUM_API_TOKEN=...              # Token API Medium (publication)
""",
        language="bash",
    )

    st.markdown("### 2. Installation")
    st.code(
        """
# Cloner et installer
git clone <repo>
cd career-signal
pip install -e .

# Installer Playwright + navigateur Chromium
playwright install chromium

# Lancer l'app
streamlit run ui/app.py
""",
        language="bash",
    )

    st.markdown("### 3. Docker (recommandé)")
    st.code(
        """
# Construire et lancer
docker-compose up --build

# L'app est accessible sur http://localhost:8501
# Les données persistent dans ./data/
""",
        language="bash",
    )

    st.markdown("### 4. Changer de provider LLM")
    st.markdown("""
Tu peux changer de provider **sans redémarrer** depuis n'importe quelle page :

- Sidebar → **🤖 Provider LLM** → sélectionner Anthropic ou OpenAI

Le cache est vidé automatiquement et le nouveau provider est utilisé
pour toutes les générations suivantes.
""")

    st.markdown("### 5. Données persistantes (`data/`)")
    cols = st.columns(2)
    with cols[0]:
        st.markdown("""
| Fichier | Contenu |
|---------|---------|
| `linkedin_cookies.json` | Session LinkedIn |
| `outreach.json` | Profils outreach |
| `outreach_daily.json` | Compteur connexions/jour |
""")
    with cols[1]:
        st.markdown("""
| Fichier | Contenu |
|---------|---------|
| `schedule.json` | Posts planifiés |
| `veille_sources.json` | Sources RSS |
| `veille_articles.json` | Articles + résumés |
""")

    st.markdown(
        """<div class="warn-box">
⚠️ <strong>Sécurité</strong> : Le dossier <code>data/</code> est dans <code>.gitignore</code>.
Ne jamais committer les cookies LinkedIn, les clés API ou les données personnelles.
</div>""",
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — Bonnes pratiques
# ════════════════════════════════════════════════════════════════════════════════
with tab_tips:
    st.markdown("## 💡 Bonnes pratiques & conseils")

    col_t1, col_t2 = st.columns(2)

    with col_t1:
        st.markdown("### 🤝 LinkedIn — Outreach")
        st.markdown(
            """<div class="tip-box">
✅ <strong>Limite journalière</strong> : Ne dépasse pas 15-20 connexions/jour.
Au-delà, LinkedIn peut restreindre ton compte temporairement.
</div>
<div class="tip-box">
✅ <strong>Headless = OFF</strong> : Toujours utiliser un vrai navigateur visible pour le scraping
et l'envoi. Playwright en mode non-headless est moins détectable.
</div>
<div class="tip-box">
✅ <strong>Notes personnalisées</strong> : Une note bien ciblée (prénom + entreprise + contexte)
a un taux d'acceptation 3x supérieur à une note générique.
</div>
<div class="warn-box">
⚠️ <strong>Session expirée</strong> : Si LinkedIn te demande de re-vérifier ton compte,
les cookies sont invalides. Supprime <code>data/linkedin_cookies.json</code>
et reconnecte-toi.
</div>""",
            unsafe_allow_html=True,
        )

        st.markdown("### 📡 Veille IA")
        st.markdown(
            """<div class="tip-box">
✅ <strong>Fréquence</strong> : Lance la veille 2-3 fois par semaine pour rester à jour
sans générer trop d'articles en doublon.
</div>
<div class="tip-box">
✅ <strong>Curation</strong> : Ne publie pas tout ce que le LLM suggère — choisis les articles
les plus pertinents pour ton audience (LLM, RAG, thèse IA).
</div>
<div class="tip-box">
✅ <strong>Personnalise</strong> : Édite toujours le post suggéré avant publication.
Ajoute ta perspective personnelle — c'est ce qui engage le plus.
</div>""",
            unsafe_allow_html=True,
        )

    with col_t2:
        st.markdown("### 🤖 LLM & Provider")
        st.markdown(
            """<div class="tip-box">
✅ <strong>OpenAI pour l'outreach</strong> : GPT-4o-mini est plus rapide et moins cher
pour les notes de connexion courtes (≤ 300 chars).
</div>
<div class="tip-box">
✅ <strong>Anthropic pour les articles</strong> : Claude produit des articles plus structurés
et mieux argumentés pour les contenus longs (Medium).
</div>
<div class="info-box">
ℹ️ Si tu reçois une erreur <strong>401 invalid x-api-key</strong>, vérifie que :
<ul>
<li>La clé API est bien dans le fichier <code>.env</code></li>
<li>Le bon provider est sélectionné dans la sidebar</li>
<li>La clé n'est pas expirée ou épuisée en crédits</li>
</ul>
</div>""",
            unsafe_allow_html=True,
        )

        st.markdown("### 📝 Contenu LinkedIn")
        st.markdown(
            """<div class="tip-box">
✅ <strong>Hook fort</strong> : La première ligne est la plus importante — elle détermine
si l'utilisateur va cliquer "voir plus". Commence par une question,
un fait surprenant ou une affirmation forte.
</div>
<div class="tip-box">
✅ <strong>Hashtags</strong> : 3-5 hashtags ciblés valent mieux que 15 hashtags génériques.
Priorité à <code>#IA</code> <code>#LLM</code> <code>#RAG</code> <code>#GenAI</code>
pour ta niche.
</div>
<div class="tip-box">
✅ <strong>Fréquence de publication</strong> : 3-4 posts/semaine est optimal pour
l'algorithme LinkedIn sans saturer ton réseau.
</div>""",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### 🚀 Workflow recommandé (hebdomadaire)")
    st.markdown("""
```
Lundi matin
  └── 📡 Lancer la veille (Phase 4) → lire les résumés → sélectionner 2-3 articles

Lundi après-midi
  └── ✍️ Générer un article Medium depuis le meilleur article de veille (Phase 1)

Mardi
  └── 📅 Approuver les posts LinkedIn de la semaine dans le scheduler (Phase 2)

Mercredi / Vendredi
  └── 🤝 Lancer une campagne outreach (20 profils, notes FR, thèse IA) (Phase 3)

En continu
  └── 🔍 Vérifier les acceptations → envoyer des messages de suivi
```
""")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#94a3b8;font-size:13px;padding:10px'>"
    "CareerSignal · Built with ❤️ by Ichrak Ennaceur · "
    "Powered by Anthropic Claude & OpenAI GPT"
    "</div>",
    unsafe_allow_html=True,
)
