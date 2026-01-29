

# StitchFlow - Embroidery SaaS for Brother PP1

## Vision
A mobile-first web app that replaces Brother Artspira, enabling users to convert images to embroidery-ready .pes files with intelligent color mapping and stitch simulation. Built with a craft-inspired, creative visual aesthetic.

---

## Core Features

### 1. User Authentication & Dashboard
- **Multi-user accounts** with Appwrite authentication
- **Personal project library** showing all saved embroidery projects
- Quick actions: New Project, Browse Templates, Recent Projects
- Warm, textured craft-inspired design with artsy color palette

### 2. Image Upload & Processing
**Mobile-optimized upload flow:**
- Camera capture or gallery selection
- Drag & drop for desktop users
- Select number of thread colors (2-15 range with recommendation)
- Choose hoop size: 100x100mm (4"x4") or 70x70mm

**Image Processing Pipeline (via Appwrite Python Function calling pyembroidery microservice):**
- Background removal using GrabCut or threshold detection
- Color quantization using K-means clustering in LAB color space
- Outline/edge detection for clean segment boundaries
- Automatic color simplification by merging similar colors

### 3. Project Editor View
**Three-panel layout (swipeable on mobile):**
- **Original Image** - Reference view with toggle for transparency preview
- **Processed Image** - Quantized colors with segment visualization
- **Thread Color Mapper** - Interactive color assignment panel

**Thread Color Mapping:**
- Each detected color shown as a swatch
- Tap to open Brother thread picker
- Search by thread number or color name
- Real-time preview updates as colors change
- Save custom color presets

### 4. Stitch Preview & Export
**Simulation View:**
- Rendered stitch pattern visualization generated from .pes data
- Toggle between realistic thread view and stitch path view
- Zoom and pan controls
- Estimated stitch count and time display

**Export Flow:**
- Download .pes file (opens in new tab)
- Save to project for future editing
- Share link option for collaboration

---

## Technical Architecture

### Frontend (Lovable/React)
- React with TypeScript
- Tailwind CSS with craft-inspired custom theme
- Mobile-first responsive design
- Canvas-based image preview and manipulation

### Backend (Appwrite - Your Local Instance)
- **Authentication**: Appwrite Auth for user accounts
- **Database**: Appwrite Database for projects, user preferences
- **Storage**: Appwrite Storage for images and .pes files
- **Functions**: Appwrite Python Functions for:
  - Image processing (color quantization, background removal)
  - pyembroidery integration for .pes generation
  - Stitch preview rendering (output as PNG/SVG)

### Processing Approach
Based on research, the recommended approach is:
1. **Python Appwrite Function** handles all image processing with OpenCV
2. **pyembroidery library** generates .pes files - it's mature, well-maintained, and the standard for open-source embroidery file handling
3. **Stitch preview** rendered via pyembroidery's PNG export capability

---

## User Flow

```
Home → Upload Image → Set Thread Count & Hoop Size
                ↓
        Processing Screen (loading with progress)
                ↓
        Project Editor (Original | Processed | Colors)
                ↓
        Map Thread Colors (Brother thread palette)
                ↓
        Preview Stitches → Export .pes → Download
```

---

## PP1-Specific Constraints (Enforced)
- Maximum embroidery area: 100x100mm or 70x70mm (user selects)
- Optimized stitch types for PP1's 400 SPM speed
- Brother thread color database integration

---

## Design Direction
- **Style**: Craft/creative with warm, inviting colors
- **Textures**: Subtle fabric/linen textures in backgrounds
- **Colors**: Warm earth tones (terracotta, sage, cream) with vibrant accent colors
- **Typography**: Friendly, rounded fonts
- **Mobile-first**: Large touch targets, swipe gestures, bottom navigation

---

## Implementation Phases

**Phase 1: Foundation**
- Appwrite integration setup
- User authentication flow
- Project database schema
- Basic dashboard UI

**Phase 2: Image Upload & Processing**
- Image upload component
- Appwrite function for color quantization
- Background removal processing
- Processed image display

**Phase 3: Thread Color Mapping**
- Brother thread color database
- Interactive color picker component
- Real-time preview updates

**Phase 4: PES Generation & Preview**
- pyembroidery integration in Appwrite function
- Stitch preview rendering
- Download functionality
- Export in new window

**Phase 5: Polish**
- Performance optimization
- Error handling improvements
- Mobile gesture refinements
- Onboarding flow

