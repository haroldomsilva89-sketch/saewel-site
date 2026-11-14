"""
gerar_social.py — artes do Instagram para cada artigo do blog
==============================================================
Roda na raiz do repositório, antes do commit (junto com o update_blog_cards.py):

    python social/gerar_social.py

O que faz:
  1. Para cada artigo em /blog/<slug>/ que ainda não tem arte, gera:
       social/<slug>-post.jpg   (feed, 1080x1350)
       social/<slug>-story.jpg  (story, 1080x1920)
     usando o título (h1), o subtítulo e a etiqueta do artigo.
     Pontos opcionais: no <head> do artigo, coloque
       <meta name="social:pontos" content="Primeiro ponto|Segundo ponto|Terceiro ponto">
     Cor por tema (automática pelas palavras do artigo):
       dourado = legislação/ANEEL · verde = bateria/BESS · azul = cidades · laranja = economia
     Para forçar uma cor: <meta name="social:tema" content="verde">
  2. Coloca a arte do post como <enclosure> no item do feed.xml.
     É dela que o Make tira a imagem para postar no Instagram.

Precisa (só na primeira vez):
    pip install playwright
    python -m playwright install chromium
"""
import html, json, os, re, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITE = "https://www.saewelenergiasolar.com.br"
PASTA = RAIZ / "social"
FONTES = (RAIZ / "fonts").as_uri()
LOGO = (PASTA / "logo-social.png").as_uri()

