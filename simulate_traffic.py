# file: simulate_traffic.py

import json
import random
import csv
import os
import networkx as nx
from networkx.readwrite import json_graph

def load_graph(filename: str = "city_grid.json") -> nx.Graph:
    with open(filename) as f:
        data = json.load(f)
    return json_graph.node_link_graph(data)

def format_path(path: list[str]) -> str:
    return "-".join(path)

def append_to_csv(filename: str, rows: list[dict]):
    is_new = not os.path.exists(filename)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        if is_new:
            writer.writeheader()
        writer.writerows(rows)

def random_vehicle_type() -> tuple[str, int]:
    vehicle_types = [
        ("4-wheeler", 70),
        ("2-wheeler", 15),
        ("6-wheeler", 5),
        ("3-wheeler", 5),
        ("8-wheeler", 3),
        ("10-wheeler", 2)
    ]
    types, weights = zip(*vehicle_types)
    choice = random.choices(types, weights=weights, k=1)[0]
    wheels = int(choice.split("-")[0])
    return choice, wheels

def traffic_multiplier(hour: int, is_weekend: bool) -> float:
    if is_weekend:
        if 14 <= hour <= 18:
            return 1.5
        return 0.6
    if 7 <= hour <= 9:
        return 2.0
    if 17 <= hour <= 20:
        return 2.5
    if 12 <= hour <= 14:
        return 0.7
    if 0 <= hour <= 5:
        return 0.3
    return 0.5

def simulate_count(hour: int, max_val: int, is_weekend: bool, zone: str = "residential") -> int:
    base = random.randint(0, max_val)
    multiplier = traffic_multiplier(hour, is_weekend)

    # Zone impact
    zone_factor = {
        "residential": 1.0,
        "commercial": 1.2,
        "industrial": 0.8,
        "park": 0.5
    }.get(zone, 1.0)

    scaled = int(base * multiplier * zone_factor)
    return max(scaled, 0)


def preferred_destination(start_zone: str, zones: dict[str, str], hour: int, is_weekend: bool) -> list[str]:
    if is_weekend:
        preferences = ["park", "commercial"]
    elif 7 <= hour <= 9:
        if start_zone == "residential":
            preferences = ["commercial", "industrial"]
        else:
            preferences = ["residential"]
    elif 17 <= hour <= 20:
        if start_zone in ("commercial", "industrial"):
            preferences = ["residential"]
        else:
            preferences = ["commercial"]
    else:
        preferences = ["commercial", "residential", "park"]

    return [n for n, z in zones.items() if z in preferences and n != start_zone]

def path_congestion_penalty(G, path: list[str]) -> float:
    penalty = 0
    for u, v in zip(path[:-1], path[1:]):
        edge_data = G.get_edge_data(u, v, default={})
        if edge_data:
            usage_factor = random.uniform(0.7, 1.3)
            if edge_data.get("capacity", 300) < 300:
                penalty += 0.5 * usage_factor
            else:
                penalty += 0.2 * usage_factor
            penalty += edge_data.get("delay", 0)
    return penalty

def main():
    print("\n🚦 Realistic Traffic Simulation with Congestion")
    G = load_graph()
    intersections = list(G.nodes())
    residential_nodes = [n for n, d in G.nodes(data=True) if d.get("zone") == "residential"]
    zones = {node: G.nodes[node].get("zone", "residential") for node in intersections}

    hour = int(input("🕐 Enter simulation hour (0 → 23): "))
    day = int(input("📅 Enter simulation day (1 → 15): "))
    is_weekend = (day % 7) in (6, 0)
    count = int(input("📍 Number of intersections to simulate: "))

    vehicle_log = []
    pedestrian_log = []
    id_counter = 1

    for _ in range(count):
        start = random.choice(residential_nodes if random.random() < 0.8 else intersections)
        start_zone = zones[start]

        veh_count = simulate_count(hour, 10, is_weekend, start_zone)
        ped_count = simulate_count(hour, 6, is_weekend, start_zone)

        for _ in range(veh_count):
            possible_dests = [n for n, z in zones.items() if n != start and z in ("commercial", "industrial")]
            if not possible_dests:
                continue
            dest = random.choice(possible_dests)
            try:
                path = nx.shortest_path(G, start, dest, weight="weight")
                congestion_delay = path_congestion_penalty(G, path)
            except nx.NetworkXNoPath:
                continue
            veh_type, weight_val = random_vehicle_type()
            vehicle_log.append({
                "id": f"veh_{id_counter:04d}",
                "type": veh_type,
                "weight": weight_val,
                "from": start,
                "to": dest,
                "path": format_path(path),
                "hour": hour,
                "day": day,
                "congestion_penalty": round(congestion_delay, 2)
            })
            id_counter += 1

        for _ in range(ped_count):
            nearby = [n for n in intersections if n != start and nx.has_path(G, start, n) and nx.shortest_path_length(G, start, n) <= 3]
            dest = random.choice(nearby) if nearby else random.choice(intersections)
            try:
                path = nx.shortest_path(G, start, dest, weight="weight")
                congestion_delay = path_congestion_penalty(G, path)
            except nx.NetworkXNoPath:
                continue
            pedestrian_log.append({
                "id": f"ped_{id_counter:04d}",
                "type": "pedestrian",
                "weight": 0,
                "from": start,
                "to": dest,
                "path": format_path(path),
                "hour": hour,
                "day": day,
                "congestion_penalty": round(congestion_delay, 2)
            })
            id_counter += 1

    if vehicle_log:
        append_to_csv("vehicles_log.csv", vehicle_log)
    if pedestrian_log:
        append_to_csv("pedestrians_log.csv", pedestrian_log)

    print("\n✅ Simulation complete!")

def path_congestion_penalty(G, path: list[str]) -> float:
    penalty = 0
    for u, v in zip(path[:-1], path[1:]):
        edge_data = G.get_edge_data(u, v, default={})
        if edge_data:
            usage_factor = random.uniform(0.7, 1.3)
            if edge_data.get("capacity", 300) < 300:
                penalty += 0.5 * usage_factor
            else:
                penalty += 0.2 * usage_factor
            penalty += edge_data.get("delay", 0)
        if G.nodes[u].get("traffic_light", False):
            penalty += G.nodes[u].get("traffic_light_delay", 0)
    return penalty

if __name__ == "__main__":
    main()