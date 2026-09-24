"""Забор следующей необработанной машины из sitemap и парсинг её страницы."""
import re
import requests
from bs4 import BeautifulSoup
from . import config

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OctanePodcastBot/1.0; +https://octane.rent)"
}
TIMEOUT = 30


def _get(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def _urls_from_sitemap(xml):
    """Достаёт <loc> из sitemap (индекса или обычного)."""
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)


def collect_car_urls():
    """Собирает все URL-кандидаты страниц авто из всех под-sitemap'ов."""
    index_xml = _get(config.SITEMAP_INDEX)
    locs = _urls_from_sitemap(index_xml)

    sub_sitemaps = [u for u in locs if u.endswith(".xml")]
    if not sub_sitemaps:
        # Индекс оказался обычным sitemap'ом
        sub_sitemaps = [config.SITEMAP_INDEX]

    pattern = re.compile(config.CAR_URL_PATTERN, re.IGNORECASE)
    car_urls = []
    seen = set()
    for sm in sub_sitemaps:
        # пропускаем заведомо нерелевантные разделы
        if any(x in sm for x in ("blog", "knowledge", "yachts", "pages")):
            continue
        try:
            xml = _get(sm)
        except Exception as e:
            print(f"[fetch] пропускаю {sm}: {e}")
            continue
        for u in _urls_from_sitemap(xml):
            if u.endswith(".xml"):
                continue
            if pattern.search(u) and u not in seen:
                # только английская версия (без /ru/ /de/ и т.п. языковых префиксов)
                if re.search(r"octane\.rent/(ru|de|nl|ar|fr|it|es|pt|da|sv|tr|zh)/", u):
                    continue
                seen.add(u)
                car_urls.append(u)
    return car_urls


def pick_next_url(state):
    """Возвращает следующий необработанный URL авто, либо None."""
    urls = collect_car_urls()
    for u in urls:
        if u not in state.get("processed_urls", []):
            return u
    return None


def _text(el):
    return el.get_text(" ", strip=True) if el else ""


def parse_car(url):
    """Парсит страницу авто. Возвращает dict с полями для сценария."""
    html = _get(url)
    soup = BeautifulSoup(html, "lxml")

    # Название
    title = ""
    if soup.find("h1"):
        title = _text(soup.find("h1"))
    if not title and soup.find("meta", property="og:title"):
        title = soup.find("meta", property="og:title").get("content", "")
    if not title and soup.title:
        title = _text(soup.title)
    title = re.sub(r"\s*\|\s*Octane.*$", "", title).strip()

    # Описание
    description = ""
    md = soup.find("meta", attrs={"name": "description"})
    if md:
        description = md.get("content", "")
    if not description:
        ogd = soup.find("meta", property="og:description")
        if ogd:
            description = ogd.get("content", "")

    # Цена (ищем AED)
    price = ""
    body_text = soup.get_text(" ", strip=True)
    m = re.search(r"(\d[\d\s,]*)\s*(?:-\s*(\d[\d\s,]*)\s*)?AED", body_text)
    if m:
        price = m.group(0).strip()

    # Характеристики (пары ключ-значение из типовых блоков спецификаций)
    specs = {}
    for row in soup.select("li, tr, .spec, .specs__item, .characteristics__item"):
        t = _text(row)
        for kw in ["engine", "power", "horsepower", "hp", "0-100", "0-60",
                   "top speed", "seats", "transmission", "year", "acceleration",
                   "doors", "fuel", "drive"]:
            if kw in t.lower() and len(t) < 80:
                specs[kw] = t
                break

    # Главное фото
    image = ""
    ogi = soup.find("meta", property="og:image")
    if ogi:
        image = ogi.get("content", "")

    return {
        "url": url,
        "title": title or "Exotic car",
        "description": description,
        "price": price,
        "specs": specs,
        "spec_text": " | ".join(specs.values()),
        "image": image,
        "raw_excerpt": body_text[:1500],
    }


if __name__ == "__main__":
    # Быстрый ручной тест
    from . import state as st
    s = st.load()
    url = pick_next_url(s)
    print("Следующий URL:", url)
    if url:
        car = parse_car(url)
        for k, v in car.items():
            if k != "raw_excerpt":
                print(f"  {k}: {v}")
