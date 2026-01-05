import pandas as pd
import numpy as np
import math
import folium
import sys
import time
import random
import copy

# --- DETERMINISTIK SEED ---
random.seed(42)
np.random.seed(42)

# --- AYARLAR ---
# GitHub Raw Veri Adresi
FILE_PATH = "https://raw.githubusercontent.com/TuncayOzkardes/EMU654-TuncayOzkardes/main/Master_Data.xlsx"

NODE_CAPACITY = 400000 
COVERAGE_RADIUS_KM = 12.0 
MIN_DISTANCE_BETWEEN_NODES = 10.0 

# CG PARAMETRELERİ
CG_ITERATIONS = 700  # Alpha yaklaşık 1.5 - 2.0 arası (140 kenarımız var)

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
    if not candidates:
        candidates = [('Merkez', center_lat, center_lon)]
        if needed_count > 1:
             for i in range(1, needed_count):
                angle = (2 * math.pi / (needed_count)) * i
                d_lat = center_lat + (0.04 * math.sin(angle))
                d_lon = center_lon + (0.04 * math.cos(angle))
                candidates.append((f"Bolge_{i}", d_lat, d_lon))
    
    selected_nodes = []
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
    print("1. Veri Hazırlanıyor...")
    print(f"Veri Kaynağı: {FILE_PATH}")
    try:
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

# --- HIZLI STRETCH HESABI İÇİN YARDIMCI ---
def bfs_shortest_path(n, adj, start_node):
    """Ağaç üzerindeki tüm mesafeleri BFS ile bulur (Ağırlıklı değil, Hop sayısı değil, KM)"""
    dists = [-1] * n
    dists[start_node] = 0
    queue = [start_node]
    
    idx = 0
    while idx < len(queue):
        u = queue[idx]
        idx += 1
        for v, w in adj[u]:
            if dists[v] == -1:
                dists[v] = dists[u] + w
                queue.append(v)
    return dists

def calculate_global_max_stretch(n, edges, dist_G):
    """Tüm ağacın Max Stretch değerini hesaplar."""
    # Adjacency List Oluştur
    adj = [[] for _ in range(n)]
    for u, v in edges:
        w = dist_G[u][v]
        adj[u].append((v, w))
        adj[v].append((u, w))
        
    max_stretch = 0
    # Her node için BFS yaparak ağaç mesafelerini bul
    for i in range(n):
        tree_dists = bfs_shortest_path(n, adj, i)
        for j in range(i+1, n):
            d_tree = tree_dists[j]
            d_geo = dist_G[i][j]
            if d_geo < 0.001: d_geo = 0.001
            
            s = d_tree / d_geo
            if s > max_stretch:
                max_stretch = s
    return max_stretch

def build_initial_greedy(nodes, dist_G):
    """Initial Solution (Aynısı)"""
    n = len(nodes)
    print("   Initial Solution İnşa Ediliyor...")
    
    start_node = 0
    ankara_coords = (39.920, 32.853)
    min_dist = float('inf')
    for i, node in enumerate(nodes):
        if "Ankara-Çankaya" in node['name']:
            start_node = i; break
        d = calculate_haversine_distance(node['lat'], node['lon'], ankara_coords[0], ankara_coords[1])
        if d < min_dist: min_dist = d; start_node = i
            
    visited = {start_node}
    unvisited = set(range(n)) - visited
    tree_edges = [] # Ordered list
    
    dist_T = np.full((n, n), np.inf)
    for i in range(n): dist_T[i][i] = 0
    
    while unvisited:
        best_edge = None
        best_max_stretch = float('inf')
        
        candidates = []
        for u in visited:
            for v in unvisited:
                if dist_G[u][v] < 400: candidates.append((u,v))
        if not candidates: # Fallback
             for u in visited:
                 for v in unvisited: candidates.append((u,v))
                 
        # Greedy Choice
        for u, v in candidates:
            w_uv = dist_G[u][v]
            local_max = 0
            for x in visited:
                d_tree_new = dist_T[x][u] + w_uv
                ratio = d_tree_new / dist_G[x][v]
                if ratio > local_max: local_max = ratio
            if local_max < best_max_stretch:
                best_max_stretch = local_max
                best_edge = (u, v)
        
        u_star, v_star = best_edge
        tree_edges.append((u_star, v_star))
        
        w_star = dist_G[u_star][v_star]
        for x in visited:
            new_d = dist_T[x][u_star] + w_star
            dist_T[x][v_star] = new_d
            dist_T[v_star][x] = new_d
            
        visited.add(v_star)
        unvisited.remove(v_star)
        
    return tree_edges

# --- CAROUSEL GREEDY LOGIC ---
def get_components(n, edges_subset):
    """Bir orman (forest) içindeki bileşenleri bulur."""
    adj = [[] for _ in range(n)]
    for u, v in edges_subset:
        adj[u].append(v)
        adj[v].append(u)
        
    visited = [False] * n
    components = []
    for i in range(n):
        if not visited[i]:
            comp = []
            stack = [i]
            visited[i] = True
            while stack:
                u = stack.pop()
                comp.append(u)
                for v in adj[u]:
                    if not visited[v]:
                        visited[v] = True
                        stack.append(v)
            components.append(comp)
    return components