MODELO = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Outfit;font-weight:400;src:url('%(F)s/outfit-v15-latin-300.woff2')}
@font-face{font-family:Outfit;font-weight:600;src:url('%(F)s/outfit-v15-latin-600.woff2')}
@font-face{font-family:Outfit;font-weight:700 900;src:url('%(F)s/outfit-v15-latin-700.woff2')}
@font-face{font-family:Corm;font-weight:600;src:url('%(F)s/cormorant-garamond-v21-latin-600.woff2')}
@font-face{font-family:Corm;font-style:italic;src:url('%(F)s/cormorant-garamond-v21-latin-300italic.woff2')}
*{margin:0;padding:0;box-sizing:border-box}
body{width:%(W)spx;height:%(H)spx;background:#0A0C0F;font-family:Outfit,Arial,sans-serif;color:#F8F5F0;overflow:hidden;position:relative}
.glow{position:absolute;width:900px;height:900px;border-radius:50%%;background:radial-gradient(circle,%(GLOW)s,rgba(0,0,0,0) 65%%);top:-380px;right:-320px}
.wrap{position:absolute;inset:0;padding:%(PAD)spx 80px;display:flex;flex-direction:column}
.logo{width:230px}
.eyebrow{margin-top:%(EYM)spx;font-size:30px;letter-spacing:.14em;text-transform:uppercase;color:%(C2)s;font-weight:700}
h1{margin-top:28px;font-family:Corm,Georgia,serif;font-weight:600;font-size:%(H1)spx;line-height:1.08}
h1 em{font-style:italic;color:%(C2)s;font-weight:300}
.sub{margin-top:34px;font-size:%(SUB)spx;line-height:1.4;color:#C9CED6;max-width:920px}
.pontos{margin-top:40px;display:flex;flex-direction:column;gap:18px}
.pt{display:flex;gap:18px;align-items:center;font-size:%(PT)spx}
.pt b{display:inline-flex;width:56px;height:56px;border-radius:14px;background:%(SOFT)s;align-items:center;justify-content:center;font-size:28px;flex:0 0 56px;color:%(C2)s}
.rod{margin-top:auto;display:flex;justify-content:space-between;align-items:center}
.cta{background:linear-gradient(135deg,%(C1)s,%(C2)s);color:#0A0C0F;font-weight:800;font-size:%(CTA)spx;padding:22px 38px;border-radius:999px}
.site{font-size:26px;color:#9BA3AD}
.barra{position:absolute;left:0;right:0;bottom:0;height:10px;background:linear-gradient(90deg,%(C1)s,%(C2)s)}
</style></head><body><div class="glow"></div><div class="wrap">
<img class="logo" src="%(LOGO)s">
<div class="eyebrow">Novo no blog · %(TAG)s</div>
<h1>%(TIT)s</h1>
<div class="sub">%(SUBT)s</div>
%(PONTOS)s
<div class="rod"><div class="cta">%(CTATXT)s</div><div class="site">saewelenergiasolar.com.br</div></div>
</div><div class="barra"></div></body></html>"""

# Cor por tema: o seguidor reconhece o assunto de longe na grade do Instagram.
TEMAS = {
    "dourado": dict(C1="#C8922A", C2="#E8B84B", GLOW="rgba(232,184,75,.28)", SOFT="rgba(200,146,42,.16)"),   # legislação, ANEEL, tarifas
    "verde":   dict(C1="#16A34A", C2="#4ADE80", GLOW="rgba(74,222,128,.24)", SOFT="rgba(74,222,128,.14)"),    # bateria, BESS, backup
    "azul":    dict(C1="#2563EB", C2="#60A5FA", GLOW="rgba(96,165,250,.26)", SOFT="rgba(96,165,250,.14)"),    # cidades, raio-x solar
    "laranja": dict(C1="#EA580C", C2="#FB923C", GLOW="rgba(251,146,60,.26)", SOFT="rgba(251,146,60,.14)"),    # economia, preço, payback
}
PALAVRAS_TEMA = [   # a primeira que bater define a cor (procura na etiqueta, no título e no endereço do artigo)
    ("verde",   ["bateria", "bess", "armazenamento", "backup", "híbrido", "hibrido", "queda de luz"]),
    ("azul",    ["raio-x", "cidade", "seo local", "rio preto", "mirassol", "catanduva", "olímpia", "olimpia",
                 "votuporanga", "bady", "bonifácio", "bonifacio", "promissão", "promissao", "nova aliança", "novo horizonte"]),
    ("laranja", ["economia", "custa", "preço", "preco", "payback", "financiamento", "vale a pena", "fatura", "conta de luz"]),
    ("dourado", ["aneel", "lei", "tarifa", "legislação", "legislacao", "resolução", "resolucao", "norma"]),
]


def tema_do_artigo(slug, d):
    """Força a cor com <meta name="social:tema" content="verde"> no artigo; senão, descobre pelas palavras."""
    if d.get("TEMA") in TEMAS:
        return d["TEMA"]
    texto = " ".join([d["TAG"], re.sub(r"<[^>]+>", " ", d["TIT"]), slug.replace("-", " ")]).lower()
    curto = " ".join([d["TAG"], slug.replace("-", " ")]).lower()   # cidade só pela etiqueta/endereço: muito artigo cita "Rio Preto" no título
    for tema, palavras in PALAVRAS_TEMA:
        base = curto if tema == "azul" else texto
        if any(p in base for p in palavras):
            return tema
    return "dourado"


FORMATOS = {
    "post": dict(W=1080, H=1350, PAD=80, EYM=70, H1=92, SUB=36, PT=34, CTA=30, CTATXT="Leia no blog → link na bio"),
    "story": dict(W=1080, H=1920, PAD=150, EYM=140, H1=110, SUB=42, PT=40, CTA=34, CTATXT="Leia o artigo → link na bio"),
}


def limpar(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t))).strip()


def dados_artigo(arq):
    s = arq.read_text(encoding="utf-8")
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', s, re.S)
    if not h1:
        return None
    tit = re.sub(r"<(?!/?em\b|br\b)[^>]+>", "", h1.group(1)).strip()   # mantém só <em> e <br>
    sub = re.search(r'class="article-subtitle"[^>]*>(.*?)</p>', s, re.S)
    eyb = re.search(r'class="article-eyebrow"[^>]*>([^<]+)<', s)
    pts = re.search(r'<meta name="social:pontos" content="([^"]+)"', s)
    tema = re.search(r'<meta name="social:tema" content="([^"]+)"', s)
    subt = limpar(sub.group(1)) if sub else ""
    if len(subt) > 170:
        subt = subt[:170].rsplit(" ", 1)[0] + "…"
    return {
        "TIT": tit,
        "SUBT": html.escape(subt),
        "TAG": html.escape(eyb.group(1).split("·")[0].strip() if eyb else "Energia Solar"),
        "PONTOS_LISTA": [p.strip() for p in pts.group(1).split("|")][:3] if pts else [],
        "TEMA": tema.group(1).strip().lower() if tema else "",
    }


def gerar(pendentes):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch(args=["--allow-file-access-from-files"])
        for slug, d in pendentes:
            pontos = ""
            if d["PONTOS_LISTA"]:
                pontos = '<div class="pontos">' + "".join(
                    '<div class="pt"><b>✓</b>%s</div>' % html.escape(x) for x in d["PONTOS_LISTA"]) + "</div>"
            cores = TEMAS[tema_do_artigo(slug, d)]
            for nome, cfg in FORMATOS.items():
                h = MODELO % dict(cfg, F=FONTES, LOGO=LOGO, PONTOS=pontos, **cores,
                                  **{k: v for k, v in d.items() if k not in ("PONTOS_LISTA", "TEMA")})
                tmp = PASTA / ("_tmp_%s.html" % nome)
                tmp.write_text(h, encoding="utf-8")
                pg = nav.new_page(viewport={"width": cfg["W"], "height": cfg["H"]})
                pg.goto(tmp.as_uri())
                pg.wait_for_timeout(700)
                pg.screenshot(path=str(PASTA / ("%s-%s.jpg" % (slug, nome))), type="jpeg", quality=88)
                pg.close()
                tmp.unlink()
            print("  🖼  arte gerada:", slug, "(cor: %s)" % tema_do_artigo(slug, d))
        nav.close()


def atualizar_feed():
    feed = RAIZ / "feed.xml"
    s = feed.read_text(encoding="utf-8")
    novo = s
    for item in re.findall(r"<item>.*?</item>", s, re.S):
        if "<enclosure" in item:
            continue
        link = re.search(r"<link>([^<]+)</link>", item)
        m = re.search(r"/blog/([^/]+)/", link.group(1)) if link else None
        if not m:
            continue
        img = PASTA / ("%s-post.jpg" % m.group(1))
        if not img.exists():
            continue
        enc = '      <enclosure url="%s/social/%s-post.jpg" length="%d" type="image/jpeg"/>\n' % (
            SITE, m.group(1), img.stat().st_size)
        k = item.rfind("</item>")
        linha_ini = item.rfind("\n", 0, k) + 1
        novo = novo.replace(item, item[:linha_ini] + enc + item[linha_ini:], 1)
    if novo != s:
        feed.write_text(novo, encoding="utf-8")
        print("  📰 feed.xml: imagem incluída nos itens novos")


def main():
    pendentes = []
    for arq in sorted((RAIZ / "blog").glob("*/index.html")):
        slug = arq.parent.name
        if (PASTA / ("%s-post.jpg" % slug)).exists():
            continue
        d = dados_artigo(arq)
        if d:
            pendentes.append((slug, d))
    if "--todos" not in sys.argv:
        # por padrão, só o artigo mais recente do feed (o que acabou de ser publicado)
        feed = (RAIZ / "feed.xml").read_text(encoding="utf-8")
        prim = re.search(r"<item>.*?<link>[^<]*/blog/([^/]+)/", feed, re.S)
        alvo = prim.group(1) if prim else ""
        pendentes = [(s, d) for s, d in pendentes if s == alvo]
    if pendentes:
        print("Gerando artes de %d artigo(s)..." % len(pendentes))
        gerar(pendentes)
    else:
        print("Nenhuma arte nova para gerar.")
    atualizar_feed()


if __name__ == "__main__":
    main()
