import arcpy
import numpy as np
import os

from classes import *

def load_shp_into_graph(workspace_path: str, shp_path: str, graph: 'Graph'):
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
            
    return current_key_start, current_key_end

# Funkcja zapisująca wynikową ścieżkę do pliku shape
def save_shp(workspace_path: str, shp_to_copy: str, shp_result: str, project_path: str, used_edges: list):
    arcpy.env.workspace = workspace_path
    shp_result_path = os.path.join(workspace_path, f"{shp_result}.shp")

    if arcpy.Exists(shp_result_path):
        arcpy.Delete_management(shp_result_path)
        print("Nadpisano warstwe")
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

    project = arcpy.mp.ArcGISProject(project_path)

    if project:
        map = project.listMaps()[0]
        map.addDataFromPath(shp_result_path)
        print("Dodano")
        project.save()

    print(f"shape saved ok {shp_result}")
