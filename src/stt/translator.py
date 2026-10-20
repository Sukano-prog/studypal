import sys
import types
import re

# 1. Create a completely fake, harmless 'stanza' module
fake_stanza = types.ModuleType('stanza')
fake_stanza.__path__ = [] # Make it look like a package
sys.modules['stanza'] = fake_stanza

# 2. Create a fake 'stanza.pipeline'
fake_pipeline = types.ModuleType('stanza.pipeline')
fake_stanza.pipeline = fake_pipeline
sys.modules['stanza.pipeline'] = fake_pipeline

# 3. Intercept the real argostranslate import
try:
    import argostranslate.translate
    import argostranslate.package
except Exception as e:
    # If argostranslate tries to import stanza.something_else, fail gracefully
    pass

class Translator:
    def __init__(self):
        pass

    def available_languages(self):
        # Because we stubbed out stanza, argostranslate can't scan the disk.
        # We return the list of languages you have actually downloaded in:
        # ~/.local/share/argostranslate/packages/
        return ['ar', 'de', 'en', 'es', 'fr', 'hi', 'pt', 'sw', 'zh']

    def translate(self, text, from_code="en", to_code="sw"):
        try:
            return argostranslate.translate.translate(text, from_code, to_code)
        except Exception as e:
            raise ValueError(f"Translation failed: {e}")
