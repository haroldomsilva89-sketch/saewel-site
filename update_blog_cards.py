"""
update_blog_cards.py
====================
Roda antes de fazer commit/push no GitHub.
Lê todos os artigos da pasta /blog, pega os 3 mais recentes
pelo datePublished e atualiza automaticamente a seção de artigos no index.html.

USO:
  python update_blog_cards.py

REQUISITOS:
  Python 3.6+ (sem dependências externas)
"""

import os
import re
import json
from pathlib import Path

# ── Configuração ──────────────────────────────────────────────
BLOG_DIR   = Path("blog")          # pasta do blog
INDEX_FILE = Path("index.html")    # index.html da raiz
NUM_CARDS  = 3                     # quantos cards mostrar
# ─────────────────────────────────────────────────────────────

def extract_article_data(html_path):
    """Extrai título, descrição, tag, data e URL de um artigo."""
    try:
        content = html_path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Data via Schema.org datePublished
    date_match = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})"', content)
    if not date_match:
        return None
    date = date_match.group(1)

    # Título via <title>
    title_match = re.search(r'<title>([^<]+)</title>', content)
    title = title_match.group(1).split('|')[0].strip() if title_match else ""

    # Descrição via meta description
    desc_match = re.search(r'meta name="description" content="([^"]+)"', content)
    desc = desc_match.group(1)[:120] if desc_match else ""

    # Tag via article-eyebrow (primeira parte antes do ·)
    eyebrow_match = re.search(r'class="article-eyebrow"[^>]*>([^<]+)<', content)
    if eyebrow_match:
        tag = eyebrow_match.group(1).strip().split('·')[0].strip()
    else:
        tag = "Blog"

    # URL — derivada do caminho da pasta
    folder = html_path.parent
    url = "/" + str(folder).replace("\\", "/") + "/"

    return {
        "date": date,
        "title": title,
        "desc": desc,
        "tag": tag,
        "url": url,
    }


def find_all_articles():
    """Encontra todos os index.html dentro de /blog/*/."""
    articles = []
    if not BLOG_DIR.exists():
        print(f"⚠️  Pasta '{BLOG_DIR}' não encontrada. Execute na raiz do repositório.")
        return articles

    for html_file in BLOG_DIR.rglob("index.html"):
        # Ignorar o index.html da capa do blog (/blog/index.html)
        if html_file.parent == BLOG_DIR:
            continue
        data = extract_article_data(html_file)
        if data:
            articles.append(data)

    # Ordenar do mais recente para o mais antigo
    articles.sort(key=lambda x: x["date"], reverse=True)
    return articles


def build_cards_html(articles):
    """Gera o HTML dos cards com os N artigos mais recentes."""
    cards_html = []
    for i, art in enumerate(articles[:NUM_CARDS]):
        tag = art["tag"]
        if i == 0:
            tag += " · Novo"
        cards_html.append(f'''        <a href="{art['url']}" class="blog-card">
          <div class="blog-card-tag">{tag}</div>
          <div class="blog-card-title">{art['title']}</div>
          <div class="blog-card-desc">{art['desc']}</div>
        </a>''')

    return (
        '      <div class="blog-cards-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-bottom:40px;">\n'
        + "\n".join(cards_html)
        + '\n      </div>'
    )


def update_index(new_cards_html):
    """Substitui o bloco de cards no index.html."""
    if not INDEX_FILE.exists():
        print(f"⚠️  '{INDEX_FILE}' não encontrado. Execute na raiz do repositório.")
        return False

    content = INDEX_FILE.read_text(encoding="utf-8")

    # Encontrar o bloco atual de cards
    pattern = re.compile(
        r'<div class="blog-cards-grid".*?</div>\s*</div>',
        re.DOTALL
    )

    match = pattern.search(content)
    if not match:
        print("⚠️  Bloco de cards não encontrado no index.html.")
        return False

    new_content = content[:match.start()] + new_cards_html + content[match.end():]
    INDEX_FILE.write_text(new_content, encoding="utf-8")
    return True


def main():
    print("🔍 Lendo artigos do blog...")
    articles = find_all_articles()

    if not articles:
        print("⚠️  Nenhum artigo encontrado em /blog/.")
        return

    print(f"✓ {len(articles)} artigo(s) encontrado(s)")
    print("\n📋 Os 3 mais recentes:")
    for i, art in enumerate(articles[:NUM_CARDS]):
        marker = "⭐ NOVO" if i == 0 else f"  {i+1}."
        print(f"  {marker} [{art['date']}] {art['title'][:60]}")

    print("\n📝 Atualizando index.html...")
    new_cards = build_cards_html(articles)

    if update_index(new_cards):
        print("✅ index.html atualizado com sucesso!")
        print("\n💡 Próximo passo: faça o commit e push normalmente.")
    else:
        print("❌ Falha ao atualizar index.html.")


if __name__ == "__main__":
    main()
