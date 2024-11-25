from functions import *

if __name__ == "__main__":
    graph = Graph()
    cwd = os.getcwd()

    workspace = cwd + '/jezdnie_torun'
    shp_points = 'pkty.shp'
    shp_path = 'jezdnie.shp'
    shp_result = "result_points1"
    shp_result_alt = "result_points_alt1"
    project_path = workspace + r'\MyProject3.aprx'

    load_shp_into_graph(workspace, shp_path, graph)
    points = get_start_end_points(workspace, shp_points)
    start, end = find_nearests_nodes(points, graph)
    a = graph.nodes[start]
    b = graph.nodes[end]

    result, used_edges = graph.astar(a, b) #zmiana metody w zależności od najszybsza trasa/najkrótsza

    # Znalezienie alternatywnej trasy kiedy te z pierwszej mają podwojoną długość
    for edge in used_edges:
        edge.length = edge.length * 2

    graph.reset_nodes()
    result_alt, used_edges_alt = graph.astar(a, b) #zmiana metody w zależności od najszybsza trasa/najkrótsza

    # Zapis warstwy do shp
    save_shp(workspace, shp_path, shp_result, project_path, used_edges)
    save_shp(workspace, shp_path, shp_result_alt, project_path, used_edges_alt)