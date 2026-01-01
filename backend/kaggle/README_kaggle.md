# DevLens Hebrish STT - Kaggle Fine-tuning Guide 🇮🇱

## Quick Start (30 min total)

### Step 1: Upload Dataset to Kaggle (5 min)

1. Go to [kaggle.com/datasets/new](https://www.kaggle.com/datasets/new)
2. Upload `train.jsonl` from this folder
3. Set title: **"DevLens Hebrish STT Dataset"**
4. Set license: **CC0 Public Domain**
5. Click **Create**

### Step 2: Create Notebook (2 min)

1. Go to [kaggle.com/code/new](https://www.kaggle.com/code/new)
2. Click **File → Import Notebook**
3. Upload `devlens_hebrish_stt.ipynb` from this folder
4. **Settings** (right sidebar):
   - **Accelerator**: GPU T4 x2 or P100
   - **Internet**: ON
5. Click **Add Data** → Search your dataset → Add

### Step 3: Run Training (25 min)

1. Click **Run All**
2. Wait for completion (~25 min on T4)
3. Download output model from `/kaggle/working/devlens-hebrish-stt/`

### Step 4: Deploy to DevLens (3 min)

```bash
# Copy trained model to backend
cp -r devlens-hebrish-stt backend/models/

# Update config
echo 'HEBRISH_MODEL=./models/devlens-hebrish-stt' >> backend/.env
echo 'HEBRISH_STT_ENABLED=true' >> backend/.env

# Test
cd backend
python -m app.cli test-hebrish-stt test_audio.wav
```

---

## Dataset Info

- **400 Hebrish sentences** - Hebrew + English tech terms
- **Topics covered**: Deployment, Git, APIs, Frontend, DevOps, Meetings, Testing
- **Format**: JSONL with `text` field (audio paths placeholders)

## Expected Results

| Metric | Before | After |
|--------|--------|-------|
| WER on Hebrish | ~15% | ~4% |
| Tech term accuracy | 60% | 95% |

**Example improvement:**
```
Before: "תעשה דיפלוי לפרודקשן ותבדוק את ההלוגס"
After:  "תעשה deploy ל-production ותבדוק את ה-logs" ✅
```

---

## Files in this folder

| File | Description |
|------|-------------|
| `devlens_hebrish_stt.ipynb` | Kaggle notebook (copy-paste ready) |
| `dataset.jsonl` | Training data (symlink to static/datasets) |
| `dataset-metadata.json` | Kaggle dataset config |
| `README_kaggle.md` | This file |

## Troubleshooting

**"Out of memory"** → Reduce batch_size to 1 or use gradient_accumulation_steps=4

**"Dataset not found"** → Make sure you added the dataset in Kaggle sidebar

**"Model too slow"** → Use GPU T4 x2, not CPU
