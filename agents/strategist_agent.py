"""
Agent 2 — Content Strategist.

Reçoit le résumé + idées clés de l'Agent 1 et décide :
- L'angle éditorial (what unique POV to take)
- Le hook principal (la phrase qui accroche)
- Le routing des plateformes (LinkedIn seul, Medium seul, ou les deux)
"""

from __future__ import annotations

import json
import logging
import re

from agents.base_agent import BaseAgent
from core.memory import ContentPipelineState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un stratège de contenu expert en Personal Branding pour les ingénieurs IA.
Tu analyses un résumé technique et tu définis :

1. content_angle : l'angle unique et différenciant (ex: "Comment j'ai réduit les hallucinations de 40%")
2. hook : la phrase d'accroche parfaite (max 15 mots, créer de la curiosité ou de la valeur immédiate)
3. target_audience : qui va lire ce contenu (ex: "ML engineers, 3-7 ans d'expérience")
4. linkedin_enabled : true/false (LinkedIn est-il adapté ?)
5. medium_enabled : true/false (Medium est-il adapté ?)

LinkedIn = posts courts, storytelling, engageant, émotionnel.
Medium = articles longs, techniques, approfondis, SEO.

Réponds TOUJOURS en JSON :
{
  "content_angle": "...",
  "hook": "...",
  "target_audience": "...",
  "linkedin_enabled": true,
  "medium_enabled": true,
  "rationale": "..."
}"""


class StrategistAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="StrategistAgent",
            system_prompt=SYSTEM_PROMPT,
        )

    def run(self, state: ContentPipelineState) -> ContentPipelineState:
        logger.info("[StrategistAgent] Définition de la stratégie...")

        # Le sujet utilisateur est NON NÉGOCIABLE — l'agent doit le servir, pas le réinterpréter.
        user_content = f"""
⚠️ SUJET IMPOSÉ PAR L'UTILISATEUR (priorité absolue) :
« {state.user_subject} »
Tu dois construire toute la stratégie AUTOUR de ce sujet exact. Ne le reformule pas, ne le remplace pas.

🌍 LANGUE CIBLE : {state.language} — le hook et l'angle doivent être formulés en {state.language}.

Contexte extrait de la source :
{state.ingested_summary}

Idées clés disponibles :
{chr(10).join(f"- {idea}" for idea in state.key_ideas)}

Niveau technique : {state.technical_level}

Définis la stratégie de contenu optimale en restant fidèle au sujet imposé.
"""
        messages = [{"role": "user", "content": user_content}]
        raw = self._agentic_loop(messages)

        try:
            json_match = re.search(r"\{[\s\S]*\}", raw)
            data = json.loads(json_match.group() if json_match else raw)

            state.content_angle = data.get("content_angle", "")
            state.hook = data.get("hook", "")
            state.target_audience = data.get("target_audience", "")
            state.linkedin_enabled = data.get("linkedin_enabled", True)
            state.medium_enabled = data.get("medium_enabled", True)
        except Exception as e:
            logger.error(f"[StrategistAgent] Erreur parsing: {e}")

        state.log_event(f"StrategistAgent: angle='{state.content_angle[:50]}...'")
        return state
