import asyncio
import json
import logging
import random
import re
import uuid
from typing import Any, Dict, List, Optional
import httpx
from openai import AsyncOpenAI
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.media import MediaItem, MediaSource
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

# Quick keyword mapping from Turkish search intents to international API keywords
TR_EN_KEYWORD_MAP: Dict[str, str] = {
    "karanlık": "dark",
    "psikolojik": "psychological",
    "gerilim": "thriller",
    "korku": "horror",
    "bilim kurgu": "science fiction",
    "distopya": "dystopian",
    "distopik": "dystopian",
    "siber-punk": "cyberpunk",
    "cyberpunk": "cyberpunk",
    "intikam": "revenge",
    "aksiyon": "action",
    "macera": "adventure",
    "gizem": "mystery",
    "dram": "drama",
    "komedi": "comedy",
    "romantik": "romance",
    "fantastik": "fantasy",
    "fantezi": "fantasy",
    "zaman yolculuğu": "time travel",
    "zaman bükücü": "time travel",
    "uzay": "space",
    "rüya": "dream",
    "suç": "crime",
    "dedektif": "mystery",
    "melankoli": "melancholic",
    "melankolik": "melancholic",
    "ahlaki çöküş": "crime",
    "kimlik buhranı": "psychological",
    "twist": "thriller",
    "animasyon": "animation",
    "kahraman": "action",
    "derin kurgu": "psychological",
    "tarih": "history",
    "tarihi": "historical",
    "tarihsel": "history",
    "dönem": "period",
    "orta çağ": "medieval",
    "antik": "ancient",
    "savaş": "war",
    "askeri": "military",
    "biyografi": "biography",
    "biyografik": "biography",
    "western": "western",
    "kovboy": "western",
    "belgesel": "documentary",
}

KNOWN_MOVIE_TITLES = {
    "fight club",
    "interstellar",
    "inception",
    "the matrix",
    "matrix",
    "the dark knight",
    "pulp fiction",
    "parasite",
    "dune",
    "whiplash",
    "se7en",
    "gladiator",
    "the prestige",
    "memento",
    "the godfather",
    "the shawshank redemption",
    "blade runner 2049",
    "arrival",
    "shutter island",
    "no country for old men",
    "oldboy",
    "eternal sunshine of the spotless mind",
    "the silence of the lambs",
    "mad max",
    "prisoners",
    "gone girl",
    "joker",
    "oppenheimer",
    "inglourious basterds",
    "requiem for a dream",
    "donnie darko",
    "schindler's list",
    "schindlers list",
    "the pianist",
    "1917",
    "saving private ryan",
    "braveheart",
}

KNOWN_SERIES_TITLES = {
    "breaking bad",
    "game of thrones",
    "dark",
    "chernobyl",
    "severance",
    "better call saul",
    "mr. robot",
    "mr robot",
    "true detective",
    "stranger things",
    "black mirror",
    "arcane",
    "band of brothers",
    "vikings",
    "peaky blinders",
}

KNOWN_ANIME_TITLES = {
    "monster",
    "attack on titan",
    "shingeki no kyojin",
    "steins;gate",
    "steins gate",
    "cowboy bebop",
    "death note",
    "fullmetal alchemist",
    "fullmetal alchemist: brotherhood",
    "fullmetal alchemist brotherhood",
    "vinland saga",
    "neon genesis evangelion",
    "evangelion",
    "hunter x hunter",
    "jujutsu kaisen",
    "demon slayer",
    "kimetsu no yaiba",
    "berserk",
    "naruto",
    "one piece",
    "bleach",
    "spirited away",
}


def _normalize_title(t: str) -> str:
    """Normalizes title string by stripping punctuation, extra whitespace, and casing."""
    return re.sub(r"[^\w\s]", "", t).lower().strip()


