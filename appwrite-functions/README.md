# StitchFlow Appwrite Functions

These Python functions handle image processing and PES file generation for the StitchFlow embroidery app.

## Functions

### 1. `process-image`
Processes uploaded images for embroidery conversion:
- Background removal using edge detection
- Color quantization using K-means clustering in LAB color space
- Resizing for hoop dimensions

### 2. `generate-pes`
Generates Brother PES embroidery files:
- Converts processed images to stitch patterns
- Uses pyembroidery library for PES format
- Generates stitch preview images

---

## Deployment Instructions

### Prerequisites
1. Appwrite CLI installed: `npm install -g appwrite-cli`
2. Login to your Appwrite: `appwrite login`
3. Set your project: `appwrite client --projectId YOUR_PROJECT_ID`

### Step 1: Create Storage Buckets

In your Appwrite Console, create these storage buckets:
- `project_images` - For original and processed images
- `pes_files` - For generated .pes embroidery files  
- `stitch_previews` - For stitch preview images

### Step 2: Configure Database

Add these attributes to your `projects` collection:
- `userId` (string, required)
- `name` (string, required)
- `description` (string, optional)
- `originalImageId` (string, optional)
- `processedImageId` (string, optional)
- `pesFileId` (string, optional)
- `previewImageId` (string, optional)
- `hoopSize` (enum: '100x100', '70x70')
- `threadCount` (integer, min: 2, max: 15)
- `colorMappings` (string, optional - JSON array)
- `extractedColors` (string, optional - JSON array)
- `status` (enum: 'draft', 'processing', 'ready', 'exported')

### Step 3: Deploy Functions

```bash
# Deploy process-image function
cd appwrite-functions/process-image
appwrite functions create \
  --functionId "process-image" \
  --name "Process Image" \
  --runtime "python-3.11" \
  --execute "any"

appwrite functions createDeployment \
  --functionId "process-image" \
  --entrypoint "main.py" \
  --code "."

# Deploy generate-pes function
cd ../generate-pes
appwrite functions create \
  --functionId "generate-pes" \
  --name "Generate PES" \
  --runtime "python-3.11" \
  --execute "any"

appwrite functions createDeployment \
  --functionId "generate-pes" \
  --entrypoint "main.py" \
  --code "."
```

### Step 4: Set Environment Variables

In Appwrite Console → Functions → Settings, add:
- `APPWRITE_ENDPOINT` - Your Appwrite endpoint (e.g., `http://localhost/v1`)
- `APPWRITE_PROJECT_ID` - Your project ID
- `APPWRITE_API_KEY` - An API key with Database and Storage permissions

---

## API Usage

### Process Image

```javascript
// Call from frontend
const response = await fetch(`${APPWRITE_ENDPOINT}/functions/process-image/executions`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Appwrite-Project': PROJECT_ID,
    'X-Appwrite-Key': API_KEY,
  },
  body: JSON.stringify({
    data: JSON.stringify({
      projectId: 'your-project-id',
      imageId: 'uploaded-image-id',
      threadCount: 6,
      hoopSize: '100x100'
    })
  })
});
```

### Generate PES

```javascript
const response = await fetch(`${APPWRITE_ENDPOINT}/functions/generate-pes/executions`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Appwrite-Project': PROJECT_ID,
    'X-Appwrite-Key': API_KEY,
  },
  body: JSON.stringify({
    data: JSON.stringify({
      projectId: 'your-project-id',
      colorMappings: [
        { originalColor: '#FF0000', threadNumber: '202', threadName: 'Red', threadColor: '#FF0000' }
      ],
      hoopSize: '100x100'
    })
  })
});
```

---

## Troubleshooting

### OpenCV not available
If OpenCV fails to install, the function falls back to PIL-based processing. For full functionality, ensure `opencv-python-headless` is in requirements.txt.

### pyembroidery issues
The pyembroidery library is well-maintained but some PES features may vary. Test generated files with Brother PE-Design or similar software.

### Memory limits
For large images, consider setting function memory limits in Appwrite Console (512MB+ recommended).
