# Packaging all updated files into a final project structure

# --- full_pipeline_cached.py (FIXED for sampling bug) ---

import os
import json
import random
import csv
import networkx as nx
from tqdm import tqdm
from city_grid_streetlights import generate_grid_with_correct_streetlights, export_graph, export_streetlights
from analyze_city import analyze, save_report

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
    zone_factor = {
        "residential": 1.0,
        "commercial": 1.2,
        "industrial": 0.8,
        "park": 0.5
    }.get(zone, 1.0)
    scaled = int(base * multiplier * zone_factor)
    return max(scaled, 0)

def main():
    print("\n--- Full City Simulation Pipeline (Realistic Cached Paths Version) ---")

    rows = int(input("Enter number of rows: ").strip())
    cols = int(input("Enter number of columns: ").strip())
    intersections_per_hour = int(input("Enter number of intersections to simulate per hour: ").strip())
    days_to_simulate = int(input("Enter number of days to simulate: ").strip())

    print("\nGenerating city grid...")
    G, pos, streetlights_dict = generate_grid_with_correct_streetlights(rows, cols)
    export_graph(G, "city_grid.json")
    export_streetlights(G, pos, streetlights_dict, "streetlights.json")

    with open("streetlights.json", "r") as f:
        streetlights = json.load(f)

    print("\nAnalyzing city...")
    summary = analyze(G, streetlights)
    save_report(summary, "city_analysis.json")

    vehicles_suffix = input("Enter suffix for vehicles_log file (example: 1): ").strip()
    pedestrians_suffix = input("Enter suffix for pedestrians_log file (example: 1): ").strip()

    vehicles_log_file = f"vehicles_log_{vehicles_suffix}.csv"
    pedestrians_log_file = f"pedestrians_log_{pedestrians_suffix}.csv"

    intersections = list(G.nodes())
    residential_nodes = [n for n, d in G.nodes(data=True) if d.get("zone") == "residential"]
    zones = {node: G.nodes[node].get("zone", "residential") for node in intersections}

    print("\nPrecomputing all shortest paths...")
    precomputed_paths = dict(nx.all_pairs_dijkstra_path(G, weight='weight'))

    id_counter = 1
    live_congestion = {}

    def update_live_congestion(path: list[str]):
        for u, v in zip(path[:-1], path[1:]):
            live_congestion[(u, v)] = live_congestion.get((u, v), 0) + 1

    def get_path_congestion_penalty(path: list[str]) -> float:
        penalty = 0
        for u, v in zip(path[:-1], path[1:]):
            edge_data = G.get_edge_data(u, v, default={})
            usage = live_congestion.get((u, v), 0)
            if edge_data:
                base = 0.2 if edge_data.get("capacity", 300) >= 300 else 0.5
                dynamic_penalty = base * (1 + usage * 0.05)
                penalty += dynamic_penalty
                penalty += edge_data.get("delay", 0)
            if G.nodes[u].get("traffic_light", False):
                penalty += G.nodes[u].get("traffic_light_delay", 0)
        return penalty

    print("\nStarting full simulation...")
    for day in tqdm(range(1, days_to_simulate + 1), desc="Days"):
        is_weekend = (day % 7) in (6, 0)
        live_congestion.clear()

        for hour in tqdm(range(0, 24), leave=False, desc=f"Hours for Day {day}"):
            vehicle_log = []
            pedestrian_log = []

            if random.random() < 0.8:
                population = residential_nodes if len(residential_nodes) >= intersections_per_hour else residential_nodes + intersections
            else:
                population = intersections
            population = list(set(population))

            for start in random.sample(population, min(intersections_per_hour, len(population))):
                start_zone = zones[start]
                veh_count = simulate_count(hour, 10, is_weekend, start_zone)
                ped_count = simulate_count(hour, 6, is_weekend, start_zone)

                possible_dests = [n for n, z in zones.items() if n != start and z in ("commercial", "industrial")]

                for _ in range(veh_count):
                    if not possible_dests:
                        continue
                    dest = random.choice(possible_dests)
                    try:
                        path = precomputed_paths[start][dest]
                        congestion_delay = get_path_congestion_penalty(path)
                        path_str = format_path(path)
                        update_live_congestion(path)
                    except KeyError:
                        continue
                    veh_type, weight_val = random_vehicle_type()
                    vehicle_log.append({
                        "id": f"veh_{id_counter:05d}",
                        "type": veh_type,
                        "weight": weight_val,
                        "from": start,
                        "to": dest,
                        "path": path_str,
                        "hour": hour,
                        "day": day,
                        "congestion_penalty": round(congestion_delay, 2)
                    })
                    id_counter += 1

                for _ in range(ped_count):
                    nearby = [n for n in intersections if n != start and n in precomputed_paths[start] and len(precomputed_paths[start][n]) <= 4]
                    dest = random.choice(nearby) if nearby else random.choice(intersections)
                    try:
                        path = precomputed_paths[start][dest]
                        congestion_delay = get_path_congestion_penalty(path)
                        path_str = format_path(path)
                        update_live_congestion(path)
                    except KeyError:
                        continue
                    pedestrian_log.append({
                        "id": f"ped_{id_counter:05d}",
                        "type": "pedestrian",
                        "weight": 0,
                        "from": start,
                        "to": dest,
                        "path": path_str,
                        "hour": hour,
                        "day": day,
                        "congestion_penalty": round(congestion_delay, 2)
                    })
                    id_counter += 1

            if vehicle_log:
                append_to_csv(vehicles_log_file, vehicle_log)
            if pedestrian_log:
                append_to_csv(pedestrians_log_file, pedestrian_log)

    print("\n✅ Full realistic cached simulation completed!")

if __name__ == "__main__":
    main()