import mysql.connector

conn = mysql.connector.connect(
    host='srv1502.hstgr.io',
    database='u792485705_mtgfinal',
    user='u792485705_final',
    password='7rWolwcD|'
)

cursor = conn.cursor(dictionary=True)
cursor.execute('SELECT id, cardtrader_id, game_id, name FROM sets LIMIT 10')
results = cursor.fetchall()

print("DB SETS:")
for row in results:
    print(f"  ID: {row['id']} | CT_ID: {row['cardtrader_id']} | Game: {row['game_id']} | Name: {row['name'][:25]}")

cursor.close()
conn.close()
