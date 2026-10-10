"""Translation engine using Argos Translate (offline, free)."""
import argostranslate.package
import argostranslate.translate


class Translator:
    """Offline translation via Argos Translate."""

    def __init__(self):
        self._installed_langs = None

    def _refresh_languages(self):
        """Get currently installed language pairs."""
        self._installed_langs = argostranslate.translate.get_installed_languages()

    def available_languages(self) -> list:
        """Return list of installed language codes."""
        if self._installed_langs is None:
            self._refresh_languages()
        return [lang.code for lang in self._installed_langs]

    def install_package(self, from_code: str, to_code: str):
        """Download and install a translation package."""
        print(f"[Argos] Installing {from_code} -> {to_code}...")
        argostranslate.package.update_package_index()
        available = argostranslate.package.get_available_packages()
        pkg = next(
            (p for p in available
             if p.from_code == from_code and p.to_code == to_code),
            None,
        )
        if pkg is None:
            raise ValueError(f"No package for {from_code} -> {to_code}")
        argostranslate.package.install_from_path(pkg.download())
        self._refresh_languages()
        print(f"[Argos] Installed {from_code} -> {to_code}")

    def translate(self, text: str, from_code: str, to_code: str) -> str:
        """Translate text between two languages."""
        if self._installed_langs is None:
            self._refresh_languages()

        from_lang = next(
            (l for l in self._installed_langs if l.code == from_code), None
        )
        to_lang = next(
            (l for l in self._installed_langs if l.code == to_code), None
        )

        if from_lang is None or to_lang is None:
            raise ValueError(
                f"Language pair {from_code} -> {to_code} not installed. "
                f"Call install_package() first."
            )

        return from_lang.get_translation(to_lang).translate(text)
