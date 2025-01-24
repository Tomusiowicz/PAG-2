from neo4j import GraphDatabase, RoutingControl

def load_nodes_into_neo4j(unique_nodes):
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        for node in unique_nodes:
            node_id = str((node.x, node.y))
            records, summary, keys = driver.execute_query(
            "CREATE (n:Node {coords: $coords})",
            {"coords": nodeid},
            routing=RoutingControl.WRITE,
            database_="neo4j",
            )

def connect_nodes_in_neo4j(graph, unique_nodes):
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        for node in unique_nodes:
            for edge in node.edges_out:
                neighbour = graph.nodes[node_exists(generate_4_ids(edge.id_to), graph.nodes)]
                neighbour_id = str((neighbour.x, neighbour.y))
                node_id = str((node.x, node.y))
                try:
                    records, summary, keys = driver.execute_query(
                        """
                        MATCH (n1:Node {coords: $coord1}), (n2:Node {coords: $coord2})
                        CREATE (n1)-[:CONNECTED {cost: $cost}]->(n2);
                        """,
                        {"coord1": node_id, "coord2": neighbour_id, "cost": edge.timecost},
                        routing=RoutingControl.WRITE,
                        database_="neo4j",
                        )
                except Exception as e:
                    print(f"Failed to create relationship: {e}")
