import os
import json
import pytz
import requests
import urllib.parse
import warnings
import swisseph as swe
from kerykeion import AstrologicalSubject

EPHE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "ephe"))
if not EPHE_PATH.endswith(os.path.sep):
    EPHE_PATH += os.path.sep

if os.path.exists(EPHE_PATH):
    swe.set_ephe_path(EPHE_PATH)

LOCAL_JSON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "ja_data.json"))

def load_address_master():
    if os.path.exists(LOCAL_JSON_PATH):
        try:
            with open(LOCAL_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    try:
        url = "https://geolonia.github.io/japanese-addresses/api/ja.json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            with open(LOCAL_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return data
    except Exception as e:
        print(f"Address master fetch error: {e}")
    
    return {}

SIGN_DATA = {
    "Aries": {"en": "Aries"}, "Taurus": {"en": "Taurus"},
    "Gemini": {"en": "Gemini"}, "Cancer": {"en": "Cancer"},
    "Leo": {"en": "Leo"}, "Virgo": {"en": "Virgo"},
    "Libra": {"en": "Libra"}, "Scorpio": {"en": "Scorpio"},
    "Sagittarius": {"en": "Sagittarius"}, "Capricorn": {"en": "Capricorn"},
    "Aquarius": {"en": "Aquarius"}, "Pisces": {"en": "Pisces"}
}

SIGN_NORM_MAP = {
    "Ari": "Aries", "Tau": "Taurus", "Gem": "Gemini", "Can": "Cancer", "Leo": "Leo", "Vir": "Virgo",
    "Lib": "Libra", "Sco": "Scorpio", "Sag": "Sagittarius", "Cap": "Capricorn", "Aqu": "Aquarius", "Pis": "Pisces",
    "Aries": "Aries", "Taurus": "Taurus", "Gemini": "Gemini", "Cancer": "Cancer", "Leo": "Leo", "Virgo": "Virgo",
    "Libra": "Libra", "Scorpio": "Scorpio", "Sagittarius": "Sagittarius", "Capricorn": "Capricorn", "Aquarius": "Aquarius", "Pisces": "Pisces"
}

SIGN_RULERS = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Pluto",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Uranus",
    "Pisces": "Neptune"
}

DIGNITIES = {
    "Sun": {"domicile": ["Leo"], "exaltation": ["Aries"], "detriment": ["Aquarius"], "fall": ["Libra"]},
    "Moon": {"domicile": ["Cancer"], "exaltation": ["Taurus"], "detriment": ["Capricorn"], "fall": ["Scorpio"]},
    "Mercury": {"domicile": ["Gemini", "Virgo"], "exaltation": ["Virgo"], "detriment": ["Sagittarius", "Pisces"], "fall": ["Pisces"]},
    "Venus": {"domicile": ["Taurus", "Libra"], "exaltation": ["Pisces"], "detriment": ["Scorpio", "Aries"], "fall": ["Virgo"]},
    "Mars": {"domicile": ["Aries", "Scorpio"], "exaltation": ["Capricorn"], "detriment": ["Libra", "Taurus"], "fall": ["Cancer"]},
    "Jupiter": {"domicile": ["Sagittarius", "Pisces"], "exaltation": ["Cancer"], "detriment": ["Gemini", "Virgo"], "fall": ["Capricorn"]},
    "Saturn": {"domicile": ["Capricorn", "Aquarius"], "exaltation": ["Libra"], "detriment": ["Cancer", "Leo"], "fall": ["Aries"]}
}

def apply_dignity_color(planet_name, sign_name):
    for p, dign in DIGNITIES.items():
        if p in planet_name:
            if any(s == sign_name for s in dign.get("domicile", [])):
                return f'<span style="color: #ff4b4b; font-weight: bold;">{sign_name}</span> <span style="font-size: 0.85em; color: #ff4b4b;">🔴 [Domicile]</span>'
            elif any(s == sign_name for s in dign.get("exaltation", [])):
                return f'<span style="color: #ff69b4; font-weight: bold;">{sign_name}</span> <span style="font-size: 0.85em; color: #ff69b4;">🩷 [Exaltation]</span>'
            elif any(s == sign_name for s in dign.get("detriment", [])):
                return f'<span style="color: #1e90ff; font-weight: bold;">{sign_name}</span> <span style="font-size: 0.85em; color: #1e90ff;">🔵 [Detriment]</span>'
            elif any(s == sign_name for s in dign.get("fall", [])):
                return f'<span style="color: #00bfff; font-weight: bold;">{sign_name}</span> <span style="font-size: 0.85em; color: #00bfff;">🩵 [Fall]</span>'
    return sign_name