def carousel_greedy_optimization(nodes, initial_edges, dist_G):
    n = len(nodes)
    current_edges = list(initial_edges) # Listeyi kopyala (Sıralı tutulmalı!)
    
    print(f"\n2. CAROUSEL GREEDY BAŞLIYOR (Iterasyon: {CG_ITERATIONS})...")
    
    # Başlangıç Skorunu Hesapla
    current_max_stretch = calculate_global_max_stretch(n, current_edges, dist_G)
    print(f"   Başlangıç Max Stretch: {current_max_stretch:.4f}")
    
    start_time = time.time()
    
    for it in range(CG_ITERATIONS):
        # 1. DESTRUCT: En eski kenarı (Listenin başı) çıkar
        removed_edge = current_edges.pop(0) # Index 0'ı sil ve kaydır
        
        # 2. Bileşenleri Bul (C1 ve C2)
        components = get_components(n, current_edges)
        # Ağaçtan 1 kenar silince tam 2 bileşen kalmalı
        if len(components) != 2:
            # Hata durumu (olmamalı), kenarı geri koy
            current_edges.append(removed_edge)
            continue
            
        comp1 = components[0]
        comp2 = components[1]
        
        # 3. CONSTRUCT: İki bileşeni bağlayan EN İYİ kenarı bul
        best_candidate = None
        best_candidate_stretch = float('inf')
        
        # Aday Havuzu (Comp1 ile Comp2 arasındaki kenarlar)
        candidates = []
        for u in comp1:
            for v in comp2:
                if dist_G[u][v] < 400: # Mesafe filtresi (Hız için)
                    candidates.append((u, v))
        
        if not candidates: # Eğer filtre yüzünden aday yoksa
             # En yakınını bul (Fallback)
             best_candidate = (comp1[0], comp2[0]) # Rastgele değil, ilk elemanlar (Deterministik)
             min_d = float('inf')
             for u in comp1:
                 for v in comp2:
                     if dist_G[u][v] < min_d:
                         min_d = dist_G[u][v]
                         best_candidate = (u,v)
        else:
            # Greedy Kriteri: Yeni kenar eklendiğinde Max Stretch ne olur?
            # Burası yavaş olabilir, ama Exact sonuç için gerekli.
            for u, v in candidates:
                # Geçici olarak ekle
                current_edges.append((u, v))
                
                # Tüm ağacın stretch'ini hesapla
                # (Optimizasyon: Sadece değişen yollara bakılabilir ama kod karmaşıklaşır)
                s = calculate_global_max_stretch(n, current_edges, dist_G)
                
                if s < best_candidate_stretch:
                    best_candidate_stretch = s
                    best_candidate = (u, v)
                
                # Geri çıkar
                current_edges.pop()
        
        # 4. ROTATE: En iyi kenarı listenin SONUNA ekle (En yeni yap)
        current_edges.append(best_candidate)
        
        # İyileşme var mı? (Sadece raporlama için)
        current_max_stretch = calculate_global_max_stretch(n, current_edges, dist_G)
        
        sys.stdout.write(f"\r   Iterasyon {it+1}/{CG_ITERATIONS} | Stretch: {current_max_stretch:.4f}")
        sys.stdout.flush()
        
    print(f"\n   Carousel Tamamlandı. Süre: {time.time()-start_time:.2f} sn")
    print(f"   Final Max Stretch: {current_max_stretch:.4f}")
    
    return current_edges

def visualize_cg_result(nodes, edges):
    print("3. Harita Çiziliyor (Yeşil Ağaç - CG Result)...")
    m = folium.Map(location=[39.0, 35.0], zoom_start=6, tiles='CartoDB positron')
    
    for node in nodes:
        folium.CircleMarker(
            location=[node['lat'], node['lon']],
            radius=4,
            color='#1f78b4',
            fill=True,
            fill_color='#1f78b4',
            popup=node['name']
        ).add_to(m)
        
    for u, v in edges:
        p1 = [nodes[u]['lat'], nodes[u]['lon']]
        p2 = [nodes[v]['lat'], nodes[v]['lon']]
        # CG sonucunu YEŞİL çizelim ki farkı belli olsun
        folium.PolyLine([p1, p2], color="green", weight=2, opacity=0.9).add_to(m)
        
    m.save("msstp_carousel_greedy_result.html")
    print("Dosya Kaydedildi: msstp_carousel_greedy_result.html")

# --- MAIN ---
if __name__ == "__main__":
    nodes = load_and_optimize_nodes()
    if nodes:
        n = len(nodes)
        
        # Mesafe Matrisi (Ortak Kullanım)
        dist_G = np.zeros((n, n))
        for i in range(n):
            for j in range(i+1, n):
                d = calculate_haversine_distance(nodes[i]['lat'], nodes[i]['lon'], nodes[j]['lat'], nodes[j]['lon'])
                if d < 0.001: d = 0.001
                dist_G[i][j] = d
                dist_G[j][i] = d
        
        # 1. Initial Greedy
        initial_edges = build_initial_greedy(nodes, dist_G)
        
        # 2. Carousel Greedy
        final_edges = carousel_greedy_optimization(nodes, initial_edges, dist_G)
        
        # 3. Görselleştir
        visualize_cg_result(nodes, final_edges)