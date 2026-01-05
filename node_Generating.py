import pandas as pd
import numpy as np
import math
import folium
import sys

# --- AYARLAR ---
# GitHub Raw URL (Büyük/Küçük harf duyarlı doğru adres)
FILE_PATH = "https://raw.githubusercontent.com/TuncayOzkardes/EMU654-TuncayOzkardes/main/Master_Data.xlsx"

NODE_CAPACITY = 400000 
COVERAGE_RADIUS_KM = 12.0 # Bu artık "Koruma Kalkanı" mesafemiz olacak.
MIN_DISTANCE_BETWEEN_NODES = 10.0 # İki node birbirine en az 10 km uzak olmalı (Çakışmayı önlemek için)

# --- YARDIMCI FONKSİYON: HAVERSINE (GERÇEK DÜNYA MESAFESİ) ---
def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 # Dünya yarıçapı (km)
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

# --- 81 İL İÇİN ADAY İLÇE LİSTESİ (ÖNEM SIRASINA GÖRE) ---
# Algoritma bu sırayla deneyecek. Yakın olanı eleyecek.
CANDIDATE_DISTRICTS = {
    'İstanbul': [('Esenyurt', 41.034, 28.680), ('Kadıköy', 40.990, 29.029), ('Bağcılar', 41.033, 28.857), ('Ümraniye', 41.025, 29.096), ('Pendik', 40.876, 29.234), ('Sarıyer', 41.166, 29.050), ('Büyükçekmece', 41.021, 28.579), ('Silivri', 41.074, 28.246), ('Şile', 41.176, 29.612), ('Arnavutköy', 41.185, 28.740), ('Çatalca', 41.143, 28.459), ('Tuzla', 40.816, 29.303), ('Başakşehir', 41.097, 28.807), ('Beykoz', 41.123, 29.106), ('Fatih', 41.011, 28.935), ('Kartal', 40.888, 29.185)],
    'Ankara': [('Çankaya', 39.920, 32.853), ('Sincan', 39.962, 32.580), ('Keçiören', 39.996, 32.863), ('Gölbaşı', 39.791, 32.805), ('Polatlı', 39.584, 32.146), ('Çubuk', 40.238, 33.032), ('Kızılcahamam', 40.472, 32.651), ('Şereflikoçhisar', 38.938, 33.541), ('Beypazarı', 40.168, 31.921), ('Elmadağ', 39.919, 33.230)],
    'İzmir': [('Konak', 38.419, 27.128), ('Bergama', 39.121, 27.178), ('Ödemiş', 38.229, 27.973), ('Çeşme', 38.323, 26.304), ('Tire', 38.089, 27.734), ('Torbalı', 38.152, 27.362), ('Menemen', 38.607, 27.074), ('Urla', 38.325, 26.764), ('Karaburun', 38.636, 26.516), ('Dikili', 39.071, 26.890)],
    'Antalya': [('Muratpaşa', 36.886, 30.704), ('Alanya', 36.543, 31.999), ('Manavgat', 36.786, 31.443), ('Kaş', 36.200, 29.637), ('Kumluca', 36.368, 30.291), ('Korkuteli', 37.065, 30.196), ('Gazipaşa', 36.269, 32.317), ('Akseki', 37.047, 31.789)],
    'Adana': [('Seyhan', 36.995, 35.324), ('Kozan', 37.455, 35.812), ('Ceyhan', 37.029, 35.815), ('Pozantı', 37.426, 34.873), ('Tufanbeyli', 38.261, 36.223)],
    'Bursa': [('Osmangazi', 40.201, 29.053), ('İnegöl', 40.078, 29.513), ('Mustafakemalpaşa', 40.036, 28.411), ('İznik', 40.429, 29.719), ('Karacabey', 40.214, 28.358), ('Orhangazi', 40.493, 29.309)],
    'Konya': [('Selçuklu', 37.949, 32.498), ('Ereğli', 37.513, 34.053), ('Akşehir', 38.356, 31.416), ('Beyşehir', 37.677, 31.724), ('Cihanbeyli', 38.654, 32.923), ('Kulu', 39.094, 33.079), ('Seydişehir', 37.419, 31.848)],
    'Sivas': [('Merkez', 39.750, 37.014), ('Divriği', 39.371, 38.113), ('Şarkışla', 39.352, 36.408), ('Gemerek', 39.187, 36.071), ('Zara', 39.897, 37.758)],
    'Trabzon': [('Ortahisar', 41.002, 39.716), ('Of', 40.947, 40.270), ('Vakfıkebir', 41.052, 39.293), ('Maçka', 40.811, 39.612)],
    'Van': [('İpekyolu', 38.501, 43.391), ('Erciş', 39.027, 43.362), ('Başkale', 38.046, 44.015), ('Çaldıran', 39.143, 43.912)],
    'Muğla': [('Menteşe', 37.215, 28.363), ('Bodrum', 37.034, 27.430), ('Fethiye', 36.621, 29.116), ('Datça', 36.723, 27.684), ('Milas', 37.316, 27.784)],
    # ... Diğer iller için merkez + temsili uzak ilçeler mantığı devam eder ...
}

