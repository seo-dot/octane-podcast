"""Реальные факты об аренде и компании — «источник правды» для экспертных блоков.

Тянет машиночитаемые данные с octane.rent (policies.json, company.json), кэширует
в knowledge.json и отдаёт компактный текст фактов для промпта. Эксперт (Дарья) и гости
опираются ТОЛЬКО на эти факты и не выдумывают правил/цифр.

Если сеть недоступна — используется VERIFIED_FALLBACK (факты, снятые с сайта вручную),
чтобы пайплайн всегда работал.
"""
import json
import time
import requests
from . import config

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; OctanePodcastBot/1.0; +https://octane.rent)"}
TIMEOUT = 30
CACHE_TTL_SEC = 24 * 3600  # обновлять знания не чаще раза в сутки

POLICIES_URL = f"{config.PODCAST_SITE}/policies.json"
COMPANY_URL = f"{config.PODCAST_SITE}/company.json"
KNOWLEDGE_CACHE = config.ROOT / "knowledge.json"

# --- Факты, снятые с octane.rent (fallback, если сеть недоступна) ---
VERIFIED_FALLBACK = {
    "rental_rules": [
        "Minimum driver age varies by car, commonly from 21+.",
        "A valid driving license is required; eligibility depends on residency and issuing country; some drivers need an international permit.",
        "A valid passport is required as ID; UAE nationals and residents may use Emirates ID.",
        "No security deposit is required on most vehicles; any deposit is specified per car in the rental contract.",
        "Basic insurance is generally included; extended coverage depends on the offer.",
        "For per-day rental, one day means 24 hours.",
        "Mileage limits may apply depending on the vehicle and are agreed in the contract.",
        "Car delivery to hotel, airport, home or office may be available.",
        "Prohibited use: driving under the influence, racing, drifting, off-road, unpaved roads, standing water, and towing.",
        "Traffic fines, parking and Salik (tolls) are usually paid separately.",
    ],
    "company_facts": [
        "Octane Rent operates in Dubai, Abu Dhabi, Sharjah and Miami.",
        "Available 24/7.",
        "Fleet of 400+ vehicles: luxury, sports, SUV and economy.",
        "Fast booking and delivery across service areas.",
        "No security deposit on most vehicles; transparent pricing.",
        "Dubai location: Al Quoz Industrial Area 3, 22nd Street, Warehouse 3.",
        "Contact: +971 4 253 6700, info@octane.rent, https://octane.rent",
    ],
}


def _fetch_json(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _flatten(obj, out, prefix=""):
    """Разворачивает произвольный JSON в список коротких строк-фактов."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(v, out, f"{prefix}{k}: " if not prefix else f"{prefix}{k} ")
    elif isinstance(obj, list):
        for v in obj:
            _flatten(v, out, prefix)
    else:
        s = f"{prefix}{obj}".strip()
        if 3 < len(s) < 240:
            out.append(s)


def refresh(force=False):
    """Обновляет кэш знаний с сайта (не чаще раза в сутки). Возвращает dict знаний."""
    if not force and KNOWLEDGE_CACHE.exists():
        age = time.time() - KNOWLEDGE_CACHE.stat().st_mtime
        if age < CACHE_TTL_SEC:
            try:
                return json.loads(KNOWLEDGE_CACHE.read_text(encoding="utf-8"))
            except Exception:
                pass

    data = {"rental_rules": [], "company_facts": []}
    try:
        pol = _fetch_json(POLICIES_URL)
        _flatten(pol, data["rental_rules"])
    except Exception as e:
        print(f"[knowledge] policies.json недоступен ({e}) — fallback")
    try:
        comp = _fetch_json(COMPANY_URL)
        _flatten(comp, data["company_facts"])
    except Exception as e:
        print(f"[knowledge] company.json недоступен ({e}) — fallback")

    # если что-то не забралось — подставляем проверенный fallback
    if len(data["rental_rules"]) < 4:
        data["rental_rules"] = VERIFIED_FALLBACK["rental_rules"]
    if len(data["company_facts"]) < 3:
        data["company_facts"] = VERIFIED_FALLBACK["company_facts"]

    # дедуп + ограничение объёма
    data["rental_rules"] = list(dict.fromkeys(data["rental_rules"]))[:40]
    data["company_facts"] = list(dict.fromkeys(data["company_facts"]))[:25]

    try:
        KNOWLEDGE_CACHE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[knowledge] не удалось сохранить кэш: {e}")
    return data


def facts_text(knowledge=None):
    """Компактный блок фактов для промпта."""
    k = knowledge or refresh()
    rules = "\n".join(f"- {x}" for x in k.get("rental_rules", []))
    company = "\n".join(f"- {x}" for x in k.get("company_facts", []))
    return (
        "VERIFIED OCTANE RENT FACTS (use ONLY these for any rental rules / company claims; "
        "never invent numbers, deposits, ages or policies):\n"
        f"[Rental rules]\n{rules}\n[Company]\n{company}"
    )


if __name__ == "__main__":
    k = refresh(force=True)
    print(facts_text(k))
