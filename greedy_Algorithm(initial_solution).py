import pandas as pd
import numpy as np
import math
import folium
import sys
import time
import random

# --- DETERMINISTIK AYARLAR ---
# Her çalıştırmada aynı sonucu garanti etmek için seed sabitliyoruz.
random.seed(42)
np.random.seed(42)

# --- AYARLAR ---
# GitHub'daki Raw Veri Adresi
FILE_PATH = "https://raw.githubusercontent.com/TuncayOzkardes/EMU654-TuncayOzkardes/main/Master_Data.xlsx"

NODE_CAPACITY = 400000 
COVERAGE_RADIUS_KM = 12.0 
MIN_DISTANCE_BETWEEN_NODES = 10.0 

# --- ADAY İLÇE LİSTESİ ---
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
    'Muğla': [('Menteşe', 37.215, 28.363), ('Bodrum', 37.034, 27.430), ('Fethiye', 36.621, 29.116), ('Datça', 36.723, 27.684), ('Milas', 37.316, 27.784)]
}

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def smart_select_districts(city_name, needed_count, center_lat, center_lon):
    candidates = CANDIDATE_DISTRICTS.get(city_name, [])
    # Eğer aday listesi yoksa merkez + sanal
    if not candidates:
        candidates = [('Merkez', center_lat, center_lon)]
        if needed_count > 1:
             for i in range(1, needed_count):
                angle = (2 * math.pi / (needed_count)) * i
                d_lat = center_lat + (0.04 * math.sin(angle))
                d_lon = center_lon + (0.04 * math.cos(angle))
                candidates.append((f"Bolge_{i}", d_lat, d_lon))
    
    selected_nodes = []
    
    # Greedy Filtering (Uzak olanı seç)
    for cand_name, cand_lat, cand_lon in candidates:
        if len(selected_nodes) >= needed_count: break
        
        is_far_enough = True
        for _, s_lat, s_lon in selected_nodes:
            dist = calculate_haversine_distance(cand_lat, cand_lon, s_lat, s_lon)
            if dist < MIN_DISTANCE_BETWEEN_NODES:
                is_far_enough = False
                break
        
        if is_far_enough:
            selected_nodes.append((cand_name, cand_lat, cand_lon))
            
    return selected_nodes

def load_and_optimize_nodes():
    print("1. Veri Okunuyor ve Node Optimizasyonu Yapılıyor...")
    print(f"Veri Kaynağı: {FILE_PATH}")
    
    try:
        # engine='openpyxl' genelde gereklidir
        df = pd.read_excel(FILE_PATH, engine='openpyxl')
    except Exception as e:
        print(f"HATA: Dosya okunamadı. {e}")
        return []

    if df['lat'].mean() > 1000:
        df['lat'] = df['lat'] / 100000000.0
        df['lon'] = df['lon'] / 100000000.0
        
    final_node_list = []
    
    for index, row in df.iterrows():
        sehir = row['il']
        nufus = row['2030_Nufus']
        alan = row['Alan_(km²)']
        lat_merkez = row['lat']
        lon_merkez = row['lon']
        
        req_pop = math.ceil(nufus / NODE_CAPACITY)
        area_per_node = math.pi * (COVERAGE_RADIUS_KM ** 2)
        req_area = min(math.ceil(alan / area_per_node), 5) 
        needed_count = max(req_pop, req_area)
        
        selected = smart_select_districts(sehir, needed_count, lat_merkez, lon_merkez)
        
        for d_name, d_lat, d_lon in selected:
            final_node_list.append({
                'id': len(final_node_list),
                'name': f"{sehir}-{d_name}",
                'lat': d_lat,
                'lon': d_lon,
                'city': sehir
            })
            
    return final_node_list

