"""Формат шоу «Octane Rent» и вся промпт-логика.

Каждый выпуск — это эпизод шоу об опыте аренды у Octane: ведущие + гость (рассказывает
о поездке и машине) + эксперт Дарья (даёт ПРОВЕРЕННУЮ инфу об аренде с сайта) +
рубрика + иногда розыгрыш. Чтобы выпуски были РАЗНЫМИ, приложение чередует:
  - историю подачи гостя (STORY_ANGLES),
  - самого гостя (GUESTS: разные нации, соло/пары),
  - тему эксперта (EXPERT_TOPICS),
  - рубрику (SEGMENTS),
  - и по расписанию — блок розыгрыша (GIVEAWAY).

Честность (важно и для доверия, и для YouTube):
  - Истории гостей — это иллюстративные фирменные истории бренда, а не выдаваемые за
    реальные проверенные отзывы конкретных клиентов. Места и факты о машине — настоящие.
  - Эксперт говорит ТОЛЬКО факты из knowledge.py (сайт). Никаких выдуманных правил/цифр.
  - Розыгрыш — с реальной механикой (подписка/коммент/промокод, розыгрыш на дату).
    НЕ называем это «прямым эфиром» — подкаст предзаписан.

Всё редактируется здесь. Человекочитаемое описание — PROMPTS.md.
"""

HOST_A = "Alex"            # ведущий (муж.)
HOST_B = "Sam"             # ведущая (жен.)
EXPERT = "Daria Makeeva"   # эксперт Octane (рубрика правил аренды)

SHOW_NAME = "Octane Drive Stories"

# --- Базовые правила шоу (в каждом выпуске) ---
BASE_RULES = f"""You write ONE episode of the audio podcast "{SHOW_NAME}" by Octane Rent
(octane.rent) — a luxury & exotic car rental company in Dubai, Abu Dhabi, Sharjah and Miami.
Audio only. English. 550-800 words.

Recurring cast:
- {HOST_A}: male host, warm and energetic, keeps the show moving.
- {HOST_B}: female host, sharp and curious, asks the good questions.
- {EXPERT}: Octane's rental expert. Appears for a short expert segment. She speaks ONLY
  verified facts provided in the input FACTS block — she NEVER invents rules, prices,
  deposits, ages or policies. If something isn't in FACTS, she says it depends on the car/contract.

Episode flow (keep this order, keep it natural, not robotic):
1) Cold open + hosts introduce today's car and welcome the guest.
2) GUEST STORY: the guest shares their experience with THIS car — where they drove, what
   they saw, how it felt, and how Octane's service/handover/delivery went. Positive and vivid.
3) EXPERT SEGMENT with {EXPERT}: she answers the episode's rental question using ONLY the FACTS.
4) SEGMENT: the short recurring rubric given in the input.
5) (If GIVEAWAY is enabled) the giveaway announcement with its real mechanics.
6) Warm outro + one booking nudge to octane.rent (Dubai, Abu Dhabi, Sharjah, Miami).

Honesty rules (strict):
- The guest is an ILLUSTRATIVE brand character, not presented as a verified named customer
  review. Keep it authentic and positive but never fabricate specific proof, star ratings,
  or claims like "verified customer". Real places and real car facts only.
- Use ONLY the provided car specs and the FACTS block. Never invent horsepower, prices,
  0-100 times, years, deposits, ages, insurance terms or rules.
- Never call the show or the giveaway "live" / "in real time" — it is pre-recorded.
- One booking nudge total. No fake urgency, no bashing other brands.

Return STRICT JSON only (no markdown fences), shape:
{{
  "youtube_title": "RUSSIAN rental-review headline, <=100 chars, EXACTLY in this format: 'Отзыв об аренде {{CleanCarName}} у Octane Rent', where {{CleanCarName}} is the clean car name from the input 'Car (clean name)' field (e.g. 'Mercedes G63') — no 'Rent' prefix, no city. This is the show's experience format — do NOT present it as a verified review by a specific real named customer.",
  "episode_title": "short episode title with the car name",
  "episode_description": "2-3 sentences, SEO-friendly. It MUST END with the exact car page URL from the input 'Car page' field (the specific car's page, NOT the octane.rent homepage).",
  "lines": [{{"speaker": "A|B|G|E", "text": "..."}}]
}}
Speakers: A={HOST_A}, B={HOST_B}, G=guest, E={EXPERT} (expert). Alternate naturally; 1-3 sentences per line."""


# --- Истории подачи гостя (флейвор рассказа) ---
STORY_ANGLES = [
    {"key": "road-trip", "name": "Road trip",
     "prompt": "Guest story flavor: a memorable drive/route in the UAE (Palm, Sheikh Zayed Rd, "
               "Hatta, desert edge) — the journey and the views."},
    {"key": "special-occasion", "name": "Special occasion",
     "prompt": "Guest story flavor: the car for a special moment — anniversary, birthday, proposal, "
               "milestone — and how it made the day."},
    {"key": "business-flex", "name": "Business trip",
     "prompt": "Guest story flavor: a business visitor who used the car for meetings and first "
               "impressions; smooth airport delivery and handover."},
    {"key": "content-shoot", "name": "Content / photoshoot",
     "prompt": "Guest story flavor: a creator/photographer who rented the car for a shoot — the "
               "locations, the light, the reactions."},
    {"key": "first-time-dubai", "name": "First time in Dubai",
     "prompt": "Guest story flavor: a tourist experiencing Dubai for the first time, discovering the "
               "city from behind the wheel of this car."},
    {"key": "weekend-escape", "name": "Weekend escape",
     "prompt": "Guest story flavor: a couple's 48-hour weekend escape and how the car set the tone."},
    {"key": "dream-car-day", "name": "Dream car for a day",
     "prompt": "Guest story flavor: someone finally driving their dream car for a day without owning "
               "it — the emotion of it."},
]

