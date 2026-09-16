import sqlite3, os
class MemoryStore:
    def __init__(self, path=None):
        from beau.core.config import BEAU_MEMORY_PATH
        self.path = path or BEAU_MEMORY_PATH
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self._init()
    def _init(self):
        with sqlite3.connect(self.path) as c:
            c.execute("CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY, user TEXT, assistant TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
    def save(self, user: str, assistant: str):
        with sqlite3.connect(self.path) as c: c.execute("INSERT INTO memory(user,assistant) VALUES(?,?)", (user, assistant))
    def recall(self, query: str, k=5):
        with sqlite3.connect(self.path) as c:
            rows = c.execute("SELECT user, assistant FROM memory ORDER BY id DESC LIMIT ?", (k,)).fetchall()
            return "\n".join(f"U:{u} A:{a}" for u,a in rows)
