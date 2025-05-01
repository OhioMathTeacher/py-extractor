# py-extractor

**Extract targeted content from PDFs using AI.**  
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

### 🖥️ CLI Version (Python Script)

The original command-line version of the extractor is located here:

[`cli/py_extractor02v2.py`](https://github.com/Technology-Educators-Alliance/py-extractor/blob/main/cli/py_extractor02v2.py)

To run it:
```bash
python3 py_extractor02v2.py
```
