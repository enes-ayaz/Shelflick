import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.llm.recommendation_engine import RecommendationEngine


async def test_recommendation_pipeline():
    print("=" * 60)
    print("MEDIA PULSE AI RECOMMENDATION PIPELINE DEMO")
    print("=" * 60)

    engine = RecommendationEngine()
    test_prompt = "Shounen klişesi içermeyen karanlık anime"
    print(f"\n[Girdi İstemi]: '{test_prompt}'")
    print("Pipeline çalıştırılıyor (Intent Parsing -> Arama -> Re-ranking)...")

    response = await engine.recommend(prompt=test_prompt, limit=5)

    print("\n--- AŞAMA A: NİYET AYRIŞTIRMA (INTENT PARSING) ---")
    intent = response.parsed_intent
    print(f"Medya Tipi Filtresi : {intent.media_type_filter}")
    print(f"Duygu Anahtar Kelimeler: {intent.mood_keywords}")
    print(f"Hedef Temalar       : {intent.target_themes}")
    print(f"Dışlanan Klişeler   : {intent.excluded_tropes}")
    print(f"Doğrudan Başlık mı? : {intent.is_direct_title_search}")

    print("\n--- AŞAMA B: SEÇİLEN YAPIM & 'NEDEN BU?' GEREKÇESİ ---")
    if response.recommended_media:
        m = response.recommended_media
        print(f"Seçilen Yapım : {m.title} ({m.release_year}) [{m.source}]")
        print(f"Taban Puanı   : {m.base_score} / 10.0 (Oy/Popülarite: {m.vote_count})")
        print(f"Afiş URL'si   : {m.poster_url}")
        print(f"Türler        : {', '.join(m.genres)}")
        print(f"Temalar       : {', '.join(m.themes[:6])}")
    print(f"Güven Skoru   : %{int(response.confidence_score * 100)}")
    print(f"\n[NEDEN BU? (Gerekçe)]:\n>> {response.justification}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_recommendation_pipeline())
