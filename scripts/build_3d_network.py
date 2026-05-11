import json
import math
import os
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import networkx as nx
import numpy as np
import polars as pl


Path("outputs/ms3").mkdir(parents=True, exist_ok=True)
max_nodes = int(os.environ.get("MS3_GRAPH_NODES", "180") or "180")
max_edges = int(os.environ.get("MS3_GRAPH_EDGES", "900") or "900")
layout_seed = int(os.environ.get("MS3_GRAPH_SEED", "11") or "11")

centrality = pl.read_csv("outputs/ms3/ms3_network_centrality_filtered.csv")
centrality_by_id = {row["person_id"]: row for row in centrality.iter_rows(named=True)}

email_ids = pl.read_parquet("data/ms3_clean_corpus.parquet", columns=["email_id"])
bridge = (
    pl.read_parquet("data/bridge_email_people.parquet", columns=["email_id", "person_id", "person_name"])
    .join(email_ids, on="email_id", how="semi")
    .with_columns(pl.col("person_name").fill_null("").str.to_lowercase().alias("person_name_key"))
    .filter(
        pl.col("person_id").is_not_null()
        & pl.col("person_name").is_not_null()
        & pl.col("person_id").is_in(["unknown", "redacted"]).not_()
        & pl.col("person_name_key").str.contains(r"unknown|redacted|\[redacted\]|█").not_()
    )
    .select("email_id", "person_id", "person_name")
    .unique()
)

name_counts = (
    bridge.group_by("person_id", "person_name")
    .len()
    .sort(["person_id", "len"], descending=[False, True])
    .unique(subset=["person_id"], keep="first")
)
name_by_id = dict(name_counts.select("person_id", "person_name").iter_rows())
edge_counts = Counter()
node_document_counts = Counter()
skipped_crowded = 0

for _, group in bridge.group_by("email_id"):
    people_in_email = sorted(group["person_id"].drop_nulls().unique().to_list())
    if len(people_in_email) < 2:
        continue
    if len(people_in_email) > 25:
        skipped_crowded += 1
        continue
    for person_id in people_in_email:
        node_document_counts[person_id] += 1
    for left, right in combinations(people_in_email, 2):
        edge_counts[(left, right)] += 1

full_graph = nx.Graph()
for (left, right), weight in edge_counts.items():
    if weight < 2:
        continue
    full_graph.add_edge(left, right, weight=float(weight))
    full_graph.nodes[left]["name"] = name_by_id.get(left, left)
    full_graph.nodes[right]["name"] = name_by_id.get(right, right)

for person_id, documents in node_document_counts.items():
    if person_id not in full_graph:
        continue
    full_graph.nodes[person_id]["documents"] = documents

epstein_id = "jeffrey-epstein"
if epstein_id in full_graph:
    full_distances = nx.single_source_shortest_path_length(full_graph, epstein_id)
else:
    full_distances = {}

weighted_degree = dict(full_graph.degree(weight="weight"))
degree = dict(full_graph.degree())
shells = defaultdict(list)
for person_id, distance in full_distances.items():
    shells[min(distance, 4)].append(person_id)

selected_ids = {epstein_id} if epstein_id in full_graph else set()
remaining_slots = max(0, max_nodes - len(selected_ids))
shell_limits = {1: 70, 2: 55, 3: 35, 4: 20}
for distance in [1, 2, 3, 4]:
    candidates = sorted(
        shells.get(distance, []),
        key=lambda person_id: (
            -weighted_degree.get(person_id, 0),
            -degree.get(person_id, 0),
            name_by_id.get(person_id, person_id),
        ),
    )
    take = min(shell_limits[distance], remaining_slots, len(candidates))
    selected_ids.update(candidates[:take])
    remaining_slots -= take

selected_edge_rows = []
for left, right, data in full_graph.edges(data=True):
    if left in selected_ids and right in selected_ids:
        selected_edge_rows.append((left, right, float(data["weight"])))
selected_edge_rows = sorted(selected_edge_rows, key=lambda row: row[2], reverse=True)[:max_edges]

graph = nx.Graph()
for person_id in selected_ids:
    if person_id not in full_graph:
        continue
    centrality_row = centrality_by_id.get(person_id, {})
    graph.add_node(
        person_id,
        name=full_graph.nodes[person_id].get("name", name_by_id.get(person_id, person_id)),
        degree=int(degree.get(person_id, 0)),
        weighted_degree=float(weighted_degree.get(person_id, 0)),
        betweenness=float(centrality_row.get("betweenness", 0) or 0),
    )

