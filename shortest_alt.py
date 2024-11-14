import arcpy
import os
import heapq
import numpy as np

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

class Edge:
    def __init__(self, id: int, id_from: tuple, id_to: tuple, id_road: int, length: float):
        self.id = id
        self.id_from = id_from
        self.id_to = id_to
        self.id_road = id_road
        self.length = length

class Graph:
    def __init__(self):
        self.nodes = dict()

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
        backwards_edge = Edge(edge.id, edge.id_to, edge.id_from, edge.id_road, edge.length)
        ending_node.add_edge(backwards_edge)

    def reset_nodes(self):
        for node in self.nodes.values():
            node.h = None
            node.g = float('inf')
            node.f = float('inf')
    def astar(self, a, b):

        # 1. Pusta otwarta lista ze startowym węzłem
        queue = []
        heapq.heappush(queue, (0, a))

        a.g = 0
        a.f = a.heuristic(b)

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
                    neigbour.f = neigbour.g + neigbour.heuristic(b)

                    heapq.heappush(queue, (neigbour.f, neigbour))

        return None, used_edges

    def get_used_edges(self, path):
        edges = []
        for i in range(len(path) - 1):
            for edge in path[i].edges_out:
                if edge.id_to == tuple(map(int, path[i + 1].id.split(','))):
                    edges.append(edge)
                    break

        return edges

class Node:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.id = str(self.x) + ',' + str(self.y)
        self.edges_out = []
        self.h = None
        self.g = float('inf')
        self.f = float('inf')

    def heuristic(self, goal):
        self.h = np.sqrt((goal.x - self.x) ** 2 + (goal.y - self.y) ** 2)  # eukidlesowa długość
        return self.h

    def add_edge(self, edge: Edge):
        self.edges_out.append(edge)

def load_shp_into_graph(workspace_path: str, shp_path: str, graph: Graph):
    arcpy.env.workspace = workspace_path
    with arcpy.da.SearchCursor(shp_path, ["FID", "SHAPE@"]) as cursor:
        for row in cursor:
            id = int(row[0])
            polyline = row[1]
            length = polyline.getLength('PLANAR', 'METERS')
            start_coords = (round(polyline.firstPoint.X), round(polyline.firstPoint.Y))
            end_coords = (round(polyline.lastPoint.X), round(polyline.lastPoint.Y))
            edge = Edge(id, start_coords, end_coords, id, length)
            graph.add_edge(edge)

def save_shp(workspace_path: str, shp_to_copy: str, shp_result: str,  used_edges: list):
    arcpy.env.workspace = workspace_path
    arcpy.CreateFeatureclass_management(out_path=workspace_path, out_name=shp_result, geometry_type="POLYLINE", template=shp_to_copy, spatial_reference=arcpy.Describe(shp_to_copy).spatialReference)

    used_edges_id = []
    for edge in used_edges:
        used_edges_id.append(edge.id)

    with arcpy.da.SearchCursor(shp_to_copy, ["FID", "SHAPE@"]) as search_cursor, \
        arcpy.da.InsertCursor(shp_result, ["FID", "SHAPE@"]) as insert_cursor:
        for row in search_cursor:
            edge_id = int(row[0])
            if edge_id in used_edges_id:
                insert_cursor.insertRow(row)

    print(f"Warstwa shp zapisana")

def print_nodes_edges(graph: Graph):
    for node in graph.nodes.values():
        print(f"Node: {node.id}")
        for edge in node.edges_out:
            print(f"Edge: {edge.id}, from:{edge.id_from}, to {edge.id_to}, len: {edge.length}")

if __name__ == "__main__":
    graph = Graph()
    cwd = os.getcwd()
    workspace = R"C:\Users\Acer\Desktop\SEMESTR_5\PAG2\PAG2-master\data"
    shp_path = "jezdnie.shp"
    shp_result = "result_shortest_new2"

    load_shp_into_graph(workspace, shp_path, graph)

    a = list(graph.nodes.values())[0]
    b = list(graph.nodes.values())[10]

    result, used_edges = graph.astar(a, b)

    graph.reset_nodes()

    # Znalezienie alternatywnej trasy kiedy te z pierwszej mają podwojoną długość
    for edge in used_edges:
       edge.length = edge.length * 2

    result_new, used_edges_new = graph.astar(a, b)

    # for edge in used_edges_new:
    #     print(edge.length)


#    for edge in used_edges:
#        print(edge.id)
#    total_cost = 0
#    for node in result:
#       print(node.id)
#       total_cost += node.g

    # zapis warstwy do pliku shp
    # save_shp(workspace, shp_path, shp_result, used_edges_new)
