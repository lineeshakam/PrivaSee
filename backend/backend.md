python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
python3 -m backend.run

test run:

$ curl -X POST http://localhost:5001/analyze -H "Content-Type: application/json" -d '{"text": "We collect your personal data and share it with third parties."}'