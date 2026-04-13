import asyncio
import json
import logging
import random
import re
from playwright.async_api import async_playwright
from datetime import datetime, date, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database.models import ScrapedEvent, compute_text_hash
from database.session import AsyncSessionMaker


_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_MAX_RETRIES = 3


async def parse_event_details(browser, link: str) -> dict | None:
    """Парсинг детальной страницы с retry через цикл (не рекурсию)."""
    for attempt in range(1, _MAX_RETRIES + 1):
        page = await browser.new_page()
        await page.set_extra_http_headers({"User-Agent": _USER_AGENT})
        try:
            await asyncio.sleep(random.uniform(0.5, 2.0))
            await page.goto(link, timeout=45000, wait_until="domcontentloaded")

            title = await page.title()
            content = await page.evaluate("""() => {
                const el = document.querySelector('article')
                    || document.querySelector('main')
                    || document.body;
                return el.innerText;
            }""")
            json_ld = await page.evaluate("""() => {
                return Array.from(
                    document.querySelectorAll('script[type="application/ld+json"]')
                ).map(s => s.innerText).join('\\n\\n');
            }""")
            meta_desc = await page.evaluate("""() => {
                const m = document.querySelector('meta[property="og:description"]');
                return m ? m.content : '';
            }""")

            await page.close()

            # Извлекаем структурированные данные из JSON-LD
            event_date_str = None
            event_name = None
            event_description = None
            if json_ld:
                for block in json_ld.split("\n\n"):
                    try:
                        ld = json.loads(block.strip())
                        if isinstance(ld, dict):
                            event_name = event_name or ld.get("name")
                            event_description = event_description or ld.get("description")
                            event_date_str = event_date_str or ld.get("startDate")
                    except (json.JSONDecodeError, TypeError):
                        pass

            # Чистый текст для AI вместо технического дампа
            clean_title = (event_name or title or "").strip()
            # Убираем мусорные суффиксы типа "на Бали - описание, фото, отзывы"
            clean_title = re.sub(r"\s*на Бали\s*[-—]\s*описание.*$", "", clean_title, flags=re.IGNORECASE)
            description = event_description or meta_desc or ""
            # Берём только полезную часть content (без навигации и пр.)
            content_clean = re.sub(r"\s+", " ", content[:2000]).strip()

            raw_text = f"{clean_title}\n\n{description}\n\n{content_clean}".strip()

            return {
                "link": link,
                "raw_text": raw_text,
                "chat_title": "baliforum.ru",
                "event_date": event_date_str,
            }
        except Exception as e:
            await page.close()
            logging.warning(f"⚠️ {link} (попытка {attempt}/{_MAX_RETRIES}): {e}")
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(2 * attempt)

    logging.warning(f"💀 Сдаюсь после {_MAX_RETRIES} попыток: {link}")
    return None


async def parse_baliforum_events() -> list[dict]:
    """Парсинг baliforum.ru"""
    events_data = []
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            logging.info("📄 Открываем список событий...")
            try:
                await page.goto("https://baliforum.ru/events", timeout=60000)
                await page.wait_for_timeout(3000)
                
                # Прокручиваем больше раз, чтобы собрать больше
                for _ in range(3): 
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)
                
                cards = await page.query_selector_all('a[href^="/events/"]')
                links = set()
                for card in cards:
                    href = await card.get_attribute("href")
                    if href and href != "/events":
                        links.add(f"https://baliforum.ru{href}")
                
                logging.info(f"🔎 Найдено {len(links)} ссылок. Парсим детально...")
            finally:
                await page.close()

            # Ограничиваем параллелизм, чтобы не забанили
            semaphore = asyncio.Semaphore(4)
            
            async def protected_parse(link):
                async with semaphore:
                    res = await parse_event_details(browser, link)
                    if res:
                        logging.info(f"✅ OK: {link.split('/')[-1]}")
                    return res

            tasks = [protected_parse(link) for link in links]
            results = await asyncio.gather(*tasks)
            
            events_data = [r for r in results if r is not None]
            await browser.close()
            
    except Exception as e:
        logging.error(f"❌ Критическая ошибка парсера: {e}")
    
    return events_data


async def save_site_events(events: list[dict]) -> int:
    """Сохранить события"""
    count = 0
    if not events:
        logging.warning("📭 Нечего сохранять (пустой список событий)")
        return 0

    async with AsyncSessionMaker() as session:
        for event in events:
            text_hash = compute_text_hash(event["raw_text"])
            
            # Проверка только по ссылке (самая надежная)
            exists = await session.scalar(
                select(ScrapedEvent).where(ScrapedEvent.link == event["link"])
            )
            
            if exists:
                continue
            
            # Парсинг даты из JSON-LD
            event_date = None
            raw_date = event.get("event_date")
            if raw_date:
                try:
                    event_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00")).date()
                except (ValueError, TypeError):
                    try:
                        event_date = date.fromisoformat(raw_date[:10])
                    except (ValueError, TypeError):
                        pass

            try:
                new_event = ScrapedEvent(
                    chat_title=event["chat_title"],
                    link=event["link"],
                    raw_text=event["raw_text"],
                    text_hash=text_hash,
                    status="pending",
                    event_date=event_date,
                )
                session.add(new_event)
                await session.commit()
                count += 1
            except IntegrityError:
                await session.rollback()
    
    logging.info(f"💾 Итого сохранено в БД: {count} (из {len(events)})")
    return count


async def run_site_parser():
    logging.info("🌐 Запуск парсера сайта v3 (Reliable)...")
    events = await parse_baliforum_events()
    saved = await save_site_events(events)
    return saved


if __name__ == "__main__":
    # Уменьшаем шум от библиотек
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    asyncio.run(run_site_parser())
