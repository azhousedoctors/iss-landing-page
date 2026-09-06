#!/usr/bin/env python3
"""
Shared post-processing for the Claude Design exports (build_landing.py,
build_apply.py).

Two things the exports do not do for themselves:
  * every PNG is inlined as a base64 data URI, which made the landing page ~80%
    image bytes, uncacheable, and impossible to lazy-load;
  * no <title>, description, canonical, or social tags, so search results and
    shared links rendered blank.
Both are fixed at build time rather than in the export, so re-exporting from
Claude Design cannot silently drop them.
"""
import re, os, sys, html, base64, hashlib, io

IMG_DIR = "img"
IMG_MAX_W = 1100    # report examples must stay legible; this is near native width
IMG_QUALITY = 85


def externalize_images(doc):
    """Write inlined PNGs out as content-hashed WebP files and repoint the tags.

    Content hashing means an image repeated across the page (or across both
    pages) is stored and downloaded exactly once. Returns (doc, bytes_saved).
    """
    try:
        from PIL import Image
    except ImportError:
        sys.stderr.write("Pillow not available - leaving images inlined\n")
        return doc, 0

    os.makedirs(IMG_DIR, exist_ok=True)
    saved = [0]
    cache = {}

    def repl(m):
        raw = base64.b64decode(m.group(1))
        digest = hashlib.sha1(raw).hexdigest()[:8]
        if digest not in cache:
            path = os.path.join(IMG_DIR, digest + ".webp")
            if not os.path.exists(path):
                im = Image.open(io.BytesIO(raw))
                if im.width > IMG_MAX_W:
                    im = im.resize(
                        (IMG_MAX_W, round(im.height * IMG_MAX_W / im.width)),
                        Image.LANCZOS,
                    )
                im.save(path, "WEBP", quality=IMG_QUALITY, method=6)
            cache[digest] = "/" + path
            saved[0] += len(raw) - os.path.getsize(path)
        return cache[digest]

    doc = re.sub(r"data:image/png;base64,([A-Za-z0-9+/=]+)", repl, doc)

    # Everything below the first image can load lazily.
    first = [True]

    def add_lazy(m):
        tag = m.group(0)
        if first[0]:
            first[0] = False
            return tag
        if "loading=" in tag:
            return tag
        return tag[:4] + ' loading="lazy" decoding="async"' + tag[4:]

    doc = re.sub(r'<img\b[^>]*src="/img/[^"]+"[^>]*>', add_lazy, doc)
    return doc, saved[0]


def inject_head_meta(doc, title, description, canonical, image):
    """Add title/description/canonical/OpenGraph tags and declare the language."""
    if "<title>" in doc:
        return doc
    e = html.escape
    meta = (
        "<title>{t}</title>\n"
        '<meta name="description" content="{d}">\n'
        '<link rel="canonical" href="{c}">\n'
        '<meta property="og:type" content="website">\n'
        '<meta property="og:site_name" content="Inspection Support Services">\n'
        '<meta property="og:title" content="{t}">\n'
        '<meta property="og:description" content="{d}">\n'
        '<meta property="og:url" content="{c}">\n'
        '<meta property="og:image" content="{i}">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        '<meta name="twitter:title" content="{t}">\n'
        '<meta name="twitter:description" content="{d}">\n'
        '<meta name="twitter:image" content="{i}">\n'
    ).format(t=e(title), d=e(description), c=canonical, i=image)

    doc = doc.replace('<meta name="viewport"', meta + '<meta name="viewport"', 1)
    doc = doc.replace("<html>", '<html lang="en">', 1)
    return doc
