import pandas as pd
import numpy as np
import math
import sys
import time
import random
import heapq
import copy

# --- AYARLAR ---
# GitHub Veri Kaynağı
FILE_PATH = "https://raw.githubusercontent.com/TuncayOzkardes/EMU654-TuncayOzkardes/main/Master_Data.xlsx"

NODE_CAPACITY = 400000 
COVERAGE_RADIUS_KM = 12.0 
MIN_DISTANCE_BETWEEN_NODES = 10.0 

# --- GVNS AYARLARI ---
GVNS_MAX_ITER = 50       # Toplam ana döngü sayısı
GVNS_K_MAX = 3           # Shaking (Sarsma) derinliği

random.seed(42)
np.random.seed(42)

# --- ADAY İLÇE LİSTESİ (Tam Liste) ---
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
                angle = (2 * math.pi / needed_count) * i
                d_lat = center_lat + (0.04 * math.sin(angle))
                d_lon = center_lon + (0.04 * math.cos(angle))
                candidates.append((f"Bolge_{i}", d_lat, d_lon))
            
    selected_nodes = []
    # Greedy Filtering
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

def load_and_generate_nodes():
    print(">>> Veri seti GitHub'dan okunuyor...")
    try:
        df = pd.read_excel(FILE_PATH, engine='openpyxl')
    except Exception as e:
        print(f"HATA: {e}")
        sys.exit(1)

    if df['lat'].mean() > 1000:
        df['lat'] /= 100000000.0
        df['lon'] /= 100000000.0
        
    final_node_list = []
    for index, row in df.iterrows():
        sehir = str(row['il']).strip()
        nufus = row['2030_Nufus']
        alan = row['Alan_(km²)']
        lat = row['lat']
        lon = row['lon']
        
        req_pop = math.ceil(nufus / NODE_CAPACITY)
        req_area = min(math.ceil(alan / (math.pi*12**2)), 5)
        needed = max(req_pop, req_area)
        
        selected = smart_select_districts(sehir, needed, lat, lon)
        for d_name, d_lat, d_lon in selected:
            final_node_list.append({
                'id': len(final_node_list),
                'name': f"{sehir}-{d_name}",
                'lat': d_lat,
                'lon': d_lon
            })
    return final_node_list

# --- METRİKLER ---
def bfs_shortest_path(n, adj, start_node):
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

def calculate_max_stretch(n, edges, dist_G):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        w = dist_G[u][v]
        adj[u].append((v, w))
        adj[v].append((u, w))
        
    max_stretch = 0
    for i in range(n):
        tree_dists = bfs_shortest_path(n, adj, i)
        for j in range(i+1, n):
            d_geo = dist_G[i][j]
            d_tree = tree_dists[j]
            if d_tree == -1: return float('inf') 
            if d_geo < 0.001: d_geo = 0.001
            s = d_tree / d_geo
            if s > max_stretch: max_stretch = s
    return max_stretch

# --- ALGORİTMA 1: TREE CONSTRUCTION (TC) ---
def run_tc_algorithm(nodes, dist_G, start_node_idx=0):
    n = len(nodes)
    print(f"--- TC (Tree Construction) Başlıyor ---")
    
    # SPT (Dijkstra benzeri) Mantığı: Köke olan mesafeyi minimize et
    min_dist = [float('inf')] * n
    in_tree = [False] * n
    min_dist[start_node_idx] = 0
    pq = [(0, start_node_idx, -1)]
    edges = []
    
    while pq:
        d, u, p = heapq.heappop(pq)
        if in_tree[u]: continue
        in_tree[u] = True
        
        if p != -1: edges.append((p, u))
            
        for v in range(n):
            if not in_tree[v]:
                # TC Kriteri: new_dist = current_dist_to_root + edge_weight
                new_dist = d + dist_G[u][v]
                if new_dist < min_dist[v]:
                    min_dist[v] = new_dist
                    heapq.heappush(pq, (new_dist, v, u))
    return edges

# --- ALGORİTMA 2: GVNS ---
def get_components(n, edges_subset):
    adj = [[] for _ in range(n)]
    for u, v in edges_subset:
        adj[u].append(v); adj[v].append(u)
    visited = [False]*n
    comps = []
    for i in range(n):
        if not visited[i]:
            c = []; st = [i]; visited[i]=True
            while st:
                curr = st.pop(); c.append(curr)
                for nxt in adj[curr]:
                    if not visited[nxt]: visited[nxt]=True; st.append(nxt)
            comps.append(c)
    return comps

