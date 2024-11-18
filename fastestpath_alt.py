import arcpy  
import os     
import heapq 
import numpy as np  

# Funkcja odtwarzająca ścieżkę na podstawie mapy poprzedników
def retrieve_path(prev, a, b):
    path = [b]
    while b != a:
        b = prev[b]  
        path.append(b)
    path.reverse()  
    return path

def generate_4_ids(coords:tuple) -> list[tuple]:
    (x, y) = coords
    return [(x,y), (x+1, y+1), (x+1, y),(x, y+1)]

def node_exists(id_list:list, nodes_dict:dict) -> bool:
    for id in id_list:
        if id not in nodes_dict:
            return False
    return True

def add_ids_and_nodes_to_dict(dict_of_nodes:dict, node_to_add:'Node', ids:list):
    for id in ids:
        dict_of_nodes[id] = node_to_add

# Klasa reprezentująca krawędź w grafie
class Edge:
    def __init__(self, id: int, id_from: tuple, id_to: tuple, id_road: int, length: float, time_cost: float):

        self.id = id  # Unikalny identyfikator krawędzi
        self.id_from = id_from  # Punkt początkowy krawędzi
        self.id_to = id_to  # Punkt końcowy krawędzi 
        self.id_road = id_road  # Identyfikator drogi - droga moze miec kilka krawedzi
        self.length = length  # Długość krawędzi (metry)
        self.time_cost = time_cost  # Czas przejazdu po krawędzi (sekundy)

# Klasa reprezentująca graf z wierzchołkami i krawędziami
class Graph:
    def __init__(self):
        
        self.nodes = dict()  #klucze to identyfikatory węzłów, wartości to obiekty klasy Node

    # Funkcja dodająca krawędź do grafu
    def add_edge(self, edge:Edge):
        ids_from = generate_4_ids(edge.id_from)
        ids_to = generate_4_ids(edge.id_to)

        if not node_exists(ids_from, self.nodes) and not node_exists(ids_to, self.nodes): #oba wierzcholki krawedzi nie znajduja sie w grafie
            starting_node = Node(*edge.id_from)
            ending_node = Node(*edge.id_to)
            #dodanie wierzcholkow do slownika w grafie
            add_ids_and_nodes_to_dict(self.nodes, starting_node, ids_from)
            add_ids_and_nodes_to_dict(self.nodes, ending_node, ids_to)
            
        elif node_exists(ids_from, self.nodes) and not node_exists(ids_to, self.nodes): #tylko wierzcholek poczatkowy jest w grafie
            starting_node = self.nodes[edge.id_from] #wskaznik do wierzcholka
            #utworzenie i dodanie brakujacego koncowego wierzcholka
            ending_node = Node(*edge.id_to)
            add_ids_and_nodes_to_dict(self.nodes, ending_node, ids_to)
            

        elif node_exists(ids_to, self.nodes) and not node_exists(ids_from, self.nodes): #tylko wierzcholek koncowy jest w grafie
            ending_node = self.nodes[edge.id_to]
            #utworzenie i dodanie brakujacego koncowego wierzcholka
            starting_node = Node(*edge.id_from)
            add_ids_and_nodes_to_dict(self.nodes, starting_node, ids_from)
            

        else: #oba wierzchołki są już w grafie
            starting_node = self.nodes[edge.id_from]
            ending_node = self.nodes[edge.id_to]
            
        #doczepienie krawędzi do wierzchołka
        starting_node.add_edge(edge)
        #utworzenie krawedzi w druga stronę
        backwards_edge = Edge(edge.id, edge.id_to, edge.id_from, edge.id_road, edge.length, edge.time_cost)
        ending_node.add_edge(backwards_edge)


    def reset_nodes(self):
        for node in self.nodes.values():
            node.h = None
            node.g = float('inf')
            node.f = float('inf')

    # Algorytm A* do wyszukiwania najszybszej trasy
    def astar_fastest(self, a, b):
        queue = []  
        heapq.heappush(queue, (0, a))  # Inicjalizacja z wartością początkową `a`
        a.g = 0  # domyslnie 0
        a.f = a.heuristic_time(b)  # Heurystyka czasu z a do celu b
        visited = set()  # Zbiór odwiedzonych węzłów
        prev = {}  # Słownik poprzedników do odtworzenia ścieżki
        prev[a] = None
        used_edges = []

        while queue:
            _, u = heapq.heappop(queue)  # Pobieramy węzeł z najniższym `f=g+h(przyblizony koszt dotarcia do wezla poczartkowego)`z kolejki

            # spr czy u nie jest w zb zamknietym
            if u in visited:
                continue

            if u.x == b.x and u.y == b.y:
                path = retrieve_path(prev, a, b)
                used_edges = self.get_used_edges(path)
                return path, used_edges

            visited.add(u) 
            for edge in u.edges_out:
                neighbor = self.nodes.get(edge.id_to)
                if neighbor in visited:
                    continue

                # Obliczamy nowy koszt dotarcia do sąsiada (czas przejazdu + 5 sekund na węzeł)
                new_neighbor_g = u.g + edge.time_cost + 5

                if new_neighbor_g < neighbor.g:
                    # Aktualizujemy koszt g i f sąsiada, jeśli znaleźliśmy lepszą trasę
                    prev[neighbor] = u
                    neighbor.g = new_neighbor_g
                    neighbor.f = neighbor.g + neighbor.heuristic_time(b)
                    heapq.heappush(queue, (neighbor.f, neighbor))

        return None, used_edges  # Zwraca pusty wynik, jeśli brak ścieżki

    # Funkcja do uzyskania krawędzi użytych w ścieżce
    def get_used_edges(self, path):
        edges = []
        for i in range(len(path) - 1):
            for edge in path[i].edges_out:
                if edge.id_to == tuple(map(int, path[i + 1].id.split(','))):
                    edges.append(edge)
                    break
        return edges