class LLMClient:
    """Multi-provider asynchronous LLM client supporting Google Gemini, OpenAI, and diverse heuristic fallback."""

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
        if self._openai_client is None and self.openai_api_key:
            self._openai_client = AsyncOpenAI(
                api_key=self.openai_api_key,
                base_url=self.openai_base_url,
                timeout=3.5,
            )
        return self._openai_client

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """Dispatches JSON prompt to configured LLM with strict timeout, falling back to fast heuristic engine."""
        if self.gemini_api_key:
            try:
                return await asyncio.wait_for(
                    self._call_gemini_rest(system_prompt, user_prompt),
                    timeout=3.5,
                )
            except Exception as exc:
                logger.warning("Gemini REST API invocation failed/timed out, using fast fallback: %s", exc)

        openai_cli = self._get_openai_client()
        if openai_cli:
            try:
                return await asyncio.wait_for(
                    self._call_openai(openai_cli, system_prompt, user_prompt),
                    timeout=3.5,
                )
            except Exception as exc:
                logger.warning("OpenAI API invocation failed/timed out, using fast fallback: %s", exc)

        logger.info("Using smart local heuristic fallback for LLM response generation.")
        return self._heuristic_fallback(system_prompt, user_prompt)

    async def _call_gemini_rest(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
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

        async with httpx.AsyncClient(timeout=3.5) as client:
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
        """Smart, diverse, score-and-relevance weighted fallback that avoids repeating 'Monster'."""
        if "Niyet Analizi" in system_prompt or "Intent Parsing" in system_prompt:
            return RecommendationEngine._fast_local_intent_parser(user_prompt).model_dump()

        # Parse candidates block from Stage B prompt
        blocks = re.split(r"\n(?=\d+\.\s*ID:)", user_prompt)
        candidates_info: List[Dict[str, Any]] = []
        for block in blocks:
            m_head = re.search(
                r"ID:\s*([^\s|]+)\s*\|\s*Başlık:\s*([^|\(\n]+)(?:\((\d{4}|N/A)\))?\s*\|\s*Kaynak:\s*([A-Z_]+)",
                block,
            )
            if not m_head:
                m_simple = re.search(r"ID:\s*([A-Za-z0-9_-]+)\s*\|\s*Başlık:\s*([^|\(\n]+)", block)
                if m_simple:
                    candidates_info.append({
                        "id": m_simple.group(1).strip(),
                        "title": m_simple.group(2).strip(),
                        "source": "UNKNOWN",
                        "score": 8.0,
                        "meta_text": block.lower(),
                    })
                continue

            cid = m_head.group(1).strip()
            ctitle = m_head.group(2).strip()
            csource = m_head.group(4).strip()
            m_score = re.search(r"Puan:\s*([\d\.]+)", block)
            cscore = float(m_score.group(1)) if m_score else 8.0
            candidates_info.append({
                "id": cid,
                "title": ctitle,
                "source": csource,
                "score": cscore,
                "meta_text": block.lower(),
            })

        prompt_m = re.search(r"KULLANICI İSTEMİ:\s*([^\n]+)", user_prompt)
        prompt_str = prompt_m.group(1).strip() if prompt_m else ""
        clean_prompt = re.sub(r"\[(ALL|ANIME|MOVIE|SERIES)\]", "", prompt_str, flags=re.IGNORECASE).strip()
        clean_p_lower = clean_prompt.lower()

        # Detect if this is a "X gibi..." reference query vs direct title query
        ref_match = re.search(r"^(.+?)\s+(?:gibi|tarzı|benzeri)\b", clean_prompt, flags=re.IGNORECASE)
        ref_title_lower = ref_match.group(1).strip().lower() if ref_match else None

        # Extract meaningful query tokens (both Turkish and translated English equivalents)
        raw_tokens = [
            w for w in re.findall(r"\w+", clean_p_lower)
            if len(w) >= 3 and w not in {"gibi", "tarzı", "benzeri", "olan", "içeren", "film", "filmi", "dizi", "dizisi", "anime", "izle", "izlemek", "istiyorum", "bana", "öner"}
        ]
        expanded_tokens = set(raw_tokens)
        for tr_k, en_v in TR_EN_KEYWORD_MAP.items():
            if tr_k in clean_p_lower:
                expanded_tokens.update(en_v.lower().split())
                expanded_tokens.add(tr_k)

        # Shuffle first so ties are broken with fresh variety every time
        random.shuffle(candidates_info)

        scored_candidates: List[tuple[float, Dict[str, Any]]] = []
        for cand in candidates_info:
            c_title_low = cand["title"].lower()
            meta = cand["meta_text"]

            norm_c = _normalize_title(cand["title"])
            norm_q = _normalize_title(clean_p_lower)

            # Detect if query is a thematic/discovery query vs a literal title search
            is_theme_query = any(k in clean_p_lower for k in TR_EN_KEYWORD_MAP) or any(
                k in clean_p_lower for k in ["film", "filmi", "dizi", "dizisi", "anime", "öner", "en iyi", "tavsiye", "ilgili", "hakkında"]
            )

            # If user asked for "X gibi...", penalize returning X itself so we recommend similar titles
            if ref_title_lower and (c_title_low == ref_title_lower or ref_title_lower in c_title_low):
                relevance = -10.0
            elif not is_theme_query and not ref_title_lower and norm_q and (norm_c == norm_q):
                # Direct title match gets highest priority ONLY if query is a true title match!
                relevance = 100.0
            else:
                # Keyword overlap score + base rating weight + controlled randomness for fresh discovery
                overlap = sum(5.0 for tok in expanded_tokens if tok in meta)
                c_score = cand.get("score") or 0.0
                score_weight = (c_score * 2.5) if c_score >= 6.0 else -20.0
                jitter = random.uniform(0.0, 0.4)
                relevance = overlap + score_weight + jitter

            scored_candidates.append((relevance, cand))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Select top 5 with balanced media source diversity if multiple sources are present
        selected: List[Dict[str, Any]] = []
        source_counts: Dict[str, int] = {}
        distinct_sources = {c["source"] for _, c in scored_candidates}

        for rel, cand in scored_candidates:
            if len(selected) >= 5:
                break
            src = cand["source"]
            # If pool has multiple sources (e.g. ALL filter), cap any single source at 2 during first pass
            if len(distinct_sources) > 1 and source_counts.get(src, 0) >= 2 and rel < 40.0:
                continue
            selected.append(cand)
            source_counts[src] = source_counts.get(src, 0) + 1

        # Fill remaining slots up to 5 if needed
        selected_ids = {c["id"] for c in selected}
        for _, cand in scored_candidates:
            if len(selected) >= 5:
                break
            if cand["id"] not in selected_ids:
                selected.append(cand)
                selected_ids.add(cand["id"])

        recommendations_list = []
        is_history_theme = any(k in clean_p_lower for k in ["tarih", "tarihi", "history", "savaş", "war", "biyografi", "orta çağ", "dönem"])
        for rank, cand in enumerate(selected[:5], 1):
            c_id = cand["id"]
            c_title = cand["title"]
            if not is_theme_query and rank == 1 and not ref_title_lower and clean_p_lower and clean_p_lower in c_title.lower():
                just = f"Doğrudan aradığın '{c_title}', yüksek puanı ve güçlü atmosferiyle listenin zirvesinde yer alıyor. Beklentini tam olarak karşılayacak birincil yapımdır."
            elif is_history_theme:
                if rank == 1:
                    just = f"Tarih ve dönem sinemasının en etkileyici başyapıtlarından biri olan '{c_title}', sunduğu tarihsel gerçekçilik, güçlü prodüksiyon ve sarsıcı derinlikle aradığın hissi eksiksiz yaşatacaktır."
                elif rank == 2:
                    just = f"'{c_title}', gerçek olaylardan ve tarihsel dönüm noktalarından ilham alan sarsıcı kurgusuyla türün en öne çıkan başyapıtlarındandır."
                elif rank == 3:
                    just = f"Tarihsel atmosferi başarıyla yansıtan '{c_title}', dönemin ruhunu, çatışmalarını ve insan psikolojisini ustalıkla işleyen yüksek puanlı bir klasiktir."
                elif rank == 4:
                    just = f"Dönem kurgusu ve güçlü oyunculuklarıyla öne çıkan '{c_title}', tarih meraklılarının izleme listesinde mutlaka yer alması gereken bir eserdir."
                else:
                    just = f"Tarih türünün en prestijli örneklerinden biri olan '{c_title}', sürükleyici anlatımı ve kalıcı etkisiyle keşif listene büyük değer katacaktır."
            elif rank == 1:
                just = f"Aradığın atmosferi ve tematik derinliği en çarpıcı şekilde işleyen '{c_title}', zevkine tam oturacak öncelikli bir başyapıttır. Kurgusal temposu seni ilk dakikadan içine çekecek."
            elif rank == 2:
                just = f"'{c_title}', benzer sürükleyici tonlarıyla alternatifler arasında öne çıkan güçlü bir yapımdır. Karakter çatışmaları ve anlatım diliyle unutulmaz bir deneyim sunar."
            elif rank == 3:
                just = f"Farklı bir perspektif arayanlar için '{c_title}', özgün dünyası ve yüksek anlatım dozajıyla dikkat çeker. Türün klişelerinden uzak, rafine bir kurguya sahiptir."
            elif rank == 4:
                just = f"Derinlikli senaryosu ve görsel atmosferiyle '{c_title}', aradığın hissi tamamlayacak niteliktedir. İzleme listene mutlaka eklemen gereken etkileyici bir eserdir."
            else:
                just = f"Türün en özgün örneklerinden biri olan '{c_title}', keşif sepetine zenginlik katacak sürpriz bir öneridir. Güçlü finali ve temposuyla beklentini aşacaktır."

            recommendations_list.append({
                "selected_external_id": c_id,
                "confidence_score": round(0.97 - (rank - 1) * 0.03, 2),
                "justification_text": just,
            })

        first_rec = (
            recommendations_list[0]
            if recommendations_list
            else {"selected_external_id": "none", "confidence_score": 0.0, "justification_text": "Öneri bulunamadı."}
        )
        return {
            "recommendations": recommendations_list,
            "selected_external_id": first_rec["selected_external_id"],
            "confidence_score": first_rec["confidence_score"],
            "justification_text": first_rec["justification_text"],
        }


class RecommendationEngine:
    """Single-stage ultra-fast recommendation pipeline:
    0ms Local Intent Parser -> Parallel Cached Candidate Retrieval -> Re-ranking & Justification.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        aggregator_service: Optional[MediaAggregatorService] = None,
    ) -> None:
        self.llm = llm_client or LLMClient()
        self.aggregator = aggregator_service or MediaAggregatorService()

    @staticmethod
    def _fast_local_intent_parser(user_prompt: str) -> UserIntentFilter:
        """0ms local intent parser replacing Stage A LLM network call."""
        raw = (user_prompt or "").strip()
        p_lower = raw.lower()

        # 1. Detect explicit prefix tag ([ANIME], [MOVIE], [SERIES], [ALL])
        prefix_match = re.search(r"\[(ALL|ANIME|MOVIE|SERIES)\]", raw, flags=re.IGNORECASE)
        media_type = prefix_match.group(1).upper() if prefix_match else "ALL"

        clean_text = re.sub(r"\[(ALL|ANIME|MOVIE|SERIES)\]", "", raw, flags=re.IGNORECASE).strip()
        clean_lower = clean_text.lower()

        # 2. Extract reference titles ("X gibi", "X tarzı", "X benzeri")
        ref_titles: List[str] = []
        match_like = re.search(r"^(.+?)\s+(?:gibi|tarzı|benzeri)\b", clean_text, flags=re.IGNORECASE)
        if match_like:
            ref_candidate = match_like.group(1).strip()
            if ref_candidate:
                ref_titles.append(ref_candidate)

        # 3. Extract moods, themes, and excluded tropes
        moods: List[str] = []
        for m in [
            "karanlık", "dark", "gerilim", "tekinsiz", "melankolik", "melankoli",
            "hüzünlü", "komik", "eğlenceli", "romantik", "epik", "sürükleyici",
        ]:
            if m in clean_lower:
                moods.append("melankolik" if m == "melankoli" else m)

        themes: List[str] = []
        theme_patterns = [
            ("tarih", "tarih"),
            ("tarihi", "tarih"),
            ("tarihsel", "tarih"),
            ("history", "tarih"),
            ("historical", "tarih"),
            ("dönem", "tarih"),
            ("orta çağ", "tarih"),
            ("antik", "tarih"),
            ("osmanlı", "tarih"),
            ("roma", "tarih"),
            ("savaş", "savaş"),
            ("war", "savaş"),
            ("askeri", "savaş"),
            ("biyografi", "biyografi"),
            ("biyografik", "biyografi"),
            ("biography", "biyografi"),
            ("psikolojik", "psikolojik"),
            ("cyberpunk", "cyberpunk"),
            ("siber-punk", "cyberpunk"),
            ("intikam", "intikam"),
            ("zaman yolculuğu", "zaman yolculuğu"),
            ("zaman bükücü", "zaman yolculuğu"),
            ("bilim kurgu", "bilim kurgu"),
            ("distopya", "distopya"),
            ("distopik", "distopya"),
            ("aksiyon", "aksiyon"),
            ("macera", "macera"),
            ("uzay", "uzay"),
            ("rüya", "rüya"),
            ("suç", "suç"),
            ("polisiye", "suç"),
            ("dedektif", "gizem"),
            ("gizem", "gizem"),
            ("korku", "korku"),
            ("horror", "korku"),
            ("komedi", "komedi"),
            ("comedy", "komedi"),
            ("romantik", "romantik"),
            ("romance", "romantik"),
            ("aşk", "romantik"),
            ("dram", "dram"),
            ("drama", "dram"),
            ("fantezi", "fantastik"),
            ("fantastik", "fantastik"),
            ("western", "western"),
            ("kovboy", "western"),
            ("belgesel", "belgesel"),
            ("ahlaki çöküş", "suç"),
            ("kimlik buhranı", "psikolojik"),
            ("twist", "gerilim"),
            ("animasyon", "animasyon"),
            ("kahraman", "aksiyon"),
        ]
        for pat, norm_theme in theme_patterns:
            if pat in clean_lower and norm_theme not in themes:
                themes.append(norm_theme)

        excluded: List[str] = []
        for e in ["shounen", "klişe", "arkadaşlık gücü", "harem"]:
            if e in clean_lower:
                label = f"{e} klişesi" if e == "shounen" else e
                if label not in excluded:
                    excluded.append(label)

        # If "karanlık" + ("anime" or "shounen") and no themes yet, infer "psikolojik"
        if "karanlık" in moods and not themes:
            themes.append("psikolojik")

        # 4. Strip command verbs to inspect potential direct title
        command_pattern = r"\b(izlemek\s+istiyorum|izlemek|seyretmek\s+istiyorum|izle|bul|seyret|öner|önerir\s+misin)\b"
        has_command_verb = bool(re.search(command_pattern, clean_lower))
        stripped_title = re.sub(command_pattern, "", clean_text, flags=re.IGNORECASE).strip(" .,!?-")
        stripped_lower = stripped_title.lower()

        # 5. Determine media_type if still ALL
        norm_stripped = _normalize_title(stripped_title)
        if media_type == "ALL":
            if any(w in clean_lower for w in ["anime", "manga", "shounen", "seinen", "isekai"]) or stripped_lower in KNOWN_ANIME_TITLES or norm_stripped in KNOWN_ANIME_TITLES:
                media_type = "ANIME"
            elif any(w in clean_lower for w in ["dizi", "dizisi", "series", "sezon", "mini dizi"]) or stripped_lower in KNOWN_SERIES_TITLES or norm_stripped in KNOWN_SERIES_TITLES:
                media_type = "SERIES"
            elif any(w in clean_lower for w in ["film", "filmi", "movie", "sinema"]) or stripped_lower in KNOWN_MOVIE_TITLES or norm_stripped in KNOWN_MOVIE_TITLES:
                media_type = "MOVIE"

        # 6. Determine if direct title search
        discovery_indicator_words = {
            "film", "filmi", "filmleri", "filmler", "movie", "movies",
            "dizi", "dizisi", "dizileri", "diziler", "series", "tv",
            "anime", "animeleri", "animesi", "animeler",
            "öner", "önerisi", "önerileri", "önerir", "önerir misin", "tavsiye", "tavsiyesi",
            "en iyi", "yüksek puanlı", "kaliteli", "güzel", "popüler", "başyapıt",
            "ilgili", "hakkında", "konulu", "türünde", "tarzında", "benzeri", "gibi",
        }
        has_discovery_words = any(w in clean_lower for w in discovery_indicator_words)

        has_descriptors = bool(
            ref_titles
            or excluded
            or "gibi" in clean_lower
            or "tarzı" in clean_lower
            or "içermeyen" in clean_lower
            or len(moods) >= 1
            or len(themes) >= 1
            or has_discovery_words
        )
        word_count = len(stripped_title.split())
        is_known = (
            stripped_lower in KNOWN_MOVIE_TITLES
            or stripped_lower in KNOWN_SERIES_TITLES
            or stripped_lower in KNOWN_ANIME_TITLES
            or norm_stripped in KNOWN_MOVIE_TITLES
            or norm_stripped in KNOWN_SERIES_TITLES
            or norm_stripped in KNOWN_ANIME_TITLES
        )
        is_direct = is_known or (has_command_verb and not has_descriptors and 1 <= word_count <= 6) or (
            not has_descriptors and 1 <= word_count <= 4
        )

        direct_title = stripped_title if is_direct and stripped_title else None

        return UserIntentFilter(
            is_direct_title_search=is_direct,
            direct_title=direct_title,
            media_type_filter=media_type,
            mood_keywords=moods if moods else (["sürükleyici"] if not is_direct else []),
            target_themes=themes if themes else (["derin kurgu"] if not is_direct else []),
            excluded_tropes=excluded,
            reference_titles=ref_titles,
        )

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
        """Stage A (0ms Local Intent Parser): Extracts structured intent without LLM latency."""
        return self._fast_local_intent_parser(user_prompt)

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
            if user_media.status == WatchStatus.COMPLETED:
                completed_titles.append(media_item.title)
                completed_ids.append(str(media_item.external_id))

            if user_media.is_favorite or (user_media.user_score and user_media.user_score >= 9.0):
                note = f" (Not: {user_media.personal_notes})" if user_media.personal_notes else ""
                gold_list.append(f"{media_item.title} [{media_item.media_source}]{note}")

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
        """Fetches a diverse, balanced pool of candidates from MediaAggregator and curated pools."""
        enable_tmdb = intent.media_type_filter in ("ALL", "MOVIE", "SERIES")
        # Anime is STRICTLY enabled only when explicitly requested (ANIME button or anime title/keyword)
        enable_anilist = (intent.media_type_filter == "ANIME")

        clean_user_prompt = re.sub(r"\[(ALL|ANIME|MOVIE|SERIES)\]", "", user_prompt, flags=re.IGNORECASE).strip()

        # Formulate primary search query
        trans_themes = self._translate_keywords(intent.target_themes + intent.mood_keywords)
        if intent.is_direct_title_search and intent.direct_title:
            search_query = intent.direct_title
        elif trans_themes:
            search_query = trans_themes[0]
        elif intent.reference_titles:
            search_query = intent.reference_titles[0]
        else:
            search_query = clean_user_prompt or user_prompt

        candidates = await self.aggregator.search_all(
            query=search_query,
            enable_tmdb=enable_tmdb,
            enable_anilist=enable_anilist,
            per_source_limit=max(limit, 12),
        )

        # Supplement with curated masterpieces that match the intent's target themes!
        if intent.target_themes:
            from app.services.external.tmdb_client import CURATED_POPULAR_MOVIES, CURATED_POPULAR_SERIES, TMDBClient
            theme_keys = {t.lower() for t in intent.target_themes + intent.mood_keywords + trans_themes}
            theme_matches: List[UnifiedMediaDTO] = []
            
            if enable_tmdb:
                for m in CURATED_POPULAR_MOVIES:
                    meta = " ".join([g.lower() for g in m.get("genres", [])] + [t.lower() for t in m.get("themes", [])])
                    if any(tk in meta for tk in theme_keys):
                        theme_matches.append(TMDBClient._dict_to_dto(m, "TMDB_MOVIE"))
                for s in CURATED_POPULAR_SERIES:
                    meta = " ".join([g.lower() for g in s.get("genres", [])] + [t.lower() for t in s.get("themes", [])])
                    if any(tk in meta for tk in theme_keys):
                        theme_matches.append(TMDBClient._dict_to_dto(s, "TMDB_SERIES"))
            
            seen_keys = {(c.source, str(c.external_id)) for c in candidates}
            for tm in theme_matches:
                key = (tm.source, str(tm.external_id))
                if key not in seen_keys:
                    candidates.insert(0, tm)
                    seen_keys.add(key)

        if len(candidates) < 10 or not intent.is_direct_title_search:
            try:
                supplement = await self.aggregator.get_random_masterpieces(
                    limit=20,
                    media_type=intent.media_type_filter,
                )
                seen_keys = {(c.source, str(c.external_id)) for c in candidates}
                for item in supplement:
                    if intent.media_type_filter != "ANIME" and item.source == "ANILIST":
                        continue
                    if intent.media_type_filter == "ANIME" and item.source != "ANILIST":
                        continue
                    key = (item.source, str(item.external_id))
                    if key not in seen_keys:
                        candidates.append(item)
                        seen_keys.add(key)
            except Exception as exc:
                logger.debug("Supplement candidate fetch skipped: %s", exc)

        # Ensure anime mode always has high-scoring anime candidates to rank if title search was too narrow
        if intent.media_type_filter == "ANIME" and len(candidates) < 5:
            try:
                anime_pop = await self.aggregator.anilist_client.get_popular_anime(page=1, per_page=20)
                seen_keys = {(c.source, str(c.external_id)) for c in candidates}
                for item in anime_pop:
                    key = (item.source, str(item.external_id))
                    if key not in seen_keys:
                        candidates.append(item)
                        seen_keys.add(key)
            except Exception as exc:
                logger.debug("AniList popular fallback skipped: %s", exc)

        # Enforce media_type filter before scoring/balancing
        if intent.media_type_filter == "MOVIE":
            candidates = [c for c in candidates if c.source == "TMDB_MOVIE"]
        elif intent.media_type_filter == "SERIES":
            candidates = [c for c in candidates if c.source == "TMDB_SERIES"]
        elif intent.media_type_filter == "ANIME":
            candidates = [c for c in candidates if c.source == "ANILIST"]
        else:
            candidates = [c for c in candidates if c.source != "ANILIST"]

        # Exclude reference title itself when user asks "X gibi..."
        if intent.reference_titles:
            ref_lows = {r.lower().strip() for r in intent.reference_titles if r.strip()}
            filtered_ref = [
                c for c in candidates
                if c.title.lower().strip() not in ref_lows
            ]
            if len(filtered_ref) >= 5:
                candidates = filtered_ref

        # Filter out titles explicitly completed or dropped by user
        if excluded_ids:
            excluded_id_set = {str(eid) for eid in excluded_ids}
            candidates = [c for c in candidates if str(c.external_id) not in excluded_id_set]

        if excluded_titles:
            excluded_titles_lower = {t.lower().strip() for t in excluded_titles}
            candidates = [c for c in candidates if c.title.lower().strip() not in excluded_titles_lower]

        if red_list_titles:
            red_lower = {r.lower() for r in red_list_titles}
            candidates = [c for c in candidates if not any(c.title.lower() in r for r in red_lower)]

        # Score & shuffle candidates by query relevance + rating + randomness so results are fresh & relevant
        query_terms = set(
            self._translate_keywords(intent.target_themes + intent.mood_keywords)
            + [w.lower() for w in re.findall(r"\w+", clean_user_prompt) if len(w) >= 3]
        )

        random.shuffle(candidates)

        def _candidate_priority(c: UnifiedMediaDTO) -> float:
            haystack = " ".join(
                [c.title, c.synopsis or ""] + (c.genres or []) + (c.themes or [])
            ).lower()
            if intent.is_direct_title_search and intent.direct_title:
                dt = intent.direct_title.lower()
                if c.title.lower() == dt:
                    return 100.0
                if dt in c.title.lower():
                    return 50.0
            kw_hits = sum(2.0 for term in query_terms if term in haystack)
            score_bonus = (c.base_score or 7.5) * 0.35
            return kw_hits + score_bonus + random.uniform(0.0, 1.2)

        candidates.sort(key=_candidate_priority, reverse=True)

        # If ALL media types are enabled, interleave Movie, Series, and Anime for balanced variety
        if intent.media_type_filter == "ALL" and not intent.is_direct_title_search:
            movies = [c for c in candidates if c.source == "TMDB_MOVIE"]
            series = [c for c in candidates if c.source == "TMDB_SERIES"]
            animes = [c for c in candidates if c.source == "ANILIST"]
            balanced: List[UnifiedMediaDTO] = []
            max_b = max(len(movies), len(series), len(animes), 1)
            for i in range(max_b):
                if i < len(movies):
                    balanced.append(movies[i])
                if i < len(series):
                    balanced.append(series[i])
                if i < len(animes):
                    balanced.append(animes[i])
            candidates = balanced

        return candidates[: max(limit, 15)]

    async def rerank_and_justify(
        self,
        user_prompt: str,
        intent: UserIntentFilter,
        candidates: List[UnifiedMediaDTO],
        user_profile: UserLibraryProfile,
        media_type: Optional[str] = None,
    ) -> RecommendationResult:
        """Evaluates candidates against user profile and outputs 'Neden Bu?' justifications."""
        if not candidates:
            return RecommendationResult(
                selected_external_id="none",
                confidence_score=0.0,
                justification_text="Aramanıza ve zevkinize uygun kriterlerde bir yapım bulunamadı.",
            )

        cand_summaries: List[str] = []
        for idx, c in enumerate(candidates, 1):
            cand_summaries.append(
                f"{idx}. ID: {c.external_id} | Başlık: {c.title} ({c.release_year or 'N/A'}) | Kaynak: {c.source}\n"
                f"   Türler: {', '.join(c.genres)} | Temalar: {', '.join(c.themes)}\n"
                f"   Puan: {c.base_score} | Özet: {(c.synopsis or '')[:200]}..."
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
        """Executes the single-stage AI recommendation pipeline with 0ms local intent parsing."""
        # Stage A: 0ms Local Intent Parsing (No LLM network call!)
        intent = self._fast_local_intent_parser(prompt)

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

        logger.info("Fast local intent parsed (media_type_filter=%s): %s", intent.media_type_filter, intent.model_dump())

        user_profile = UserLibraryProfile()
        if user_id and session:
            try:
                user_profile = await self.get_user_profile(session, user_id)
            except Exception as e:
                logger.warning("Could not load user library profile from database: %s", e)

        candidates = await self.fetch_candidates(
            intent=intent,
            user_prompt=prompt,
            limit=max(limit, 15),
            session=session,
            red_list_titles=user_profile.red_list,
            excluded_titles=user_profile.completed_titles,
            excluded_ids=user_profile.completed_ids,
        )

        clean_user_prompt = re.sub(r"\[(ALL|ANIME|MOVIE|SERIES)\]", "", prompt, flags=re.IGNORECASE).strip()
        search_target = (intent.direct_title or clean_user_prompt).lower().strip()

        best_match = None
        norm_target = _normalize_title(search_target)
        if candidates and intent.is_direct_title_search and norm_target:
            best_match = next((c for c in candidates if _normalize_title(c.title) == norm_target), None)
            if not best_match and len(norm_target) >= 3:
                best_match = next(
                    (c for c in candidates if norm_target == _normalize_title(c.title)),
                    None,
                )

        if best_match:
            remaining_cands = [c for c in candidates if str(c.external_id) != str(best_match.external_id)]
            eval_candidates = [best_match] + remaining_cands
        else:
            eval_candidates = candidates

        # Stage B: Re-ranking and Justification (Single LLM call or fast heuristic fallback)
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
        """Provides a serendipitous 'Şansıma Güveniyorum' high-scoring recommendation."""
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
                stmt = select(MediaItem).where(
                    func.coalesce(MediaItem.site_score, MediaItem.imdb_score, 0.0) >= 7.8
                )
                if target_filter == "MOVIE":
                    stmt = stmt.where(MediaItem.media_source == MediaSource.TMDB_MOVIE)
                elif target_filter == "SERIES":
                    stmt = stmt.where(MediaItem.media_source == MediaSource.TMDB_SERIES)
                elif target_filter == "ANIME":
                    stmt = stmt.where(MediaItem.media_source == MediaSource.ANILIST)
                else:
                    stmt = stmt.where(MediaItem.media_source != MediaSource.ANILIST)

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

        if not selected_dto:
            pool = await self.aggregator.get_random_masterpieces(limit=25, media_type=target_filter)
            valid_pool = [
                m for m in pool
                if m.title.lower() not in user_saved_titles and str(m.external_id) not in user_saved_titles
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
                        synopsis="When Earth becomes uninhabitable in the future, a farmer and ex-NASA pilot is tasked to pilot a spacecraft to find a new planet for humans.",
                        genres=["Adventure", "Drama", "Science Fiction"],
                        themes=["space exploration", "time dilation"],
                        base_score=8.7,
                        vote_count=2100000,
                    )
                elif target_filter == "SERIES":
                    selected_dto = UnifiedMediaDTO(
                        external_id="1396",
                        source="TMDB_SERIES",
                        title="Breaking Bad",
                        release_year=2008,
                        poster_url="https://image.tmdb.org/t/p/w500/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
                        synopsis="A chemistry teacher diagnosed with inoperable lung cancer turns to manufacturing methamphetamine.",
                        genres=["Drama", "Crime"],
                        themes=["drugs", "moral descent"],
                        base_score=9.5,
                        vote_count=2100000,
                    )
                elif target_filter == "ANIME":
                    selected_dto = UnifiedMediaDTO(
                        external_id="16498",
                        source="ANILIST",
                        title="Attack on Titan",
                        release_year=2013,
                        poster_url="https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx16498-C6FPmWm59CyP.jpg",
                        synopsis="Centuries ago mankind was almost slaughtered by titans.",
                        genres=["Action", "Drama", "Fantasy"],
                        themes=["post-apocalyptic", "military"],
                        base_score=8.5,
                        vote_count=500000,
                    )
                else:
                    selected_dto = UnifiedMediaDTO(
                        external_id="238",
                        source="TMDB_MOVIE",
                        title="The Godfather",
                        release_year=1972,
                        poster_url="https://image.tmdb.org/t/p/w500/3bhkrj58Vtu7enYsRolD1fZdja1.jpg",
                        synopsis="Spanning the years 1945 to 1955, a chronicle of the fictional Italian-American Corleone crime family.",
                        genres=["Drama", "Crime"],
                        themes=["mafia", "family", "loyalty"],
                        base_score=8.7,
                        vote_count=1900000,
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
