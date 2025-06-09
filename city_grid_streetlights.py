# file: city_grid_streetlights.py

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import random
import json
import tkinter as tk
from tkinter import messagebox
import threading

ZONES = ["residential", "commercial", "industrial", "park"]

ZONE_PROBABILITIES = {
    "residential": 0.45,
    "commercial": 0.25,
    "industrial": 0.15,
    "park": 0.15
}

def assign_zone(r, c, rows, cols):
    if r < rows * 0.2:
        return "residential"
    elif r > rows * 0.8:
        return "industrial"
    elif c > cols * 0.7:
        return "commercial"
    else:
        return random.choices(list(ZONE_PROBABILITIES.keys()), weights=ZONE_PROBABILITIES.values(), k=1)[0]

def add_edge_with_metadata(G, u, v):
    road_type = random.choices(["major", "minor"], weights=[0.3, 0.7])[0]
    distance = round(random.uniform(0.5, 2.0) if road_type == "minor" else random.uniform(2.0, 5.0), 2)
    capacity = random.randint(300, 800) if road_type == "major" else random.randint(100, 300)
    delay = 0.1 if random.random() < 0.3 else 0

    G.add_edge(u, v, weight=distance + delay, distance=distance, road_type=road_type, capacity=capacity, delay=delay)

def node_name(r, c):
    return chr(65 + r) + str(c + 1)

def generate_grid_with_correct_streetlights(rows, cols):
    G = nx.DiGraph()

    for r in range(rows):
        for c in range(cols):
            zone = assign_zone(r, c, rows, cols)
            zone_light_chance = {
                "residential": 0.3,
                "commercial": 0.6,  # more lights
                "industrial": 0.2,
                "park": 0.1
            }
            has_traffic_light = random.random() < zone_light_chance.get(zone, 0.3)
            traffic_light_delay = round(random.uniform(0.05, 0.3), 2) if has_traffic_light else 0  # 🆕
            G.add_node(
                node_name(r, c),
                zone=zone,
                traffic_light=has_traffic_light,
                traffic_light_delay=traffic_light_delay  # 🆕
            )

    for r in range(rows):
        for c in range(cols):
            current = node_name(r, c)
            if c + 1 < cols:
                add_edge_with_metadata(G, current, node_name(r, c + 1))
            if r + 1 < rows:
                add_edge_with_metadata(G, current, node_name(r + 1, c))

    streetlights = {}
    for u, v, d in G.edges(data=True):
        zone_u = G.nodes[u]['zone']
        zone_v = G.nodes[v]['zone']
        zone_factor = 1

        if "industrial" in (zone_u, zone_v):
            zone_factor = 0.8
        elif "commercial" in (zone_u, zone_v):
            zone_factor = 1.5
        elif "park" in (zone_u, zone_v):
            zone_factor = 0.5

        lights = max(1, int(d['distance'] * zone_factor * 2))
        streetlights[(u, v)] = lights

    pos = {node: (int(node[1:]) - 1, -(ord(node[0]) - 65)) for node in G.nodes()}
    return G, pos, streetlights

def export_graph(G, filename):
    data = nx.readwrite.json_graph.node_link_data(G)
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✅ Exported graph to {filename}")

def export_streetlights(G, pos, streetlights, filename):
    light_positions = []
    for (u, v), count in streetlights.items():
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        dx, dy = x2 - x1, y2 - y1
        length = (dx**2 + dy**2)**0.5
        ox = -dy / length * 0.03
        oy = dx / length * 0.03

        for i in range(1, count + 1):
            t = i / (count + 1)
            x = x1 + t * dx + ox
            y = y1 + t * dy + oy
            light_positions.append({"from": u, "to": v, "x": x, "y": y})

    with open(filename, "w") as f:
        json.dump(light_positions, f, indent=2)
    print(f"✅ Exported {len(light_positions)} streetlights to {filename}")

def draw_graph(G, pos, streetlights, rows, cols):
    plt.figure(figsize=(cols + 2, rows + 2))
    nx.draw_networkx_nodes(G, pos, node_color='white', edgecolors='black', node_size=900, linewidths=1.5)
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')

    major_edges = [(u, v) for u, v, d in G.edges(data=True) if d['road_type'] == 'major']
    minor_edges = [(u, v) for u, v, d in G.edges(data=True) if d['road_type'] == 'minor']

    nx.draw_networkx_edges(G, pos, edgelist=major_edges, edge_color='black', width=6, arrows=True, arrowsize=20)
    nx.draw_networkx_edges(G, pos, edgelist=minor_edges, edge_color='yellow', style='dashed', width=3, arrows=True, arrowsize=20)

    for (u, v), count in streetlights.items():
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        dx = x2 - x1
        dy = y2 - y1
        length = (dx**2 + dy**2)**0.5
        ox = -dy / length * 0.03
        oy = dx / length * 0.03

        for i in range(1, count + 1):
            t = i / (count + 1)
            x = x1 + t * dx + ox
            y = y1 + t * dy + oy
            plt.scatter(x, y, color='yellow', s=50, marker='o')

    major_patch = mpatches.Patch(color='black', label='Major Road')
    minor_patch = mpatches.Patch(color='yellow', label='Minor Road (Dashed)')
    light_patch = mpatches.Patch(color='yellow', label='Streetlight', alpha=0.5)
    plt.legend(handles=[major_patch, minor_patch, light_patch], loc='upper right', fontsize=8)

    plt.title(f"City Grid with Streetlights ({rows}x{cols})", fontsize=14)
    plt.axis('off')
    plt.tight_layout()
    plt.show()

def print_summary(G, streetlights, rows, cols):
    print(f"\n✅ Generated {rows * cols} intersections with zones and streetlights.")
    print("🔆 Sample roads with streetlights:")
    for i, (u, v, d) in enumerate(G.edges(data=True)):
        if i < 100:
            print(f"{u} ({G.nodes[u]['zone']}) → {v} ({G.nodes[v]['zone']}): {d['distance']} km ({d['road_type']}, capacity {d['capacity']}) — Streetlights: {streetlights[(u, v)]}")

def main():
    print("\n🌐 City Grid Generator (Zones, Capacity, Streetlights, Traffic Lights)")
    rows = int(input("Enter number of rows: "))
    cols = int(input("Enter number of columns: "))

    G, pos, streetlights = generate_grid_with_correct_streetlights(rows, cols)

    if rows > 10 or cols > 10:
        print("⚠️ Large grid detected. Skipping visualization. Exporting data only...")
    else:
        draw_graph(G, pos, streetlights, rows, cols)

    export_graph(G, "city_grid.json")
    export_streetlights(G, pos, streetlights, "streetlights.json")
    print_summary(G, streetlights, rows, cols)

if __name__ == "__main__":
    main()