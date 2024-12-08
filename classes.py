import heapq
import numpy as np

def node_exists(id_list:list, nodes_dict:dict) -> bool:
    for id in id_list:
        if id not in nodes_dict:
            return False
    return True

def add_ids_and_nodes_to_dict(dict_of_nodes:dict, node_to_add:'Node', ids:list):
    for id in ids:
        dict_of_nodes[id] = node_to_add

def generate_4_ids(coords:tuple) -> list[tuple]:
    (x, y) = coords
    return [(x,y), (x+1, y+1), (x+1, y),(x, y+1)]

def retrieve_path(prev, a, b):
    path = [b]
    while b != a:
        b = prev[b]  
        path.append(b)
    path.reverse()  
    return path

#Klasa reprezentująca krawędź grafu
class Edge:
    def __init__(self, id: int, id_from: tuple, id_to: tuple, id_road: int, length: float, time_cost: float, oneway: int):
        self.id = id  
        self.id_from = id_from  
        self.id_to = id_to 
        self.id_road = id_road  
        self.length = length  
        self.time_cost = time_cost  
        self.oneway = oneway 

#Klasa reprezentująca graf
class Graph:
    def __init__(self):
        self.nodes = dict()  # klucze to identyfikatory węzłów, wartości to obiekty klasy Node

    # Funkcja dodająca krawędź do grafu
    def add_edge(self, edge: Edge):
        ids_from = generate_4_ids(edge.id_from)
        ids_to = generate_4_ids(edge.id_to)

        if not node_exists(ids_from, self.nodes) and not node_exists(ids_to, self.nodes):  # oba wierzcholki krawedzi nie znajduja sie w grafie
            starting_node = Node(*edge.id_from)
            ending_node = Node(*edge.id_to)

            add_ids_and_nodes_to_dict(self.nodes, starting_node, ids_from)
            add_ids_and_nodes_to_dict(self.nodes, ending_node, ids_to)

        elif node_exists(ids_from, self.nodes) and not node_exists(ids_to, self.nodes):  # tylko wierzcholek poczatkowy jest w grafie
            starting_node = self.nodes[edge.id_from]  
            ending_node = Node(*edge.id_to)
            add_ids_and_nodes_to_dict(self.nodes, ending_node, ids_to)


        elif node_exists(ids_to, self.nodes) and not node_exists(ids_from, self.nodes):  # tylko wierzcholek koncowy jest w grafie
            ending_node = self.nodes[edge.id_to]
            starting_node = Node(*edge.id_from)
            add_ids_and_nodes_to_dict(self.nodes, starting_node, ids_from)


        else:  # oba wierzchołki są już w grafie
            starting_node = self.nodes[edge.id_from]
            ending_node = self.nodes[edge.id_to]

       # Uwzględniamy kierunkowść
        if edge.oneway == 0:  # Dwukierunkowa
            starting_node.add_edge(edge)  # from -> to
            backwards_edge = Edge(edge.id, edge.id_to, edge.id_from, edge.id_road, edge.length, edge.time_cost, oneway=0)
            ending_node.add_edge(backwards_edge)  # to -> from
        elif edge.oneway == 1:  # Jednokierunkowa zgodnie z geometria
            starting_node.add_edge(edge)
        elif edge.oneway == 2:  # Jednokierunkowa w przeciwnym kierunku
            backwards_edge = Edge(edge.id, edge.id_to, edge.id_from, edge.id_road, edge.length, edge.time_cost, oneway=2)
            ending_node.add_edge(backwards_edge)


    def reset_nodes(self):
        for node in self.nodes.values():
            node.h = None
            node.g = float('inf')
            node.f = float('inf')

    # Algorytm A* do wyszukiwania najszybszej trasy
    def astar_fastest(self, a, b):
        queue = []
        heapq.heappush(queue, (0, a))  
        a.g = 0  
        a.f = a.heuristic_time(b)  
        visited = set()  
        prev = {}  
        prev[a] = None
        used_edges = []

        while queue:
            _, u = heapq.heappop(queue)  # Pobieramy węzeł z najniższym `f=g+h(przyblizony koszt dotarcia do wezla poczartkowego)`z kolejki
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

                new_neighbor_g = u.g + edge.time_cost

                if new_neighbor_g < neighbor.g:
                    # Aktualizujemy koszt g i f sąsiada, jeśli znaleźliśmy lepszą trasę
                    prev[neighbor] = u
                    neighbor.g = new_neighbor_g
                    neighbor.f = neighbor.g + neighbor.heuristic_time(b)
                    heapq.heappush(queue, (neighbor.f, neighbor))

        return None, used_edges  

    def astar(self, a, b):

        queue = []
        heapq.heappush(queue, (0, a))

        a.g = 0
        a.f = a.heuristic_length(b)

        visited = set()
        prev = {} 
        prev[a] = None
        used_edges = []

        while queue:
            _, u = heapq.heappop(queue)
            if u in visited:
                continue

            if u.x == b.x and u.y == b.y:
                path = retrieve_path(prev, a, b)
                used_edges = self.get_used_edges(path)
                return path, used_edges
            visited.add(u)

            # - dla każdego sąsiada bieżącego węzła:
            for edge in u.edges_out:
                neigbour = self.nodes.get(edge.id_to)

                if neigbour in visited:
                    continue

                new_neigbour_g = u.g + edge.length

                if new_neigbour_g < neigbour.g:
                    prev[neigbour] = u
                    neigbour.g = new_neigbour_g
                    neigbour.f = neigbour.g + neigbour.heuristic_length(b)
                    heapq.heappush(queue, (neigbour.f, neigbour))

        return None, used_edges
    
    def dijkstra(self, a, b):

        queue = []  
        heapq.heappush(queue, (0, a)) 
        distances = {node: float('inf') for node in self.nodes.values()}  
        distances[a] = 0  
        prev = {node: None for node in self.nodes.values()}  

        while queue:
            current_distance, current_node = heapq.heappop(queue)
            if current_node == b:
                break

            for edge in current_node.edges_out:
                neighbor = self.nodes[edge.id_to]
                distance = current_distance + edge.length  

                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    prev[neighbor] = current_node
                    heapq.heappush(queue, (distance, neighbor))

        path = []
        used_edges = []
        total_distance = distances[b]
        current = b
        while current is not None:
            path.append(current)
            prev_node = prev[current]
            if prev_node:
                for edge in prev_node.edges_out:
                    if edge.id_to == tuple(map(int, current.id.split(','))):
                        used_edges.append(edge)
                        break
            current = prev_node
        path.reverse()  

        return None, path, used_edges, total_distance

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
        self.id = f"{self.x},{self.y}"  
        self.edges_out = []  
        self.h = None  
        self.g = float('inf')  
        self.f = float('inf')  

    def heuristic_time(self, goal):
        max_speed = 100 / 3.6
        self.h = np.sqrt((goal.x - self.x) ** 2 + (goal.y - self.y) ** 2) / max_speed
        return self.h

    def heuristic_length(self, goal):
        self.h = np.sqrt((goal.x - self.x) ** 2 + (goal.y - self.y) ** 2)  
        return self.h

    def add_edge(self, edge: Edge):
        self.edges_out.append(edge)
