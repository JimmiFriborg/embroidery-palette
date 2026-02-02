# InkStitch Microservice

Docker microservice for generating embroidery PES files from images using the proper pipeline:

1. **Pillow** — image preprocessing (resize, format conversion, alpha handling)
2. **Potrace** — bitmap → SVG vector tracing (per color region)
3. **Ink/Stitch** — SVG with stitch parameters → PES (proper fill stitches, underlay, etc.)
4. **pyembroidery** — format conversion/resizing (PES↔DST↔VP3, etc.)

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/image-to-pes` | Full pipeline: image → quantize → vectorize → stitch → PES |
| POST | `/svg-to-pes` | SVG with inkstitch attributes → PES (skip image processing) |
| POST | `/resize-or-convert` | pyembroidery: resize/convert existing embroidery files |

## Deployment (Unraid Compose Manager)

```bash
# Copy this folder to Tower
scp -r inkstitch-service/ root@192.168.30.100:/boot/config/plugins/compose.manager/projects/stitch-inkstitch/

# Or create manually
mkdir -p /boot/config/plugins/compose.manager/projects/stitch-inkstitch
# Copy Dockerfile, docker-compose.yml, and app/ folder

# Build and start
cd /boot/config/plugins/compose.manager/projects/stitch-inkstitch
docker compose up -d --build
```

Service will be available at: `http://192.168.30.100:5021`

## Usage

### Image to PES
```bash
curl -X POST http://192.168.30.100:5021/image-to-pes \
  -F "file=@design.png" \
  -F "hoop_size=100x100" \
  -F "quality=balanced" \
  -F 'thread_colors=["#FF0000","#00FF00","#0000FF"]' \
  -o design.pes
```

### SVG to PES (with inkstitch attributes)
```bash
curl -X POST http://192.168.30.100:5021/svg-to-pes \
  -F "file=@design.svg" \
  -o design.pes
```

### Resize/Convert
```bash
curl -X POST http://192.168.30.100:5021/resize-or-convert \
  -F "file=@design.pes" \
  -F "target_format=dst" \
  -F "scale=0.8" \
  -o design.dst
```

## Quality Presets

| Preset | Row Spacing | Max Stitch | Underlay | Best For |
|--------|------------|------------|----------|----------|
| fast | 0.35mm | 3.5mm | No | Quick tests |
| balanced | 0.25mm | 3.0mm | Yes | PP1 recommended |
| quality | 0.20mm | 2.5mm | Yes (2-layer) | Show pieces |

## Architecture

```
[Frontend] → [Appwrite Function] → [InkStitch API :5021]
                                         ├── Pillow (resize/preprocess)
                                         ├── potrace (bitmap → SVG paths)
                                         ├── Ink/Stitch CLI (SVG → PES)
                                         └── pyembroidery (convert/resize)
```
