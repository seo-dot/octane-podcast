"""Генерация сценария подкаста (диалог двух ведущих) + SEO-заголовок и описание.

Провайдеры LLM: groq (бесплатно, по умолчанию), openai, anthropic, gemini.
Каждый выпуск использует один "угол подачи" из src/angles.py — приложение чередует
их по порядковому номеру эпизода, поэтому выпуски получаются РАЗНЫМИ.

Если провайдер = none или нет ключа — используется офлайн-шаблон (fallback),
чтобы пайплайн работал даже без LLM.
"""
import json
import re
from . import config, angles, knowledge


_CITIES = {"dubai": "Dubai", "abu-dhabi": "Abu Dhabi", "sharjah": "Sharjah", "miami": "Miami"}


def _city_of(car):
    """Город из URL (напр. .../suv-cars-sharjah/...) или из названия ('... in Dubai')."""
    hay = f"{car.get('url', '')} {car.get('title', '')}".lower()
    for key, nice in _CITIES.items():
        if key in hay or key.replace("-", " ") in hay:
            return nice
    return "the UAE"


def _clean_car_name(title):
    """'Rent Mercedes G63 in Sharjah' -> 'Mercedes G63'."""
    name = re.sub(r"^\s*Rent\s+", "", title or "", flags=re.IGNORECASE)
    name = re.sub(r"\s+in\s+(Dubai|Abu Dhabi|Sharjah|Miami)\s*$", "", name, flags=re.IGNORECASE)
    return name.strip() or (title or "this car")


def _build_user_prompt(car, facts):
    return (
        f"Car page: {car['url']}\n"
        f"Name: {car['title']}\n"
        f"Car (clean name): {_clean_car_name(car['title'])}\n"
        f"City: {_city_of(car)}\n"
        f"Rental price: {car.get('price') or 'not specified'}\n"
        f"Specs: {car.get('spec_text') or 'not specified'}\n"
        f"Page description: {car.get('description') or ''}\n\n"
        f"{facts}\n"
    )


def _extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        text = m.group(0)
    return json.loads(text)


# ---------- Провайдеры ----------

