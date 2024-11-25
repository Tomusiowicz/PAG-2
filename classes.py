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


class Edge:
    def __init__(self, id: int, id_from: tuple, id_to: tuple, id_road: int, length: float, time_cost: float):

        self.id = id  # Unikalny identyfikator krawędzi
        self.id_from = id_from  # Punkt początkowy krawędzi
        self.id_to = id_to  # Punkt końcowy krawędzi
        self.id_road = id_road  # Identyfikator drogi - droga moze miec kilka krawedzi
        self.length = length  # Długość krawędzi (metry)
        self.time_cost = time_cost  # Czas przejazdu po krawędzi (sekundy)


class Graph:
    def __init__(self):

        self.nodes = dict()  # klucze to identyfikatory węzłów, wartości to obiekty klasy Node

    # Funkcja dodająca krawędź do grafu
    def add_edge(self, edge: Edge):
        ids_from = generate_4_ids(edge.id_from)
        ids_to = generate_4_ids(edge.id_to)

        if not node_exists(ids_from, self.nodes) and not node_exists(ids_to,
                                                                     self.nodes):  # oba wierzcholki krawedzi nie znajduja sie w grafie
            starting_node = Node(*edge.id_from)
            ending_node = Node(*edge.id_to)
            # dodanie wierzcholkow do slownika w grafie
            add_ids_and_nodes_to_dict(self.nodes, starting_node, ids_from)
            add_ids_and_nodes_to_dict(self.nodes, ending_node, ids_to)

        elif node_exists(ids_from, self.nodes) and not node_exists(ids_to,
                                                                   self.nodes):  # tylko wierzcholek poczatkowy jest w grafie
            starting_node = self.nodes[edge.id_from]  # wskaznik do wierzcholka
            # utworzenie i dodanie brakujacego koncowego wierzcholka
            ending_node = Node(*edge.id_to)
            add_ids_and_nodes_to_dict(self.nodes, ending_node, ids_to)


        elif node_exists(ids_to, self.nodes) and not node_exists(ids_from,
                                                                 self.nodes):  # tylko wierzcholek koncowy jest w grafie
            ending_node = self.nodes[edge.id_to]
            # utworzenie i dodanie brakujacego koncowego wierzcholka
            starting_node = Node(*edge.id_from)
            add_ids_and_nodes_to_dict(self.nodes, starting_node, ids_from)


        else:  # oba wierzchołki są już w grafie
            starting_node = self.nodes[edge.id_from]
            ending_node = self.nodes[edge.id_to]

        # doczepienie krawędzi do wierzchołka
        starting_node.add_edge(edge)
        # utworzenie krawedzi w druga stronę
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

    def astar(self, a, b):

        # 1. Pusta otwarta lista ze startowym węzłem
        queue = []
        heapq.heappush(queue, (0, a))

        a.g = 0
        a.f = a.heuristic_length(b)

        # 2. Pusta zamknięta lista
        visited = set()
        prev = {} # poprzednik
        prev[a] = None
        used_edges = []

        # 3. Dopóki otwarta lista nie jest pusta:
        while queue:
        # - wybieramy węzeł z najmniejszą wartością f z otwartej listy i zamiana go na bieżący węzeł
            _, u = heapq.heappop(queue)
        #spr czy u nie jest w zb zamknietym

            if u in visited:
                continue

        # - jeżeli bieżący węzeł jest końcowym zwracamy go i odtwarzamy ścieżke
            if u.x == b.x and u.y == b.y:
                path = retrieve_path(prev, a, b)

                used_edges = self.get_used_edges(path)
                return path, used_edges

            # - przesunięcie bieżacego węzła do zamkniętej listy
            visited.add(u)

            # - dla każdego sąsiada bieżącego węzła:
            for edge in u.edges_out:
                neigbour = self.nodes.get(edge.id_to)

            # - jeżeli sąsiedni węzeł jest w zamkniętej liście lub jest ścianą pomiń go
                if neigbour in visited:
                    continue
            # - policz wartość g(koszt od początkowego węzła do bieżącego + koszt od bieżacego do sąsiada)

                new_neigbour_g = u.g + edge.length

            # - jeżeli nowa wartość g jest mniejsza od obecnego g aktualizuj wartości g i f sąsiada i aktualizuj go jako bieżący węzeł
                if new_neigbour_g < neigbour.g:
                    # print(neigbour_to_g, neigbour.g)
                    prev[neigbour] = u
                    neigbour.g = new_neigbour_g
                    neigbour.f = neigbour.g + neigbour.heuristic_length(b)

                    heapq.heappush(queue, (neigbour.f, neigbour))

        return None, used_edges

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

    def heuristic_length(self, goal):
        self.h = np.sqrt((goal.x - self.x) ** 2 + (goal.y - self.y) ** 2)  # eukidlesowa długość
        return self.h

    def add_edge(self, edge: Edge):
        self.edges_out.append(edge)
