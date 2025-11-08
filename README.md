# NFT Agent

This NFT Agent leverages the Alchemy and OpenSea APIs to retrieve real-time NFT prices and portfolio data. It is built on the Sentient Agent Framework.

---

## ⚙️ Setup Instructions

### 1. Create a Secrets File

Copy the example environment file:

```bash
cp .env.example .env
```

---

### 2. Add Model Credentials

Add your **Gemini API key** to the `.env` file.

---

### 3. Add Search Provider Credentials

Add your **OpenSea API key** and **Alchemy API key** to the `.env` file.

---

## 🌍 Supported Chains

* Ethereum
* Base
* Arbitrum
* Avalanche
* Optimism
* Polygon

---

## 💻 Local Installation

### 4. Create a Python Virtual Environment

```bash
python3 -m venv .venv
```

### 5. Activate the Virtual Environment

```bash
source .venv/bin/activate
```

### 6. Install Dependencies

```bash
pip install -r requirements.txt
```

### 7. Run the NFT Agent

```bash
python -m src.nft_agent
```

---

## 🚀 Features

* Fetches **NFT ownership** and **floor prices** using Alchemy & OpenSea APIs
* Supports **multiple blockchain networks**
* Uses **Loguru** for clean, structured logging

---

## 🧩 Example `.env` File

```bash
ALCHEMY_API_KEY=enter-your-alchemy-api-key-here
OPENSEA_API_KEY=enter-your-opensea-api-key-here
GEMINI_API_KEY=enter-your-gemini-api-key-here
NFT_AGENT_PORT=8003

```

---

## 📦 Requirements

All dependencies are listed in `requirements.txt`.

Install them with:

```bash
pip install -r requirements.txt
```

---