for left, right, weight in selected_edge_rows:
    if left in graph and right in graph:
        graph.add_edge(left, right, weight=weight)

betweenness_values = [graph.nodes[node]["betweenness"] for node in graph.nodes]
edge_weights = [data["weight"] for _, _, data in graph.edges(data=True)]
max_betweenness = max(betweenness_values) if betweenness_values else 1
max_edge_weight = max(edge_weights) if edge_weights else 1
epstein_id = "jeffrey-epstein"
epstein_distances = {node_id: full_distances.get(node_id, 4) for node_id in graph.nodes}
shell_radii = {0: 0, 1: 105, 2: 245, 3: 405, 4: 580}
distance_colors = {
    0: "#f4b860",
    1: "#64c7b2",
    2: "#5aa7e8",
    3: "#9b7ee8",
}


def distance_color(distance):
    return distance_colors.get(distance, "#d76f9a")


def distance_label(distance):
    if distance == 0:
        return "Epstein"
    if distance == 1:
        return "1 step from Epstein"
    if distance == 2:
        return "2 steps from Epstein"
    if distance == 3:
        return "3 steps from Epstein"
    return "4+ steps from Epstein"


def radius_for_distance(distance):
    if distance == 0:
        return 18
    if distance == 1:
        return 9
    if distance == 2:
        return 6
    if distance == 3:
        return 4.4
    return 3.3


def shell_point(index, total, shell_radius, distance):
    if total == 1:
        return np.array([shell_radius, 0.0, 0.0])
    golden_angle = math.pi * (3 - math.sqrt(5))
    y = 1 - 2 * (index + 0.5) / total
    radial = math.sqrt(max(0.0, 1 - y * y))
    theta = index * golden_angle + distance * 0.73 + layout_seed * 0.01
    return np.array(
        [
            shell_radius * math.cos(theta) * radial,
            shell_radius * y,
            shell_radius * math.sin(theta) * radial,
        ]
    )


positions = {}
for distance in sorted(set(epstein_distances.values()) | {4}):
    node_ids = [
        node_id
        for node_id in graph.nodes
        if min(epstein_distances.get(node_id, 4), 4) == min(distance, 4)
    ]
    node_ids = sorted(
        node_ids,
        key=lambda node_id: (
            -graph.nodes[node_id]["betweenness"],
            -graph.nodes[node_id]["weighted_degree"],
            graph.nodes[node_id]["name"],
        ),
    )
    shell_radius = shell_radii.get(min(distance, 4), shell_radii[4])
    for index, node_id in enumerate(node_ids):
        positions[node_id] = shell_point(index, len(node_ids), shell_radius, min(distance, 4))

nodes = []
for node_id in graph.nodes:
    data = graph.nodes[node_id]
    position = positions[node_id]
    betweenness_ratio = data["betweenness"] / max_betweenness if max_betweenness else 0
    distance = epstein_distances.get(node_id, 4)
    nodes.append(
        {
            "id": node_id,
            "name": data["name"],
            "degree": data["degree"],
            "weighted_degree": round(data["weighted_degree"], 3),
            "betweenness": round(data["betweenness"], 6),
            "epstein_distance": distance,
            "distance_label": distance_label(distance),
            "color": distance_color(distance),
            "x": round(float(position[0]), 4),
            "y": round(float(position[1]), 4),
            "z": round(float(position[2]), 4),
            "radius": radius_for_distance(distance),
            "broker_score": round(betweenness_ratio, 5),
        }
    )

links = []
for source, target, data in graph.edges(data=True):
    links.append(
        {
            "source": source,
            "target": target,
            "weight": round(data["weight"], 3),
            "strength": round(math.log1p(data["weight"]) / math.log1p(max_edge_weight), 5),
        }
    )

graph_data = {
    "nodes": nodes,
    "links": links,
    "metadata": {
        "nodes": len(nodes),
        "links": len(links),
        "full_filtered_nodes": full_graph.number_of_nodes(),
        "full_filtered_edges": full_graph.number_of_edges(),
        "skipped_crowded_emails": skipped_crowded,
        "source": "data/ms3_clean_corpus.parquet and data/bridge_email_people.parquet",
        "node_selection": f"distance shell sample around Epstein, capped at {max_nodes} nodes",
        "unknown_redacted_removed": True,
        "size_encoding": "largest bubble is Epstein; node size decreases with shortest-path distance from Epstein",
        "color_encoding": "node color shows shortest-path distance from Epstein",
        "layout": "radial 3D shells by shortest-path distance from Epstein",
        "shell_radii": {str(key): value for key, value in shell_radii.items()},
    },
}

