# Phone / Google Drive (no server)

## What you see when it is broken

Unstyled black text, empty table, URL starts with `content://` — the browser **blocked** separate `css/` and `js/` files.

## Fix: use the built `index.html`

After `node scripts/build-mobile-pack.js`, **`index.html` is one large file (~400 KB)** with styles, scripts, and word data **inside** it.

1. Copy the project from git (or run the build on a PC and copy the folder).
2. On the phone, open **`index.html`** in Chrome (from Drive or Downloads).
3. Check size: **index.html must be ~400 KB**. If it is only ~10 KB, you have the old dev file — pull/build again.

You do **not** need the `css/`, `js/`, or `data/` folders on the phone for the main pages (they are already inside `index.html`).

## Edit the site on a PC

- Change **`pages/*.html`**, **`css/styles.css`**, **`js/*.js`**
- Run: `node scripts/build-offline-bundles.js --with-tones` then `node scripts/build-mobile-pack.js`
- That refreshes **`index.html`**, **`pronunciation.html`**, **`tones.html`** at the project root

## Optional

- **`mobile/`** — same self-contained copies (handy if you only copy that folder)
- **`START.html`** — small menu linking to the three pages
