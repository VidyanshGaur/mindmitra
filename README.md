# MindMitra

An educational CLNLP final-project prototype for cognitive gaming and memory assistance for elderly dementia patients.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Dataset note

This prototype uses synthetic/demo information. For language research, DementiaBank provides controlled-access dementia speech data: https://dementia.talkbank.org/access/

`data/intents.csv` is the project's training dataset. The app trains a TF-IDF + Logistic Regression model from it whenever the Streamlit session starts. Add more example sentences under each intent to improve the classifier.

## Local storage

The app creates `mindmitra.db` automatically. This SQLite database stores demo reminders, mood check-ins, and game scores on the local device. Do not upload this file to a public repository if it contains real personal information.

Do not use identifiable patient data without consent and institutional approval.