def gvns_shaking(n, current_edges, k, dist_G):
    new_edges = list(current_edges)
    for _ in range(k):
        if not new_edges: break
        new_edges.pop(random.randint(0, len(new_edges)-1))
    
    # Rastgele tamir
    while len(new_edges) < n - 1:
        comps = get_components(n, new_edges)
        if len(comps) < 2: break
        c1 = comps[random.randint(0, len(comps)-1)]
        c2 = comps[(random.randint(0, len(comps)-1) + 1) % len(comps)]
        new_edges.append((random.choice(c1), random.choice(c2)))
    return new_edges

def gvns_local_search(n, edges, dist_G):
    best_edges = list(edges)
    best_s = calculate_max_stretch(n, best_edges, dist_G)
    improved = True
    iter_limit = 0
    
    # Hızlı olması için limitli local search
    while improved and iter_limit < 15:
        improved = False; iter_limit += 1
        removed = best_edges.pop(random.randint(0, len(best_edges)-1))
        comps = get_components(n, best_edges)
        
        if len(comps) == 2:
            best_link = None
            # Sadece 20 rastgele bağlantı dene (Hız için)
            for _ in range(20):
                u = random.choice(comps[0])
                v = random.choice(comps[1])
                best_edges.append((u,v))
                s = calculate_max_stretch(n, best_edges, dist_G)
                if s < best_s:
                    best_s = s; best_link = (u,v)
                best_edges.pop()
            
            if best_link:
                best_edges.append(best_link); improved = True
            else:
                best_edges.append(removed)
        else:
            best_edges.append(removed)
    return best_edges, best_s

def run_gvns_algorithm(nodes, dist_G):
    print("--- GVNS Başlıyor ---")
    n = len(nodes)
    # Başlangıç: TC çözümü
    current_edges = run_tc_algorithm(nodes, dist_G)
    current_stretch = calculate_max_stretch(n, current_edges, dist_G)
    
    for i in range(GVNS_MAX_ITER):
        k = 1
        while k <= GVNS_K_MAX:
            shaken_edges = gvns_shaking(n, current_edges, k, dist_G)
            refined_edges, refined_stretch = gvns_local_search(n, shaken_edges, dist_G)
            
            if refined_stretch < current_stretch:
                current_stretch = refined_stretch
                current_edges = refined_edges
                k = 1
                print(f"  > GVNS İyileşme: {current_stretch:.4f}")
            else:
                k += 1
    return current_edges, current_stretch

# --- MAIN ---
if __name__ == "__main__":
    nodes = load_and_generate_nodes()
    if not nodes: sys.exit()
    n = len(nodes)
    print(f"Node Sayısı: {n}")
    
    dist_G = np.zeros((n, n))
    for i in range(n):
        for j in range(i+1, n):
            d = calculate_haversine_distance(nodes[i]['lat'], nodes[i]['lon'], nodes[j]['lat'], nodes[j]['lon'])
            if d < 0.001: d = 0.001
            dist_G[i][j] = d; dist_G[j][i] = d

    print("\n" + "="*40)
    print("BENCHMARK ALGORITHMS RUNNING...")
    print("="*40)

    # 1. RUN TC
    t0 = time.time()
    tc_edges = run_tc_algorithm(nodes, dist_G)
    tc_time = time.time() - t0
    tc_stretch = calculate_max_stretch(n, tc_edges, dist_G)
    
    # 2. RUN GVNS
    t1 = time.time()
    gvns_edges, gvns_stretch = run_gvns_algorithm(nodes, dist_G)
    gvns_time = time.time() - t1
    
    print("\n" + "="*50)
    print(f"{'ALGORITHM':<20} | {'MAX STRETCH':<15} | {'TIME (s)':<10}")
    print("-" * 50)
    print(f"{'Tree Construction':<20} | {tc_stretch:<15.4f} | {tc_time:<10.2f}")
    print(f"{'GVNS':<20} | {gvns_stretch:<15.4f} | {gvns_time:<10.2f}")
    print("-" * 50)