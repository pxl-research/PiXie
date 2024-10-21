import json
import pandas as pd
import os
import psycopg2

# Databaseverbinding maken
conn = psycopg2.connect(
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    host="db",
    port="5432",
)
cursor = conn.cursor()

# Users.json inlezen en gegevens invoegen
with open("src/assets/helper/Users.json") as f:
    users = json.load(f)

for username, info in users.items():
    cursor.execute(
        "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
        (username, info["password"], info["role"]),
    )

# doc_list.csv inlezen en gegevens invoegen
doc_df = pd.read_csv("src/assets/helper/doc_list.csv")

for index, row in doc_df.iterrows():
    cursor.execute(
        "INSERT INTO documents (file_name, file_hash, last_updated) VALUES (%s, %s, %s)",
        (row["file_name"], row["file_hash"], row["last_updated"]),
    )

# Wijzigingen opslaan en verbinding sluiten
conn.commit()
cursor.close()
conn.close()

print("Gegevens zijn succesvol gemigreerd!")
