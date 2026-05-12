# TruthChain — Decentralized Geopolitical Fact-Checking Engine

**TruthChain** is a decentralized consensus oracle that combines a multi-model AI ensemble with human network governance and blockchain immutability to verify geopolitical claims in real-time.

Claims are submitted by human "nodes," verified by a 3-model NLP ensemble, and — once consensus is reached — permanently anchored to the Algorand TestNet as immutable proof.

---

## Technical Architecture

```
┌────────────────────────────────────────────────────────┐
│                    Frontend (index.html)                │
│         X/Twitter-inspired UI  ·  Live Blockchain Feed │
└──────────────────────┬─────────────────────────────────┘
                       │  REST API
┌──────────────────────▼─────────────────────────────────┐
│               FastAPI Backend (main.py)                 │
│   Claim Ingestion  ·  Voting  ·  Consensus Engine      │
│   Strike System  ·  Ban Hammer  ·  Sudden Death Logic  │
└───┬──────────────┬─────────────────┬───────────────────┘
    │              │                 │
    ▼              ▼                 ▼
┌────────┐  ┌────────────┐  ┌──────────────────┐
│Supabase│  │  HF AI     │  │ Algorand TestNet │
│ + pgvec│  │  Ensemble   │  │  (Blockchain)    │
│  (RAG) │  │             │  │                  │
│        │  │ ┌─────────┐ │  │  0-ALGO self-txn │
│ Vector │  │ │ DeBERTa │ │  │  with JSON note  │
│ search │  │ ├─────────┤ │  └──────────────────┘
│        │  │ │  BART   │ │
│        │  │ ├─────────┤ │
│        │  │ │ RoBERTa │ │
└────────┘  │ └─────────┘ │
            └─────────────┘
```

### Core Components

| Module | Purpose |
|---|---|
| `main.py` | FastAPI application — handles claim submission, voting, AI orchestration, consensus logic (including Sudden Death tie-breaking), strike/ban system, and blockchain anchoring. |
| `model.py` | AI Ensemble — routes claims through DeBERTa, BART, and RoBERTa via the Hugging Face Inference API. Returns a 2/3 majority verdict with averaged confidence. |
| `blockchain.py` | Algorand integration — broadcasts a 0-ALGO self-transaction with the claim verdict encoded in the `note` field. |
| `db.py` | Supabase client initialization with environment-based configuration. |
| `ingest.py` | Ingests official government/treaty statements into the vector database for RAG-based context retrieval. |
| `index.html` | Single-file frontend — X/Twitter-inspired dark-mode UI with node selection, claim feed, voting, real-time consensus visualization, and a live blockchain activity sidebar. |
| `init_db.sql` | Database schema — creates `nodes`, `claims`, `votes`, and `official_statements` tables with pgvector support and a cosine similarity search function. |

### AI Ensemble Consensus

The system runs **three NLI (Natural Language Inference) models** sequentially to avoid HF free-tier rate limits:

1. **DeBERTa-v3-large-mnli** — High-accuracy entailment detection
2. **BART-large-mnli** — Zero-shot classification (factual truth vs. misinformation)
3. **RoBERTa-large-mnli** — Cross-reference auditor for tie-breaking

A **2/3 majority** among the models determines the AI verdict. The AI ensemble carries **3 points** toward the consensus threshold.

### Consensus & Sudden Death

- Human nodes vote to **Verify** or **Refute** each claim (1 point per vote)
- The AI ensemble contributes **3 points** toward the leading direction
- Consensus is reached at **≥ 4 points**
- If a **3 vs 3 deadlock** occurs (AI vs. humans disagree), a **4th human vote slot** unlocks for a "Sudden Death" tie-breaker
- Authors **cannot vote** on their own claims (enforced at both UI and API level)

### Blockchain Anchoring

When consensus is reached, a **0-ALGO self-transaction** is broadcast to the **Algorand TestNet** with the claim text, verdict, and confidence score encoded in the transaction's `note` field. The resulting TxID is stored in the database and displayed in the real-time sidebar.

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- A [Supabase](https://supabase.com) project (free tier works)
- A [Hugging Face](https://huggingface.co) account with an API token
- An Algorand TestNet wallet (funded via the [TestNet faucet](https://bank.testnet.algorand.network/))

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/YOUR_USERNAME/truthchain.git
cd truthchain
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL (e.g., `https://xxxxx.supabase.co`) |
| `SUPABASE_KEY` | Supabase `anon` public key |
| `HF_API_TOKEN` | Hugging Face API token (starts with `hf_`) |
| `ALGO_MNEMONIC` | 25-word Algorand wallet mnemonic (wrapped in quotes) |

### 3. Initialize the Database

1. Open the **Supabase Dashboard → SQL Editor**
2. Paste the contents of `init_db.sql`
3. Click **Run** to create all tables, indexes, and seed the node identities

### 4. Ingest Reference Data

```bash
python ingest.py
```

This populates the `official_statements` table with vectorized government/treaty data for RAG context retrieval.

### 5. Start the Server

```bash
python main.py
```

The server starts at `http://localhost:8000`. Open it in your browser to access the TruthChain UI.

---

## Project Structure

```
truthchain/
├── .env.example        # Environment variable template
├── blockchain.py       # Algorand TestNet transaction module
├── db.py               # Supabase client initialization
├── index.html          # Frontend UI (single-file, Tailwind CSS)
├── ingest.py           # Vector database ingestion script
├── init_db.sql         # PostgreSQL schema + seed data
├── main.py             # FastAPI backend + consensus engine
├── model.py            # AI Ensemble (DeBERTa, BART, RoBERTa)
├── requirements.txt    # Python dependencies
├── test_hf.py          # Hugging Face API diagnostic tool
└── test_system.py      # End-to-end system test
```

---

## License

This project is built for academic and demonstration purposes.
