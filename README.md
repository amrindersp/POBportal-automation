python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# create DB + table
# mysql> CREATE DATABASE automation_db;
# mysql> USE automation_db;
# mysql> CREATE TABLE automation_runs (...);

uvicorn app.main:app --reload
