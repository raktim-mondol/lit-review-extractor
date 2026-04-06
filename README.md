# Literature Review Extractor

Source: [github.com/raktim-mondol/lit-review-extractor](https://github.com/raktim-mondol/lit-review-extractor)

Scans markdown-format papers from `paper_in_markdown/`, sends each one to a Dashscope-hosted LLM, extracts structured fields defined in `columns_config.json`, and writes a formatted Excel file to `result/`.

---

## How it works

```
paper_in_markdown/*.md
        │
        ▼
 process_papers.py  ──reads──  columns_config.json  (what to extract)
        │           ──reads──  guideline.md          (system prompt, optional)
        │           ──reads──  .env                  (API key, model, base URL)
        │
        ▼
 result/
 ├── literature_review.xlsx   ← one row per paper
 ├── json_outputs/            ← one JSON file per paper
 └── progress_checkpoint.json ← resume state
```

---

## Setup

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Configure `.env`**

Create a `.env` file in the project root (it is gitignored — never committed):

```env
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_BASE_URL=your_provider_api_base_url
DASHSCOPE_MODEL=qwen3-max-2026-01-23
```


| Variable             | Required | Description                                  |
| -------------------- | -------- | -------------------------------------------- |
| `DASHSCOPE_API_KEY`  | yes      | Your Dashscope API key                       |
| `DASHSCOPE_BASE_URL` | no       | API base URL (set this to your provider endpoint) |
| `DASHSCOPE_MODEL`    | no       | Model name (default: `qwen3-max-2026-01-23`) |


A ready-to-use template is provided in `.env.example` — copy it to `.env` and fill in your credentials.

**Available model options**


| Model                  | Vision | Notes                              |
| ---------------------- | ------ | ---------------------------------- |
| `qwen3-max-2026-01-23` | no     | Default — strong general reasoning |
| `qwen3-coder-next`     | no     | Coding-focused, latest generation  |
| `qwen3-coder-plus`     | no     | Coding-focused, balanced           |
| `glm-4.7`              | no     | GLM series, fast                   |
| `glm-5`                | no     | GLM series, advanced               |
| `MiniMax-M2.5`         | no     | MiniMax series                     |
| `qwen3.5-plus`         | yes    | Qwen vision, plus tier             |
| `kimi-k2.5`            | yes    | Kimi vision, strong multimodal     |


**3. Add your papers**

Drop markdown files into `paper_in_markdown/`. Papers are processed in alphabetical order by filename.

**4. Run**

```bash
python process_papers.py
```

---

## Customising extracted columns

Edit `columns_config.json` — **no code changes needed**.

Each entry defines one Excel column:

```json
{
  "column_name": "Cancer Type",
  "field_key": "cancer_type",
  "description": "Cancer type(s) studied in the paper",
  "width": 20
}
```


| Field         | Required | Description                                                |
| ------------- | -------- | ---------------------------------------------------------- |
| `column_name` | yes      | Excel column header                                        |
| `field_key`   | yes      | JSON key the model returns — unique, snake_case, no spaces |
| `description` | yes      | Instruction sent to the model for this field               |
| `width`       | no       | Excel column width in characters (default: 25)             |


**To add a column** — append a new entry to the array.  
**To remove a column** — delete its entry.  
**To rename a column** — change `column_name`.  
**To change what the model extracts** — change `description`.

The four fixed columns `Serial No.`, `File Name`, `Status`, and `Error` are always present and cannot be removed via the config.

---

## Optional: custom system prompt

If a `guideline.md` file is present in the project root, its content is used as the system prompt sent to the model. If the file is absent, a built-in default prompt is used automatically.

---

## Resuming interrupted runs

Progress is saved to `result/progress_checkpoint.json` after every paper. If the script is stopped, re-running it will skip already completed papers.

To force reprocessing of specific papers by serial number:

```bash
python process_papers.py --force 2 5 7
```

Serial numbers are assigned in alphabetical order of filenames (1-based).

---

## File reference

```
project/
├── process_papers.py          # Main script
├── columns_config.json        # Column definitions — edit this to customise output
├── requirements.txt           # Python dependencies
├── .env                       # API credentials — gitignored, never committed
├── guideline.md               # Optional custom system prompt
├── paper_in_markdown/         # Input: drop .md papers here
└── result/                    # Output: created automatically
    ├── literature_review.xlsx
    ├── json_outputs/
    └── progress_checkpoint.json
```

---

## Notes

- Fields not found in a paper are written as `Not Reported (NR)`.
- Alternate row shading and frozen header row are applied automatically in the Excel output.
- The script retries failed API calls up to 3 times with a 10-second delay before logging the failure and moving on.