def get_cities_for_prefecture(pref):
    if pref == "Overseas / Other":
        return []
    master = load_address_master()
    if master and pref in master:
        return master[pref]
    return []

def validate_and_get_coords(pref, city_name):
    cleaned_city = city_name.strip()
    
    if pref == "Overseas / Other":
        try:
            encoded_name = urllib.parse.quote(cleaned_city)
            url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={encoded_name}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    coords = data[0]["geometry"]["coordinates"]
                    return True, "", coords[1], coords[0]
        except Exception:
            pass
        return True, "", 35.6812, 139.7671

    master = load_address_master()
    if master and pref in master:
        allowed_cities = master[pref]
        matched = any(c == cleaned_city or c.endswith(cleaned_city) or cleaned_city in c for c in allowed_cities)
        if not matched:
            return False, "Location does not exist in this prefecture.", None, None

    search_query = f"{pref}{cleaned_city}"
    try:
        encoded_name = urllib.parse.quote(search_query)
        url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={encoded_name}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                first_res = data[0]
                addr = first_res.get("properties", {}).get("address", "")
                title = first_res.get("properties", {}).get("title", "")
                full_text = addr + title
                if pref in full_text:
                    coords = first_res["geometry"]["coordinates"]
                    return True, "", coords[1], coords[0]
                else:
                    return False, "Location does not exist in this prefecture.", None, None
            else:
                return False, "Location does not exist in this prefecture.", None, None
    except Exception as e:
        print(f"Geocoding error: {e}")
    
    return False, "Location not found or communication error.", None, None

def get_house_ruler_chains(houses_list, bodies_meta, house_name_map, use_5_deg_rule=False, house_cusp_abs=None):
    body_house_map = {}
    major_bodies = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}

    for key, p in bodies_meta:
        h_raw = p.get('house', 'First_House') if isinstance(p, dict) else getattr(p, 'house', 'First_House')
        h_num = house_name_map.get(str(h_raw), 1)
        
        if use_5_deg_rule and key in major_bodies and house_cusp_abs:
            sign = p.get('sign', 'Aries') if isinstance(p, dict) else getattr(p, 'sign', 'Aries')
            pos = p.get('position', 0.0) if isinstance(p, dict) else getattr(p, 'position', 0.0)
            norm_sign = SIGN_NORM_MAP.get(str(sign), "Aries")
            s_idx = list(SIGN_DATA.keys()).index(norm_sign) if norm_sign in SIGN_DATA else 0
            abs_p_pos = s_idx * 30 + pos
            
            next_idx = (h_num % 12)
            cusp_next = house_cusp_abs[next_idx]
            dist = (cusp_next - abs_p_pos) % 360
            if 0.0 <= dist <= 5.0:
                h_num = next_idx + 1

        body_house_map[key] = h_num

    house_links = {}
    for i, h in enumerate(houses_list, 1):
        sign = h.get('sign', 'Aries') if isinstance(h, dict) else getattr(h, 'sign', 'Aries')
        norm_sign = SIGN_NORM_MAP.get(str(sign), "Aries")
        ruler_key = SIGN_RULERS.get(norm_sign, "Sun")
        target_house = body_house_map.get(ruler_key, i)
        house_links[i] = target_house

    chain_results = []
    for start_h in range(1, 13):
        path = [start_h]
        visited = set([start_h])
        current = start_h
        status = "end"
        loop_target = None
        
        while current in house_links:
            next_house = house_links[current]
            if next_house == current:
                status = "domicile"
                break
            if next_house in visited:
                path.append(next_house)
                status = "loop"
                loop_target = next_house
                break
            visited.add(next_house)
            path.append(next_house)
            current = next_house
            if len(path) > 15:
                break
        
        path_str = " → ".join([f"{h}{'st' if h==1 else 'nd' if h==2 else 'rd' if h==3 else 'th'} House" for h in path])
        start_h_str = f"{start_h}{'st' if start_h==1 else 'nd' if start_h==2 else 'rd' if start_h==3 else 'th'} House"
        if status == "domicile":
            display_text = f"**{start_h_str}** ➡️ {path_str} (Domicile)"
        elif status == "loop":
            display_text = f"**{start_h_str}** ➡️ {path_str} (Loop with {loop_target}{'st' if loop_target==1 else 'nd' if loop_target==2 else 'rd' if loop_target==3 else 'th'} House)"
        else:
            display_text = f"**{start_h_str}** ➡️ {path_str}"
        chain_results.append(display_text)
        
    return chain_results