def build_exact_greedy_tree(nodes):
    n = len(nodes)
    print(f"2. Exact Greedy İnşa Başlıyor ({n} Node)...")
    
    # 1. Fiziksel Mesafeler (d_G)
    dist_G = np.zeros((n, n))
    for i in range(n):
        for j in range(i+1, n):
            d = calculate_haversine_distance(nodes[i]['lat'], nodes[i]['lon'], nodes[j]['lat'], nodes[j]['lon'])
            if d < 0.001: d = 0.001 
            dist_G[i][j] = d
            dist_G[j][i] = d
            
    # 2. Başlangıç Node Seçimi (Ankara - Çankaya)
    # Sabit başlangıç noktası -> Deterministik Sonuç
    start_node = 0
    min_dist = float('inf')
    ankara_coords = (39.920, 32.853)
    
    for i, node in enumerate(nodes):
        # Eğer listede Çankaya varsa direkt onu seç, yoksa koordinata en yakını seç
        if "Ankara-Çankaya" in node['name']:
            start_node = i
            break
        d = calculate_haversine_distance(node['lat'], node['lon'], ankara_coords[0], ankara_coords[1])
        if d < min_dist:
            min_dist = d
            start_node = i

    print(f"   Başlangıç Kökü: {nodes[start_node]['name']} (ID: {start_node})")
    
    visited = {start_node}
    unvisited = set(range(n)) - visited
    tree_edges = []
    
    # Ağaç Mesafeleri (d_T)
    dist_T = np.full((n, n), np.inf)
    for i in range(n): dist_T[i][i] = 0
    
    step = 0
    start_time = time.time()
    
    # --- ANA DÖNGÜ ---
    while unvisited:
        step += 1
        best_edge = None
        best_max_stretch = float('inf')
        
        # Aday Havuzu
        candidates = []
        for u in visited:
            for v in unvisited:
                # 300 km filtresi performans için makul bir heuristic,
                # ama kesinlik için istersen bu "if"i kaldırabilirsin.
                # Ben işlem süresi aşırı uzamasın diye 400km limitini tutuyorum,
                # bu da akademik olarak "Candidate Filtering Heuristic" olarak açıklanır.
                if dist_G[u][v] < 400: 
                    candidates.append((u, v))
        
        # Eğer filtre yüzünden aday kalmazsa (Fallback)
        if not candidates:
             min_d = float('inf')
             for u in visited:
                 for v in unvisited:
                     if dist_G[u][v] < min_d:
                         min_d = dist_G[u][v]
                         best_edge = (u, v)
             candidates = [best_edge]
        
        # --- GREEDY SELECTION (EXACT - NO SAMPLING) ---
        # Burada 'random.sample' YOK. Tüm ağacı tarıyoruz.
        
        for u, v in candidates:
            w_uv = dist_G[u][v]
            local_max = 0
            
            # FULL SCAN: Tüm ağaç düğümleri ile kontrol et (Rastgelelik yok!)
            for x in visited:
                d_tree_new = dist_T[x][u] + w_uv
                d_orig = dist_G[x][v]
                
                # Stretch Oranı
                ratio = d_tree_new / d_orig
                if ratio > local_max:
                    local_max = ratio
            
            if local_max < best_max_stretch:
                best_max_stretch = local_max
                best_edge = (u, v)
        
        # En iyi kenarı ekle
        u_star, v_star = best_edge
        tree_edges.append((u_star, v_star))
        
        # Ağaç Mesafelerini Güncelle
        w_star = dist_G[u_star][v_star]
        for x in visited:
            new_d = dist_T[x][u_star] + w_star
            dist_T[x][v_star] = new_d
            dist_T[v_star][x] = new_d
            
        visited.add(v_star)
        unvisited.remove(v_star)
        
        # İlerleme (Tek satırda güncellenir)
        sys.stdout.write(f"\r   İlerleme: %{int(step/(n-1)*100)} | Son Eklenen: {nodes[v_star]['name']} | Max Stretch: {best_max_stretch:.2f}")
        sys.stdout.flush()
        
    print(f"\n   İnşa Tamamlandı. Süre: {time.time()-start_time:.2f} sn")
    return tree_edges

def visualize_result(nodes, edges):
    print("3. Harita Çiziliyor (CartoDB Positron - Beyaz)...")
    m = folium.Map(location=[39.0, 35.0], zoom_start=6, tiles='CartoDB positron')
    
    for node in nodes:
        folium.CircleMarker(
            location=[node['lat'], node['lon']],
            radius=4,
            color='#1f78b4', # Koyu Mavi
            fill=True,
            fill_color='#1f78b4',
            popup=node['name']
        ).add_to(m)
        
    for u, v in edges:
        p1 = [nodes[u]['lat'], nodes[u]['lon']]
        p2 = [nodes[v]['lat'], nodes[v]['lon']]
        folium.PolyLine([p1, p2], color="#e31a1c", weight=2, opacity=0.8).add_to(m)
        
    m.save("msstp_initial_solution_exact.html")
    print("Harita Kaydedildi: msstp_initial_solution_exact.html")

# --- MAIN ---
if __name__ == "__main__":
    nodes = load_and_optimize_nodes()
    if nodes:
        edges = build_exact_greedy_tree(nodes)
        visualize_result(nodes, edges)