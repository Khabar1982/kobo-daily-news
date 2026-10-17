import json
from datetime import datetime
import feedparser
import requests
from bs4 import BeautifulSoup
from ebooklib import epub

def get_clean_article(url, fallback_summary):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 14542.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Cerca i contenitori dell'articolo usati da Il Post
            article_body = (
                soup.find("div", class_="entry-content")
                or soup.find("div", id="singleArticleBody")
                or soup.find("article")
            )
            
            if article_body:
                paragraphs = article_body.find_all("p")
                valid_p = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20]
                if len(valid_p) >= 2:
                    return "<br><br>".join(valid_p)
    except Exception as e:
        print(f"Errore lettura pagina {url}: {e}")

    # Se la pagina web non risponde o è bloccata, usa il testo del feed RSS
    clean_summary = BeautifulSoup(fallback_summary, "html.parser").get_text().strip()
    if clean_summary:
        return clean_summary.replace("\n", "<br><br>")
    return "Contenuto non disponibile in versione testuale."

def build_daily_epub():
    today_str = datetime.now().strftime("%d-%m-%Y")
    book = epub.EpubBook()
    book.set_identifier(f"kobo-daily-{today_str}")
    book.set_title(f"Il Giornale del Mattino - {today_str}")
    book.set_language("it")
    book.add_author("Il Post Bot")

    with open("sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)

    chapters = []
    toc = []
    seen_urls = set()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for source in sources:
        try:
            # Scarica il feed RSS con header reale per evitare blocchi
            resp = requests.get(source["url"], headers=headers, timeout=15)
            feed = feedparser.parse(resp.content)
            entries = feed.entries[:source.get("max_articles", 10)]

            for entry in entries:
                url = getattr(entry, "link", None)
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                title = getattr(entry, "title", "Articolo senza titolo")
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                
                content = get_clean_article(url, summary)

                chap_id = f"art_{len(chapters) + 1}"
                chapter = epub.EpubHtml(title=title, file_name=f"{chap_id}.xhtml", lang="it")
                chapter.content = f"<h2>{title}</h2><p style='color:#666;'><i>{source['name']}</i></p><hr/><div style='font-size:1.1em; line-height:1.5;'>{content}</div>"

                book.add_item(chapter)
                chapters.append(chapter)
                toc.append(chapter)
                print(f"Inserito articolo: {title}")
        except Exception as err:
            print(f"Errore caricamento feed {source['name']}: {err}")

    if not chapters:
        fallback = epub.EpubHtml(title="Nessun articolo", file_name="empty.xhtml", lang="it")
        fallback.content = "<h2>Nessun articolo disponibile per oggi.</h2>"
        book.add_item(fallback)
        chapters.append(fallback)
        toc.append(fallback)

    book.toc = tuple(toc)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + chapters

    filename = f"Giornale_{today_str}.epub"
    epub.write_epub(filename, book, {})
    epub.write_epub("giornale_oggi.epub", book, {})
    print(f"Compilazione completata con {len(chapters)} articoli.")

    # Pagina HTML minimale per il Kobo Clara BW
    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Giornale Kobo</title>
    <style>
        body {{ font-family: sans-serif; text-align: center; padding: 40px 15px; background: #fff; color: #000; }}
        h1 {{ font-size: 26px; margin-bottom: 8px; }}
        p {{ font-size: 18px; margin-bottom: 30px; color: #444; }}
        a.btn {{
            display: inline-block;
            background: #000;
            color: #fff;
            text-decoration: none;
            padding: 18px 36px;
            font-size: 22px;
            font-weight: bold;
            border-radius: 6px;
        }}
    </style>
</head>
<body>
    <h1>Il Giornale del Mattino</h1>
    <p>Edizione del {today_str} ({len(chapters)} articoli)</p>
    <a class="btn" href="giornale_oggi.epub">SCARICA IL GIORNALE</a>
</body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    build_daily_epub()
