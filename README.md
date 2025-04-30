# py-extractor

**Extract positionality statements and other targeted content from PDFs using AI.**  
This tool was designed for large-scale qualitative research in educational scholarship, but can be adapted for other domains.

---

## 🧰 What’s Included

This repo contains:

- 💽 `py_extractor_x86_64` — for **Intel-based Macs**
- 🍏 `py_extractor_arm64` — for **Apple Silicon Macs** (M1/M2)
- 🧠 `run_py_extractor.sh` — a smart launcher that auto-detects your system and runs the right version
- 📂 `README.txt` — basic usage and support info
- 📄 `LICENSE.txt` — licensed for **non-commercial, educational use only** (CC BY-NC 4.0)

---

## 🚀 Quick Start (Terminal Pros)

```bash
curl -L https://github.com/Technology-Educators-Alliance/py-extractor/releases/download/v0.2.0/py_extractor_bundle.zip -o py_extractor_bundle.zip && \
unzip py_extractor_bundle.zip && \
cd py_extractor_bundle && \
chmod +x run_py_extractor.sh py_extractor_* && \
./run_py_extractor.sh
```

---

## 🧪 Manual Use

1. Download and unzip the bundle
2. Open Terminal
3. Run:
   ```bash
   ./run_py_extractor.sh
   ```
   Or, if you prefer manual control:
   ```bash
   uname -m
   ./py_extractor_x86_64   # if "x86_64"
   ./py_extractor_arm64    # if "arm64"
   ```

---

## ❗ License

This project is licensed under a **Creative Commons Attribution–NonCommercial 4.0 International (CC BY-NC 4.0)** license.  
You may remix, adapt, and use the code for non-commercial purposes, with attribution.

📄 See [`LICENSE.txt`](LICENSE.txt) for details.

---

## 👥 Project Maintainer

Maintained by [Technology Educators Alliance](https://github.com/Technology-Educators-Alliance)
