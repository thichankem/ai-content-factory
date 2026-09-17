---
name: asset-hunter
description: Automated search and acquisition skill for public domain archival footage, vintage photographs, newspapers, and navigational route maps from Wikimedia Commons, Chronicling America, and National Archives.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# Asset Hunter Skill — Public Domain & Archival Media Acquisition

High-credibility documentary production demands authentic historical media to anchor synthetic AI footage. This skill searches and links public domain archival media directly to pipeline scenes.

## 1. Archival Search Endpoints

Search federated document and media providers:

```bash
# Search Wikimedia Commons for public domain archival photos
curl "http://127.0.0.1:8000/documents/search?q=Titanic+sinking&provider=wikimedia"

# Search Chronicling America for historic newspaper front pages
curl "http://127.0.0.1:8000/documents/search?q=San+Francisco+earthquake+1906&provider=chronicling-america"

# Search USGS for seismic epicenter and fault line data
curl "http://127.0.0.1:8000/documents/search?q=Sumatra+2004&provider=usgs"
```

## 2. Procedural Route & Infographic Generation

For disaster travel routes (nautical, flight, storm tracks):

```bash
# Generate high-contrast SVG route map
curl -X POST "http://127.0.0.1:8000/projects/{project_id}/graphics/map" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Hải trình định mệnh RMS Titanic",
    "map_type": "nautical",
    "points": [
      {"label": "Southampton", "x": 15.0, "y": 25.0, "timestamp": "10/04/1912"},
      {"label": "Cherbourg", "x": 22.0, "y": 35.0, "timestamp": "10/04/1912"},
      {"label": "Queenstown", "x": 12.0, "y": 18.0, "timestamp": "11/04/1912"},
      {"label": "Điểm va chạm băng trôi", "x": 68.0, "y": 55.0, "timestamp": "14/04 23:40", "note": "41°43′N 49°56′W"}
    ],
    "show_danger_zone": true,
    "danger_label": "Khu vực chìm tàu",
    "danger_x": 68.0,
    "danger_y": 55.0
  }'
```

```bash
# Generate comparative casualty or Richter infographic
curl -X POST "http://127.0.0.1:8000/projects/{project_id}/graphics/infographic" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "So sánh các thảm họa hàng hải chấn động",
    "subtitle": "Số thương vong sinh mạng",
    "chart_type": "bar",
    "labels": ["Titanic (1912)", "Lusitania (1915)", "Wilhelm Gustloff (1945)", "Doña Paz (1987)"],
    "values": [1517, 1198, 9400, 4386],
    "unit": "người"
  }'
```

## 3. Batch Asset Ingestion

Link acquired archival assets to specific scenes:
```bash
curl -X POST "http://127.0.0.1:8000/projects/{project_id}/external/batch-import" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "asset_type": "historical_photo",
        "scene_id": "scene-01",
        "url": "https://commons.wikimedia.org/wiki/File:Titanic_leaving_Southampton.jpg",
        "label": "Tàu Titanic rời cảng Southampton",
        "attribution": "Public Domain - Wikimedia Commons"
      }
    ]
  }'
```
