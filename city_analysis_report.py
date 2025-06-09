import json

# ───── Assumptions ─────
STREETLIGHT_POWER_KW = 0.1    # 150 W at 100% voltage
# Lights on from 7 PM (19) to 6 AM (6) inclusive => 12 hours
ACTIVE_HOURS = [*range(19, 24), *range(0, 7)]


def load_json(path):
    """Load JSON data from the given file path."""
    with open(path, 'r') as f:
        return json.load(f)


def cross_verify_lamps(city_data, volt_sched):
    """
    Verify streetlight counts between city data and voltage schedule.
    Returns (total_city, total_sched, missing_edges).
    """
    total_city = city_data.get('total_streetlights', 0)
    total_sched = 0
    missing = []
    for src, targets in volt_sched.items():
        for dst in targets:
            edge_key = f"{src}-{dst}"
            road_info = city_data.get('road_stats', {}).get(edge_key)
            if road_info:
                total_sched += road_info.get('streetlights', 0)
            else:
                missing.append(edge_key)

    print(f"City reports {total_city} streetlights.")
    if missing:
        print(f"⚠️ Warning: {len(missing)} edges not in city data:")
        for e in missing:
            print(f"  - {e}")
    print(f"Schedule covers {total_sched} streetlights (matched).\n")
    return total_city, total_sched, missing


def calc_baseline(city_data):
    """
    Calculate baseline energy (kWh) assuming full voltage (100%) for all lights
    over 12 hours (7 PM–6 AM inclusive).
    """
    total = city_data.get('total_streetlights', 0)
    hours = len(ACTIVE_HOURS)
    return total * STREETLIGHT_POWER_KW * hours


def calc_optimized(city_data, volt_sched):
    """
    Calculate optimized energy (kWh) using the voltage schedule.
    Scales power by (V/100)^2 for each lamp, edge, and active hour (12h).
    """
    energy = 0.0
    for src, targets in volt_sched.items():
        for dst, hours_map in targets.items():
            edge_key = f"{src}-{dst}"
            lamps = city_data.get('road_stats', {}).get(edge_key, {}).get('streetlights', 0)
            if not lamps:
                continue
            for h_str, V in hours_map.items():
                h = int(h_str)
                if h in ACTIVE_HOURS:
                    power_per_light = STREETLIGHT_POWER_KW * (V / 100) ** 2
                    energy += power_per_light * lamps  # 1 hour
    return energy


def compute_city_area(city_data):
    """
    Estimate city grid area by averaging block lengths in rows and columns.
    Works for arbitrary grid labels (e.g., A1..J20).
    Returns (area_km2, area_m2).
    """
    rows, cols = {}, {}
    for edge_key, stats in city_data.get('road_stats', {}).items():
        src, dst = edge_key.split('-')
        # Row if same letter
        if src[0] == dst[0]:
            rows.setdefault(src[0], []).append(stats['length_km'])
        # Column if same numeric part
        elif src[1:] == dst[1:]:
            cols.setdefault(src[1:], []).append(stats['length_km'])

    if not rows or not cols:
        return 0.0, 0.0

    avg_row = sum(sum(l) for l in rows.values()) / len(rows)
    avg_col = sum(sum(l) for l in cols.values()) / len(cols)
    area_km2 = avg_row * avg_col
    area_m2 = area_km2 * 1e6
    return area_km2, area_m2


def main():
    city = load_json('city_analysis.json')
    sched = load_json('smoothed_voltage_schedule.json')

    # 1) Verify lamps
    cross_verify_lamps(city, sched)

    # 2) Compute area
    area_km2, area_m2 = compute_city_area(city)
    print(f"🏙️ City area estimate: {area_km2:.4f} km² ({area_m2:.2f} m²)\n")

    # 3) Baseline energy
    baseline = calc_baseline(city)
    print(f"🔋 Baseline (100% voltage): {baseline:.2f} kWh")

    # 4) Optimized energy
    optimized = calc_optimized(city, sched)
    print(f"🌙 After optimization:    {optimized:.2f} kWh")

    # 5) Savings
    saved = baseline - optimized
    pct = (saved / baseline * 100) if baseline else 0
    print(f"💾 You saved {saved:.2f} kWh ({pct:.1f}% reduction) in one night!")

if __name__ == '__main__':
    main()
