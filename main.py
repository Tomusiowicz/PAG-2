import arcpy
import os

class Edge:
    def __init__(self, id:int, id_from:tuple, id_to:tuple, id_road:int, length:float):
        self.id = id
        self.id_from = id_from
        self.id_to = id_to
        self.id_road = id_road
        self.length = length

class Graph:
    def __init__(self):
        self.nodes = dict()
    
    def add_edge(self, edge:Edge):
        if not edge.id_from in self.nodes and not edge.id_to in self.nodes: #oba wierzcholki krawedzi nie znajduja sie w grafie
            starting_node = Node(*edge.id_from)
            ending_node = Node(*edge.id_to)
            #dodanie wierzcholkow do slownika w grafie
            self.nodes[edge.id_from] = starting_node
            self.nodes[edge.id_to] = ending_node

        elif edge.id_from in self.nodes and not edge.id_to in self.nodes: #tylko wierzcholek poczatkowy jest w grafie
            starting_node = self.nodes[edge.id_from] #wskaznik do wierzcholka
            #utworzenie i dodanie brakujacego koncowego wierzcholka
            ending_node = Node(*edge.id_to)
            self.nodes[edge.id_to] = ending_node

        elif edge.id_to in self.nodes and not edge.id_from in self.nodes: #tylko wierzcholek koncowy jest w grafie
            ending_node = self.nodes[edge.id_to]
            starting_node = Node(*edge.id_from)
            self.nodes[edge.id_from] = starting_node

        else: #oba wierzchołki są już w grafie
            starting_node = self.nodes[edge.id_from]
            ending_node = self.nodes[edge.id_to]

        #doczepienie krawędzi do wierzchołka
        starting_node.add_edge(edge)
        #utworzenie krawedzi w druga stronę
        backwards_edge = Edge(edge.id, edge.id_to, edge.id_from, edge.id_road, edge.length)
        ending_node.add_edge(backwards_edge)

class Node:
    def __init__(self, x:int, y:int):
        self.x = x
        self.y = y
        self.id = str(self.x) + ',' + str(self.y)
        self.edges_out = []

    def add_edge(self, edge:Edge):
        self.edges_out.append(edge)

def load_shp_into_graph(workspace_path:str, shp_path:str, graph:Graph):
    arcpy.env.workspace = workspace_path
    with arcpy.da.SearchCursor(shp_path, ["FID", "SHAPE@"]) as cursor:
        for row in cursor:
            id = int(row[0])
            polyline = row[1]
            length = polyline.getLength('PLANAR', 'METERS')
            start_coords = (round(polyline.firstPoint.X), round(polyline.firstPoint.Y))
            end_coords = (round(polyline.lastPoint.X), round(polyline.lastPoint.Y))
            edge = Edge(id , start_coords, end_coords, id, length)
            graph.add_edge(edge)
    
def print_nodes_edges(graph:Graph):
    for node in graph.nodes.values():
        print(f"Node: {node.id}")
        for edge in node.edges_out:
            print(f"Edge: {edge.id}, from:{edge.id_from}, to {edge.id_to}, len: {edge.length}")

def write_nodes_to_file(graph: Graph):
    f = open("nodes.txt", "x")
    for node in graph.nodes.values():
        f.write(f"Node: {node.id} \n")
        for edge in node.edges_out:
            f.write(f"Edge: {edge.id}, from:{edge.id_from}, to {edge.id_to}, len: {edge.length} \n")
    f.close()

if __name__ == "__main__":
    graph = Graph()
    cwd = os.getcwd()
    workspace = cwd + '\jezdnie_torun'
    shp_path = "jezdnie_torun\L4_1_BDOT10k__OT_SKJZ_L.shp"
    load_shp_into_graph(workspace, shp_path, graph)
    #write_nodes_to_file(graph)