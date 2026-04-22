import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine("postgresql://postgres:postgres@localhost:5432/db_real")

df = pd.read_csv('creditcard.csv')

df_normal = df[df['Class'] == 0].head(50000)
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
