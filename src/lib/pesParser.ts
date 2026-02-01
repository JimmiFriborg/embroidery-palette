/**
 * PES File Parser for in-browser .pes file viewing
 * Parses Brother PES embroidery files and extracts stitch data.
 * 
 * PES format reference: https://edutechwiki.unige.ch/en/Embroidery_format_PES
 */

export interface PesThread {
  color: string; // hex
  name: string;
  catalogNumber: string;
}

export interface PesStitch {
  x: number;
  y: number;
  type: 'stitch' | 'move' | 'trim' | 'stop' | 'end';
}

export interface PesColorBlock {
  thread: PesThread;
  stitches: PesStitch[];
}

export interface PesPattern {
  name: string;
  width: number;   // in 0.1mm units
  height: number;
  colorBlocks: PesColorBlock[];
  bounds: { minX: number; minY: number; maxX: number; maxY: number };
  totalStitches: number;
  colorCount: number;
}

// Brother PES thread color table (standard palette)
const PES_THREAD_COLORS: [number, number, number, string][] = [
  [0, 0, 0, 'Unknown'],
  [14, 31, 124, 'Prussian Blue'],
  [10, 85, 163, 'Blue'],
  [48, 135, 119, 'Teal Green'],
  [75, 107, 175, 'Cornflower Blue'],
  [237, 23, 31, 'Red'],
  [209, 92, 0, 'Reddish Brown'],
  [145, 54, 151, 'Magenta'],
  [228, 154, 203, 'Light Lilac'],
  [145, 95, 172, 'Lilac'],
  [158, 214, 125, 'Mint Green'],
  [232, 169, 0, 'Deep Gold'],
  [254, 186, 53, 'Orange'],
  [255, 255, 0, 'Yellow'],
  [112, 188, 31, 'Lime Green'],
  [186, 152, 0, 'Brass'],
  [168, 168, 168, 'Silver'],
  [125, 111, 0, 'Russet Brown'],
  [255, 255, 179, 'Cream Brown'],
  [79, 85, 86, 'Pewter'],
  [0, 0, 0, 'Black'],
  [11, 61, 145, 'Ultramarine'],
  [119, 1, 118, 'Royal Purple'],
  [41, 49, 51, 'Dark Gray'],
  [42, 19, 1, 'Dark Brown'],
  [246, 74, 138, 'Deep Rose'],
  [178, 118, 36, 'Light Brown'],
  [252, 187, 197, 'Salmon Pink'],
  [254, 55, 15, 'Vermilion'],
  [240, 240, 240, 'White'],
  [106, 28, 138, 'Violet'],
  [168, 221, 196, 'Seacrest'],
  [37, 132, 187, 'Sky Blue'],
  [254, 179, 67, 'Pumpkin'],
  [255, 243, 107, 'Cream Yellow'],
  [208, 166, 96, 'Khaki'],
  [209, 84, 0, 'Clay Brown'],
  [102, 186, 73, 'Leaf Green'],
  [19, 74, 70, 'Peacock Blue'],
  [135, 135, 135, 'Gray'],
  [216, 204, 198, 'Warm Gray'],
  [67, 86, 7, 'Dark Olive'],
  [253, 217, 222, 'Flesh Pink'],
  [249, 147, 188, 'Pink'],
  [0, 56, 34, 'Deep Green'],
  [178, 175, 212, 'Lavender'],
  [104, 106, 176, 'Wisteria Blue'],
  [239, 227, 185, 'Beige'],
  [247, 56, 102, 'Carmine'],
  [181, 75, 100, 'Amber Red'],
  [19, 43, 26, 'Olive Green'],
  [199, 1, 86, 'Dark Fuchsia'],
  [254, 158, 50, 'Tangerine'],
  [168, 222, 235, 'Light Blue'],
  [0, 103, 62, 'Emerald Green'],
  [78, 41, 144, 'Purple'],
  [47, 126, 32, 'Moss Green'],
  [255, 204, 204, 'Flesh Pink (lt)'],
  [255, 217, 17, 'Harvest Gold'],
  [9, 91, 166, 'Electric Blue'],
  [240, 249, 112, 'Lemon Yellow'],
  [227, 243, 91, 'Fresh Green'],
  [255, 153, 0, 'Applique Material'],
  [255, 240, 141, 'Applique Position'],
  [255, 200, 200, 'Applique'],
];

