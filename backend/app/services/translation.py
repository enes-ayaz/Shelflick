import asyncio
import logging
import re
import urllib.parse
from typing import Dict, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

TURKISH_CHARS = set("çğıöşüÇĞİÖŞÜ")
ENGLISH_MARKER_WORDS = {
    "the", "and", "of", "in", "to", "a", "is", "was", "for", "with",
    "by", "an", "his", "her", "their", "when", "after", "who", "from",
    "into", "that", "this", "which", "about", "starring", "series", "film",
    "story", "lives", "years", "during", "takes", "place", "set", "young",
    "man", "woman", "earth", "world", "becomes", "must", "save", "between"
}

CURATED_TURKISH_SYNOPSES: Dict[str, str] = {
    # Iconic Movies
    "Inception": "Rüya paylaşımı teknolojisiyle zihinlerden sır çalan Dom Cobb'a, bu kez bir fikri yerleştirme (başlangıç) görevi verilir; ancak geçmişinin hayaletleri tüm ekibi tehlikeye atacaktır.",
    "Interstellar": "Dünya yaşanmaz hale geldiğinde, eski bir NASA pilotu Joseph Cooper, insanlığın kurtuluşu için solucan deliğinden geçerek yeni bir gezegen arayışına çıkar.",
    "The Dark Knight": "Batman, Teğmen Gordon ve Savcı Harvey Dent ile birlikte Gotham'ı kaosa sürükleyen Joker'in yarattığı psikolojik ve ölümcül tehdidi durdurmaya çalışır.",
    "Fight Club": "Uykusuzluk çeken sıradan bir büro çalışanı ve karizmatik sabun üreticisi Tyler Durden, hızla kontrolden çıkan gizli bir yeraltı dövüş kulübü kurar.",
    "Pulp Fiction": "İki kiralık katil, bir boksör, bir gangster ve karısının hayatları; şiddet, kader ve kefaret dolu dört farklı öyküde iç içe geçer.",
    "The Matrix": "Yazılımcı ve hacker Thomas Anderson (Neo), gerçekliğin insanlığı uyutmak için tasarlanmış devasa bir simülasyon olduğunu öğrenir ve isyana katılır.",
    "The Shawshank Redemption": "İşlemediği bir suçtan ömür boyu hapse mahkum edilen bankacı Andy Dufresne, Shawshank Cezaevi'nde umudunu kaybetmeden direnir.",
    "The Godfather": "New York'un en güçlü mafya ailelerinden birinin reisi olan Don Vito Corleone suikasta uğrayınca, isteksiz küçük oğlu Michael ailenin başına geçer.",
    "Se7en": "Emekliliğine günler kalan kıdemli bir dedektif ile fevri ortağı, yedi ölümcül günahı temel alarak seri cinayetler işleyen bir katilin peşine düşer.",
    "The Prestige": "19. yüzyıl Londra'sında iki illüzyonist, en kusursuz sahne numarasını yaratabilmek için birbirlerinin sırlarını çalmaya çalışırken ölümcül bir takıntıya kapılır.",
    "Whiplash": "Hırslı genç bir caz bateristi, ülkenin en prestijli konservatuarında acımasız ve sınırları zorlayan bir müzik hocasının orkestrasına kabul edilir.",
    "Parasite": "Yoksul Kim ailesi, tek tek ve kurnazca zengin Park ailesinin evine sızarak onların hayatına ortak olur; ancak beklenmedik bir sır dengeleri altüst eder.",
    "Spirited Away": "Ailesi domuza dönüşen 10 yaşındaki Chihiro, onları kurtarmak için ruhların ve cadıların hüküm sürdüğü gizemli bir hamamda çalışmak zorundadır.",
    "Dune": "Galaksinin en tehlikeli ve değerli maddesini barındıran çöl gezegeni Arrakis'e gönderilen Paul Atreides, halkının kaderini sırtlamak zorundadır.",
    "Oppenheimer": "Amerikalı fizikçi J. Robert Oppenheimer ve ekibinin İkinci Dünya Savaşı'nı bitiren ilk nükleer silahı geliştirme süreci ve sonrasındaki ahlaki hesaplaşması.",
    "Joker": "Toplum tarafından dışlanan ve başarısız bir stand-up komedyeni olan Arthur Fleck, Gotham'ı sarsacak bir kaos ve suç figürüne dönüşür.",
    "Prisoners": "Altı yaşındaki kızı ve arkadaşı kaçırılan Keller Dover, polisin çaresiz kaldığı noktada adaleti kendi elleriyle sağlamaya karar verir.",
    "Gone Girl": "Evlilik yıldönümlerinde karısı esrarengiz bir şekilde ortadan kaybolan Nick Dunne, tüm şüphelerin ve medya baskısının odağı haline gelir.",
    "Spider-Man: Across the Spider-Verse": "Miles Morales, çoklu evrenler arasında seyahat ederken diğer Örümcek Kahramanlarla ve evrenin varlığını tehdit eden yeni bir güçle karşılaşır.",
    "Blade Runner 2049": "Los Angeles polis memuru K, toplumun kalanını kaosa sürükleyebilecek uzun süredir gizli kalmış bir sırrı keşfeder ve 30 yıldır kayıp olan Rick Deckard'ı bulmaya çalışır.",
    "Arrival": "Dünyanın çeşitli yerlerine gizemli uzay gemileri indiğinde, uzaylılarla iletişim kurması için dilbilimci Louise Banks görevlendirilir.",
    "Mad Max: Fury Road": "Kıyamet sonrası çölde, zalim hükümdara başkaldıran İmparatoriçe Furiosa ve Max Rockatansky, özgürlük için nefes kesen bir kaçışa başlar.",

    # Iconic TV Series & Anime
    "Breaking Bad": "Ölümcül akciğer kanseri teşhisi konan lise kimya öğretmeni Walter White, ailesinin geleceğini güvence altına almak için metamfetamin üretimine başlar.",
    "Game of Thrones": "Westeros'un Yedi Krallığı'nda soylu aileler Demir Taht'ı ele geçirmek için entrikalar yürütürken, kuzeydeki kadim tehdit uyanır.",
    "Chernobyl": "1986'da Çernobil Nükleer Santrali'ndeki feci patlamanın ardından, gerçeği saklamaya çalışan bürokrasiye karşı bilim insanlarının fedakar mücadelesi.",
    "Arcane": "Ütopik Piltover ve ezilen yeraltı şehri Zaun arasındaki çatışmada, iki kız kardeş Vi ve Jinx farklı taraflara savrularak karşı karşıya gelir.",
    "Severance": "Lumon şirketinde çalışan Mark, iş ve kişisel anılarını cerrahi müdahaleyle birbirinden ayıran bir ekibin başındadır; ancak şirketin karanlık sırları açığa çıkar.",
    "Succession": "Dünyanın en büyük medya imparatorluklarından birini yöneten Roy ailesinde, yaşlanan babanın çekilmesiyle çocuklar arasında acımasız bir güç savaşı başlar.",
    "True Detective": "Louisiana'da 17 yıl boyunca çözülemeyen karanlık bir cinayet davası, iki dedektifin hayatını ve psikolojisini derinden sarsar.",
    "The Wire": "Baltimore sokaklarında uyuşturucu ticareti, polis teşkilatı, liman işçileri ve siyaset arasındaki karmaşık ve acımasız ilişkiler ağı.",
    "Fargo": "Minnesota'nın karlı kasabalarında sıradan insanların masum gibi görünen hataları, kurnaz suçlular ve cinayetlerle içinden çıkılmaz bir kaosa dönüşür.",
    "Dark": "Almanya'nın Winden kasabasında iki çocuğun kaybolması, dört ailenin geçmişi ile kasabanın altındaki zaman döngüsü arasındaki korkutucu gerçeği ortaya çıkarır.",
    "Stranger Things": "1980'lerde küçük bir kasabada bir çocuğun kaybolması, gizli hükümet deneylerini ve doğaüstü 'Ters Dünya' tehlikesini açığa çıkarır.",
    "The Last of Us": "Kıyamet sonrası dünyada ölümcül mantar salgınına karşı bağışıklığı olan genç Ellie'yi güvenli bir bölgeye ulaştırmak zorunda olan Joel'un hayatta kalma mücadelesi.",
    "Better Call Saul": "Ahlaki sınırları zorlayan küçük çaplı avukat Jimmy McGill'in, Breaking Bad'in ünlü kurnaz savunma avukatı Saul Goodman'a dönüşüm hikayesi.",
    "Sherlock": "Modern Londra'da dahi dedektif Sherlock Holmes ve ortağı Dr. John Watson, en karmaşık suçları zekalarıyla çözüme kavuşturur.",
    "Attack on Titan": "İnsanlık, devasa surların ardında insan yiyen devasa Titanlardan saklanırken, surların yıkılmasıyla Eren Yeager ve arkadaşları intikam savaşına başlar.",
    "Death Note": "Üzerine adı yazılan herkesin öldüğü gizemli bir defteri bulan dahi öğrenci Light Yagami, dünyayı suçtan arındırmak isterken dahi dedektif L ile zeka savaşına girer.",
    "Fullmetal Alchemist: Brotherhood": "Ölen annelerini diriltmek için simyayı kullanan iki kardeş Edward ve Alphonse Elric, kaybettikleri bedenlerini geri almak için Felsefe Taşı'nı arar.",
}