html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Epstein Email Network - 3D Graph</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Arial, Helvetica, sans-serif;
      background: #f6f3ee;
      color: #17202a;
    }}
    html, body {{
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: #f6f3ee;
    }}
    #scene {{
      position: fixed;
      inset: 0;
      width: 100vw;
      height: 100vh;
      display: block;
    }}
    .panel {{
      position: fixed;
      left: 18px;
      top: 18px;
      width: min(360px, calc(100vw - 36px));
      background: rgba(255, 255, 255, 0.84);
      border: 1px solid rgba(23, 32, 42, 0.16);
      border-radius: 8px;
      backdrop-filter: blur(10px);
      padding: 14px 16px;
      box-sizing: border-box;
      box-shadow: 0 18px 50px rgba(54, 64, 74, 0.18);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 18px;
      line-height: 1.2;
      font-weight: 700;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin: 12px 0;
    }}
    .stat {{
      border: 1px solid rgba(23, 32, 42, 0.14);
      border-radius: 6px;
      padding: 8px;
      background: rgba(23, 32, 42, 0.04);
    }}
    .stat b {{
      display: block;
      font-size: 16px;
    }}
    .stat span {{
      display: block;
      margin-top: 2px;
      color: #5a6671;
      font-size: 11px;
    }}
    .controls {{
      display: grid;
      gap: 10px;
      margin-top: 10px;
    }}
    .legend {{
      display: grid;
      gap: 7px;
      margin-top: 12px;
      padding-top: 10px;
      border-top: 1px solid rgba(23, 32, 42, 0.12);
      color: #26313b;
      font-size: 12px;
    }}
    .legend-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }}
    .swatch {{
      width: 11px;
      height: 11px;
      border-radius: 999px;
      border: 1px solid rgba(23, 32, 42, 0.3);
      flex: 0 0 auto;
    }}
    label {{
      display: grid;
      grid-template-columns: 120px 1fr 42px;
      align-items: center;
      gap: 8px;
      color: #26313b;
      font-size: 12px;
    }}
    input[type="range"] {{
      width: 100%;
      min-width: 0;
      accent-color: #56b6c2;
    }}
    button {{
      border: 1px solid rgba(23, 32, 42, 0.2);
      border-radius: 6px;
      background: rgba(86, 182, 194, 0.18);
      color: #17202a;
      height: 32px;
      cursor: pointer;
    }}
    button:hover {{
      background: rgba(86, 182, 194, 0.28);
    }}
    .hint {{
      margin: 10px 0 0;
      color: #4f5c66;
      font-size: 12px;
      line-height: 1.4;
    }}
    #tooltip {{
      position: fixed;
      left: 0;
      top: 0;
      transform: translate(-999px, -999px);
      pointer-events: none;
      max-width: 280px;
      padding: 9px 10px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.94);
      border: 1px solid rgba(23, 32, 42, 0.18);
      color: #17202a;
      font-size: 12px;
      line-height: 1.35;
      box-shadow: 0 14px 32px rgba(54, 64, 74, 0.22);
    }}
    #tooltip b {{
      display: block;
      font-size: 13px;
      margin-bottom: 4px;
    }}
    @media (max-width: 640px) {{
      .panel {{
        left: 0;
        right: 0;
        top: 0;
        width: 100vw;
        border-left: 0;
        border-right: 0;
        border-radius: 0;
        padding: 12px;
        overflow: hidden;
      }}
      h1 {{
        font-size: 16px;
      }}
      label {{
        grid-template-columns: 86px minmax(0, 1fr) 30px;
        gap: 6px;
      }}
      .stats {{
        gap: 6px;
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .stat {{
        min-width: 0;
        padding: 7px;
      }}
      .hint {{
        display: none;
      }}
    }}
  </style>
</head>
<body>
  <canvas id="scene"></canvas>
  <section class="panel">
    <h1>Epstein Email Network</h1>
    <div class="stats">
      <div class="stat"><b id="node-count">0</b><span>nodes</span></div>
      <div class="stat"><b id="link-count">0</b><span>edges</span></div>
      <div class="stat"><b>3D</b><span>orbit view</span></div>
    </div>
    <div class="controls">
      <label>Node size <input id="node-scale" type="range" min="60" max="180" value="100"><span id="node-scale-value">100</span></label>
      <label>Edge opacity <input id="edge-opacity" type="range" min="5" max="75" value="42"><span id="edge-opacity-value">42</span></label>
      <label>Label size <input id="label-size" type="range" min="55" max="170" value="126"><span id="label-size-value">126</span></label>
      <button id="reset-view" type="button">Reset view</button>
    </div>
    <div class="legend">
      <div class="legend-row"><span class="swatch" style="background:#f4b860"></span><span>Epstein, largest node</span></div>
      <div class="legend-row"><span class="swatch" style="background:#64c7b2"></span><span>1 network step from Epstein</span></div>
      <div class="legend-row"><span class="swatch" style="background:#5aa7e8"></span><span>2 network steps from Epstein</span></div>
      <div class="legend-row"><span class="swatch" style="background:#9b7ee8"></span><span>3 network steps from Epstein</span></div>
      <div class="legend-row"><span class="swatch" style="background:#d76f9a"></span><span>4+ network steps from Epstein</span></div>
    </div>
    <p class="hint">Drag to rotate. Scroll to zoom. Right-drag to pan. Shells, colors, and node size show shortest-path distance from Epstein.</p>
  </section>
  <div id="tooltip"></div>

  <script type="importmap">
    {{
      "imports": {{
        "three": "./vendor/three.module.js"
      }}
    }}
  </script>
  <script type="application/json" id="graph-data">{json.dumps(graph_data)}</script>
  <script type="module">
    import * as THREE from "three";
    import {{ OrbitControls }} from "./vendor/OrbitControls.js";

    const data = JSON.parse(document.getElementById("graph-data").textContent);
    const canvas = document.getElementById("scene");
    const tooltip = document.getElementById("tooltip");
    const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true, alpha: false }});
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf6f3ee);
    scene.fog = new THREE.FogExp2(0xf6f3ee, 0.0011);

    const camera = new THREE.PerspectiveCamera(48, 1, 0.1, 2400);
    camera.position.set(0, 105, 560);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.rotateSpeed = 0.52;
    controls.zoomSpeed = 0.75;
    controls.panSpeed = 0.55;

    scene.add(new THREE.AmbientLight(0xffffff, 0.92));
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
    keyLight.position.set(60, 80, 100);
    scene.add(keyLight);
    const rimLight = new THREE.DirectionalLight(0x56b6c2, 0.65);
    rimLight.position.set(-80, -20, -50);
    scene.add(rimLight);

    const group = new THREE.Group();
    scene.add(group);

    const nodeById = new Map(data.nodes.map((node) => [node.id, node]));
    const nodeMeshes = [];
    const labelSprites = [];
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let hovered = null;
    let nodeScale = 1;
    let edgeOpacity = 0.42;
    let labelScale = 1.26;

    const edgeMaterial = new THREE.LineBasicMaterial({{
      color: 0x5f6f7a,
      transparent: true,
      opacity: edgeOpacity,
      depthWrite: false
    }});
    const edgeGeometry = new THREE.BufferGeometry();
    const edgePositions = [];
    for (const link of data.links) {{
      const source = nodeById.get(link.source);
      const target = nodeById.get(link.target);
      if (!source || !target) continue;
      edgePositions.push(source.x, source.y, source.z, target.x, target.y, target.z);
    }}
    edgeGeometry.setAttribute("position", new THREE.Float32BufferAttribute(edgePositions, 3));
    const edgeLines = new THREE.LineSegments(edgeGeometry, edgeMaterial);
    group.add(edgeLines);

    const shellColors = {{
      "1": 0x64c7b2,
      "2": 0x5aa7e8,
      "3": 0x9b7ee8,
      "4": 0xd76f9a
    }};
    for (const [distance, radius] of Object.entries(data.metadata.shell_radii)) {{
      if (distance === "0") continue;
      const shellGeometry = new THREE.SphereGeometry(Number(radius), 48, 24);
      const shellMaterial = new THREE.MeshBasicMaterial({{
        color: shellColors[distance] || shellColors["4"],
        transparent: true,
        opacity: 0.085,
        wireframe: true,
        depthWrite: false
      }});
      const shell = new THREE.Mesh(shellGeometry, shellMaterial);
      group.add(shell);
    }}

    function nodeColor(node) {{
      return new THREE.Color(node.color);
    }}

    function makeLabel(text) {{
      const labelCanvas = document.createElement("canvas");
      const context = labelCanvas.getContext("2d");
      const size = 72;
      context.font = "700 30px Arial";
      const metrics = context.measureText(text);
      labelCanvas.width = Math.min(520, Math.max(170, metrics.width + 34));
      labelCanvas.height = size;
      context.font = "700 30px Arial";
      context.fillStyle = "rgba(255, 255, 255, 0.86)";
      context.fillRect(0, 9, labelCanvas.width, 48);
      context.fillStyle = "#17202a";
      context.fillText(text, 17, 44);
      const texture = new THREE.CanvasTexture(labelCanvas);
      const material = new THREE.SpriteMaterial({{ map: texture, transparent: true, depthWrite: false, depthTest: false }});
      const sprite = new THREE.Sprite(material);
      sprite.userData.baseScale = {{ x: labelCanvas.width / 19, y: labelCanvas.height / 19 }};
      sprite.scale.set(sprite.userData.baseScale.x * labelScale, sprite.userData.baseScale.y * labelScale, 1);
      return sprite;
    }}

    for (const node of data.nodes) {{
      const geometry = new THREE.SphereGeometry(node.radius, 24, 16);
      const material = new THREE.MeshStandardMaterial({{
        color: nodeColor(node),
        roughness: 0.48,
        metalness: 0.18,
        emissive: nodeColor(node),
        emissiveIntensity: 0.08
      }});
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(node.x, node.y, node.z);
      mesh.userData = node;
      nodeMeshes.push(mesh);
      group.add(mesh);

      const label = makeLabel(node.name);
      label.position.set(node.x, node.y + node.radius + 4.5, node.z);
      label.userData = {{ ...node, baseScale: label.userData.baseScale }};
      labelSprites.push(label);
      group.add(label);
    }}

    function resize() {{
      const width = window.innerWidth;
      const height = window.innerHeight;
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }}

    function updateScales() {{
      for (const mesh of nodeMeshes) {{
        const radius = mesh.userData.radius * nodeScale;
        mesh.scale.setScalar(radius / mesh.userData.radius);
      }}
      edgeMaterial.opacity = edgeOpacity;
      for (const sprite of labelSprites) {{
        sprite.visible = true;
        sprite.scale.set(sprite.userData.baseScale.x * labelScale, sprite.userData.baseScale.y * labelScale, 1);
      }}
    }}

    function showTooltip(event, node) {{
      tooltip.innerHTML = `<b>${{node.name}}</b>${{node.distance_label}}<br>Degree: ${{node.degree.toLocaleString()}}<br>Weighted degree: ${{Math.round(node.weighted_degree).toLocaleString()}}<br>Betweenness: ${{node.betweenness.toFixed(4)}}`;
      tooltip.style.transform = `translate(${{event.clientX + 14}}px, ${{event.clientY + 14}}px)`;
    }}

    function hideTooltip() {{
      tooltip.style.transform = "translate(-999px, -999px)";
    }}

    function onPointerMove(event) {{
      pointer.x = (event.clientX / window.innerWidth) * 2 - 1;
      pointer.y = -(event.clientY / window.innerHeight) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObjects(nodeMeshes, false);
      if (hits.length) {{
        const next = hits[0].object;
        if (hovered && hovered !== next) hovered.material.emissiveIntensity = 0.08;
        hovered = next;
        hovered.material.emissiveIntensity = 0.35;
        showTooltip(event, hovered.userData);
      }} else {{
        if (hovered) hovered.material.emissiveIntensity = 0.08;
        hovered = null;
        hideTooltip();
      }}
    }}

    document.getElementById("node-count").textContent = data.metadata.nodes.toLocaleString();
    document.getElementById("link-count").textContent = data.metadata.links.toLocaleString();

    for (const id of ["node-scale", "edge-opacity", "label-size"]) {{
      const input = document.getElementById(id);
      const output = document.getElementById(`${{id}}-value`);
      input.addEventListener("input", () => {{
        output.textContent = input.value;
        nodeScale = Number(document.getElementById("node-scale").value) / 100;
        edgeOpacity = Number(document.getElementById("edge-opacity").value) / 100;
        labelScale = Number(document.getElementById("label-size").value) / 100;
        updateScales();
      }});
    }}

    document.getElementById("reset-view").addEventListener("click", () => {{
      camera.position.set(0, 105, 560);
      controls.target.set(0, 0, 0);
      controls.update();
    }});

    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onPointerMove);
    resize();
    updateScales();

    function animate() {{
      controls.update();
      renderer.render(scene, camera);
      requestAnimationFrame(animate);
    }}
    animate();
  </script>
</body>
</html>
"""

Path("outputs/ms3/network_3d.html").write_text(html)
print(f"wrote outputs/ms3/network_3d.html with {len(nodes)} nodes and {len(links)} links")
