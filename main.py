import asyncio

from app.db.init_db import init_db


# Точка входа для первой проверки БД.
# Пока мы просто создаем таблицы и убеждаемся, что подключение работает.
# async def main() -> None:
#     await init_db()
#     print("Tables created successfully.")
#
#
# if __name__ == "__main__":
#     asyncio.run(main())


from app.parsers.f1cosmos import parse_news_list


SAMPLE_HTML = """
<ul>
  <li>
    <a
      title="Lewis Hamilton receives bleak 'F1 limit' warning from former driver"
      href="/dashboard/news/lewis-hamilton-sent-bleak-f1-limit-warning-2651415556"
    >
      <img
        alt="Lewis Hamilton receives bleak 'F1 limit' warning from former driver"
        src="https://cdn.racingnews365.com/2026/Hamilton/Hamilton-China-Thurs.jpg"
      />
      <h3>Lewis Hamilton receives bleak 'F1 limit' warning from former driver</h3>
      <time datetime="2026-05-14">33 minutes ago</time>
      <span class="text-foreground/70">Racingnews365</span>
      <span>Analysis</span>
    </a>
  </li>
</ul>
"""


def main() -> None:
    items = parse_news_list(SAMPLE_HTML)

    for item in items:
        print(item.model_dump())


if __name__ == "__main__":
    main()