/**
 * Parse a PES file from an ArrayBuffer
 */
export function parsePes(buffer: ArrayBuffer): PesPattern | null {
  try {
    const view = new DataView(buffer);
    const bytes = new Uint8Array(buffer);
    
    // Check PES signature: "#PES" at offset 0
    const sig = String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]);
    if (sig !== '#PES') {
      console.error('Not a valid PES file');
      return null;
    }
    
    // PES version (4 bytes after signature)
    const version = String.fromCharCode(bytes[4], bytes[5], bytes[6], bytes[7]);
    
    // PEC offset at byte 8 (little-endian uint32)
    const pecOffset = view.getUint32(8, true);
    
    if (pecOffset === 0 || pecOffset >= buffer.byteLength) {
      console.error('Invalid PEC offset');
      return null;
    }
    
    // Parse PEC section
    return parsePecSection(bytes, view, pecOffset);
    
  } catch (e) {
    console.error('PES parse error:', e);
    return null;
  }
}

function parsePecSection(bytes: Uint8Array, view: DataView, pecOffset: number): PesPattern {
  let offset = pecOffset;
  
  // PEC label (starts with "LA:")
  const labelStart = offset + 3; // Skip "LA:"
  let name = '';
  for (let i = 0; i < 16; i++) {
    const ch = bytes[labelStart + i];
    if (ch === 0x20 || ch === 0x00) break;
    name += String.fromCharCode(ch);
  }
  
  // Skip to color count (offset + 48 from PEC start)
  offset = pecOffset + 48;
  const colorCount = bytes[offset] + 1;
  offset++;
  
  // Read color indices
  const colorIndices: number[] = [];
  for (let i = 0; i < colorCount; i++) {
    colorIndices.push(bytes[offset + i]);
  }
  
  // Skip to stitch data (PEC stitch data starts after header)
  // PEC header is 532 bytes from PEC start  
  offset = pecOffset + 532;
  
  // Parse stitch data
  const allStitches: PesStitch[] = [];
  let x = 0;
  let y = 0;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  
  while (offset < bytes.length - 1) {
    const b0 = bytes[offset];
    const b1 = bytes[offset + 1];
    
    // End of stitches
    if (b0 === 0xFF && b1 === 0x00) {
      allStitches.push({ x, y, type: 'end' });
      break;
    }
    
    // Color change
    if (b0 === 0xFE && b1 === 0xB0) {
      offset += 2;
      // Read color byte
      if (offset < bytes.length) {
        offset++; // Skip color byte
      }
      allStitches.push({ x, y, type: 'stop' });
      continue;
    }
    
    // Decode stitch coordinates
    let dx = 0, dy = 0;
    let stitchType: 'stitch' | 'move' | 'trim' = 'stitch';
    
    if (b0 & 0x80) {
      // 12-bit x coordinate
      if (b0 & 0x20) stitchType = 'trim';
      if (b0 & 0x10) stitchType = 'move';
      
      dx = ((b0 & 0x0F) << 8) | b1;
      if (dx & 0x800) dx -= 0x1000; // Sign extend
      offset += 2;
      
      if (offset >= bytes.length) break;
      const b2 = bytes[offset];
      
      if (b2 & 0x80) {
        const b3 = offset + 1 < bytes.length ? bytes[offset + 1] : 0;
        dy = ((b2 & 0x0F) << 8) | b3;
        if (dy & 0x800) dy -= 0x1000;
        offset += 2;
      } else {
        dy = b2;
        if (dy > 63) dy -= 128;
        offset += 1;
      }
    } else {
      // 7-bit coordinates
      dx = b0;
      if (dx > 63) dx -= 128;
      
      dy = b1;
      if (dy > 63) dy -= 128;
      
      offset += 2;
    }
    
    x += dx;
    y += dy;
    
    allStitches.push({ x, y, type: stitchType });
    
    if (stitchType === 'stitch') {
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);
    }
  }
  
  // Split stitches into color blocks
  const colorBlocks: PesColorBlock[] = [];
  let currentBlock: PesStitch[] = [];
  let colorIdx = 0;
  
  for (const stitch of allStitches) {
    if (stitch.type === 'stop') {
      if (currentBlock.length > 0) {
        const threadIdx = colorIdx < colorIndices.length ? colorIndices[colorIdx] : 0;
        colorBlocks.push({
          thread: getThread(threadIdx),
          stitches: currentBlock,
        });
        currentBlock = [];
        colorIdx++;
      }
      continue;
    }
    
    if (stitch.type === 'end') break;
    currentBlock.push(stitch);
  }
  
  // Don't forget the last block
  if (currentBlock.length > 0) {
    const threadIdx = colorIdx < colorIndices.length ? colorIndices[colorIdx] : 0;
    colorBlocks.push({
      thread: getThread(threadIdx),
      stitches: currentBlock,
    });
  }
  
  const totalStitches = allStitches.filter(s => s.type === 'stitch').length;
  
  return {
    name: name || 'Untitled',
    width: maxX - minX,
    height: maxY - minY,
    colorBlocks,
    bounds: { minX, minY, maxX, maxY },
    totalStitches,
    colorCount: colorBlocks.length,
  };
}

