import time
import polib
from googletrans import Translator

def translate_po_file(input_file, output_file, target_lang, delay=0.5):
    """Translate only empty msgstr entries in a .po file."""
    po = polib.pofile(input_file)
    translator = Translator()

    translated_count = 0
    skipped_count = 0

    for entry in po:
        if entry.msgstr.strip():  # Already translated → skip
            skipped_count += 1
            continue

        if not entry.msgid.strip():  # Empty key → skip
            continue

        if "django" in entry.occurrences[0][0] or "site-packages" in entry.occurrences[0][0]:
            continue

        try:
            translated = translator.translate(entry.msgid, dest=target_lang).text
            entry.msgstr = translated
            translated_count += 1
            print(f"{entry.msgid} → {translated}")
        except Exception as e:
            print(f"Failed to translate '{entry.msgid}': {e}")

        time.sleep(delay)  # avoid getting rate-limited

    po.save(output_file)
    print(f"\nTranslation complete! Saved to {output_file}")
    print(f"Translated {translated_count} new entries, skipped {skipped_count} existing ones.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Translate only new/empty entries in a Django .po file.")
    parser.add_argument("input_file", help="Path to the input .po file (e.g. locale/en/LC_MESSAGES/django.po)")
    parser.add_argument("output_file", help="Path to save the translated .po file")
    parser.add_argument("lang", help="Target language code (e.g. fr, es, de, ar, ja)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay (seconds) between translations")
    args = parser.parse_args()

    translate_po_file(args.input_file, args.output_file, args.lang, args.delay)
