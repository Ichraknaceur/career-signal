"""
OutreachAgent — Phase 3.

Génère une note de connexion LinkedIn personnalisée (≤ 300 chars)
basée sur le profil LinkedIn d'une personne et le contexte de l'utilisateur.

La note doit être :
  - Personnalisée (prénom, poste, entreprise mentionnés naturellement)
  - Concise et non-commerciale (pas de pitch agressif)
  - En accord avec la langue choisie
  - ≤ 300 caractères (limite LinkedIn stricte)
"""

from __future__ import annotations

import logging

from agents.base_agent import BaseAgent
from core.memory import ContentPipelineState
from tools.outreach_store import OutreachRecord

logger = logging.getLogger(__name__)

# ── Tool definition ───────────────────────────────────────────────────────────
WRITE_NOTE_TOOL: dict = {
    "name": "write_connection_note",
    "description": (
        "Sauvegarde la note de connexion LinkedIn générée pour ce profil. "
        "Doit être ≤ 300 caractères (limite LinkedIn). "
        "Appelle ce tool UNE SEULE FOIS par profil."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "note": {
                "type": "string",
                "description": "La note de connexion personnalisée. MAX 300 caractères.",
            },
            "language": {
                "type": "string",
                "description": "Langue de la note (ex: English, French, Arabic…)",
            },
        },
        "required": ["note", "language"],
    },
}

SYSTEM_PROMPT = """Tu es un expert en networking LinkedIn professionnel.

Ta mission : rédiger des notes de connexion LinkedIn PERSONNALISÉES et AUTHENTIQUES.

Règles ABSOLUES :
1. ≤ 300 caractères STRICT (LinkedIn refuse au-delà) — compte chaque caractère.
2. Mentionner le prénom de la cible + quelque chose de spécifique (poste, entreprise, domaine).
3. Ton sincère, authentique, pas de pitch commercial.
4. Mettre en avant le contexte de l'expéditeur (thèse, projet, spécialité) de façon naturelle.
5. Pas de formules génériques ("J'aimerais rejoindre votre réseau", "Je me permets de…").
6. Terminer par un CTA ouvert et non intrusif (echanger, discuter, suivre son travail).
7. Rédige TOUJOURS dans la langue spécifiée.
8. Si l'expéditeur est en fin de thèse / chercheur : mentionner le lien avec le domaine cible.

Exemples de bonnes notes (≤ 300 chars) :
- "Bonjour Julien, en fin de thèse IA (LLMs/RAG), votre parcours chez AVISIA en conseil Data m'inspire. J'aimerais échanger sur votre expérience si vous avez un moment !"  [165 chars ✓]
- "Hi Sarah, finishing my PhD on LLM & RAG — your applied AI work at Mistral is exactly what I'm building toward. Would love to connect!"  [134 chars ✓]
- "Bonjour Marc, vos travaux sur les agents IA autonomes résonnent avec ma thèse en cours. Je serais ravie d'échanger avec vous !"  [127 chars ✓]

Appelle le tool `write_connection_note` avec la note finale."""


class OutreachAgent(BaseAgent):
    """
    Génère une note de connexion LinkedIn personnalisée pour un profil donné.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OutreachAgent",
            system_prompt=SYSTEM_PROMPT,
        )
        self._tools = [WRITE_NOTE_TOOL]
        self._generated_note: str = ""
        self._generated_language: str = "English"

    # ── Tool handler ─────────────────────────────────────────────────────────
    def handle_write_connection_note(self, note: str, language: str = "English") -> dict:
        """Handler appelé quand le LLM utilise write_connection_note."""
        note = note[:300]  # Hard limit
        self._generated_note = note
        self._generated_language = language
        logger.info(f"[OutreachAgent] Note générée — {len(note)} chars, langue={language}")
        return {
            "success": True,
            "chars": len(note),
            "language": language,
        }

    # ── Point d'entrée ────────────────────────────────────────────────────────
    def generate_note(
        self,
        record: OutreachRecord,
        sender_niche: str,
        sender_goal: str = "",
        language: str = "English",
        sender_name: str = "",
        sender_context: str = "",
    ) -> str:
        """
        Génère une note de connexion pour un OutreachRecord.

        Args:
            record          : Le profil cible (name, title, company, about)
            sender_niche    : Niche de l'expéditeur (ex: "Applied AI / Gen AI — LLM, RAG")
            sender_goal     : Objectif de connexion (optionnel si sender_context fourni)
            language        : Langue de la note
            sender_name     : Nom complet de l'expéditeur (ex: "Ichrak Ennaceur")
            sender_context  : Contexte détaillé de l'expéditeur (thèse, projet, objectif…)

        Returns:
            Note de connexion ≤ 300 chars.
        """
        self._generated_note = ""
        self._generated_language = language

        about_excerpt = record.about[:200] if record.about else "N/A"

        # Bloc contexte expéditeur
        sender_block = f"- Niche / domaine : {sender_niche}\n"
        if sender_context:
            sender_block += f"- Contexte personnel : {sender_context}\n"
        elif sender_goal:
            sender_block += f"- Objectif du réseau : {sender_goal}\n"
        if sender_name:
            sender_block += f"- Prénom/Nom expéditeur : {sender_name}\n"

        user_content = f"""
Génère une note de connexion LinkedIn personnalisée (≤ 300 caractères) pour ce profil :

=== PROFIL CIBLE ===
Prénom/Nom  : {record.name}
Poste       : {record.title}
Entreprise  : {record.company}
Localisation: {record.location}
À propos    : {about_excerpt}

=== EXPÉDITEUR ===
{sender_block}
=== INSTRUCTIONS ===
Langue de la note : {language}
Limite STRICTE : ≤ 300 caractères (compte précisément).
Mentionne le prénom de la cible et son entreprise/domaine spécifique.
Si l'expéditeur est en thèse IA/LLM/RAG : exploite ce contexte comme point commun.
Termine par une invitation à échanger, naturelle et non intrusive.

Appelle `write_connection_note` avec la note finale.
"""
        messages = [{"role": "user", "content": user_content}]
        try:
            self._agentic_loop(messages)
        except RuntimeError as e:
            logger.error(f"[OutreachAgent] Erreur agentic loop: {e}")

        if not self._generated_note:
            # Fallback si le tool n'a pas été appelé
            fallback = (
                f"Hi {record.name.split()[0]}, I came across your profile "
                f"and your work in {record.title} really resonated with me. "
                f"Would love to connect!"
            )[:300]
            logger.warning("[OutreachAgent] Fallback note utilisée")
            return fallback

        return self._generated_note

    def run(self, state: ContentPipelineState) -> ContentPipelineState:
        """Interface BaseAgent — non utilisé directement."""
        logger.warning("[OutreachAgent] .run() appelé directement — utilise .generate_note().")
        return state