function getThread(index: number): PesThread {
  if (index >= 0 && index < PES_THREAD_COLORS.length) {
    const [r, g, b, name] = PES_THREAD_COLORS[index];
    return {
      color: `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`,
      name,
      catalogNumber: index.toString(),
    };
  }
  return { color: '#000000', name: 'Unknown', catalogNumber: '0' };
}

/**
 * Render a PES pattern to a canvas
 */
export function renderPesPattern(
  canvas: HTMLCanvasElement,
  pattern: PesPattern,
  options: {
    backgroundColor?: string;
    showGrid?: boolean;
    showJumps?: boolean;
    lineWidth?: number;
    padding?: number;
  } = {}
): void {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  
  const {
    backgroundColor = '#FFFFFF',
    showGrid = true,
    showJumps = false,
    lineWidth = 1.5,
    padding = 20,
  } = options;
  
  const { bounds } = pattern;
  const patternWidth = bounds.maxX - bounds.minX;
  const patternHeight = bounds.maxY - bounds.minY;
  
  if (patternWidth === 0 || patternHeight === 0) return;
  
  // Calculate scale to fit canvas
  const scaleX = (canvas.width - padding * 2) / patternWidth;
  const scaleY = (canvas.height - padding * 2) / patternHeight;
  const scale = Math.min(scaleX, scaleY);
  
  // Center offset
  const offsetX = padding + (canvas.width - padding * 2 - patternWidth * scale) / 2 - bounds.minX * scale;
  const offsetY = padding + (canvas.height - padding * 2 - patternHeight * scale) / 2 - bounds.minY * scale;
  
  // Clear canvas
  ctx.fillStyle = backgroundColor;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  
  // Draw grid (10mm squares)
  if (showGrid) {
    ctx.strokeStyle = '#f0f0f0';
    ctx.lineWidth = 0.5;
    const gridSize = 100 * scale; // 100 units = 10mm
    
    for (let x = 0; x < canvas.width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }
  }
  
  // Draw hoop outline (100x100mm = 1000x1000 units)
  ctx.strokeStyle = '#e0e0e0';
  ctx.lineWidth = 2;
  ctx.setLineDash([5, 5]);
  const hoopSize = 1000 * scale;
  const hoopX = (canvas.width - hoopSize) / 2;
  const hoopY = (canvas.height - hoopSize) / 2;
  ctx.strokeRect(hoopX, hoopY, hoopSize, hoopSize);
  ctx.setLineDash([]);
  
  // Draw stitches per color block
  for (const block of pattern.colorBlocks) {
    ctx.strokeStyle = block.thread.color;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    
    let isMoving = true;
    
    ctx.beginPath();
    
    for (const stitch of block.stitches) {
      const sx = stitch.x * scale + offsetX;
      const sy = stitch.y * scale + offsetY;
      
      if (stitch.type === 'move' || stitch.type === 'trim') {
        if (showJumps) {
          ctx.stroke();
          ctx.beginPath();
          ctx.setLineDash([2, 4]);
          ctx.strokeStyle = block.thread.color + '40';
          ctx.moveTo(sx, sy);
        } else {
          ctx.stroke();
          ctx.beginPath();
          ctx.moveTo(sx, sy);
        }
        isMoving = true;
      } else {
        if (isMoving) {
          ctx.stroke();
          ctx.beginPath();
          ctx.setLineDash([]);
          ctx.strokeStyle = block.thread.color;
          ctx.moveTo(sx, sy);
          isMoving = false;
        } else {
          ctx.lineTo(sx, sy);
        }
      }
    }
    
    ctx.stroke();
  }
}

