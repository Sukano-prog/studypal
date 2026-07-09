StudyPal - Advanced Study Assistant

Python Version: 3.8+
License: MIT
Platform: Windows, Linux, macOS

Study Smarter, Not Harder - Convert your study materials into audio for better learning and accessibility.

Features (v1.0)

- Multiple Document Support: PDF, DOCX, TXT
- TTS Provider: PyTTSX3 (cross-platform)
- Note Taking: Built-in notes
- Audio Caching: Faster playback
- Controls: Speed and volume adjustment
- Themes: Dark and Light modes
- Bookmarks: Save your reading positions
- Study Tracking: Track your study sessions

Quick Start

Installation

Clone the repository:
git clone https://github.com/Sukano-prog/studypal.git
cd studypal

Create virtual environment:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

Install dependencies:
pip install -r requirements.txt

Run StudyPal:
python run.py

First Use

1. Launch StudyPal
2. Click Text, PDF, or DOCX to load a document
3. Click Play to start listening
4. Use Speed and Volume controls to adjust playback
5. Take notes in the right panel

Project Structure

studypal/
    src/
        audio/           Audio playback engine
        engine/          Document and TTS engine
        gui/             UI components
        config.py        Application configuration
        main.py          Entry point
    requirements.txt     Dependencies
    setup.py            Installation script
    run.py              Launcher
    README.md           Documentation
    LICENSE             MIT License

Development

Building from Source

Windows:
pip install pyinstaller
pyinstaller --onefile --windowed --name=StudyPal run.py

Linux and macOS:
pip install pyinstaller
pyinstaller --onefile --name=StudyPal run.py

Contributing

Contributions are welcome! Please see CONTRIBUTING.md for guidelines.

License

This project is licensed under the MIT License - see the LICENSE file for details.
