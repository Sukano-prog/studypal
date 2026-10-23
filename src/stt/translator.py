"""Translation via Argos Translate (offline, CPU)."""
import os
# Force MiniSBD sentence splitter ΓÇö Stanza does not support Swahili
os.environ.setdefault("ARGOS_CHUNK_TYPE", "MINISBD")

# Windows stanza lacks a capital-P Pipeline attribute (Argos calls it).
# Add alias BEFORE argostranslate imports so sbd.py sees it.
try:
    import stanza
    if not hasattr(stanza, "Pipeline") and hasattr(stanza, "pipeline"):
        stanza.Pipeline = stanza.pipeline
except ImportError:
    pass

import argostranslate.translate


class Translator:
    def __init__(self):
        pass

    def available_languages(self):
        """Return list of installed language codes."""
        langs = argostranslate.translate.get_installed_languages()
        return sorted({lang.code for lang in langs})

    def translate(self, text, from_code="en", to_code="sw"):
        """Translate text using the language-object Argos API."""
        if not text or from_code == to_code:
            return text

        installed = argostranslate.translate.get_installed_languages()
        from_lang = next((l for l in installed if l.code == from_code), None)
        to_lang = next((l for l in installed if l.code == to_code), None)

        if not from_lang or not to_lang:
            raise ValueError(f"Language not installed: {from_code} -> {to_code}")

        translation = from_lang.get_translation(to_lang)
        if translation is None:
            raise ValueError(f"No translation path: {from_code} -> {to_code}")

        return translation.translate(text)