# Klasa reprezentująca wierzchołek grafu
class Node:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.id = f"{self.x},{self.y}"  # Identyfikator współrzędnych
        self.edges_out = []  # Lista krawędzi wychodzących z wierzchołka
        self.h = None  # Wartość heurystyki 
        self.g = float('inf')  # Koszt dotarcia do węzła
        self.f = float('inf')  # Wartość heurystyki łącznej A* g+h

    def heuristic_time(self, goal):
        max_speed = 90 / 3.6 
        self.h = np.sqrt((goal.x - self.x) ** 2 + (goal.y - self.y) ** 2) / max_speed
        return self.h

    def add_edge(self, edge: Edge):
        self.edges_out.append(edge)

# Funkcja ładująca dane z pliku shp do grafu
def load_shp_into_graph(workspace_path: str, shp_path: str, graph: Graph):
    arcpy.env.workspace = workspace_path
    speed_dict = {
        'gminna': 50 / 3.6,
        'powiatowa': 60 / 3.6,
        'wojewódzka': 90 / 3.6,
        'wewnętrzna': 15 / 3.6
    }
    with arcpy.da.SearchCursor(shp_path, ["FID", "SHAPE@", "KAT_ZARZAD"]) as cursor:
        for row in cursor:
            id = int(row[0])
            polyline = row[1]
            length = polyline.getLength('PLANAR', 'METERS')  # Długość krawędzi w metrach
            start_coords = (round(polyline.firstPoint.X), round(polyline.firstPoint.Y))
            end_coords = (round(polyline.lastPoint.X), round(polyline.lastPoint.Y))
            speed = speed_dict.get(row[2], 50 / 3.6) 
            time_cost = length / speed 
            edge = Edge(id, start_coords, end_coords, id, length, time_cost)
            graph.add_edge(edge)

def calculate_euclidean_distance(p1, p2):
    return np.sqrt((p2[0] - p1[0])**2 + (p2[1]-p1[1])**2)

def get_start_end_points(workspace_path: str, shp_path: str) -> list[tuple]: #first point is starting second is ending
    arcpy.env.workspace = workspace_path
    with arcpy.da.SearchCursor(shp_path, ["FID", "SHAPE@"]) as cursor:
        points = []
        for row in cursor:
            point = row[1].firstPoint
            coords = (point.X, point.Y)
            points.append(coords)
    return points

def find_nearests_nodes(points:list[tuple], graph:Graph): #returns ids in dict 
    start = points[0]
    end = points[1]
    print(start, end)
    current_key_start = None
    current_key_end = None
    current_shortest_dist_start = float('inf')
    current_shortest_dist_end = float('inf')
    
    for key in graph.nodes:
        start_distance = calculate_euclidean_distance(start, key)
        end_distance = calculate_euclidean_distance(end, key)

        if start_distance < current_shortest_dist_start:
            current_key_start = key
            current_shortest_dist_start = start_distance

        if end_distance < current_shortest_dist_end:
            current_key_end = key
            current_shortest_dist_end = end_distance
            
    print(current_key_start, current_key_end)
    return current_key_start, current_key_end

# Funkcja zapisująca wynikową ścieżkę do pliku shape
def save_shp(workspace_path: str, shp_to_copy: str, shp_result: str, used_edges: list):
    arcpy.env.workspace = workspace_path
    arcpy.CreateFeatureclass_management(
        out_path=workspace_path, out_name=shp_result,
        geometry_type="POLYLINE", template=shp_to_copy,
        spatial_reference=arcpy.Describe(shp_to_copy).spatialReference
    )

    used_edges_id = [edge.id for edge in used_edges]

    with arcpy.da.SearchCursor(shp_to_copy, ["FID", "SHAPE@"]) as search_cursor, \
         arcpy.da.InsertCursor(shp_result, ["FID", "SHAPE@"]) as insert_cursor:
        for row in search_cursor:
            if int(row[0]) in used_edges_id:
                insert_cursor.insertRow(row)

    print(f"shape saved ok {shp_result}")

if __name__ == "__main__":
    graph = Graph()
    cwd = os.getcwd()
    workspace = cwd + '/jezdnie_torun'
    #workspace = R"C:\Users\Acer\Desktop\SEMESTR_5\PAG2\PAG2-master\data"
    shp_points = 'pkty.shp'
    shp_path = 'jezdnie.shp'
    shp_result = "result_from_points"

    load_shp_into_graph(workspace, shp_path, graph)
    points = get_start_end_points(workspace, shp_points)
    start, end = find_nearests_nodes(points, graph)
    a = graph.nodes[start]
    b = graph.nodes[end]

    result, used_edges = graph.astar_fastest(a, b)

    #graph.reset_nodes()
    # Znalezienie alternatywnej trasy kiedy te z pierwszej mają podwojoną długość
    for edge in used_edges:
        edge.time_cost = edge.time_cost * 2

    #result_new, used_edges_new = graph.astar_fastest(a, b)

    # Zapis warstwy do shp
    save_shp(workspace, shp_path, shp_result, used_edges)
