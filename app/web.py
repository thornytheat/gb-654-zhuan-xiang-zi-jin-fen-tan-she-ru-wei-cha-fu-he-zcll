from pathlib import Path
from fastapi.templating import Jinja2Templates

BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE / "templates"))
PAGES = [('/budgets', 'm1_budgets.html', '预算采信'), ('/eligibility', 'm2_eligibility.html', '资格校验'), ('/weights', 'm3_weights.html', '权重测算'), ('/allocations', 'm4_allocations.html', '金额分摊'), ('/remainders', 'm5_remainders.html', '尾差裁决'), ('/runs', 'm6_runs.html', '批次复核')]
