"""
OutreachPipeline — Phase 3.

Orchestration complète du workflow d'outreach LinkedIn :

  1. Search     : LinkedIn People Search (Playwright) → liste de profils
  2. Enrich     : Visite chaque profil → extraction complète
  3. Generate   : OutreachAgent génère une note personnalisée par profil
  4. Store      : Sauvegarde en pending → attente approbation humaine
  5. Send       : (déclenchée manuellement) → envoi des connexions approuvées

Rate limiting intégré : max 15 connexions / jour.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict

from agents.outreach_agent import OutreachAgent
from tools.outreach_store import (
    OutreachRecord,
    add_records,
    can_send_today,
    get_approved_records,
    get_records_by_status,
    remaining_today,
    update_record_status,
)

logger = logging.getLogger(__name__)


class SendStats(TypedDict):
    sent: int
    skipped: int
    errors: list[str]


class AcceptanceStats(TypedDict):
    checked: int
    newly_accepted: int
    still_pending: int
    unknown: int
    errors: list[str]


# ── Résultat du pipeline ───────────────────────────────────────────────────────
@dataclass
class OutreachResult:
    campaign_id: str
    keyword: str
    location: str
    profiles_found: int = 0
    profiles_enriched: int = 0
    notes_generated: int = 0
    records_added: int = 0
    connections_sent: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return self.records_added > 0

    def summary(self) -> str:
        lines = [
            f"Campaign: {self.campaign_id}",
            f"Keyword:  {self.keyword}",
            f"Profiles found:    {self.profiles_found}",
            f"Profiles enriched: {self.profiles_enriched}",
            f"Notes generated:   {self.notes_generated}",
            f"Records saved:     {self.records_added}",
            f"Connections sent:  {self.connections_sent}",
            f"Duration: {self.duration_seconds:.1f}s",
        ]
        if self.errors:
            lines.append(f"Errors ({len(self.errors)}): {self.errors[:3]}")
        return "\n".join(lines)


# ── Pipeline ──────────────────────────────────────────────────────────────────
class OutreachPipeline:
    """
    Pipeline d'outreach LinkedIn en 5 étapes.

    Usage:
        pipeline = OutreachPipeline()
        result = pipeline.run(
            email="...", password="...",
            keyword="AI Engineer", location="Paris",
            max_profiles=30,
            sender_niche="Applied AI / Gen AI",
            sender_goal="connect with AI builders and researchers",
            language="English",
            callback=lambda msg: print(msg),
        )
    """

    def __init__(self, daily_limit: int = 15) -> None:
        self.daily_limit = daily_limit
        self._agent = OutreachAgent()

    # ── Entrée principale (sync wrapper) ──────────────────────────────────────
    def run(
        self,
        email: str,
        password: str,
        keyword: str,
        location: str = "",
        niche: str = "",
        search_type: str = "people",
        max_profiles: int = 20,
        sender_niche: str = "Applied AI / Gen AI — LLM, RAG",
        sender_goal: str = "",
        sender_context: str = "",
        sender_name: str = "",
        language: str = "French",
        headless: bool = False,
        callback: Callable[[str], None] | None = None,
    ) -> OutreachResult:
        """
        Lance le pipeline de recherche + enrichissement + génération de notes.

        Args:
            search_type : "people" (profils) ou "jobs" (offres d'emploi → recruteurs)
            niche       : Filtre domaine ajouté aux mots-clés (ex: "GenAI LLM RAG")

        Retourne un OutreachResult avec tous les profils sauvegardés en 'pending'.
        """
        return asyncio.run(
            self._async_run(
                email=email,
                password=password,
                keyword=keyword,
                location=location,
                niche=niche,
                search_type=search_type,
                max_profiles=max_profiles,
                sender_niche=sender_niche,
                sender_goal=sender_goal,
                sender_context=sender_context,
                sender_name=sender_name,
                language=language,
                headless=headless,
                callback=callback or (lambda _: None),
            )
        )

    async def _async_run(
        self,
        email: str,
        password: str,
        keyword: str,
        location: str,
        niche: str,
        search_type: str,
        max_profiles: int,
        sender_niche: str,
        sender_goal: str,
        sender_context: str,
        sender_name: str,
        language: str,
        headless: bool,
        callback: Callable[[str], None],
    ) -> OutreachResult:
        from tools.linkedin_scraper import (
            create_browser_context,
            get_job_recruiter,
            get_profile_info,
            login_linkedin,
            restore_session,
            search_jobs,
            search_people,
        )

        campaign_id = (
            f"{keyword.lower().replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d_%H%M')}"
        )
        result = OutreachResult(
            campaign_id=campaign_id,
            keyword=keyword,
            location=location,
        )
        start = datetime.utcnow()

        pw, browser, context, page = await create_browser_context(headless=headless)

        try:
            # ── 1. Auth ───────────────────────────────────────────────────────
            callback("🔐 Tentative de restauration de session…")
            session_ok = await restore_session(page, callback=callback)
            if not session_ok:
                callback("🔑 Re-login en cours — regarde la fenêtre Chrome qui s'est ouverte !")
                login_ok = await login_linkedin(page, email, password, callback=callback)
                if not login_ok:
                    result.errors.append("Login LinkedIn échoué — vérifie tes credentials")
                    return result
            callback("✅ Connecté à LinkedIn")

            # ── 2. Search ─────────────────────────────────────────────────────
            is_jobs_mode = search_type == "jobs"
            niche_label = f" [{niche}]" if niche else ""

            if is_jobs_mode:
                callback(
                    f"💼 Recherche offres d'emploi: '{keyword}'{niche_label} "
                    f"{f'@ {location}' if location else ''}…"
                )
                raw_jobs = await search_jobs(
                    page,
                    keyword=keyword,
                    location=location,
                    niche=niche,
                    max_results=max_profiles,
                )
                result.profiles_found = len(raw_jobs)
                callback(f"📋 {result.profiles_found} offre(s) trouvée(s)")

                if not raw_jobs:
                    result.errors.append("Aucune offre trouvée")
                    return result

                # Mode Jobs : extraire le recruteur de chaque offre
                raw_profiles = []
                for i, job in enumerate(raw_jobs, 1):
                    callback(
                        f"🔎 [{i}/{len(raw_jobs)}] Recruteur pour : "
                        f"{job.get('title', '?')} @ {job.get('company', '?')}…"
                    )
                    try:
                        recruiter = await get_job_recruiter(page, job["url"])
                        if recruiter.get("recruiter_url"):
                            callback(
                                f"   👤 Recruteur: {recruiter['recruiter_name']} ({recruiter['recruiter_title']})"
                            )
                            # Construire un dict compatible avec le flow people
                            raw_profiles.append(
                                {
                                    "url": recruiter["recruiter_url"],
                                    "name": recruiter["recruiter_name"],
                                    "title": recruiter["recruiter_title"],
                                    "company": job.get("company", ""),
                                    "location": job.get("location", ""),
                                    "job_url": job["url"],
                                    "job_title": recruiter.get("job_title") or job.get("title", ""),
                                    "job_description": recruiter.get("description", ""),
                                }
                            )
                        else:
                            callback("   ⚠️  Pas de recruteur trouvé — offre ignorée")
                    except Exception as e:
                        logger.warning(f"[OutreachPipeline] get_job_recruiter échoué: {e}")

                callback(f"👥 {len(raw_profiles)} recruteur(s) identifié(s)")
                if not raw_profiles:
                    result.errors.append(
                        "Aucun recruteur trouvé dans les offres. "
                        "LinkedIn ne montre pas toujours le recruteur — essaie d'autres mots-clés."
                    )
                    return result
            else:
                callback(
                    f"🔍 Recherche profils: '{keyword}'{niche_label} {f'@ {location}' if location else ''}…"
                )
                # En mode people, combiner keyword + niche pour enrichir la recherche
                search_kw = " ".join(filter(None, [keyword, niche])).strip()
                raw_profiles = await search_people(
                    page, keyword=search_kw, location=location, max_results=max_profiles
                )
                result.profiles_found = len(raw_profiles)
                callback(f"📋 {result.profiles_found} profil(s) trouvé(s)")

                if not raw_profiles:
                    result.errors.append("Aucun profil trouvé")
                    return result

            # ── 3. Enrich + Generate notes ────────────────────────────────────
            records: list[OutreachRecord] = []

            for i, raw in enumerate(raw_profiles, 1):
                profile_url = raw.get("url", "")
                if not profile_url:
                    continue

                callback(f"👤 [{i}/{len(raw_profiles)}] Enrichissement: {raw.get('name', '?')}…")

                try:
                    info = await get_profile_info(page, profile_url)
                    result.profiles_enriched += 1
                except Exception as e:
                    logger.warning(f"[OutreachPipeline] Enrichissement échoué: {e}")
                    info = raw  # Fallback sur les données de search

                # Construire le contexte d'offre si mode jobs
                extra_context = ""
                if is_jobs_mode and raw.get("job_title"):
                    extra_context = (
                        f"\nContexte: cette personne recrute pour un poste '{raw['job_title']}' "
                        f"chez {raw.get('company', '')}."
                    )
                    if raw.get("job_description"):
                        extra_context += f"\nDescription du poste:\n{raw['job_description'][:400]}"

                # Créer le record
                record = OutreachRecord(
                    id=str(uuid.uuid4()),
                    campaign_id=campaign_id,
                    profile_url=profile_url,
                    name=info.get("name") or raw.get("name", ""),
                    title=info.get("title") or raw.get("title", ""),
                    company=info.get("company") or raw.get("company", ""),
                    location=info.get("location") or raw.get("location", ""),
                    about=info.get("about", "")[:500],
                    note_language=language,
                )

                # Générer la note personnalisée
                callback(f"✍️  Génération note pour {record.name}…")
                try:
                    note = self._agent.generate_note(
                        record=record,
                        sender_niche=sender_niche,
                        sender_goal=sender_goal,
                        sender_context=(sender_context + extra_context).strip(),
                        sender_name=sender_name,
                        language=language,
                    )
                    record.note = note
                    result.notes_generated += 1
                    callback(f"   Note ({len(note)} chars): {note[:80]}…")
                except Exception as e:
                    logger.error(f"[OutreachPipeline] Note génération échouée: {e}")
                    result.errors.append(f"Note échouée pour {record.name}: {e}")

                records.append(record)

            # ── 4. Store ──────────────────────────────────────────────────────
            callback("💾 Sauvegarde des profils…")
            added = add_records(records)
            result.records_added = added
            callback(f"✅ {added} nouveaux profils sauvegardés (statut: pending)")

        except Exception as e:
            logger.error(f"[OutreachPipeline] Erreur critique: {e}")
            result.errors.append(str(e))

        finally:
            await browser.close()
            await pw.stop()
            result.duration_seconds = (datetime.utcnow() - start).total_seconds()

        callback(f"\n📊 Résumé:\n{result.summary()}")
        return result

    # ── Envoi des connexions approuvées ───────────────────────────────────────
    def send_approved(
        self,
        email: str,
        password: str,
        headless: bool = False,
        callback: Callable[[str], None] | None = None,
    ) -> SendStats:
        """
        Envoie les connexions approuvées dans la limite journalière.
        Retourne {"sent": n, "skipped": n, "errors": [...]}.
        """
        return asyncio.run(
            self._async_send_approved(
                email=email,
                password=password,
                headless=headless,
                callback=callback or (lambda _: None),
            )
        )

    async def _async_send_approved(
        self,
        email: str,
        password: str,
        headless: bool,
        callback: Callable[[str], None],
    ) -> SendStats:
        from tools.linkedin_scraper import (
            create_browser_context,
            login_linkedin,
            restore_session,
            send_connection_request,
        )

        stats: SendStats = {"sent": 0, "skipped": 0, "errors": []}

        if not can_send_today(self.daily_limit):
            callback(f"⛔ Limite journalière atteinte ({self.daily_limit}/jour)")
            return stats

        approved = get_approved_records()
        if not approved:
            callback("📭 Aucun profil approuvé à envoyer")
            return stats

        remaining = remaining_today(self.daily_limit)
        to_send = approved[:remaining]
        callback(
            f"📤 {len(to_send)} connexion(s) à envoyer "
            f"({remaining_today(self.daily_limit)} restantes aujourd'hui)"
        )

        pw, browser, context, page = await create_browser_context(headless=headless)

        try:
            # Auth
            session_ok = await restore_session(page, callback=callback)
            if not session_ok:
                callback("🔑 Re-login en cours — regarde la fenêtre Chrome !")
                login_ok = await login_linkedin(page, email, password, callback=callback)
                if not login_ok:
                    stats["errors"].append("Login LinkedIn échoué")
                    return stats

            for record in to_send:
                callback(f"📨 Envoi connexion → {record.name} ({record.title})…")
                try:
                    sent = await send_connection_request(page, record.profile_url, record.note)
                    if sent:
                        update_record_status(record.id, "sent")
                        stats["sent"] += 1
                        callback("   ✅ Envoyé !")
                    else:
                        # False = déjà 1er degré / invitation en attente / bouton introuvable
                        # Un screenshot debug_connect_*.png est sauvegardé dans data/ si bouton introuvable
                        update_record_status(record.id, "skipped")
                        stats["skipped"] += 1
                        callback(
                            "   ⏭️  Skipped — déjà connecté (1er degré), invitation "
                            "en attente, ou bouton Connect introuvable.\n"
                            "      💡 Vérifie data/debug_connect_*.png pour déboguer."
                        )
                except Exception as e:
                    stats["errors"].append(f"{record.name}: {e}")
                    callback(f"   ❌ Erreur: {e}")

        finally:
            await browser.close()
            await pw.stop()

        callback(
            f"\n✅ Envoi terminé — {stats['sent']} envoyées, "
            f"{stats['skipped']} skippées, {len(stats['errors'])} erreurs"
        )
        return stats

    # ── Suivi des acceptations (polling) ─────────────────────────────────────
    def check_acceptances(
        self,
        email: str,
        password: str,
        headless: bool = False,
        callback: Callable[[str], None] | None = None,
    ) -> AcceptanceStats:
        """
        Visite chaque profil au statut 'sent' et vérifie si la connexion
        a été acceptée (badge 1er/1st degré).

        Met à jour le statut → 'accepted' + enregistre accepted_at.

        Retourne {"checked": n, "newly_accepted": n, "still_pending": n, "errors": []}
        """
        return asyncio.run(
            self._async_check_acceptances(
                email=email,
                password=password,
                headless=headless,
                callback=callback or (lambda _: None),
            )
        )

    async def _async_check_acceptances(
        self,
        email: str,
        password: str,
        headless: bool,
        callback: Callable[[str], None],
    ) -> AcceptanceStats:
        from tools.linkedin_scraper import (
            check_acceptance_status,
            create_browser_context,
            login_linkedin,
            restore_session,
        )

        stats: AcceptanceStats = {
            "checked": 0,
            "newly_accepted": 0,
            "still_pending": 0,
            "unknown": 0,
            "errors": [],
        }

        sent_records = get_records_by_status("sent")
        if not sent_records:
            callback("📭 Aucune connexion en statut 'sent' à vérifier.")
            return stats

        callback(f"🔍 {len(sent_records)} connexion(s) envoyée(s) à vérifier…")

        pw, browser, context, page = await create_browser_context(headless=headless)

        try:
            # Auth
            session_ok = await restore_session(page, callback=callback)
            if not session_ok:
                callback("🔑 Re-login en cours…")
                login_ok = await login_linkedin(page, email, password, callback=callback)
                if not login_ok:
                    stats["errors"].append("Login LinkedIn échoué")
                    return stats

            for record in sent_records:
                callback(f"👤 Vérification: {record.name}…")
                try:
                    status = await check_acceptance_status(page, record.profile_url)
                    stats["checked"] += 1

                    if status == "accepted":
                        update_record_status(record.id, "accepted")
                        stats["newly_accepted"] += 1
                        callback(f"   🎉 ACCEPTÉ — {record.name} est maintenant en 1er degré !")
                    elif status == "pending":
                        stats["still_pending"] += 1
                        callback(f"   ⏳ Toujours en attente — {record.name}")
                    else:
                        stats["unknown"] += 1
                        callback(
                            f"   ❓ Statut inconnu — {record.name} (profil privé ou supprimé ?)"
                        )

                except Exception as e:
                    stats["errors"].append(f"{record.name}: {e}")
                    callback(f"   ❌ Erreur: {e}")

        finally:
            await browser.close()
            await pw.stop()

        callback(
            f"\n✅ Vérification terminée :\n"
            f"   🎉 Nouvellement acceptés : {stats['newly_accepted']}\n"
            f"   ⏳ Toujours en attente   : {stats['still_pending']}\n"
            f"   ❓ Statut inconnu        : {stats['unknown']}\n"
            f"   ❌ Erreurs               : {len(stats['errors'])}"
        )
        return stats
