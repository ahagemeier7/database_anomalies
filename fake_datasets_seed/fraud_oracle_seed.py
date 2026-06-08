import os
import pandas as pd
from sqlalchemy import create_engine, text

# https://www.kaggle.com/datasets/shivamb/insurance-claim-analysis-code

engine = create_engine("postgresql://postgres:postgres@localhost:5432/db_real")

diretorio_atual = os.path.dirname(os.path.abspath(__file__))

#build the complete path
caminho_csv = os.path.join(diretorio_atual, 'fraud_oracle.csv')

df = pd.read_csv(caminho_csv)

df_normal = df[df['FraudFound_P'] == 0].reset_index(drop=True)
df_fraude = df[df['FraudFound_P'] == 1].reset_index(drop=True)


df_normal['id'] = range(1, len(df_normal) + 1)

df_normal.to_sql('insurance_claims', engine, if_exists='replace', index=False)

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE insurance_claims ADD PRIMARY KEY (id);"))
    conn.commit()

print("Normal claims inserted!\n")

# =========================================================
input("turn the containers on, and then press ENTER to send the frauds to the database, to test if the model will find them")
# =========================================================

df_fraude['id'] = range(len(df_normal) + 1, len(df_normal) + len(df_fraude) + 1)

df_fraude.to_sql('insurance_claims', engine, if_exists='append', index=False)

print("Fraud claims inserted!\n")
