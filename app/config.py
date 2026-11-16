from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    db_path: str = "./data/grantalloc.db"
    rule_version: str = "2026.11"
    timezone: str = "Asia/Shanghai"

    @classmethod
    def from_env(cls):
        return cls(db_path=os.getenv("DB_PATH", cls.db_path),
                   rule_version=os.getenv("RULE_VERSION", cls.rule_version))
