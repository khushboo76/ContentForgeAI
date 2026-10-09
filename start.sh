cd ~/Documents/automated-content-generator && \
(cd backend && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt && .venv/bin/python -m pip install pypdf && .venv/bin/python -m uvicorn main:app --reload) & \
(cd ~/Documents/automated-content-generator/frontend && npm install && npm run dev)