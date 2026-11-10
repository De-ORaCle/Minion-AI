# Minion — Offline AI Agent Setup Guide (Ollama)

This guide walks you through setting up and running offline AI models for **Minion**.

---

## 1. System Status
- **Ollama Engine**: Detected as installed (`v0.40.5`).
- **Installed Model**: `llama3.2:3b` (2.0 GB, ID: `a80c4f17acd5`).
- **Offline Readiness**: **Minion** uses local Ollama models for deep semantic activity classification, smart context clustering, and AI-powered post generation across LinkedIn, X/Twitter, and team standup formats.

---

## 2. Supported Offline Models for Minion

| Model Name | Download Size | RAM / VRAM Req. | Speed | Best For |
|---|---|---|---|---|
| **`llama3.2:3b`** *(Default & Recommended)* | ~2.0 GB | 4 GB - 8 GB | Very Fast | High quality post generation, accurate activity classification, context clustering. |
| **`llama3.2:1b`** *(Ultra-Light)* | ~1.3 GB | 2 GB - 4 GB | Ultra Fast | Low-spec laptops, battery conservation, rapid categorization. |
| **`qwen2.5:3b`** | ~1.9 GB | 4 GB - 8 GB | Very Fast | Outstanding reasoning, code understanding, and structured summaries. |
| **`mistral:7b`** *(Power Users)* | ~4.1 GB | 8 GB - 16 GB | Moderate | Deep creative writing, detailed devlogs, complex topic segmentation. |

---

## 3. How to Download Additional Models

In your terminal (PowerShell, Command Prompt, or Windows Terminal):

### Ultra-Lightweight (For older hardware or minimal battery drain):
```powershell
ollama pull llama3.2:1b
```

### High Reasoning & Code Understanding:
```powershell
ollama pull qwen2.5:3b
```

### Check Available Models:
```powershell
ollama list
```

---

## 4. Starting the Ollama Service
Ensure Ollama is running in the background. If it isn't running in your system tray:
```powershell
ollama serve
```
By default, Ollama serves its local REST API at:
```
http://127.0.0.1:11434
```

---

## 5. In-App Integration
Inside **Minion**:
1. Navigate to the **⚙️ AI & Settings** tab.
2. Check the **Local AI Agent** card — it will display `● CONNECTED` with `llama3.2:3b` selected.
3. You can also download new models directly using the in-app **Download Model** bar!
