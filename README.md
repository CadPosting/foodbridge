# foodbridge
FoodBridge: food donation coordination system

## Run locally
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/flask --app foodbridge init-db   # creates instance/foodbridge.db
.venv/bin/flask --app foodbridge run --debug
.venv/bin/python -m pytest tests           # pass "tests"; the [7] in the folder path confuses pytest otherwise
```
