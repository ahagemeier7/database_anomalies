import io
import zipfile
import requests
import pandas as pd

# URL pública de um repositório que contém o ZIP do dataset original europeu (Kaggle)
url = 'https://raw.githubusercontent.com/stat432/credit-analysis/main/data-raw/creditcard.csv.zip'

print("1. Baixando o dataset original compactado direto na memória...")
response = requests.get(url)
z = zipfile.ZipFile(io.BytesIO(response.content))

print("2. Extraindo e lendo o CSV...")
# O pd.read_csv consegue ler direto do arquivo compactado aberto na memória
df = pd.read_csv(z.open('creditcard.csv'))

print("3. Realizando amostragem estratificada...")
# Separamos todas as fraudes reais
df_fraud = df[df['Class'] == 1]  # Contém 492 linhas

# Selecionamos uma amostra menor de transações normais
df_normal = df[df['Class'] == 0].sample(n=15000, random_state=42)

# Combinamos as duas partes e embaralhamos as linhas
df_small = pd.concat([df_fraud, df_normal]).sample(frac=1, random_state=42)

# 4. Salvar o arquivo compacto pronto para o Git!
output_filename = 'creditcard_small.csv'
df_small.to_csv(output_filename, index=False)

print(f"\nSucesso! O arquivo '{output_filename}' foi gerado.")
print(f"Total de linhas: {len(df_small)}")
print(f"Fraudes mantidas: {len(df_fraud)}")
print(f"Transações normais: {len(df_normal)}")
print(f"Tamanho estimado em disco: ~2.4 MB (Perfeito para subir no GitHub)")