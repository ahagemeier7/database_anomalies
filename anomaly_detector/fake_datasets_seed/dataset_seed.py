import os
import pandas as pd
from sqlalchemy import create_engine, text

#https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud

engine = create_engine("postgresql://postgres:postgres@localhost:5432/db_real")

diretorio_atual = os.path.dirname(os.path.abspath(__file__))

# 2. Monta o caminho completo até o CSV
caminho_csv = os.path.join(diretorio_atual, 'creditcard.csv')

# 3. Lê usando o caminho completo
df = pd.read_csv(caminho_csv)

df_normal = df[df['Class'] == 0].head(50000).reset_index(drop=True)
df_fraude = df[df['Class'] == 1]


df_normal.to_sql('credit_card_transactions', engine, if_exists='replace', index_label='id')

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE credit_card_transactions ADD PRIMARY KEY (id);"))
    conn.commit()

print("Normal transactions inserted!\n")

# =========================================================
input("turn the containers on, and then press ENTER to send the frauds to the database, to test if the model will find them")
# =========================================================


df_fraude.index = range(50000, 50000 + len(df_fraude)) 


df_fraude.to_sql('credit_card_transactions', engine, if_exists='append', index_label='id')
