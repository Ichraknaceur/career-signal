"""
LinkedIn Poster — Phase 3.

Publie un post sur LinkedIn via Playwright.

Stealth identique au scraper :
  - Session persistante via cookies
  - Délais humains aléatoires
  - Headless=False recommandé

Flow de publication :
  1. Naviguer sur /feed
  2. Cliquer "Start a post" / "Créer un post" → ouvre la modal
  3. Taper le contenu (avec hashtags en fin)
  4. Cliquer "Post" / "Publier"
  5. Attendre confirmation

Implémentation avec Playwright locator API — plus robuste que CSS selectors
statiques qui deviennent obsolètes à chaque mise à jour de LinkedIn.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from collections.abc import Callable

logger = logging.getLogger(__name__)

LINKEDIN_BASE = "https://www.linkedin.com"

# ── Regex pour les labels LinkedIn (FR + EN) ──────────────────────────────────
_START_POST_RE = re.compile(
    r"Créer un post|Start a post|Rédiger.*post|Commencer.*post|"
    r"Partagez.*article|Qu.*voulez.*parler|What.*talk about",
    re.IGNORECASE,
)
_SUBMIT_POST_RE = re.compile(r"^(Publier|Post)$", re.IGNORECASE)


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _human_delay(min_s: float = 1.0, max_s: float = 3.0) -> None:
    await asyncio.sleep(random.uniform(min_s, max_s))


async def _find_start_post_btn(page):
    """
    Cherche le bouton 'Start a post' / 'Créer un post' avec plusieurs stratégies.
    Retourne un locator cliquable ou None.
    """
    # Stratégie 1 : get_by_role button avec regex FR+EN
    loc = page.get_by_role("button", name=_START_POST_RE)
    try:
        count = await loc.count()
        for i in range(count):
            btn = loc.nth(i)
            if await btn.is_visible():
                return btn
    except Exception:
        pass

    # Stratégie 2 : chercher le placeholder "De quoi voulez-vous parler ?"
    # LinkedIn affiche parfois un input/div cliquable dans le feed
    for sel in [
        '[data-placeholder*="voulez-vous parler"]',
        '[data-placeholder*="talk about"]',
        '[placeholder*="voulez-vous parler"]',
        '[placeholder*="talk about"]',
        ".share-box-feed-entry__trigger",
        ".share-box-feed-entry__closed-share-box",
        '[data-control-name="share_panel"]',
    ]:
        try:
            el = await page.wait_for_selector(sel, timeout=3000)
            if el and await el.is_visible():
                return el
        except Exception:
            continue

    # Stratégie 3 : get_by_text partiel
    try:
        txt_loc = page.get_by_text(re.compile(r"voulez-vous parler|talk about", re.I))
        if await txt_loc.count() > 0:
            el = txt_loc.first
            if await el.is_visible():
                return el
    except Exception:
        pass

    return None


async def _find_textarea(page):
    """
    Cherche le champ de saisie du post après ouverture de la modal.
    Retourne un locator ou None.
    """
    # Stratégie 1 : div contenteditable dans la modal
    for sel in [
        'div[role="textbox"][contenteditable="true"]',
        'div[contenteditable="true"][data-placeholder]',
        '.ql-editor[contenteditable="true"]',
        'div[aria-label*="text editor"]',
        'div[aria-label*="éditeur de texte"]',
    ]:
        try:
            el = await page.wait_for_selector(sel, timeout=5000)
            if el and await el.is_visible():
                return el
        except Exception:
            continue

    # Stratégie 2 : locator par rôle textbox
    try:
        tb = page.get_by_role("textbox")
        count = await tb.count()
        for i in range(count):
            t = tb.nth(i)
            if await t.is_visible():
                return t
    except Exception:
        pass

    return None


# ── Publication principale ────────────────────────────────────────────────────
async def post_to_linkedin(
    page,
    content: str,
    hashtags: list[str] | None = None,
) -> bool:
    """
    Publie un post sur LinkedIn.

    Args:
        page     : Page Playwright authentifiée (session active requise)
        content  : Corps du post (≤ 1300 chars)
        hashtags : Liste de hashtags (ex: ["#ai", "#genai"])

    Returns:
        True si publié avec succès, False sinon.
    """
    # Assemblage du texte complet
    full_text = content.strip()
    if hashtags:
        full_text += "\n\n" + " ".join(hashtags)

    try:
        # 1. Naviguer sur le feed
        logger.info("[Poster] Navigation sur le feed LinkedIn…")
        await page.goto(f"{LINKEDIN_BASE}/feed", wait_until="domcontentloaded")
        await _human_delay(2, 4)

        # 2. Ouvrir la modal "Start a post"
        logger.info("[Poster] Recherche du bouton de création de post…")
        start_btn = await _find_start_post_btn(page)
        if not start_btn:
            logger.error("[Poster] Bouton 'Créer un post / Start a post' introuvable")
            return False

        await start_btn.click()
        logger.info("[Poster] Modal de post ouverte")
        await _human_delay(1.5, 3)

        # 3. Localiser la zone de texte
        logger.info("[Poster] Recherche de la zone de texte…")
        textarea = await _find_textarea(page)
        if not textarea:
            logger.error("[Poster] Zone de texte introuvable après ouverture de la modal")
            return False

        # 4. Taper le contenu (saisie humaine ligne par ligne)
        await textarea.click()
        await _human_delay(0.5, 1)

        lines = full_text.split("\n")
        for i, line in enumerate(lines):
            if line:
                await page.keyboard.type(line, delay=random.randint(20, 60))
            if i < len(lines) - 1:
                await page.keyboard.press("Enter")
                await asyncio.sleep(random.uniform(0.05, 0.15))

        logger.info(f"[Poster] Texte saisi ({len(full_text)} chars)")
        await _human_delay(1, 2.5)

        # 5. Cliquer "Post" / "Publier" via locator
        logger.info("[Poster] Envoi du post…")
        submit_loc = page.get_by_role("button", name=_SUBMIT_POST_RE)
        submitted = False
        try:
            sc = await submit_loc.count()
            for i in range(sc):
                s = submit_loc.nth(i)
                if await s.is_visible() and await s.is_enabled():
                    await s.click()
                    submitted = True
                    break
        except Exception:
            pass

        if not submitted:
            # Fallback CSS selectors
            for sel in [
                ".share-actions__primary-action",
                'button[aria-label*="Publier"]',
                'button[aria-label*="Post"]',
            ]:
                try:
                    el = await page.wait_for_selector(sel, timeout=4000)
                    if el and await el.is_visible():
                        await el.click()
                        submitted = True
                        break
                except Exception:
                    continue

        if not submitted:
            logger.error("[Poster] Bouton 'Post / Publier' introuvable")
            return False

        # 6. Attendre la confirmation (disparition de la modal)
        await _human_delay(2, 4)

        # Vérifier que la modal est fermée (signe de succès)
        modal_open = await page.query_selector(
            '.share-creation-state__content, [class*="share-creation"]'
        )
        if modal_open:
            logger.warning("[Poster] La modal est encore ouverte — possible échec")
            return False

        logger.info("[Poster] ✅ Post publié avec succès")
        return True

    except Exception as e:
        logger.error(f"[Poster] Erreur lors de la publication: {e}")
        return False


# ── Point d'entrée autonome ───────────────────────────────────────────────────
async def publish_post_with_session(
    email: str,
    password: str,
    content: str,
    hashtags: list[str] | None = None,
    headless: bool = False,
    callback=None,
) -> bool:
    """
    Publie un post LinkedIn en gérant la session complète.
    Wrappeur complet utilisable depuis le pipeline.

    Returns:
        True si publié avec succès.
    """
    from tools.linkedin_scraper import (
        create_browser_context,
        login_linkedin,
        restore_session,
    )

    pw, browser, context, page = await create_browser_context(headless=headless)
    try:
        # Auth
        session_ok = await restore_session(page)
        if not session_ok:
            if callback:
                callback("🔑 Session expirée — re-login…")
            login_ok = await login_linkedin(page, email, password, callback=callback)
            if not login_ok:
                logger.error("[Poster] Authentification LinkedIn échouée")
                return False

        # Publication
        return await post_to_linkedin(page, content, hashtags)

    finally:
        await browser.close()
        await pw.stop()


async def publish_posts_with_session(
    email: str,
    password: str,
    posts: list[dict],
    headless: bool = True,
    callback: Callable[[str], None] | None = None,
    delay_between_posts_s: float = 5.0,
) -> list[dict]:
    """
    Publie plusieurs posts dans une seule session LinkedIn.

    Chaque élément de `posts` doit contenir :
      - id
      - content
      - hashtags (optionnel)
    """
    from tools.linkedin_scraper import (
        create_browser_context,
        login_linkedin,
        restore_session,
    )

    results: list[dict] = []
    pw, browser, context, page = await create_browser_context(headless=headless)

    try:
        if callback:
            callback("🔐 Connexion à LinkedIn…")

        session_ok = await restore_session(page)
        if not session_ok:
            if callback:
                callback("🔑 Session expirée — re-login…")
            login_ok = await login_linkedin(page, email, password, callback=callback)
            if not login_ok:
                error = "Authentification LinkedIn échouée"
                logger.error("[Poster] %s", error)
                return [{"id": post.get("id"), "success": False, "error": error} for post in posts]

        for i, post in enumerate(posts, 1):
            post_id = post.get("id")
            content = post.get("content", "")
            hashtags = post.get("hashtags") or []

            if callback:
                callback(f"📤 [{i}/{len(posts)}] Publication du post {post_id}…")

            try:
                success = await post_to_linkedin(page, content, hashtags)
                result = {"id": post_id, "success": success}
                if not success:
                    result["error"] = "Échec de publication LinkedIn"
                results.append(result)
            except Exception as e:
                logger.error("[Poster] Erreur batch post %s: %s", post_id, e)
                results.append({"id": post_id, "success": False, "error": str(e)})

            if i < len(posts):
                await asyncio.sleep(delay_between_posts_s)

        return results

    finally:
        await browser.close()
        await pw.stop()
