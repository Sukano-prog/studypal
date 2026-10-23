"""Translation via Argos Translate (offline, CPU)."""

import os
# Force MiniSBD sentence splitter — Stanza does not support Swahili
os.environ.setdefault("ARGOS_CHUNK_TYPE", "MINISBD")

import argostranslate.translate


class Translator:
    def __init__(self):
        pass

    def available_languages(self):
        """Return list of installed language codes."""
        langs = argostranslate.translate.get_installed_languages()
        return sorted({lang.code for lang in langs})

    def translate(self, text, from_code="en", to_code="sw"):
        """Translate text using the correct Argos API (language-object based)."""
        if not text or from_code == to_code:
            return text

        installed = argostranslate.translate.get_installed_languages()
        from_lang = next((l for l in installed if l.code == from_code), None)
        to_lang = next((l for l in installed if l.code == to_code), None)

        if not from_lang or not to_lang:
            raise RuntimeError(
                f"Language not installed: {from_code} -> {to_code}"
            )

        translation = from_lang.get_translation(to_lang)
        if translation is None:
            raise RuntimeError(
                f"No translation path: {from_code} -> {to_code}"
            )

        return translation.translate(text)