def calculate_midpoints(bodies, chart_angles=None):
    body_map = {b["key"]: b["abs_pos"] for b in bodies}
    planet_keys = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
    outer_planets = {"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
    
    priority = [
        "Sun", "Moon", "Mercury", "Venus", "Mars",
        "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
        "Chiron", "North Node", "South Node", "ASC", "MC"
    ]
    
    def get_prio(key):
        return priority.index(key) if key in priority else 99

    def get_midpoint_pos(pos1, pos2):
        diff = abs(pos1 - pos2)
        if diff > 180:
            mp = (pos1 + pos2 + 360) / 2
        else:
            mp = (pos1 + pos2) / 2
        return mp % 360

    hit_results = []
    aspect_angles = [0, 90, 180]
    orb_limit = 1.5

    all_points = list(body_map.items())
    n = len(all_points)

    for i in range(n):
        for j in range(i + 1, n):
            k1, pos1 = all_points[i]
            k2, pos2 = all_points[j]
            
            if k1 in outer_planets and k2 in outer_planets:
                continue
            
            is_node_involved = (k1 in ["North Node", "South Node"] or k2 in ["North Node", "South Node"])
            if is_node_involved:
                if not (k1 in planet_keys or k2 in planet_keys):
                    continue

            if not (k1 in planet_keys or k2 in planet_keys) and not is_node_involved:
                allowed_pairs = {("Sun", "Moon"), ("Moon", "Sun"), ("ASC", "MC"), ("MC", "ASC")}
                if (k1, k2) not in allowed_pairs and (k2, k1) not in allowed_pairs:
                    continue

            if get_prio(k1) > get_prio(k2):
                k1, k2 = k2, k1
                pos1, pos2 = pos2, pos1

            mp_pos = get_midpoint_pos(pos1, pos2)
            mp_name = f"{k1}/{k2}"

            for target_k, target_pos in all_points:
                if target_k == k1 or target_k == k2:
                    continue
                
                diff = min(abs(mp_pos - target_pos), 360 - abs(mp_pos - target_pos))
                for ang in aspect_angles:
                    orb = abs(diff - ang)
                    if orb <= orb_limit:
                        asp_label = "0°" if ang == 0 else ("90°" if ang == 90 else "180°")
                        hit_results.append({
                            "prio1": get_prio(k1),
                            "prio2": get_prio(k2),
                            "axis": mp_name,
                            "target": target_k,
                            "aspect": asp_label,
                            "orb": orb
                        })

    unique_hits = {}
    for h in hit_results:
        key = (h["axis"], h["target"], h["aspect"])
        if key not in unique_hits or h["orb"] < unique_hits[key]["orb"]:
            unique_hits[key] = h

    formatted_lines = []
    sorted_hits = sorted(unique_hits.values(), key=lambda x: (x["prio1"], x["prio2"], x["orb"]))
    for h in sorted_hits:
        line = f"- **{h['axis']}** = **{h['target']}** `({h['aspect']} / orb: {h['orb']:.2f}°)`"
        formatted_lines.append(line)

    if not formatted_lines:
        return ["*(No midpoint hits found)*"]
        
    return formatted_lines

def format_deg_min(decimal_deg):
    deg = int(decimal_deg)
    minutes = round((decimal_deg - deg) * 60)
    if minutes == 60:
        deg += 1
        minutes = 0
    return f"{deg}°{minutes:02d}′"

def to_dms(val, is_lat=True):
    abs_val = abs(val)
    deg = int(abs_val)
    minutes_float = (abs_val - deg) * 60
    minute = int(minutes_float)
    second = round((minutes_float - minute) * 60)
    
    if second == 60:
        second = 0
        minute += 1
    if minute == 60:
        minute = 0
        deg += 1
        
    if is_lat:
        direction = "N" if val >= 0 else "S"
    else:
        direction = "E" if val >= 0 else "W"
            
    return f"{deg}°{minute:02d}'{second:02d}\" {direction}"

def get_s_name(key):
    norm = SIGN_NORM_MAP.get(str(key).strip(), "Aries")
    s = SIGN_DATA.get(norm, {"en": key})
    return s['en']

def get_p_name(key):
    return key

def format_house_name(h_num):
    sfx = {"1": "st", "2": "nd", "3": "rd"}.get(str(h_num), "th")
    return f"{h_num}{sfx} House"

def calculate_aspects(bodies, view_type="By Pair"):
    aspect_defs = [
        ("Conjunction", 0, 7.0, "Conjunction (0°)"),
        ("Opposition", 180, 7.0, "Opposition (180°)"),
        ("Trine", 120, 6.0, "Trine (120°)"),
        ("Square", 90, 6.0, "Square (90°)"),
        ("Sextile", 60, 5.0, "Sextile (60°)"),
        ("Quincunx", 150, 3.0, "Quincunx (150°)")
    ]
    results = []
    n = len(bodies)
    for i in range(n):
        for j in range(i + 1, n):
            b1, b2 = bodies[i], bodies[j]
            diff = min(abs(b1["abs_pos"] - b2["abs_pos"]), 360 - abs(b1["abs_pos"] - b2["abs_pos"]))
            for _, target_ang, orb_limit, en_lbl in aspect_defs:
                orb = abs(diff - target_ang)
                if orb <= orb_limit:
                    results.append({"label": en_lbl, "b1": b1["key"], "b2": b2["key"], "orb": orb})
    
    if not results:
        return "*(No aspects)*"
    
    lines = []
    if view_type == "アスペクト別":
        grouped = {}
        for r in results: grouped.setdefault(r["label"], []).append(r)
        for label, items in grouped.items():
            lines.append(f"**■ {label}**")
            for item in sorted(items, key=lambda x: x["orb"]):
                lines.append(f"- {get_p_name(item['b1'])} & {get_p_name(item['b2'])} `(orb: {item['orb']:.2f}°)`")
            lines.append("")
    else:
        priority = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "North Node", "South Node", "Chiron"]
        def get_prio(r):
            p1 = priority.index(r["b1"]) if r["b1"] in priority else 99
            p2 = priority.index(r["b2"]) if r["b2"] in priority else 99
            if p1 > p2: r["b1"], r["b2"] = r["b2"], r["b1"]
            return (min(p1, p2), max(p1, p2), r["orb"])
        
        sorted_results = sorted(results, key=get_prio)
        prev = None
        for r in sorted_results:
            if prev and r["b1"] != prev: lines.append("")
            lines.append(f"- {get_p_name(r['b1'])} & {get_p_name(r['b2'])} : **{r['label']}** `(orb: {r['orb']:.2f}°)`")
            prev = r["b1"]
            
    return "\n".join(lines)

