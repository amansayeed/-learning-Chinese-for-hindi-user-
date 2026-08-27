# Phone / Google Drive (no server)

## Quick start (phone)

1. Copy the **`mobile/`** folder from git to your phone (or copy **`mobile/index.html`** alone).
2. Open **`index.html`** in Chrome — **not** hsk.html, START menu links, or the small root index.
3. Tap **☰** in the top bar — Words, HSK 1–6, pronunciation, and tones switch **inside** that file.

**File size check:** `mobile/index.html` should be about **7–8 MB** with the canonical vocabulary embedded. If it is only ~400 KB, you have the old broken copy — pull latest git or rebuild (below).

Chrome on phone often **blocks localStorage** for files opened from Drive or Downloads. The app includes a memory fallback so this does not break navigation or word lists.

## Why other links fail on phone

Opening one HTML file from Google Drive uses a `content://` URL. The browser **cannot open other `.html` files** next to it (`hsk2.html`, etc.) → `ERR_FILE_NOT_FOUND`. The unified **`mobile/index.html`** avoids that by keeping everything in one file.

## Rebuild on a PC (optional)

```bash
node scripts/build-offline-bundles.js --with-tones
```

If Node.js is unavailable, run:

```bash
python scripts/build_vocabulary_master.py
python scripts/build_mobile_pack.py
python scripts/build_offline_app.py
```

That writes **`mobile/index.html`** (all-in-one). Commit and push so phones get the updated file from git.

## PC / full folder

If you copy the **whole project** and open via **`file://`**, separate pages at the repo root still work.
