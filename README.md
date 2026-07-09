# 📚 StudyPal - Advanced Study Assistant

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)]()

> **Study Smarter, Not Harder** - Convert your study materials into audio for better learning and accessibility.

## ✨ Features

- 📄 **Multiple Document Support**: PDF, DOCX, TXT, and more
- 🎤 **TTS Providers**: PyTTSX3, Google TTS
- 📝 **Note Taking**: Built-in notes with tagging
- 🔖 **Bookmarks**: Save your reading positions
- ⚡ **Audio Caching**: Smart caching for faster playback
- 🎛️ **Controls**: Speed, volume, and audio effects
- 🌙 **Themes**: Dark and Light modes
- 📊 **Study Tracking**: Track your study sessions

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/studypal.git
cd studypal

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run StudyPal
python run.py
```

### First Use

1. Launch StudyPal
2. Click `📄 Text`, `📕 PDF`, or `📘 DOCX` to load a document
3. Select your preferred voice
4. Click `▶ Play` to start listening
5. Use `Speed` and `Volume` controls to adjust playback
6. Take notes in the right panel

## 📁 Project Structure

```
studypal/
├── src/
│   ├── audio/           # Audio playback engine
│   ├── engine/          # Document and TTS engine
│   ├── gui/             # UI components
│   ├── config.py        # Application configuration
│   └── main.py          # Entry point
├── requirements.txt     # Dependencies
├── setup.py            # Installation script
├── run.py              # Launcher
├── README.md           # Documentation
└── LICENSE             # MIT License
```

## 🛠️ Development

### Building from Source

**Windows:**
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name=StudyPal run.py
```

**Linux/macOS:**
```bash
pip install pyinstaller
pyinstaller --onefile --name=StudyPal run.py
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Made with ❤️ for students everywhere
</p>