def detect_patterns(bodies):
    patterns = []
    aspect_pairs = []
    n = len(bodies)
    
    body_map = {b["key"]: b["abs_pos"] for b in bodies}

    for i in range(n):
        for j in range(i + 1, n):
            pos1, pos2 = bodies[i]["abs_pos"], bodies[j]["abs_pos"]
            k1, k2 = bodies[i]["key"], bodies[j]["key"]
            diff = min(abs(pos1 - pos2), 360 - abs(pos1 - pos2))
            if diff <= 6.0: aspect_pairs.append((k1, k2, "Conjunction", diff))
            if abs(diff - 180) <= 6.0: aspect_pairs.append((k1, k2, "Opposition", abs(diff - 180)))
            if abs(diff - 120) <= 6.0: aspect_pairs.append((k1, k2, "Trine", abs(diff - 120)))
            if abs(diff - 90) <= 5.0: aspect_pairs.append((k1, k2, "Square", abs(diff - 90)))
            if abs(diff - 60) <= 5.0: aspect_pairs.append((k1, k2, "Sextile", abs(diff - 60)))
            if abs(diff - 150) <= 3.0: aspect_pairs.append((k1, k2, "Quincunx", abs(diff - 150)))

    valid_stellium_bodies = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
    
    stellium_edges = []
    filtered_bodies = [b for b in bodies if b["key"] in valid_stellium_bodies]
    fn = len(filtered_bodies)
    
    for i in range(fn):
        for j in range(i + 1, fn):
            b1, b2 = filtered_bodies[i], filtered_bodies[j]
            diff = min(abs(b1["abs_pos"] - b2["abs_pos"]), 360 - abs(b1["abs_pos"] - b2["abs_pos"]))
            
            is_luminary = (b1["key"] in ["Sun", "Moon"] or b2["key"] in ["Sun", "Moon"])
            orb_limit = 10.0 if is_luminary else 7.5
            
            if diff <= orb_limit:
                stellium_edges.append((b1["key"], b2["key"]))

    adj = {}
    for k1, k2 in stellium_edges:
        adj.setdefault(k1, set()).add(k2)
        adj.setdefault(k2, set()).add(k1)

    visited = set()
    stellium_groups = []
    for node in adj:
        if node not in visited:
            component = []
            stack = [node]
            visited.add(node)
            while stack:
                curr = stack.pop()
                component.append(curr)
                for neighbor in adj.get(curr, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        stack.append(neighbor)
            if len(component) >= 3:
                stellium_groups.append(component)

    priority = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
    for comp in stellium_groups:
        comp_sorted = sorted(comp, key=lambda x: priority.index(x) if x in priority else 99)
        m_names = " & ".join([get_p_name(m) for m in comp_sorted])
        
        avg_pos = sum([body_map[k] for k in comp_sorted]) / len(comp_sorted)
        s_idx = int((avg_pos % 360) // 30)
        s_keys = list(SIGN_DATA.keys())
        s_loc = get_s_name(s_keys[s_idx]) if s_idx < len(s_keys) else ""
        
        patterns.append(f"Stellium (approx. {s_loc}) : {m_names}")

    opps = [(a, b) for a, b, t, _ in aspect_pairs if t == "Opposition"]
    squares = [(a, b) for a, b, t, _ in aspect_pairs if t == "Square"]
    trines = [(a, b) for a, b, t, _ in aspect_pairs if t == "Trine"]
    sextiles = [(a, b) for a, b, t, _ in aspect_pairs if t == "Sextile"]
    quincunxes = [(a, b) for a, b, t, _ in aspect_pairs if t == "Quincunx"]

    sq_dict, tr_dict, sex_dict, qui_dict = {}, {}, {}, {}
    for a, b in squares:
        sq_dict.setdefault(a, set()).add(b); sq_dict.setdefault(b, set()).add(a)
    for a, b in trines:
        tr_dict.setdefault(a, set()).add(b); tr_dict.setdefault(b, set()).add(a)
    for a, b in sextiles:
        sex_dict.setdefault(a, set()).add(b); sex_dict.setdefault(b, set()).add(a)
    for a, b in quincunxes:
        qui_dict.setdefault(a, set()).add(b); qui_dict.setdefault(b, set()).add(a)

    for op_a, op_b in opps:
        common_sq = sq_dict.get(op_a, set()).intersection(sq_dict.get(op_b, set()))
        for apex in common_sq:
            p_apex, p_a, p_b = get_p_name(apex), get_p_name(op_a), get_p_name(op_b)
            patterns.append(f"T-Square [Apex: {p_apex}] : {p_apex} & {p_a} & {p_b}")

    checked_gt = set()
    for a, neighbors in tr_dict.items():
        for b in neighbors:
            common_tr = tr_dict.get(a, set()).intersection(tr_dict.get(b, set()))
            for c in common_tr:
                if a < b < c:
                    sorted_key = (a, b, c)
                    if sorted_key not in checked_gt:
                        checked_gt.add(sorted_key)
                        p_a, p_b, p_c = get_p_name(a), get_p_name(b), get_p_name(c)
                        patterns.append(f"Grand Trine : {p_a} & {p_b} & {p_c}")

    checked_mt = set()
    for a, neighbors in sex_dict.items():
        for b in neighbors:
            if a < b:
                common_tr = tr_dict.get(a, set()).intersection(tr_dict.get(b, set()))
                for c in common_tr:
                    sorted_key = tuple(sorted([a, b, c]))
                    if sorted_key not in checked_mt:
                        checked_mt.add(sorted_key)
                        p_a, p_b, p_c = get_p_name(sorted_key[0]), get_p_name(sorted_key[1]), get_p_name(sorted_key[2])
                        patterns.append(f"Mini Trine : {p_a} & {p_b} & {p_c}")

    for a, sex_neighbors in sex_dict.items():
        for b in sex_neighbors:
            common_qui = qui_dict.get(a, set()).intersection(qui_dict.get(b, set()))
            for apex in common_qui:
                p_apex, p_a, p_b = get_p_name(apex), get_p_name(a), get_p_name(b)
                patterns.append(f"Yod [Apex: {p_apex}] : {p_apex} & {p_a} & {p_b}")

    unique, seen = [], set()
    for pat in patterns:
        if ":" in pat:
            header, body = pat.split(":", 1)
            sig = (header.strip(), tuple(sorted([p.strip() for p in body.split("&")])))
        else:
            sig = pat
        if sig not in seen:
            seen.add(sig)
            unique.append(pat)
    return unique

def get_chart_data(name, year, month, day, hour, minute, lat, lng, city_display_name, view_type, is_unknown_time):
    calc_h, calc_m = (12, 0) if is_unknown_time else (hour, minute)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            chart = AstrologicalSubject(
                name=name, 
                year=year, 
                month=month, 
                day=day,
                hour=calc_h, 
                minute=calc_m, 
                lat=lat, 
                lng=lng
            )
        except Exception as e:
            return {"error": f"Horoscope calculation error: {str(e)}"}
            
    bodies_meta = [
        ("Sun", chart.sun), ("Moon", chart.moon), ("Mercury", chart.mercury),
        ("Venus", chart.venus), ("Mars", chart.mars), ("Jupiter", chart.jupiter),
        ("Saturn", chart.saturn), ("Uranus", chart.uranus), ("Neptune", chart.neptune), ("Pluto", chart.pluto)
    ]

    for key, attr_list in [("North Node", ["true_north_lunar_node", "node"]), ("South Node", ["true_south_lunar_node", "south_node"]), ("Chiron", ["chiron"])]:
        for attr in attr_list:
            if hasattr(chart, attr) and getattr(chart, attr):
                bodies_meta.append((key, getattr(chart, attr)))
                break

    all_aspect_objs, p_lines = [], []
    house_name_map = {
        "First_House": 1, "Second_House": 2, "Third_House": 3, "Fourth_House": 4,
        "Fifth_House": 5, "Sixth_House": 6, "Seventh_House": 7, "Eighth_House": 8,
        "Ninth_House": 9, "Tenth_House": 10, "Eleventh_House": 11, "Twelfth_House": 12
    }

    houses_list = [
        chart.first_house, chart.second_house, chart.third_house, chart.fourth_house,
        chart.fifth_house, chart.sixth_house, chart.seventh_house, chart.eighth_house,
        chart.ninth_house, chart.tenth_house, chart.eleventh_house, chart.twelfth_house
    ] if not is_unknown_time else []

    house_cusp_abs = []
    if not is_unknown_time:
        for h in houses_list:
            s_norm = SIGN_NORM_MAP.get(str(h.sign), "Aries")
            s_idx = list(SIGN_DATA.keys()).index(s_norm) if s_norm in SIGN_DATA else 0
            house_cusp_abs.append(s_idx * 30 + h.position)

    major_bodies = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}

    for key, p in bodies_meta:
        sign = p.get('sign', 'Aries') if isinstance(p, dict) else getattr(p, 'sign', 'Aries')
        pos = p.get('position', 0.0) if isinstance(p, dict) else getattr(p, 'position', 0.0)
        h_raw = p.get('house', 'First_House') if isinstance(p, dict) else getattr(p, 'house', 'First_House')

        h_num = house_name_map.get(str(h_raw), 1)
        norm_sign = SIGN_NORM_MAP.get(str(sign), "Aries")
        s_idx = list(SIGN_DATA.keys()).index(norm_sign) if norm_sign in SIGN_DATA else 0
        abs_p_pos = s_idx * 30 + pos
        all_aspect_objs.append({"key": key, "abs_pos": abs_p_pos})
        
        p_name, s_name = get_p_name(key), get_s_name(sign)
        formatted_pos = format_deg_min(pos)
        
        colored_sign = apply_dignity_color(p_name, s_name)
        
        if is_unknown_time:
            base_str = f"**{p_name}** : {colored_sign} `({formatted_pos})`"
        else:
            base_h_label = format_house_name(h_num)
            rule_str = ""
            if key in major_bodies:
                next_idx = (h_num % 12)
                cusp_next = house_cusp_abs[next_idx]
                dist = (cusp_next - abs_p_pos) % 360
                if 0.0 <= dist <= 5.0:
                    eff_h = next_idx + 1
                    eff_label = format_house_name(eff_h)
                    rule_str = f" (5-degree rule applied ➡️ {eff_label})"
            
            if rule_str:
                base_str = f"**{p_name}** : {colored_sign} ({base_h_label}) `({formatted_pos})`<br>&nbsp;&nbsp;&nbsp;&nbsp;↳{rule_str.strip()}"
            else:
                base_str = f"**{p_name}** : {colored_sign} ({base_h_label}) `({formatted_pos})`"

        p_lines.append(base_str)

    angles_list, h_lines = [], []
    ruler_list = []
    ruler_list_with_5deg = []
    
    if not is_unknown_time:
        asc_s = get_s_name(chart.first_house.sign)
        mc_s = get_s_name(chart.tenth_house.sign)
        asc_lbl = "ASC (Ascendant)"
        mc_lbl = "MC (Midheaven)"
        
        asc_pos_str = format_deg_min(chart.first_house.position)
        mc_pos_str = format_deg_min(chart.tenth_house.position)
        
        angles_list = [
            f"**{asc_lbl}** : {asc_s} `({asc_pos_str})`",
            f"**{mc_lbl}** : {mc_s} `({mc_pos_str})`"
        ]
        
        asc_abs_pos = 0
        for h_idx, h in enumerate(houses_list):
            if h_idx == 0:
                s_norm = SIGN_NORM_MAP.get(str(h.sign), "Aries")
                s_idx_asc = list(SIGN_DATA.keys()).index(s_norm) if s_norm in SIGN_DATA else 0
                asc_abs_pos = s_idx_asc * 30 + h.position
            if h_idx == 9:
                s_norm = SIGN_NORM_MAP.get(str(h.sign), "Aries")
                s_idx_mc = list(SIGN_DATA.keys()).index(s_norm) if s_norm in SIGN_DATA else 0
                mc_abs_pos = s_idx_mc * 30 + h.position

        for item in all_aspect_objs:
            if item["key"] == "ASC":
                item["abs_pos"] = asc_abs_pos
            elif item["key"] == "MC":
                item["abs_pos"] = mc_abs_pos

        for i, h in enumerate(houses_list, 1):
            h_pos_str = format_deg_min(h.position)
            h_lines.append(f"**{format_house_name(i)}** : {get_s_name(h.sign)} `({h_pos_str})`")
        
        ruler_list = get_house_ruler_chains(houses_list, bodies_meta, house_name_map, use_5_deg_rule=False)
        ruler_list_with_5deg = get_house_ruler_chains(houses_list, bodies_meta, house_name_map, use_5_deg_rule=True, house_cusp_abs=house_cusp_abs)
    else:
        h_lines.append("*(Houses excluded due to unknown birth time)*")

    time_note = "(Assumed 12:00)" if is_unknown_time else ""
    date_str = f"{year}-{month:02d}-{day:02d} {calc_h:02d}:{calc_m:02d} {time_note}"
    
    lat_str = to_dms(chart.lat, is_lat=True)
    lng_str = to_dms(chart.lng, is_lat=False)
    loc_str = f"[{city_display_name}] [{lat_str}, {lng_str} (Decimal: {chart.lat:.4f}, {chart.lng:.4f})]"

    midpoints_data = calculate_midpoints(all_aspect_objs, chart_angles=None)

    return {
        "error": None, "date_str": date_str, "loc_str": loc_str,
        "angles": angles_list, "bodies": p_lines, "houses": h_lines,
        "house_rulers": ruler_list,
        "house_rulers_with_5deg": ruler_list_with_5deg,
        "midpoints": midpoints_data,
        "aspects": calculate_aspects(all_aspect_objs, view_type),
        "patterns": detect_patterns(all_aspect_objs)
    }
