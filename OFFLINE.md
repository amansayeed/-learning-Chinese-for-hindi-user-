# Phone / Google Drive (no server)

## Quick start (phone)

1. Copy the **`mobile/`** folder from git to your phone (or copy **`mobile/index.html`** alone).
2. Open **`index.html`** in Chrome — **not** hsk.html, START menu links, or the small root index.
3. Tap **☰** in the top bar — Words, HSK 1–6, pronunciation, and tones switch **inside** that file.

**File size check:** `mobile/index.html` should be about **17–18 MB** with the canonical vocabulary, the TOCFL/CCCC levels and the character database embedded. If it is only ~400 KB, you have the old broken copy — pull latest git or rebuild (below).

Chrome on phone often **blocks localStorage** for files opened from Drive or Downloads. The app includes a memory fallback so this does not break navigation or word lists.

## Why other links fail on phone

Opening one HTML file from Google Drive or a file manager uses a `content://` URL that grants access to **that file only**. Chrome re-requests the URL on every navigation — even a plain `#fragment` — and the grant is already spent, so anything that reaches the browser ends on `ERR_FILE_NOT_FOUND`.

The pages handle this themselves:

- The all-in-one **`mobile/index.html`** keeps every page inside one file and switches views in memory, so nothing navigates.
- A single page opened on its own (`hsk2.html`, `characters.html`, …) says so at the top and dims the links to its sibling files instead of letting a tap end on a browser error.

`python scripts/smoke_test_sandbox_nav.py` clicks each kind of link in a simulated `content://` document and fails the build if one can still escape.

## Rebuild on a PC (optional)

```bash
python scripts/build_vocabulary_master.py
python scripts/build_mobile_pack.py
python scripts/build_offline_app.py
```

That writes **`mobile/index.html`** (all-in-one). Commit and push so phones get the updated file from git.

Each data builder (`build_hsk.py`, `build_tocfl_8000.py`, `build_characters.py`, …) writes its own `data/*.js` bundle, so no separate bundling step is needed. The tone quartets are the one exception and still need Node:

```bash
node scripts/build-tone-data.js
```

## Checks

```bash
python scripts/verify_all_pages.py        # every shipped page: links, bundling, content:// guard
python scripts/verify_unified_app.py      # canonical vocabulary and the all-in-one file
python scripts/smoke_test_ui.py           # the real modules against a minimal DOM
python scripts/smoke_test_bundle.py       # the shipped bundle renders words
python scripts/smoke_test_sandbox_nav.py  # no link escapes a content:// document
```

## PC / full folder

If you copy the **whole project** and open via **`file://`**, separate pages at the repo root still work.
