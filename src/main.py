"""Оркестратор: один запуск = один (или CARS_PER_RUN) новый эпизод.

Шаги: выбрать машину -> распарсить -> сценарий -> озвучка -> субтитры -> видео
       -> (опц.) загрузка на YouTube -> обновить state -> (опц.) RSS.
Запуск: python -m src.main   (продакшн)
        python -m src.main --test   (без платных ключей: шаблон + gTTS, без загрузки)
"""
import os
import re
import sys
import datetime
from . import (config, state as st, fetch_car, generate_script, synthesize,
               subtitles, build_video, build_feed)


def slugify(text):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "episode"


def run_once(state):
    url = fetch_car.pick_next_url(state)
    if not url:
        print("[main] новых машин нет — все URL обработаны. Пропускаю.")
        return False

    print(f"[main] машина: {url}")
    car = fetch_car.parse_car(url)
    print(f"[main] распознано: {car['title']} | {car.get('price')}")

    episode_index = len(state.get("episodes", []))
    script = generate_script.generate(car, episode_index=episode_index)
    print(f"[main] сценарий: {len(script['lines'])} реплик, план: {script.get('plan')}")

    date_str = datetime.date.today().isoformat()
    slug = slugify(car["title"])
    base = f"{date_str}-{slug}"

    # 1) Аудио
    audio_path = str(config.EPISODES_DIR / f"{base}.mp3")
    meta = synthesize.synthesize(script["lines"], audio_path)
    print(f"[main] аудио: {meta['duration_sec']}с -> {base}.mp3")

    # 2) Субтитры (SRT)
    srt_path = str(config.EPISODES_DIR / f"{base}.srt")
    subtitles.build_srt(meta["segments"], srt_path)

    # 3) Видео (заставка + фото + вшитые субтитры)
    video_path = None
    if config.VIDEO_ENABLED:
        try:
            img_path = build_video.download_image(
                car.get("image", ""), str(config.TMP_DIR / f"{base}.jpg"))
            video_path = str(config.VIDEOS_DIR / f"{base}.mp4")
            vinfo = build_video.build_video(
                image_path=img_path, audio_path=audio_path, srt_path=srt_path,
                title_text=car["title"], out_path=video_path, tmp_dir=str(config.TMP_DIR))
            print(f"[main] видео: {vinfo['duration_sec']}с -> {base}.mp4")
        except Exception as e:
            print(f"[main] сборка видео не удалась ({e}) — продолжаю без видео")
            video_path = None

    # 4) Загрузка на YouTube
    youtube = None
    if config.YOUTUBE_ENABLED and video_path and os.path.exists(video_path):
        try:
            from . import youtube_upload
            tags = ["Octane Rent", car["title"], "car rental Dubai", "luxury car rental",
                    "exotic car", "supercar", "Dubai", "Abu Dhabi"]
            youtube = youtube_upload.upload(
                video_path,
                title=script.get("youtube_title", car["title"]),
                description=script.get("episode_description", ""),
                tags=tags, srt_path=srt_path)
            print(f"[main] YouTube: {youtube['url']}")
        except Exception as e:
            print(f"[main] загрузка на YouTube не удалась ({e})")

    episode = {
        "file": f"{base}.mp3",
        "video": f"{base}.mp4" if video_path and os.path.exists(video_path) else "",
        "srt": f"{base}.srt",
        "title": script.get("episode_title", car["title"]),
        "description": script.get("episode_description", car.get("description", "")),
        "youtube_title": script.get("youtube_title", car["title"]),
        "youtube_url": (youtube or {}).get("url", ""),
        "plan": script.get("plan", {}),
        "source_url": url,
        "image": car.get("image", ""),
        "pub_date": build_feed.now_rfc2822(),
        "duration_sec": meta["duration_sec"],
        "bytes": meta["bytes"],
    }
    st.mark_processed(state, url)
    st.add_episode(state, episode)
    return True


def main():
    # --test: без платных ключей (шаблон + бесплатная озвучка), без загрузки на YouTube
    if "--test" in sys.argv:
        os.environ["SCRIPT_PROVIDER"] = "none"
        os.environ["TTS_PROVIDER"] = os.environ.get("TTS_PROVIDER", "gtts")
        config.SCRIPT_PROVIDER = "none"
        config.TTS_PROVIDER = os.environ["TTS_PROVIDER"]
        config.YOUTUBE_ENABLED = False
        print("[main] ТЕСТ-режим: шаблон сценария + бесплатная озвучка, без загрузки")

    state = st.load()
    made = 0
    for _ in range(max(1, config.CARS_PER_RUN)):
        try:
            if run_once(state):
                made += 1
            else:
                break
        except Exception as e:
            print(f"[main] ошибка на эпизоде: {e}")
            break

    if made:
        st.save(state)
        if config.RSS_ENABLED:
            feed = build_feed.build(state)
            print(f"[main] RSS обновлён: {feed}")
        print(f"[main] готово: +{made} эпизод(ов).")
    else:
        if config.RSS_ENABLED:
            build_feed.build(state)
        print("[main] новых эпизодов нет.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
