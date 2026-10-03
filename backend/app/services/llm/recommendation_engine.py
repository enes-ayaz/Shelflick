import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional
import httpx
from openai import AsyncOpenAI
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.media import MediaItem
from app.models.user_media import UserMedia, WatchStatus
from app.schemas.unified_media import UnifiedMediaDTO
from app.services.llm.prompts import (
    INTENT_PARSING_SYSTEM_PROMPT,
    RERANKING_JUSTIFICATION_SYSTEM_PROMPT,
)
from app.services.llm.schemas import (
    RecommendationResponse,
    RecommendationResult,
    SingleRecommendation,
    UserIntentFilter,
    UserLibraryProfile,
)
from app.services.media_aggregator import MediaAggregatorService

logger = logging.getLogger(__name__)


class LLMClient:
    """Multi-provider asynchronous LLM client supporting Google Gemini and OpenAI compatible APIs."""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.gemini_api_key = gemini_api_key or settings.GEMINI_API_KEY
        self.openai_api_key = openai_api_key or settings.OPENAI_API_KEY
        self.openai_base_url = openai_base_url or settings.OPENAI_BASE_URL
        self.model_name = model_name or settings.LLM_MODEL
        self._openai_client: Optional[AsyncOpenAI] = None

    def _get_openai_client(self) -> Optional[AsyncOpenAI]:
        """Lazy-loads an AsyncOpenAI client instance."""
        if self._openai_client is None and self.openai_api_key:
            self._openai_client = AsyncOpenAI(
                api_key=self.openai_api_key,
                base_url=self.openai_base_url,
            )
        return self._openai_client

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """Dispatches JSON prompt to configured LLM (Gemini REST, OpenAI, or smart heuristic fallback)."""
        # 1. Try Google Gemini REST API if GEMINI_API_KEY is present
        if self.gemini_api_key:
            try:
                return await self._call_gemini_rest(system_prompt, user_prompt)
            except Exception as exc:
                logger.warning("Gemini REST API invocation failed, falling back: %s", exc)

        # 2. Try OpenAI compatible API if OPENAI_API_KEY is present
        openai_cli = self._get_openai_client()
        if openai_cli:
            try:
                return await self._call_openai(openai_cli, system_prompt, user_prompt)
            except Exception as exc:
                logger.warning("OpenAI API invocation failed, falling back: %s", exc)

        # 3. Fallback heuristic engine if no keys configured or external call fails
        logger.info("Using smart local heuristic fallback for LLM response generation.")
        return self._heuristic_fallback(system_prompt, user_prompt)

    async def _call_gemini_rest(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Calls Google Gemini v1beta generateContent endpoint with JSON response mime type."""
        model = self.model_name if "gemini" in self.model_name else "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": settings.LLM_TEMPERATURE,
            },
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw_text)

    async def _call_openai(
        self,
        client: AsyncOpenAI,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """Calls OpenAI or compatible endpoint enforcing JSON format."""
        model = self.model_name if not self.model_name.startswith("gemini") else "gpt-4o-mini"
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=settings.LLM_TEMPERATURE,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    def _heuristic_fallback(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Deterministic heuristic fallback when external LLM API is rate-limited or unavailable."""
        # Stage A: Intent Parsing Fallback
        if "Niyet Analizi" in system_prompt or "Intent Parsing" in system_prompt:
            p_lower = user_prompt.lower()
            media_type = "ALL"
            if "[anime]" in p_lower or "anime" in p_lower:
                media_type = "ANIME"
            elif "[series]" in p_lower or "dizi" in p_lower or "series" in p_lower:
                media_type = "SERIES"
            elif "[movie]" in p_lower or "film" in p_lower or "movie" in p_lower or "sinema" in p_lower:
                media_type = "MOVIE"

            # Clean prefixes like [ANIME], [MOVIE], etc.
            clean_text = re.sub(r"\[(ALL|ANIME|MOVIE|SERIES)\]", "", user_prompt, flags=re.IGNORECASE).strip()
            clean_lower = clean_text.lower()

            moods = []
            for m in ["karanlık", "dark", "gerilim", "melankolik", "hüzünlü", "komik", "eğlenceli", "romantik"]:
                if m in clean_lower:
                    moods.append(m)

            themes = []
            for t in ["psikolojik", "cyberpunk", "intikam", "zaman yolculuğu", "bilim kurgu", "distopya", "aksiyon", "macera"]:
                if t in clean_lower:
                    themes.append(t)

            excluded = []
            for e in ["shounen", "klişe", "arkadaşlık gücü", "harem"]:
                if e in clean_lower:
                    excluded.append(f"{e} klişesi")

            ref_titles = []
            match_like = re.search(r"(\w+)\s+(gibi|tarzı)", clean_text, re.IGNORECASE)
            if match_like:
                ref_titles.append(match_like.group(1))

            # Detect direct title search:
            # If user used command words (izle, bul, seyret) OR user typed a short specific query (<= 5 words) without complex descriptor phrases
            has_complex_descriptors = bool(len(moods) >= 2 or len(themes) >= 2 or ref_titles or excluded)
            word_count = len(clean_text.split())
            is_direct = bool(re.search(r"\b(izle|bul|seyret)\b", clean_lower)) or (not has_complex_descriptors and 1 <= word_count <= 5)

            if is_direct:
                direct_title = re.sub(r"\b(izle|bul|seyret)\b", "", clean_text, flags=re.IGNORECASE).strip()
            else:
                direct_title = None

            return {
                "is_direct_title_search": is_direct,
                "direct_title": direct_title,
                "media_type_filter": media_type,
                "mood_keywords": moods if moods else (["sürükleyici"] if not is_direct else []),
                "target_themes": themes if themes else (["derin kurgu"] if not is_direct else []),
                "excluded_tropes": excluded,
                "reference_titles": ref_titles,
            }

        # Stage B: Re-ranking Fallback
        lines = user_prompt.split("\n")
        candidates_info = []
        for line in lines:
            m = re.search(r"ID:\s*([A-Za-z0-9_-]+)\s*\|\s*Başlık:\s*([^|\(]+)", line)
            if m:
                cand_id = m.group(1).strip()
                cand_title = m.group(2).strip()
                candidates_info.append((cand_id, cand_title))

        prompt_m = re.search(r"KULLANICI İSTEMİ:\s*([^\n]+)", user_prompt)
        prompt_str = prompt_m.group(1).strip() if prompt_m else ""
        clean_prompt = re.sub(r"\[(ALL|ANIME|MOVIE|SERIES)\]", "", prompt_str, flags=re.IGNORECASE).strip()

        # If direct title match exists, put it first
        if clean_prompt:
            clean_p_lower = clean_prompt.lower()
            for idx, (c_id, c_title) in enumerate(candidates_info):
                if clean_p_lower in c_title.lower() or c_title.lower() in clean_p_lower:
                    match_item = candidates_info.pop(idx)
                    candidates_info.insert(0, match_item)
                    break

        recommendations_list = []
        for rank, (c_id, c_title) in enumerate(candidates_info[:5], 1):
            if rank == 1 and clean_prompt and (clean_prompt.lower() in c_title.lower() or c_title.lower() in clean_prompt.lower()):
                just = f"Doğrudan aradığın '{c_title}', yüksek puanı ve güçlü atmosferiyle listenin 1. sırasındaki yapımdır."
            elif rank == 1:
                just = f"Aradığın temayı en dengeli ve sürükleyici şekilde işleyen '{c_title}', zevkine tam oturacak öncelikli bir başyapıttır."
            elif rank == 2:
                just = f"'{c_title}', benzer tonları ve derin kurgusuyla alternatifler arasında öne çıkan çarpıcı bir yapımdır."
            elif rank == 3:
                just = f"Farklı bir anlatım arayanlar için '{c_title}', güçlü karakter dinamikleri ve temposuyla dikkat çeker."
            elif rank == 4:
                just = f"Kurgusal derinliği ve yüksek temposuyla '{c_title}', aradığın hissi tamamlayacak niteliktedir."
            else:
                just = f"Türün en özgün eserlerinden biri olan '{c_title}', keşif sepetine eklemen gereken sürpriz bir öneridir."

            recommendations_list.append({
                "selected_external_id": c_id,
                "confidence_score": round(0.98 - (rank - 1) * 0.03, 2),
                "justification_text": just,
            })

        first_rec = recommendations_list[0] if recommendations_list else {"selected_external_id": "none", "confidence_score": 0.0, "justification_text": "Öneri bulunamadı."}
        return {
            "recommendations": recommendations_list,
            "selected_external_id": first_rec["selected_external_id"],
            "confidence_score": first_rec["confidence_score"],
            "justification_text": first_rec["justification_text"],
        }


# Quick keyword mapping from Turkish search intents to international API keywords
TR_EN_KEYWORD_MAP: Dict[str, str] = {
    "karanlık": "dark",
    "psikolojik": "psychological",
    "gerilim": "thriller",
    "korku": "horror",
    "bilim kurgu": "sci-fi",
    "distopya": "dystopian",
    "cyberpunk": "cyberpunk",
    "intikam": "revenge",
    "aksiyon": "action",
    "macera": "adventure",
    "gizem": "mystery",
    "dram": "drama",
    "komedi": "comedy",
    "romantik": "romance",
    "fantastik": "fantasy",
    "zaman yolculuğu": "time travel",
    "derin kurgu": "psychological thriller",
}


class RecommendationEngine:
    """Core recommendation pipeline: Intent Parsing -> Candidate Retrieval -> Re-ranking & Justification."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        aggregator_service: Optional[MediaAggregatorService] = None,
    ) -> None:
        self.llm = llm_client or LLMClient()
        self.aggregator = aggregator_service or MediaAggregatorService()

    @staticmethod
    def _translate_keywords(keywords: List[str]) -> List[str]:
        """Translates Turkish mood and theme keywords to English for external API search."""
        translated: List[str] = []
        for kw in keywords:
            kw_clean = kw.lower().strip()
            if kw_clean in TR_EN_KEYWORD_MAP:
                translated.append(TR_EN_KEYWORD_MAP[kw_clean])
            else:
                translated.append(kw_clean)
        return translated

    async def parse_intent(self, user_prompt: str) -> UserIntentFilter:
        """Stage A: Extracts structured intent and search parameters from natural language."""
        raw_json = await self.llm.generate_json(
            system_prompt=INTENT_PARSING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        return UserIntentFilter.model_validate(raw_json)

    async def get_user_profile(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> UserLibraryProfile:
        """Retrieves user's Gold List (favorites) and Red List (dropped media)."""
        stmt = (
            select(UserMedia, MediaItem)
            .join(MediaItem, UserMedia.media_id == MediaItem.id)
            .where(UserMedia.user_id == user_id)
        )
        result = await session.execute(stmt)
        entries = result.all()

        gold_list: List[str] = []
        red_list: List[str] = []
        completed_titles: List[str] = []
        completed_ids: List[str] = []

        for user_media, media_item in entries:
            # COMPLETED: Exclude already watched titles from recommendation pool
            if user_media.status == WatchStatus.COMPLETED:
                completed_titles.append(media_item.title)
                completed_ids.append(str(media_item.external_id))

            # Gold List: is_favorite == True or user_score >= 9.0
            if user_media.is_favorite or (user_media.user_score and user_media.user_score >= 9.0):
                note = f" (Not: {user_media.personal_notes})" if user_media.personal_notes else ""
                gold_list.append(f"{media_item.title} [{media_item.media_source}]{note}")

            # Red List: status == DROPPED or user_score <= 4.0
            if user_media.status == WatchStatus.DROPPED or (user_media.user_score and user_media.user_score <= 4.0):
                reason = f" (Neden: {user_media.drop_reason})" if user_media.drop_reason else ""
                red_list.append(f"{media_item.title} [{media_item.media_source}]{reason}")

        return UserLibraryProfile(
            user_id=user_id,
            gold_list=gold_list,
            red_list=red_list,
            completed_titles=completed_titles,
            completed_ids=completed_ids,
        )

    async def fetch_candidates(
        self,
        intent: UserIntentFilter,
        user_prompt: str,
        limit: int = 15,
        session: Optional[AsyncSession] = None,
        red_list_titles: Optional[List[str]] = None,
        excluded_titles: Optional[List[str]] = None,
        excluded_ids: Optional[List[str]] = None,
    ) -> List[UnifiedMediaDTO]:
        """Fetches potential candidates from MediaAggregator and local database matching intent."""
        # 1. Determine provider routing based on media_type_filter
        enable_tmdb = intent.media_type_filter in ("ALL", "MOVIE", "SERIES")
        enable_anilist = intent.media_type_filter in ("ALL", "ANIME")

        # Clean prompt by stripping tags like [ANIME], [MOVIE], [SERIES]
        clean_user_prompt = re.sub(r"\[(ALL|ANIME|MOVIE|SERIES)\]", "", user_prompt, flags=re.IGNORECASE).strip()

        # 2. Formulate search query with international API keyword translation
        if intent.is_direct_title_search and intent.direct_title:
            search_query = intent.direct_title
        elif intent.reference_titles:
            ref = intent.reference_titles[0]
            trans_themes = self._translate_keywords(intent.target_themes)
            search_query = f"{ref} {' '.join(trans_themes)}"
        elif clean_user_prompt and len(clean_user_prompt.split()) <= 4:
            search_query = clean_user_prompt
        elif intent.target_themes or intent.mood_keywords:
            raw_keywords = intent.target_themes + intent.mood_keywords
            trans_keywords = self._translate_keywords(raw_keywords)
            search_query = trans_keywords[0] if trans_keywords else clean_user_prompt
        else:
            search_query = clean_user_prompt or user_prompt

        # 3. Query MediaAggregator
        candidates = await self.aggregator.search_all(
            query=search_query,
            enable_tmdb=enable_tmdb,
            enable_anilist=enable_anilist,
            per_source_limit=limit,
        )

        # Fallback if first search returned no candidates
        if not candidates and (intent.target_themes or intent.mood_keywords):
            for fallback_kw in self._translate_keywords(intent.mood_keywords + intent.target_themes):
                if fallback_kw == search_query:
                    continue
                candidates = await self.aggregator.search_all(
                    query=fallback_kw,
                    enable_tmdb=enable_tmdb,
                    enable_anilist=enable_anilist,
                    per_source_limit=limit,
                )
                if candidates:
                    break

        # 4. Only augment with local database records if external candidate search yielded nothing
        if not candidates and session:
            try:
                db_stmt = select(MediaItem).order_by(desc(MediaItem.site_score)).limit(10)
                db_res = await session.execute(db_stmt)
                db_items = db_res.scalars().all()
                for d in db_items:
                    dto = UnifiedMediaDTO(
                        external_id=d.external_id,
                        source=d.media_source.value,
                        title=d.title,
                        original_title=d.original_title,
                        release_year=d.release_year,
                        poster_url=d.poster_url,
                        synopsis=d.synopsis,
                        genres=d.genres or [],
                        themes=d.themes or [],
                        base_score=d.site_score or d.imdb_score or 0.0,
                        vote_count=d.site_vote_count,
                    )
                    candidates.append(dto)
            except Exception as exc:
                logger.debug("Local database candidate fetch skipped: %s", exc)

        # 5. Filter out titles explicitly completed or dropped by user
        if excluded_ids:
            excluded_id_set = {str(eid) for eid in excluded_ids}
            candidates = [c for c in candidates if str(c.external_id) not in excluded_id_set]

        if excluded_titles:
            excluded_titles_lower = {t.lower().strip() for t in excluded_titles}
            candidates = [c for c in candidates if c.title.lower().strip() not in excluded_titles_lower]

        if red_list_titles:
            red_lower = {r.lower() for r in red_list_titles}
            candidates = [c for c in candidates if not any(c.title.lower() in r for r in red_lower)]

        return candidates[:limit]

    async def rerank_and_justify(
        self,
        user_prompt: str,
        intent: UserIntentFilter,
        candidates: List[UnifiedMediaDTO],
        user_profile: UserLibraryProfile,
        media_type: Optional[str] = None,
    ) -> RecommendationResult:
        """Stage B: Calls LLM to evaluate candidates against user profile and output 'Neden Bu?' justification."""
        if not candidates:
            return RecommendationResult(
                selected_external_id="none",
                confidence_score=0.0,
                justification_text="Aramanıza ve zevkinize uygun kriterlerde bir yapım bulunamadı.",
            )

        # Construct candidate summaries for the prompt
        cand_summaries: List[str] = []
        for idx, c in enumerate(candidates, 1):
            cand_summaries.append(
                f"{idx}. ID: {c.external_id} | Başlık: {c.title} ({c.release_year or 'N/A'}) | Kaynak: {c.source}\n"
                f"   Türler: {', '.join(c.genres)} | Temalar: {', '.join(c.themes)}\n"
                f"   Puan: {c.base_score} | Özet: {c.synopsis[:200]}..."
            )

        candidates_block = "\n\n".join(cand_summaries)
        gold_block = "\n".join(user_profile.gold_list) if user_profile.gold_list else "Belirtilmemiş."
        red_block = "\n".join(user_profile.red_list) if user_profile.red_list else "Belirtilmemiş."
        excluded_block = ", ".join(intent.excluded_tropes) if intent.excluded_tropes else "Yok."

        media_type_constraint = ""
        effective_mt = media_type or (intent.media_type_filter if intent.media_type_filter != "ALL" else None)
        if effective_mt:
            mt_norm = effective_mt.upper().strip()
            if mt_norm in ("MOVIE", "FILM"):
                media_type_constraint = (
                    "\n\n🚨 KESİNLİKLE ZORUNLU TÜR KURALI: Kullanıcı sadece MOVIE (Film) istiyor! "
                    "Kesinlikle dizi veya anime önerme. Önerilen 5 yapımın tamamı istisnasız sinema filmi (MOVIE) olmalıdır."
                )
            elif mt_norm in ("TV", "SERIES", "DIZI"):
                media_type_constraint = (
                    "\n\n🚨 KESİNLİKLE ZORUNLU TÜR KURALI: Kullanıcı sadece SERIES (Dizi) istiyor! "
                    "Kesinlikle sinema filmi veya anime önerme. Önerilen 5 yapımın tamamı istisnasız dizi (SERIES) olmalıdır."
                )
            elif mt_norm in ("ANIME",):
                media_type_constraint = (
                    "\n\n🚨 KESİNLİKLE ZORUNLU TÜR KURALI: Kullanıcı sadece ANIME istiyor! "
                    "Kesinlikle standart batı sinema filmi veya batı dizisi önerme. Önerilen 5 yapımın tamamı istisnasız ANIME olmalıdır."
                )

        user_content = (
            f"KULLANICI İSTEMİ: {user_prompt}\n\n"
            f"İSTENMEYEN KLİŞELER / TROPELER: {excluded_block}\n\n"
            f"KULLANICININ ALTIN LİSTESİ (FAVORİLER):\n{gold_block}\n\n"
            f"KULLANICININ KIRMIZI LİSTESİ (DROPPED / BIRAKILANLAR):\n{red_block}\n\n"
            f"ADAY YAPIMLAR LİSTESİ:\n{candidates_block}\n\n"
            "GÖREV: Yukarıdaki adaylar arasından en uygun ve birbirinden farklı TAM OLARAK 5 YAPIMIN external_id değerini seç. "
            "Her bir yapım için AYRI AYRI maksimum 2 cümlelik, sinopsis içermeyen, kullanıcının zevkine atıfta bulunan "
            "'Neden Bu?' gerekçesini üret ve JSON 'recommendations' listesi olarak döndür."
            f"{media_type_constraint}"
        )

        raw_result = await self.llm.generate_json(
            system_prompt=RERANKING_JUSTIFICATION_SYSTEM_PROMPT,
            user_prompt=user_content,
        )
        return RecommendationResult.model_validate(raw_result)

    async def recommend(
        self,
        prompt: str,
        user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None,
        limit: int = 10,
        media_type: Optional[str] = None,
    ) -> RecommendationResponse:
        """Executes the full two-stage AI recommendation pipeline."""
        # Stage A: Intent Parsing
        intent = await self.parse_intent(prompt)

        # Enforce media_type filter if explicitly passed
        if media_type:
            mt_norm = media_type.upper().strip()
            if mt_norm in ("MOVIE", "FILM"):
                intent.media_type_filter = "MOVIE"
            elif mt_norm in ("TV", "SERIES", "DIZI"):
                intent.media_type_filter = "SERIES"
            elif mt_norm in ("ANIME",):
                intent.media_type_filter = "ANIME"
            elif mt_norm in ("ALL", "HEPSI", "TUMU"):
                intent.media_type_filter = "ALL"

        logger.info("Parsed user intent (media_type_filter=%s): %s", intent.media_type_filter, intent.model_dump())

        # Load user taste profile if user_id & DB session available (fault tolerant)
        user_profile = UserLibraryProfile()
        if user_id and session:
            try:
                user_profile = await self.get_user_profile(session, user_id)
            except Exception as e:
                logger.warning("Could not load user library profile from database: %s", e)

        # Retrieve candidates (strictly excluding COMPLETED titles/IDs)
        candidates = await self.fetch_candidates(
            intent=intent,
            user_prompt=prompt,
            limit=limit,
            session=session,
            red_list_titles=user_profile.red_list,
            excluded_titles=user_profile.completed_titles,
            excluded_ids=user_profile.completed_ids,
        )

        # Enforce strict type isolation on candidates if filtered
        if intent.media_type_filter == "MOVIE":
            candidates = [c for c in candidates if c.source == "TMDB_MOVIE"]
        elif intent.media_type_filter == "SERIES":
            candidates = [c for c in candidates if c.source == "TMDB_SERIES"]
        elif intent.media_type_filter == "ANIME":
            candidates = [c for c in candidates if c.source == "ANILIST"]

        # Direct title exact match check:
        clean_user_prompt = re.sub(r"\[(ALL|ANIME|MOVIE|SERIES)\]", "", prompt, flags=re.IGNORECASE).strip()
        search_target = (intent.direct_title or clean_user_prompt).lower().strip()

        best_match = None
        if intent.is_direct_title_search and candidates:
            # 1. Exact match
            best_match = next((c for c in candidates if c.title.lower().strip() == search_target), None)
            if not best_match:
                # 2. Substring match
                best_match = next((c for c in candidates if search_target in c.title.lower() or c.title.lower() in search_target), None)

        if best_match:
            remaining_cands = [c for c in candidates if str(c.external_id) != str(best_match.external_id)]
            eval_candidates = [best_match] + remaining_cands
        else:
            eval_candidates = candidates

        # Stage B: Re-ranking and Justification
        ranking_result = await self.rerank_and_justify(
            user_prompt=prompt,
            intent=intent,
            candidates=eval_candidates,
            user_profile=user_profile,
            media_type=media_type,
        )

        candidate_map = {str(c.external_id): c for c in eval_candidates}
        final_recommendations: List[SingleRecommendation] = []
        seen_ids = set()

        if best_match:
            final_recommendations.append(
                SingleRecommendation(
                    media=best_match,
                    justification=f"Doğrudan aradığın '{best_match.title}' yapımını senin için bulduk. Aradığın atmosferi ve hikayeyi tam olarak karşılayan birincil önerimizdir.",
                    confidence_score=1.0,
                )
            )
            seen_ids.add(str(best_match.external_id))

        # Add items selected by LLM re-ranking
        for rec in ranking_result.recommendations:
            rec_id = str(rec.selected_external_id)
            if rec_id in candidate_map and rec_id not in seen_ids:
                media_item = candidate_map[rec_id]
                just_text = rec.justification_text.strip() if rec.justification_text else ""
                if not just_text:
                    just_text = f"'{media_item.title}', kurgusal derinliği ve türündeki başarısıyla aradığın deneyimi sunacaktır."
                final_recommendations.append(
                    SingleRecommendation(
                        media=media_item,
                        justification=just_text,
                        confidence_score=rec.confidence_score or 0.95,
                    )
                )
                seen_ids.add(rec_id)
                if len(final_recommendations) >= 5:
                    break

        # Fallback / fill to ensure exactly 5 items if more candidates are available
        for c in eval_candidates:
            if len(final_recommendations) >= 5:
                break
            c_id = str(c.external_id)
            if c_id not in seen_ids:
                rank_num = len(final_recommendations) + 1
                genre_str = ", ".join(c.genres[:2]) if c.genres else "başarılı"
                if rank_num == 2:
                    just = f"'{c.title}', {genre_str} türündeki güçlü anlatımı ve {c.base_score} puanıyla listenin en dikkat çekici alternatifidir. Sürükleyici temposu arayışına tam uyum sağlar."
                elif rank_num == 3:
                    just = f"Farklı bir derinlik arayanlar için '{c.title}', özgün karakter dinamikleriyle öne çıkar. Tematik örgüsü zevkine hitap edecek zengin bir deneyim sunar."
                elif rank_num == 4:
                    just = f"Kurgusal başarısı ve yüksek seyir zevkiyle '{c.title}', keşif listeni zenginleştirecek harika bir yapımdır. Beklentini fazlasıyla karşılayacak niteliktedir."
                else:
                    just = f"Türün en beğenilen yapımlarından biri olan '{c.title}', mutlaka şans vermen gereken sürpriz bir öneridir. Atmosferiyle seni hemen etkisi altına alacaktır."

                final_recommendations.append(
                    SingleRecommendation(
                        media=c,
                        justification=just,
                        confidence_score=round(0.92 - (rank_num - 1) * 0.03, 2),
                    )
                )
                seen_ids.add(c_id)

        first_rec = final_recommendations[0] if final_recommendations else None
        return RecommendationResponse(
            recommendations=final_recommendations,
            recommended_media=first_rec.media if first_rec else None,
            justification=first_rec.justification if first_rec else "Öneri bulunamadı.",
            confidence_score=first_rec.confidence_score if first_rec else 0.0,
            parsed_intent=intent,
            candidates_count=len(candidates),
            all_candidates=candidates,
        )

    async def get_random_masterpiece(
        self,
        user_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None,
        media_type: Optional[str] = None,
    ) -> RecommendationResponse:
        """Provides a serendipitous 'Şansıma Güveniyorum' high-scoring recommendation,

        filtering out titles already present in the user's library and selecting randomly
        from paginated top-rated pools matching the optional media_type.
        """
        import random
        selected_dto: Optional[UnifiedMediaDTO] = None
        user_saved_titles: set[str] = set()

        norm_mt = media_type.upper().strip() if media_type else None
        if norm_mt in ("FILM", "MOVIE"):
            target_filter = "MOVIE"
        elif norm_mt in ("TV", "SERIES", "DIZI"):
            target_filter = "SERIES"
        elif norm_mt in ("ANIME",):
            target_filter = "ANIME"
        else:
            target_filter = "ALL"

        if user_id and session:
            try:
                user_items_stmt = (
                    select(MediaItem.title, MediaItem.external_id)
                    .join(UserMedia, UserMedia.media_id == MediaItem.id)
                    .where(UserMedia.user_id == user_id)
                )
                user_res = await session.execute(user_items_stmt)
                for row in user_res.all():
                    user_saved_titles.add(row[0].lower())
                    user_saved_titles.add(str(row[1]))
            except Exception as e:
                logger.warning("Failed to fetch user library in get_random_masterpiece: %s", e)

        if session:
            try:
                # 1. Query random high-scoring item from database (>= 7.8)
                stmt = select(MediaItem).where(
                    func.coalesce(MediaItem.site_score, MediaItem.imdb_score, 0.0) >= 7.8
                )
                if target_filter == "MOVIE":
                    stmt = stmt.where(MediaItem.media_source == MediaSource.TMDB_MOVIE)
                elif target_filter == "SERIES":
                    stmt = stmt.where(MediaItem.media_source == MediaSource.TMDB_SERIES)
                elif target_filter == "ANIME":
                    stmt = stmt.where(MediaItem.media_source == MediaSource.ANILIST)

                if user_id:
                    subquery = select(UserMedia.media_id).where(UserMedia.user_id == user_id)
                    stmt = stmt.where(MediaItem.id.not_in(subquery))

                stmt = stmt.order_by(func.random()).limit(1)
                res = await session.execute(stmt)
                item = res.scalars().first()
                if item:
                    selected_dto = UnifiedMediaDTO(
                        external_id=item.external_id,
                        source=item.media_source.value,
                        title=item.title,
                        original_title=item.original_title,
                        release_year=item.release_year,
                        poster_url=item.poster_url,
                        synopsis=item.synopsis,
                        genres=item.genres or [],
                        themes=item.themes or [],
                        base_score=item.site_score or item.imdb_score or 8.5,
                        vote_count=item.site_vote_count or item.imdb_vote_count,
                    )
            except Exception as exc:
                logger.warning("Database query in get_random_masterpiece skipped due to error: %s", exc)

        # 2. If not found in DB, pull randomized high-rated masterpieces from external pool
        if not selected_dto:
            pool = await self.aggregator.get_random_masterpieces(limit=25, media_type=target_filter)
            # Filter out any title user already has in library
            valid_pool = [
                m for m in pool
                if m.title.lower() not in user_saved_titles and m.external_id not in user_saved_titles
            ]
            if valid_pool:
                selected_dto = random.choice(valid_pool)
            elif pool:
                selected_dto = random.choice(pool)
            else:
                if target_filter == "MOVIE":
                    selected_dto = UnifiedMediaDTO(
                        external_id="157336",
                        source="TMDB_MOVIE",
                        title="Interstellar",
                        release_year=2014,
                        poster_url="https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
                        synopsis="The adventures of a group of explorers who make use of a newly discovered wormhole...",
                        genres=["Adventure", "Drama", "Science Fiction"],
                        themes=["space exploration", "time dilation"],
                        base_score=8.7,
                        vote_count=35000,
                    )
                elif target_filter == "SERIES":
                    selected_dto = UnifiedMediaDTO(
                        external_id="1396",
                        source="TMDB_SERIES",
                        title="Breaking Bad",
                        release_year=2008,
                        poster_url="https://image.tmdb.org/t/p/w500/ztkUQFLlC19CCMYHW9o1zWhJvUj.jpg",
                        synopsis="A chemistry teacher diagnosed with inoperable lung cancer turns to manufacturing methamphetamine...",
                        genres=["Drama", "Crime"],
                        themes=["drugs", "moral descent"],
                        base_score=9.5,
                        vote_count=13000,
                    )
                else:
                    selected_dto = UnifiedMediaDTO(
                        external_id="16498",
                        source="ANILIST",
                        title="Attack on Titan",
                        release_year=2013,
                        poster_url="https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx16498-C6FPmWm59CyP.jpg",
                        synopsis="Centuries ago mankind was almost slaughtered by titans...",
                        genres=["Action", "Drama", "Fantasy"],
                        themes=["post-apocalyptic", "military"],
                        base_score=8.5,
                        vote_count=500000,
                    )

        genre_text = ", ".join(selected_dto.genres[:2]) if selected_dto.genres else "etkileyici"
        justification = (
            f"Kritiklerde ve toplulukta {selected_dto.base_score} puan ortalaması yakalayan {selected_dto.title}, "
            f"{genre_text} türünde çıtayı yukarı taşıyan, hiç düşünmeden başlayabileceğin birinci sınıf bir başyapıttır."
        )

        intent = UserIntentFilter(
            is_direct_title_search=False,
            media_type_filter=target_filter,
            mood_keywords=["başyapıt", "şaheser"],
        )

        return RecommendationResponse(
            recommendations=[
                SingleRecommendation(
                    media=selected_dto,
                    justification=justification,
                    confidence_score=0.98,
                )
            ],
            recommended_media=selected_dto,
            justification=justification,
            confidence_score=0.98,
            parsed_intent=intent,
            candidates_count=1,
            all_candidates=[selected_dto],
        )
