# AnkiAI 🧠

AnkiAI is a powerful tool designed to streamline your learning workflow by leveraging DeepSeek AI to generate flashcards for Anki.

---

## ⚠️ Notes

* **AI Determinism:** Please be aware that Large Language Models (LLMs) are non-deterministic by nature. This means that for the same input, the results—including the number of cards, level of detail, and formatting—may vary between runs.

* **Local Execution (Ollama):** Running models locally ensures 100% privacy, but it involves significant hardware and performance trade-offs:
    * **System Resources:** Generation is resource-intensive and relies heavily on your hardware. A minimum of 8 GB VRAM is recommended for a smooth experience. Running out of VRAM (Video RAM) will significantly degrade performance or can cause hallucination, the application to crash.
    * **Performance:** Local inference takes significantly longer than cloud-based APIs. Expect a slower "cards-per-minute" rate depending on your system's power.

---

## 🤖 Recommended Local Models
For the best balance between speed and logic when generating Anki cards via Ollama, I recommend:

* **Llama 3.1 (8B):** Currently the best all-rounder. Fast, reliable, and follows complex instructions well.
* **Mistral-Nemo (12B):** Excellent for longer lecture notes and very stable in maintaining JSON formatting.
* **Qwen 2.5 (7B):** A highly capable model that excels at logical extraction and technical definitions.

---

## ✨ Features
* **DeepSeek Integration:** Uses DeepSeek's powerful LLM to extract and format knowledge into flashcards.
* **Ollama Integration:** Support for local LLMs via Ollama ensures your data never leaves your machine.
* **Direct Export:** Generates files ready for Anki import (no additional plugins like AnkiConnect required).
* **Smart Formatting:** Automatically structures complex information into concise Q&A pairs.

---

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* A DeepSeek API Key
* Anki (for importing the generated cards)

### Installation
1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Cuzimnero/AnkiAI.git](https://github.com/Cuzimnero/AnkiAI.git)
   cd AnkiAI
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   
