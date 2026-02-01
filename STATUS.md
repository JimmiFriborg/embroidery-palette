# Embroidery Palette — Deployment Status
*Last updated: 2026-02-01 18:35*

## Phase A: Deploy Frontend ⏳
- [x] Created Appwrite site `embroidery-palette` (ID: embroidery-palette)
- [x] Set build env vars (VITE_APPWRITE_ENDPOINT, VITE_APPWRITE_PROJECT_ID)
- [x] Built and deployed dist (status: ready, deployment: 697f8280941e2b8f6c1b)
- [ ] **BLOCKED — needs Jimmi:** Assign domain in Appwrite Console
  - Go to Console → Project → Sites → `embroidery-palette` → Custom Domains
  - Add `embroidery-palette.sites.friborg.uk` (or `stitch.friborg.uk` if switching)
  - API key lacks `rules.write` scope for proxy rule creation

## Phase B: Deploy Backend Functions 🔄
- [x] Updated `process-image` to python-3.11, timeout 120s
- [x] Updated `generate-pes` to python-3.11, timeout 120s
- [x] Verified env vars set (APPWRITE_ENDPOINT, PROJECT_ID, API_KEY)
- [x] Packaged functions with shared lib/ modules
- [ ] **IN PROGRESS:** process-image building (OpenCV compiling from source ~10-20min)
  - Deployment: 697f8e0fbe1e55938f8c
- [ ] **QUEUED:** generate-pes waiting for build slot
  - Deployment: 697f8e151be7c4bd87eb

## Phase C: End-to-End Testing
- [ ] Test upload → process → color map → export
- [ ] Validate PES output with pyembroidery

## Phase D: PES Viewer
- [ ] In-browser PES display (canvas/SVG stitch rendering)
- [ ] Import existing .pes files

## Phase E: ReSpira Integration (Future - after proven export)
- [ ] Study BLE protocol from jhbruhn/respira
- [ ] WebBluetooth integration