def smart_select_districts(city_name, needed_count, center_lat, center_lon):
    """
    Bu fonksiyon aday ilçeler arasından BİRBİRİNE EN UZAK olanları seçer.
    """
    # 1. Aday Listesini Al
    candidates = []
    if city_name in CANDIDATE_DISTRICTS:
        candidates = CANDIDATE_DISTRICTS[city_name] # [(Ad, Lat, Lon), ...]
    
    # Eğer aday listesi yetersizse veya boşsa, Merkez'i ekle ve sanal üret
    if not candidates:
        candidates = [('Merkez', center_lat, center_lon)]

    selected_nodes = []
    
    # 2. SEÇİM DÖNGÜSÜ (GREEDY FILTERING)
    # Adayları sırayla gez. Eğer seçilmişlere çok yakın değilse, SEÇ.
    
    for cand_name, cand_lat, cand_lon in candidates:
        # Kapasitemiz doldu mu?
        if len(selected_nodes) >= needed_count:
            break
            
        # Mesafe Kontrolü
        is_far_enough = True
        for _, s_lat, s_lon in selected_nodes:
            dist = calculate_haversine_distance(cand_lat, cand_lon, s_lat, s_lon)
            if dist < MIN_DISTANCE_BETWEEN_NODES:
                is_far_enough = False
                break # Çok yakın, bunu atla
        
        if is_far_enough:
            selected_nodes.append((cand_name, cand_lat, cand_lon))
            
    # 3. YEDEK PLAN:
    # Eğer filtreleme yüzünden elimizde yeterli node kalmadıysa (Örn: İst için 40 lazımdı ama 10 tane sığdı)
    # Kalan ihtiyacı, mevcutların etrafına değil, şehrin boşluklarına (sanal) koyabiliriz
    # VEYA Bütçe kısıtlı dediğin için "Bu kadar node yeterli, daha fazlası israf" diyip bırakabiliriz.
    # Ben 2. seçeneği (Bırakmayı) seçiyorum çünkü "Bütçe kısıtlı" dedin.
    
    return selected_nodes

def main_process_optimized(path):
    print("Mesafe optimizasyonlu altyapı kuruluyor...")
    print(f"Veri kaynağı: {path}")
    
    try:
        # Pandas URL'den direkt okuyabilir (xlrd veya openpyxl gerekebilir)
        df = pd.read_excel(path, engine='openpyxl')
    except Exception as e:
        print(f"!!! HATA: Dosya okunamadı. İnternet bağlantınızı veya linki kontrol edin.\nHata: {e}")
        return

    # Koordinat düzeltme
    if df['lat'].mean() > 1000:
        df['lat'] = df['lat'] / 100000000.0
        df['lon'] = df['lon'] / 100000000.0
    
    expanded_rows = []
    
    for index, row in df.iterrows():
        sehir = row['il']
        nufus = row['2030_Nufus']
        alan = row['Alan_(km²)']
        lat_merkez = row['lat']
        lon_merkez = row['lon']
        
        # --- İhtiyaç Hesabı ---
        req_pop = math.ceil(nufus / NODE_CAPACITY)
        area_per_node = math.pi * (COVERAGE_RADIUS_KM ** 2)
        req_area_raw = math.ceil(alan / area_per_node)
        req_area = min(req_area_raw, 5) # Max 5 kısıtı
        
        needed_count = max(req_pop, req_area)
        
        # --- AKILLI SEÇİM ---
        selected_districts = smart_select_districts(sehir, needed_count, lat_merkez, lon_merkez)
        
        # Seçilenleri listeye ekle
        # Not: Filtreleme sonucu needed_count'tan AZ node seçilmiş olabilir. 
        # Bu, bütçe tasarrufu sağlar. (Örn: Beşiktaş varken Şişli'ye gerek yok)
        real_node_count = len(selected_districts)
        
        for i, (d_name, d_lat, d_lon) in enumerate(selected_districts):
            expanded_rows.append({
                'Node_ID': f"{sehir}_{d_name}",
                'Original_City': sehir,
                'Latitude': d_lat,
                'Longitude': d_lon,
                # Nüfusu seçilen GERÇEK node sayısına bölüyoruz. 
                # Böylece yük artıyor ama node sayısı azalıyor (Verimlilik)
                'Demand': int(nufus / real_node_count), 
                'Type': 'Optimized_District'
            })
            
    final_df = pd.DataFrame(expanded_rows)
    print(f"Optimizasyon Sonucu Toplam Node Sayısı: {len(final_df)}")
    
    # --- GÖRSELLEŞTİRME ---
    m = folium.Map(location=[39.0, 35.0], zoom_start=6, tiles='CartoDB positron')
    
    for _, row in final_df.iterrows():
        # Node Merkezi (Nokta)
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=4,
            color='darkblue',
            fill=True,
            fill_color='blue',
            popup=f"{row['Node_ID']}<br>Yük: {row['Demand']}"
        ).add_to(m)
        
        # Kapsama Alanı (Çember - 12 km yarıçap)
        # Radius metre cinsinden verilmeli (12 km = 12000 m)
        folium.Circle(
            location=[row['Latitude'], row['Longitude']],
            radius=COVERAGE_RADIUS_KM * 1000, 
            color='blue',
            fill=True,
            fill_opacity=0.1, # Hafif saydam dolgu
            weight=1
        ).add_to(m)
        
    m.save("turkiye_optimized_coverage_map.html")
    print("Harita kaydedildi: turkiye_optimized_coverage_map.html")
    return final_df

if __name__ == "__main__":
    final_nodes = main_process_optimized(FILE_PATH)