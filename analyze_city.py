# file: analyze_city.py

import json
import networkx as nx
import matplotlib.pyplot as plt
from networkx.readwrite import json_graph
from collections import defaultdict

def load_city_graph(filename="city_grid.json"):
    with open(filename, 'r') as f:
        data = json.load(f)
    G = json_graph.node_link_graph(data)
    return G

def load_streetlights(filename="streetlights.json"):
    with open(filename, 'r') as f:
        return json.load(f)

def analyze(G, streetlights):
    road_stats = {}
    light_map = {}
    type_stats = defaultdict(lambda: {"lights": 0, "length": 0, "capacity": 0, "count": 0})
    zone_stats = defaultdict(lambda: {"intersections": 0, "roads": 0, "traffic_lights": 0, "avg_traffic_light_delay": 0})

    for node, data in G.nodes(data=True):
        zone = data.get("zone", "unknown")
        zone_stats[zone]["intersections"] += 1
        if data.get("traffic_light", False):
            zone_stats[zone]["traffic_lights"] += 1
            zone_stats[zone]["avg_traffic_light_delay"] += data.get("traffic_light_delay", 0)

    for light in streetlights:
        key = (light['from'], light['to'])
        light_map[key] = light_map.get(key, 0) + 1

    total_lights = sum(light_map.values())
    roads_with_no_lights = []

    for u, v, d in G.edges(data=True):
        lights = light_map.get((u, v), 0)
        length = d.get('distance', 0)
        road_type = d.get('road_type', 'unknown')
        capacity = d.get('capacity', 0)
        delay = d.get('delay', 0)

        road_stats[(u, v)] = {
            "length_km": length,
            "road_type": road_type,
            "streetlights": lights,
            "lights_per_km": round(lights / length, 2) if length else 0,
            "capacity": capacity,
            "delay": delay
        }

        type_stats[road_type]["lights"] += lights
        type_stats[road_type]["length"] += length
        type_stats[road_type]["capacity"] += capacity
        type_stats[road_type]["count"] += 1

        zone_stats[G.nodes[u]['zone']]["roads"] += 1

        if lights == 0:
            roads_with_no_lights.append((u, v))

    for t in type_stats:
        l = type_stats[t]["lights"]
        km = type_stats[t]["length"]
        type_stats[t]["avg_lights_per_km"] = round(l / km, 2) if km else 0
        c = type_stats[t]["capacity"]
        n = type_stats[t]["count"]
        type_stats[t]["avg_capacity"] = round(c / n, 2) if n else 0
    
    for zone, stats in zone_stats.items():
        if stats["traffic_lights"] > 0:
            stats["avg_traffic_light_delay"] = round(stats["avg_traffic_light_delay"] / stats["traffic_lights"], 2)


    summary = {
        "total_intersections": G.number_of_nodes(),
        "total_roads": G.number_of_edges(),
        "total_streetlights": total_lights,
        "roads_without_streetlights": roads_with_no_lights,
        "road_stats": road_stats,
        "type_stats": dict(type_stats),
        "zone_stats": dict(zone_stats),
        "intersections_with_traffic_lights": sum(1 for _, d in G.nodes(data=True) if d.get("traffic_light", False))  # NEW
    }

    return summary

def print_summary(summary):
    print("\nCity Grid Analysis")
    print(f"🧠 Intersections: {summary['total_intersections']}")
    print(f"🧠 Roads: {summary['total_roads']}")
    print(f"🧠 Total streetlights: {summary['total_streetlights']}")
    print(f"🧠 Roads with NO streetlights: {len(summary['roads_without_streetlights'])}")
    print(f"🧠 Intersections: {summary['total_intersections']}")
    print(f"🧠 Intersections with traffic lights: {summary['intersections_with_traffic_lights']}")
    if summary['roads_without_streetlights']:
        for r in summary['roads_without_streetlights']:
            print(f"   ❌ {r[0]} → {r[1]}")

    print("\n\U0001f4ca Road Type Breakdown:")
    for rtype, stats in summary['type_stats'].items():
        print(f"  {rtype.capitalize()} roads: {stats['count']} total, {stats['lights']} lights, {stats['avg_lights_per_km']} lights/km, {stats['avg_capacity']} avg capacity")

    print("\n\U0001f3d9️ Zone Breakdown:")
    for zone, stats in summary['zone_stats'].items():
        print(f"  {zone.capitalize()}: {stats['intersections']} intersections, {stats['roads']} roads, {stats['traffic_lights']} traffic lights")

def save_report(summary, filename="city_analysis.json"):
    json_summary = dict(summary)
    json_summary["road_stats"] = {f"{u}-{v}": stats for (u, v), stats in summary["road_stats"].items()}
    with open(filename, 'w') as f:
        json.dump(json_summary, f, indent=2)
    print(f"\n Analysis saved to {filename}")

def plot_streetlights_bar_chart(road_stats):
    roads = [f"{u}→{v}" for (u, v) in road_stats]
    lights = [data["streetlights"] for data in road_stats.values()]
    colors = ['black' if data["road_type"] == "major" else 'goldenrod' for data in road_stats.values()]

    plt.figure(figsize=(max(10, len(roads) * 0.3), 5))
    plt.bar(roads, lights, color=colors)
    plt.ylabel("Streetlights")
    plt.title("Streetlights per Road")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.show()

def main():
    print("Loading city data...")
    G = load_city_graph("city_grid.json")
    streetlights = load_streetlights("streetlights.json")

    summary = analyze(G, streetlights)
    print_summary(summary)

    save = input("\nSave report to JSON? (y/n): ").strip().lower()
    if save == 'y':
        save_report(summary)

    plot = input("Show bar chart of streetlights per road? (y/n): ").strip().lower()
    if plot == 'y':
        plot_streetlights_bar_chart(summary["road_stats"])

if __name__ == "__main__":
    main()