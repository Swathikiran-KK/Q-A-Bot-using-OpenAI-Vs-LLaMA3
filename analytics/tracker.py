# analytics/tracker.py
import time, pandas as pd, os
from typing import Optional, Any, Dict, List

class MetricsTracker:
    def __init__(self):
        self.rows: List[Dict[str, Any]] = []
        self._next_id = 1  # simple incremental run_id

    def _alloc_id(self) -> int:
        rid = self._next_id
        self._next_id += 1
        return rid

    def log(self, row: dict) -> int:
        """Append a row and return its run_id."""
        run_id = row.get("run_id") or self._alloc_id()
        stamped = {
            **row,
            "run_id": run_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.rows.append(stamped)
        return run_id

    def update_by_id(self, run_id: int, **fields):
        for r in reversed(self.rows):
            if r.get("run_id") == run_id:
                r.update(fields)
                return True
        return False

    def df(self):
        return pd.DataFrame(self.rows)

    # Persistence
    def save_csv(self, path="llm_benchmarks.csv"):
        if not self.rows: 
            # still write an empty df to keep schema stable
            pd.DataFrame(self.rows).to_csv(path, index=False)
            return
        df = self.df()
        df.to_csv(path, index=False)

    def load_csv(self, path="llm_benchmarks.csv"):
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                self.rows = df.to_dict(orient="records")
                # restore next_id (max existing + 1)
                if "run_id" in df.columns and not df["run_id"].empty:
                    self._next_id = int(df["run_id"].max()) + 1
            except Exception:
                pass

    def clear(self):
        self.rows = []
        self._next_id = 1
