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
        feed = feedparser.parse(source["url"])
        entries = feed.entries[:source.get("max_articles", 15)]

        for entry in entries:
            try:
                article = Article(entry.link, language="it")
                article.download()
                article.parse()

                title = article.title or entry.title
                text_content = article.text.replace("\n", "<br><br>")

                chap_id = f"art_{len(chapters) + 1}"
                chapter = epub.EpubHtml(title=title, file_name=f"{chap_id}.xhtml", lang="it")
                chapter.content = f"<h2>{title}</h2><p><i>Fonte: {source['name']}</i></p><hr/><div>{text_content}</div>"

                book.add_item(chapter)
                chapters.append(chapter)
                toc.append(chapter)
            except Exception as e:
                print(f"Errore su {entry.link}: {e}")

    book.toc = tuple(toc)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + chapters

    filename = f"Giornale_{today_str}.epub"
    epub.write_epub(filename, book, {})
    print(f"Creato con successo: {filename}")

if __name__ == "__main__":
    build_daily_epub()