# --- Гости (ротация: разные нации, соло/пары). Персона — иллюстративная. ---
GUESTS = [
    {"key": "uk-solo", "seed": "a British solo traveller, dry humour"},
    {"key": "german-couple", "seed": "a German couple on holiday, precise and enthusiastic"},
    {"key": "indian-family", "seed": "an Indian entrepreneur visiting for business, warm and expressive"},
    {"key": "saudi-local", "seed": "a Saudi local who knows the region well, relaxed and proud"},
    {"key": "american-creator", "seed": "an American content creator, upbeat and visual"},
    {"key": "french-couple", "seed": "a French couple celebrating an anniversary, romantic and chic"},
    {"key": "russian-solo", "seed": "a Russian-speaking expat living in Dubai, cool and candid"},
    {"key": "nigerian-solo", "seed": "a Nigerian first-time visitor, curious and joyful"},
    {"key": "chinese-couple", "seed": "a Chinese couple on a luxury city break, elegant and detail-loving"},
    {"key": "emirati-local", "seed": "an Emirati local showing a friend around, generous host energy"},
]

# --- Темы экспертного блока (Дарья) — каждая опирается на FACTS ---
EXPERT_TOPICS = [
    {"key": "deposit", "q": "Do I need a security deposit to rent with Octane?"},
    {"key": "documents", "q": "What documents and license do I need to rent?"},
    {"key": "age", "q": "What's the minimum age to rent an exotic car?"},
    {"key": "delivery", "q": "Can the car be delivered to my hotel or the airport?"},
    {"key": "insurance", "q": "What insurance is included?"},
    {"key": "fines-salik", "q": "How do tolls (Salik), parking and traffic fines work?"},
    {"key": "day-mileage", "q": "How is a rental day counted, and are there mileage limits?"},
    {"key": "prohibited", "q": "What am I not allowed to do with the car?"},
]

# --- Рубрики (короткий повторяющийся блок) ---
SEGMENTS = [
    {"key": "place-of-week", "name": "Place of the week",
     "prompt": "Short rubric 'Place of the week': hosts spotlight one real UAE/Miami spot and which "
               "car type suits it."},
    {"key": "rental-lifehack", "name": "Rental life-hack",
     "prompt": "Short rubric 'Rental life-hack': one genuinely useful, FACTS-consistent tip "
               "(e.g. airport delivery, 24h day, Salik)."},
    {"key": "weekend-route", "name": "Weekend route",
     "prompt": "Short rubric 'Weekend route': a ready 1-day driving route matched to today's car."},
    {"key": "car-duel", "name": "Car duel",
     "prompt": "Short rubric 'Car duel': hosts playfully argue which occasion today's car wins at."},
]

# --- Розыгрыш (реальная механика; НЕ «прямой эфир») ---
GIVEAWAY = {
    "every_n_episodes": 3,   # анонс каждые N выпусков
    "prize": "a professional photoshoot with a Lamborghini",
    "how_to_enter": "subscribe to the channel and leave a comment naming your dream Octane car",
    "prompt": (
        "GIVEAWAY block: announce an ongoing Octane giveaway. Prize: {prize}. To enter: {how}. "
        "State clearly it's easy and free to enter and the winner is announced in a future episode "
        "and on Octane's social channels. Do NOT say 'live' or 'right now on air'. Keep it short and exciting."
    ),
}


def plan_episode(index):
    """Детерминированно собирает состав выпуска по его номеру — соседние выпуски разные."""
    story = STORY_ANGLES[index % len(STORY_ANGLES)]
    guest = GUESTS[index % len(GUESTS)]
    topic = EXPERT_TOPICS[index % len(EXPERT_TOPICS)]
    segment = SEGMENTS[index % len(SEGMENTS)]
    giveaway = (index % GIVEAWAY["every_n_episodes"]) == 0
    return {
        "index": index,
        "story": story,
        "guest": guest,
        "expert_topic": topic,
        "segment": segment,
        "giveaway": giveaway,
    }


def build_system_prompt(plan):
    parts = [BASE_RULES, "", "This episode's setup:",
             f"- {plan['story']['prompt']}",
             f"- Guest persona (illustrative): {plan['guest']['seed']}.",
             f"- Expert question for {EXPERT}: \"{plan['expert_topic']['q']}\" (answer ONLY from FACTS).",
             f"- {plan['segment']['prompt']}"]
    if plan["giveaway"]:
        parts.append("- " + GIVEAWAY["prompt"].format(prize=GIVEAWAY["prize"], how=GIVEAWAY["how_to_enter"]))
    else:
        parts.append("- No giveaway this episode.")
    return "\n".join(parts)
