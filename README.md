# Magic All Cards (GUI)

![Magic All Cards GUI](gui.png)

Magic All Cards is a Tkinter desktop app that keeps the MTGJSON `AllPrintings.json` database up to date, lets you filter entire Magic: The Gathering sets, and downloads the corresponding Scryfall card images into a clean folder hierarchy.

> 🇧🇷 Precisa das instruções em português? Confira o arquivo [`README.pt-BR.md`](README.pt-BR.md).

## Feature Highlights
- **Hands-off MTGJSON sync** – the app fetches `Meta.json`, determines whether `AllPrintings.json` needs an update (~1 GB), streams the download with progress + speed, and loads every set automatically on startup.
- **Bilingual GUI** – every label, dialog, and log entry is available in English and Portuguese. The interface now defaults to English, but you can switch languages anytime and the preference is stored in `config.json`.
- **18 image languages** – choose which Scryfall localization to download (EN, ES, FR, DE, IT, PT, JA, KO, RU, ZHS, ZHT, HE, LA, GRC, AR, SA, PH, QYA). When a card is missing in that language, the downloader automatically falls back to English and records the fallback in the log.
- **Advanced filters** – select multiple sets, filter by card type, rarity, or name substring, and only cards with a valid Scryfall ID are queued.
- **Progress and safety** – the UI shows both percentage and card counters. If a batch crosses ~40 000 cards (~10 GB) you must confirm before the download proceeds.
- **Deterministic folder layout** – files are stored as `SET/<Language>/<Color>/<Type>/<Rarity>/<number_name>.png`, prioritizing lands, colors, and rarities exactly as requested.
- **Packaged distribution** – tested with PyInstaller so you can ship a single `.exe` to players who do not have Python installed.

## Requirements
- Python 3.10+
- Packages listed in `requirements.txt`

Install everything with:

```powershell
pip install -r requirements.txt
```

## Usage
```powershell
python magic_all_cards.py
```

1. When the window opens, wait for the log to report the MTGJSON download (only on first run) followed by “sets loaded”.
2. Pick the **Image language** you want from the dropdown. English is the most complete, but any of the 18 languages can be selected.
3. Use **App language** to toggle the entire GUI/logs between English and Portuguese. The last choice is saved to `config.json` and reused the next time you launch.
4. Set additional filters (card type, rarity, name contains, set search) and choose one or more sets from the list.
5. Click **Choose destination folder** and then press **Download selected cards**. If the selection is extremely large you’ll be asked to confirm before the download starts.

### Folder Structure
Each selected set produces:

```
<dest>/<SET>/<Language>/<Color>/<Type>/<Rarity>/<number_name>.png
```

- **Language** – numbered folders such as `01-English`, `02-Spanish`, etc.
- **Color** – `White`, `Blue`, `Black`, `Red`, `Green`, `Colorless`, or `Multicolor`.
- **Type** – `Land`, `Creature`, `Planeswalker`, `Instant`, `Sorcery`, `Enchantment`, `Artifact`, `Battle`, or `Others` (lands are always prioritized as requested).
- **Rarity** – `Common`, `Uncommon`, `Rare`, `Mythic`, `Special`, `Promo`, `Bonus`, or `NoRarity`.

> **Note:** the project ships as source-first. Run it directly with Python as described above. Binary builders such as PyInstaller/cx_Freeze are no longer maintained in this repository.

## Dependencies
- `requests` for HTTP transfers
- `tkinter` (bundled with the standard Windows Python installer)


## License
This project is distributed under the [Creative Commons Attribution-NonCommercial 4.0 International](LICENSE)
license. You may adapt and share the code for non-commercial purposes as long as you credit the author and
keep the same non-commercial terms in derivative works.

## Notes
- `AllPrintings.json` is roughly 1 GB; the first download may take a while depending on your connection.
- Respect Scryfall’s API terms—avoid running multiple instances concurrently or hammering the service.
- For debugging, run the script from a terminal so stdout/stderr remain visible.
