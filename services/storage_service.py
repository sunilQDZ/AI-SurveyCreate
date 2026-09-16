import json
import os
from datetime import datetime
from config import OUTPUT_FILE, RESPONSES_FILE, FINALIZED_DIR

# Ensure output files exist
for path, default in [(OUTPUT_FILE, []), (RESPONSES_FILE, [])]:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(default, fh, indent=2)


def save_history(entry: dict):
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    data.append(entry)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_finalized_template(final_template: dict) -> tuple[str, str]:
    template_id = datetime.now().strftime("%Y%m%d%H%M%S")
    os.makedirs(FINALIZED_DIR, exist_ok=True)
    file_path = os.path.join(FINALIZED_DIR, f"template_{template_id}.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(final_template, f, ensure_ascii=False, indent=2)

    save_history({
        "timestamp": datetime.now().isoformat(),
        "action": "finalize",
        "path": file_path,
        "template": final_template
    })

    return template_id, file_path