def _gen_openai_compatible(system, user, api_key, base_url, model):
    """Groq и OpenAI используют один и тот же клиент (OpenAI-совместимый API)."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.9,  # выше -> заметнее вариативность между выпусками
    )
    try:
        kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
    except Exception:
        kwargs.pop("response_format", None)
        resp = client.chat.completions.create(**kwargs)
    return _extract_json(resp.choices[0].message.content)


def _gen_anthropic(system, user):
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model="claude-3-5-haiku-latest",
        max_tokens=2000,
        temperature=0.9,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return _extract_json(resp.content[0].text)


def _gen_gemini(system, user):
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    resp = model.generate_content(system + "\n\n" + user)
    return _extract_json(resp.text)


VALID_SPEAKERS = {"A", "B", "G", "E"}


def _gen_fallback(car, plan):
    """Офлайн-шаблон без LLM: полноценный эпизод с гостем, экспертом, рубрикой, розыгрышем."""
    name = car["title"]
    price = car.get("price") or "great daily rates"
    specs = car.get("spec_text") or ""
    guest = plan["guest"]["seed"]
    lines = [
        ("A", f"Welcome back to Octane Drive Stories. Today's car — the {name}."),
        ("B", f"And we've got a guest who just spent time with it. Say hi!"),
        ("G", f"Hey! So — {guest.split(',')[0]} here, and honestly the {name} made my trip."),
        ("G", f"They delivered it straight to my hotel, quick handover, and off I went across the city."),
        ("A", f"{('What we know spec-wise: ' + specs + '.') if specs else 'It turns heads everywhere in Dubai.'}"),
        ("B", f"Daria, quick expert question — {plan['expert_topic']['q']}"),
        ("E", "Great question. Based on Octane's terms: no security deposit on most cars, "
              "basic insurance is generally included, and a rental day is 24 hours. Exact "
              "conditions are always set per car in the contract."),
        ("A", f"Love that. And pricing on the {name} starts around {price}."),
        ("B", f"Quick rubric — {plan['segment']['name']}: a great match for this car and a UAE spot worth the drive."),
    ]
    if plan["giveaway"]:
        lines.append(("A", "Before we go — our giveaway is on: win a professional photoshoot with a "
                           "Lamborghini. Subscribe and comment your dream Octane car to enter — "
                           "winner announced in a future episode."))
    lines += [
        ("B", f"That's the {name}. Book it in Dubai, Abu Dhabi, Sharjah or Miami at octane dot rent."),
        ("A", "See you on the next drive."),
    ]
    clean_name = _clean_car_name(name)
    city = _city_of(car)
    return {
        "youtube_title": f"Renting the {clean_name} in {city} — My Octane Rent Experience",
        "episode_title": f"{name} — {plan['story']['name']}",
        "episode_description": (
            f"Octane Drive Stories: a guest's experience with the {name}, plus expert rental tips "
            f"from Daria. Rental from {price}. Book in Dubai, Abu Dhabi, Sharjah or Miami at https://octane.rent"
        ),
        "lines": [{"speaker": s, "text": t} for s, t in lines],
    }


def generate(car, episode_index=0):
    """episode_index — номер выпуска: определяет состав (гость, эксперт, рубрика, розыгрыш)."""
    plan = angles.plan_episode(episode_index)
    facts = knowledge.facts_text()
    system = angles.build_system_prompt(plan)
    user = _build_user_prompt(car, facts)
    provider = config.SCRIPT_PROVIDER

    try:
        if provider == "openrouter" and config.OPENROUTER_API_KEY:
            data = _gen_openai_compatible(system, user, config.OPENROUTER_API_KEY,
                                          config.OPENROUTER_BASE_URL, config.OPENROUTER_MODEL)
        elif provider == "groq" and config.GROQ_API_KEY:
            data = _gen_openai_compatible(system, user, config.GROQ_API_KEY,
                                          config.GROQ_BASE_URL, config.GROQ_MODEL)
        elif provider == "openai" and config.OPENAI_API_KEY:
            data = _gen_openai_compatible(system, user, config.OPENAI_API_KEY, None, "gpt-4o-mini")
        elif provider == "anthropic" and config.ANTHROPIC_API_KEY:
            data = _gen_anthropic(system, user)
        elif provider == "gemini" and config.GEMINI_API_KEY:
            data = _gen_gemini(system, user)
        else:
            print(f"[script] провайдер '{provider}' недоступен/без ключа — шаблон.")
            data = _gen_fallback(car, plan)
    except Exception as e:
        print(f"[script] ошибка LLM ({e}); шаблон.")
        data = _gen_fallback(car, plan)

    # Валидация/нормализация
    if not data.get("lines"):
        data = _gen_fallback(car, plan)
    for ln in data["lines"]:
        sp = str(ln.get("speaker", "A")).upper().strip()[:1]
        ln["speaker"] = sp if sp in VALID_SPEAKERS else "A"
        ln["text"] = str(ln.get("text", "")).strip()
    data["lines"] = [ln for ln in data["lines"] if ln["text"]]
    data.setdefault("youtube_title", car["title"])
    data.setdefault("episode_title", car["title"])
    data.setdefault("episode_description", car.get("description", ""))
    data["angle"] = plan["story"]["key"]
    data["plan"] = {
        "story": plan["story"]["key"], "guest": plan["guest"]["key"],
        "expert_topic": plan["expert_topic"]["key"], "segment": plan["segment"]["key"],
        "giveaway": plan["giveaway"],
    }
    return data


if __name__ == "__main__":
    demo = {"url": "https://octane.rent/sports-cars/lamborghini-huracan-for-rent-dubai/",
            "title": "Lamborghini Huracan", "price": "2500 AED",
            "spec_text": "engine V10 | 640 hp | 0-100 3.2s", "description": ""}
    for i in range(3):
        out = generate(demo, episode_index=i)
        print(f"\n=== эпизод {i} ===", out["plan"])
        print(out["youtube_title"])
