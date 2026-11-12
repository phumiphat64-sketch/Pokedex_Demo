import io
import pandas as pd
import requests

# 1. โหลดข้อมูลเดิมจากไฟล์ของคุณ (เปลี่ยนชื่อไฟล์ตรงนี้หากคุณใช้ pokemon_2.csv)
file_name = 'pokemon.csv' 
df_original = pd.read_csv(file_name)

# 2. ดึงข้อมูลตาราง Stats ล่าสุดจาก Pokemondb.net
url = "https://pokemondb.net/pokedex/all"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
print(f"Fetching data from {url}...")
response = requests.get(url, headers=headers)

if response.status_code == 200:
    # อ่านตารางทั้งหมดจาก HTML (Pokemondb มีตารางใหญ่ตารางเดียวในหน้านี้)
    tables = pd.read_html(io.StringIO(response.text))
    db_df = tables[0]
    
    # 3. คลีนและเตรียมข้อมูลจาก Pokemondb
    # เปลี่ยนชื่อคอลัมน์ให้ตรงกันเพื่อเตรียม Merge
    db_df.rename(columns={
        '#': 'pokedex_number',
        'Total': 'base_total_new',
        'HP': 'hp_new',
        'Attack': 'attack_new',
        'Defense': 'defense_new',
        'Sp. Atk': 'sp_attack_new',
        'Sp. Def': 'sp_defense_new',
        'Speed': 'speed_new'
    }, inplace=True)

    # แปลง Pokedex Number เป็น Integer เพื่อใช้เป็น Key ในการ Join
    db_df['pokedex_number'] = db_df['pokedex_number'].astype(int)
    
    # Pokemondb จะมีร่าง Mega/Regional ซ้อนอยู่ใน Pokedex Number เดียวกัน
    # เราจะ Drop duplicates ให้เหลือแค่แถวแรกสุด ซึ่งก็คือ Base Form ที่ตรงกับ Dataset เดิม
    db_base_forms = db_df.drop_duplicates(subset=['pokedex_number'], keep='first')

    # เลือกมาเฉพาะคอลัมน์ที่ต้องการอัปเดต
    cols_to_update = ['pokedex_number', 'base_total_new', 'hp_new', 'attack_new', 
                      'defense_new', 'sp_attack_new', 'sp_defense_new', 'speed_new']
    db_base_forms = db_base_forms[cols_to_update]

    # 4. Merge ข้อมูลใหม่เข้าไปใน Dataset เดิม (Left Join)
    df_merged = pd.merge(df_original, db_base_forms, on='pokedex_number', how='left')

    # 5. แทนที่ค่า Stat เดิมที่ผิด ด้วยค่าใหม่ที่ดึงมาได้
    stat_mapping = {
        'hp': 'hp_new',
        'attack': 'attack_new',
        'defense': 'defense_new',
        'sp_attack': 'sp_attack_new',
        'sp_defense': 'sp_defense_new',
        'speed': 'speed_new',
        'base_total': 'base_total_new'
    }

    # อัปเดตค่าและลบคอลัมน์ _new ทิ้ง
    for old_col, new_col in stat_mapping.items():
        df_merged[old_col] = df_merged[new_col].fillna(df_merged[old_col]).astype(int)
        
    df_merged.drop(columns=stat_mapping.values(), inplace=True)

    # 6. บันทึกไฟล์ใหม่
    output_name = 'pokemon_updated.csv'
    df_merged.to_csv(output_name, index=False)
    print(f"อัปเดตค่า Stats ตาม Pokemondb เรียบร้อย! บันทึกเป็นไฟล์ '{output_name}'")
else:
    print(f"เกิดข้อผิดพลาดในการดึงข้อมูล HTTP Status: {response.status_code}")