def is_english_or_needs_translation(text: Optional[str]) -> bool:
    """Returns True if the synopsis is likely English or lacks Turkish characters."""
    if not text or len(text.strip()) < 5:
        return False
    clean = text.strip()
    turkish_char_count = sum(1 for c in clean if c in TURKISH_CHARS)
    if turkish_char_count >= 2:
        return False

    words = set(re.findall(r"\b[a-zA-Z]+\b", clean.lower()))
    english_hits = len(words.intersection(ENGLISH_MARKER_WORDS))
    return english_hits >= 1 or len(words) >= 3


async def translate_to_turkish(text: str) -> str:
    """Translates text to natural Turkish using Google Translate API."""
    if not text or not text.strip():
        return text

    clean_text = text.strip()
    try:
        encoded_q = urllib.parse.quote(clean_text[:1800])
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=tr&dt=t&q={encoded_q}"
        async with httpx.AsyncClient(timeout=3.5) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                data = resp.json()
                translated = "".join(
                    [part[0] for part in data[0] if part and len(part) > 0 and part[0]]
                )
                if translated and len(translated.strip()) > 5:
                    return translated.strip()
    except Exception as exc:
        logger.debug("Fast translation to Turkish failed: %s", exc)

    return text


async def resolve_turkish_synopsis(
    synopsis: Optional[str],
    external_id: Optional[str] = None,
    source: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    """Ensures media synopsis is provided in high-quality Turkish.

    1. Checks curated Turkish synopses first (instant 0ms response).
    2. Checks if synopsis is already in Turkish.
    3. Queries TMDB API for official Turkish overview if it's a TMDB item.
    4. Translates English synopsis to Turkish.
    """
    clean_title = (title or "").strip()
    if clean_title and clean_title in CURATED_TURKISH_SYNOPSES:
        return CURATED_TURKISH_SYNOPSES[clean_title]

    raw_synopsis = (synopsis or "").strip()

    # If it's already in Turkish, return immediately
    if raw_synopsis and not is_english_or_needs_translation(raw_synopsis):
        return raw_synopsis

    # 1. Try official TMDB tr-TR overview if it's a TMDB item
    if external_id and settings.TMDB_API_KEY:
        clean_id = str(external_id).strip()
        if clean_id.isdigit():
            mtype = "tv" if source in ("TMDB_SERIES", "tv", "series") else "movie"
            try:
                async with httpx.AsyncClient(timeout=2.5) as client:
                    resp = await client.get(
                        f"https://api.themoviedb.org/3/{mtype}/{clean_id}",
                        params={"api_key": settings.TMDB_API_KEY, "language": "tr-TR"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        tr_overview = (data.get("overview") or "").strip()
                        if tr_overview and len(tr_overview) > 15:
                            return tr_overview
            except Exception as e:
                logger.debug("TMDB Turkish overview query failed for %s: %s", clean_id, e)

    # 2. Translate English synopsis to Turkish
    if raw_synopsis:
        translated = await translate_to_turkish(raw_synopsis)
        if translated and translated != raw_synopsis:
            return translated

    return raw_synopsis or (f"{clean_title or 'Bu yapım'} hakkında Türkçe açıklama yakında eklenecektir.")
