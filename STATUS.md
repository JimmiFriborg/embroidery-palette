# Embroidery Palette — Deployment Status
*Last updated: 2026-02-01 19:20*

## Phase A: Deploy Frontend ⏳
- [x] Created Appwrite site `embroidery-palette`
- [x] Set build env vars (VITE_APPWRITE_ENDPOINT, VITE_APPWRITE_PROJECT_ID)
- [x] Built and deployed dist (status: ready)
- [ ] **BLOCKED — needs Jimmi:** Domain rule in Appwrite Console
  - Site exists but `embroidery-palette.sites.friborg.uk` shows "rule_not_found"
  - Need to assign domain via Console → Sites → embroidery-palette → Custom Domains

## Phase B: Deploy Backend Functions ✅
- [x] Updated `process-image` to python-3.11, timeout 120s
- [x] Updated `generate-pes` to python-3.11, timeout 120s  
- [x] Env vars verified (APPWRITE_ENDPOINT, PROJECT_ID, API_KEY)
- [x] Replaced OpenCV with scikit-image (musl-compatible, builds in 40s vs 15min timeout)
- [x] **process-image deployed** — ready (43s build, 107MB)
- [x] **generate-pes deployed** — ready (35s build, 107MB)
- [x] Code pushed to GitHub

## Phase C: End-to-End Testing
- [ ] Test upload → process → color map → export (needs frontend domain)

## Phase D: PES Viewer
- [ ] In-browser PES display

## Phase E: ReSpira Integration (deferred)