/**
 * Generate a stitch preview from region/color data (for pre-export preview)
 */
export function generateStitchPreview(
  canvas: HTMLCanvasElement,
  processedImageUrl: string | null,
  colorMappings: { originalColor: string; threadColor: string }[],
  hoopSize: '100x100' | '70x70'
): void {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  
  const hoopMm = hoopSize === '100x100' ? 100 : 70;
  const padding = 20;
  const drawSize = Math.min(canvas.width, canvas.height) - padding * 2;
  
  // White background
  ctx.fillStyle = '#FFFFFF';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  
  // Draw hoop outline
  ctx.strokeStyle = '#d4d4d4';
  ctx.lineWidth = 2;
  ctx.setLineDash([8, 4]);
  const hoopX = (canvas.width - drawSize) / 2;
  const hoopY = (canvas.height - drawSize) / 2;
  ctx.strokeRect(hoopX, hoopY, drawSize, drawSize);
  ctx.setLineDash([]);
  
  // Hoop label
  ctx.fillStyle = '#999';
  ctx.font = '12px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(`${hoopMm}×${hoopMm}mm hoop`, canvas.width / 2, hoopY + drawSize + 16);
  
  // If we have a processed image, draw it inside the hoop
  if (processedImageUrl) {
    const img = new window.Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      // Draw image fitted in hoop with margins
      const margin = drawSize * 0.05;
      const imgArea = drawSize - margin * 2;
      const imgScale = Math.min(imgArea / img.width, imgArea / img.height);
      const imgW = img.width * imgScale;
      const imgH = img.height * imgScale;
      const imgX = (canvas.width - imgW) / 2;
      const imgY = (canvas.height - imgH) / 2;
      
      ctx.drawImage(img, imgX, imgY, imgW, imgH);
      
      // Draw stitch direction lines overlay
      drawStitchOverlay(ctx, imgX, imgY, imgW, imgH, colorMappings);
    };
    img.src = processedImageUrl;
  }
  
  // Draw color legend
  const legendY = hoopY + drawSize + 30;
  const swatchSize = 16;
  const legendX = (canvas.width - colorMappings.length * (swatchSize + 8)) / 2;
  
  colorMappings.forEach((mapping, i) => {
    const x = legendX + i * (swatchSize + 8);
    ctx.fillStyle = mapping.threadColor || mapping.originalColor;
    ctx.fillRect(x, legendY, swatchSize, swatchSize);
    ctx.strokeStyle = '#ccc';
    ctx.lineWidth = 1;
    ctx.strokeRect(x, legendY, swatchSize, swatchSize);
  });
}

function drawStitchOverlay(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number,
  colorMappings: { originalColor: string; threadColor: string }[]
): void {
  // Draw subtle stitch-direction lines over the image
  ctx.globalAlpha = 0.15;
  ctx.strokeStyle = '#000';
  ctx.lineWidth = 0.5;
  
  const spacing = 3;
  for (let ly = y; ly < y + h; ly += spacing) {
    ctx.beginPath();
    ctx.moveTo(x, ly);
    ctx.lineTo(x + w, ly);
    ctx.stroke();
  }
  
  ctx.globalAlpha = 1.0;
}
