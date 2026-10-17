import json
from datetime import datetime
import feedparser
from newspaper import Article
from ebooklib import epub

def build_daily_epub():
    today_str = datetime.now().strftime("%d-%m-%Y")
    book = epub.EpubBook()
    book.set_identifier(f"daily-news-{today_str}")
    book.set_title(f"Il Giornale del Mattino - {today_str}")
    book.set_language("it")
    book.add_author("Daily News Bot")

    with open("sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)

    chapters = []
    toc = []

    for source in sources:
        print(f"Lettura fonte: {source['name']}")
        feed = feedparser.parse(source["url"])
        entries = feed.entries[:source.get("max_articles", 15)]

        for entry in entries:
            try:
                article = Article(entry.link, language="it")
                article.download()
                article.parse()

                title = article.title if article.title else entry.title
                
                body_text = article.text.strip()
                if not body_text and hasattr(entry, "summary"):
                    body_text = entry.summary

                text_content = body_text.replace("\n", "<br><br>")

                chap_id = f"art_{len(chapters) + 1}"
                chapter = epub.EpubHtml(title=title, file_name=f"{chap_id}.xhtml", lang="it")
                chapter.content = f"<h2>{title}</h2><p><i>Fonte: {source['name']}</i></p><hr/><div>{text_content}</div>"

                book.add_item(chapter)
                chapters.append(chapter)
                toc.append(chapter)
                print(f"Aggiunto: {title}")
            except Exception as e:
                print(f"Salto articolo {entry.link}: {e}")

    if not chapters:
        fallback = epub.EpubHtml(title="Nessun articolo", file_name="empty.xhtml", lang="it")
        fallback.content = "<h2>Nessun articolo trovato per oggi.</h2>"
        book.add_item(fallback)
        chapters.append(fallback)
        toc.append(fallback)

    book.toc = tuple(toc)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + chapters

    # Salviamo sia il file con data sia una copia fissa "giornale_oggi.epub"
    filename = f"Giornale_{today_str}.epub"
    epub.write_epub(filename, book, {})
    epub.write_epub("giornale_oggi.epub", book, {})
    print(f"File creato con successo: {filename}")

    # Pagina HTML ultraleggera per lo schermo E-Ink del Kobo
    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Giornale Kobo</title>
    <style>
        body {{ font-family: sans-serif; text-align: center; padding: 50px 20px; background: #fff; color: #000; }}
        h1 {{ font-size: 26px; margin-bottom: 10px; }}
        p {{ font-size: 18px; margin-bottom: 35px; color: #333; }}
        a.btn {{
            display: inline-block;
            background: #000;
            color: #fff;
            text-decoration: none;
            padding: 20px 40px;
            font-size: 24px;
            font-weight: bold;
            border-radius: 6px;
        }}
    </style>
</head>
<body>
    <h1>Il Giornale del Mattino</h1>
    <p>Edizione del {today_str}</p>
    <a class="btn" href="giornale_oggi.epub">SCARICA IL GIORNALE</a>
</body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    build_daily_epub()
