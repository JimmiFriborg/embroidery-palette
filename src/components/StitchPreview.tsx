import { useRef, useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { parsePes, renderPesPattern, type PesPattern } from '@/lib/pesParser';
import {
  Upload,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Grid3x3,
  Eye,
  EyeOff,
  FileDown,
  Layers,
  Clock,
  Hash,
  Palette,
} from 'lucide-react';

interface StitchPreviewProps {
  /** Pre-parsed pattern data */
  pattern?: PesPattern | null;
  /** URL to a processed image (shown as background) */
  processedImageUrl?: string | null;
  /** Hoop size */
  hoopSize?: '100x100' | '70x70';
  /** Color mappings for legend */
  colorMappings?: { originalColor: string; threadColor: string; threadName: string }[];
  /** Allow file upload */
  allowUpload?: boolean;
  /** Canvas width */
  width?: number;
  /** Canvas height */
  height?: number;
  /** Callback when a PES file is loaded */
  onPatternLoaded?: (pattern: PesPattern) => void;
  /** Compact mode (no controls) */
  compact?: boolean;
}

export function StitchPreview({
  pattern: externalPattern,
  processedImageUrl,
  hoopSize = '100x100',
  colorMappings = [],
  allowUpload = true,
  width = 400,
  height = 400,
  onPatternLoaded,
  compact = false,
}: StitchPreviewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [pattern, setPattern] = useState<PesPattern | null>(externalPattern || null);
  const [showGrid, setShowGrid] = useState(true);
  const [showJumps, setShowJumps] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  // Update pattern when external prop changes
  useEffect(() => {
    if (externalPattern) {
      setPattern(externalPattern);
    }
  }, [externalPattern]);

  // Render pattern to canvas
  const renderCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Set canvas resolution (2x for retina)
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr * zoom;
    canvas.height = height * dpr * zoom;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr * zoom, dpr * zoom);

    if (pattern) {
      renderPesPattern(canvas, pattern, {
        showGrid,
        showJumps,
        lineWidth: 1.5 / zoom,
        padding: 20,
      });
    } else if (processedImageUrl) {
      // Show processed image with stitch overlay
      drawProcessedPreview(ctx, width, height, processedImageUrl, hoopSize, colorMappings);
    } else {
      // Empty state
      drawEmptyState(ctx, width, height, hoopSize);
    }
  }, [pattern, processedImageUrl, showGrid, showJumps, zoom, width, height, hoopSize, colorMappings]);

  useEffect(() => {
    renderCanvas();
  }, [renderCanvas]);

  // Handle PES file upload
  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    
    const reader = new FileReader();
    reader.onload = (event) => {
      const buffer = event.target?.result as ArrayBuffer;
      const parsed = parsePes(buffer);
      
      if (parsed) {
        setPattern(parsed);
        onPatternLoaded?.(parsed);
      }
    };
    reader.readAsArrayBuffer(file);
  }, [onPatternLoaded]);

  // Handle drag and drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file && file.name.toLowerCase().endsWith('.pes')) {
      setFileName(file.name);
      const reader = new FileReader();
      reader.onload = (event) => {
        const buffer = event.target?.result as ArrayBuffer;
        const parsed = parsePes(buffer);
        if (parsed) {
          setPattern(parsed);
          onPatternLoaded?.(parsed);
        }
      };
      reader.readAsArrayBuffer(file);
    }
  }, [onPatternLoaded]);

  if (compact) {
    return (
      <div className="relative rounded-lg overflow-hidden bg-white border">
        <canvas
          ref={canvasRef}
          style={{ width, height }}
          className="block"
        />
      </div>
    );
  }

  return (
    <Card className="border-0 shadow-soft">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Layers className="h-4 w-4" />
          Stitch Preview
          {fileName && (
            <Badge variant="secondary" className="ml-auto text-xs">
              {fileName}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Canvas */}
        <div
          className={`relative rounded-lg overflow-hidden bg-white border-2 transition-colors ${
            isDragging ? 'border-primary border-dashed' : 'border-muted'
          }`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          <canvas
            ref={canvasRef}
            style={{ width: '100%', height: 'auto', maxHeight: '50vh' }}
            className="block"
          />
          
          {isDragging && (
            <div className="absolute inset-0 bg-primary/10 flex items-center justify-center">
              <p className="text-primary font-medium">Drop .pes file here</p>
            </div>
          )}
        </div>

        {/* Stats */}
        {pattern && (
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="p-2 rounded-lg bg-secondary/50">
              <Hash className="h-3.5 w-3.5 mx-auto mb-1 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Stitches</p>
              <p className="text-sm font-semibold">{pattern.totalStitches.toLocaleString()}</p>
            </div>
            <div className="p-2 rounded-lg bg-secondary/50">
              <Palette className="h-3.5 w-3.5 mx-auto mb-1 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Colors</p>
              <p className="text-sm font-semibold">{pattern.colorCount}</p>
            </div>
            <div className="p-2 rounded-lg bg-secondary/50">
              <Clock className="h-3.5 w-3.5 mx-auto mb-1 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Est. Time</p>
              <p className="text-sm font-semibold">
                {Math.round(pattern.totalStitches / 400)}min
              </p>
            </div>
          </div>
        )}

        {/* Color blocks */}
        {pattern && pattern.colorBlocks.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {pattern.colorBlocks.map((block, i) => (
              <div
                key={i}
                className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-secondary/50 text-xs"
              >
                <div
                  className="w-3 h-3 rounded-full border border-black/10"
                  style={{ backgroundColor: block.thread.color }}
                />
                <span className="text-muted-foreground">{block.thread.name}</span>
                <span className="text-muted-foreground/50">
                  ({block.stitches.filter(s => s.type === 'stitch').length})
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Controls */}
        <div className="flex items-center gap-1.5">
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => setShowGrid(!showGrid)}
            title={showGrid ? 'Hide grid' : 'Show grid'}
          >
            <Grid3x3 className={`h-3.5 w-3.5 ${showGrid ? 'text-primary' : ''}`} />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => setShowJumps(!showJumps)}
            title={showJumps ? 'Hide jump stitches' : 'Show jump stitches'}
          >
            {showJumps ? <Eye className="h-3.5 w-3.5 text-primary" /> : <EyeOff className="h-3.5 w-3.5" />}
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => setZoom(z => Math.min(z * 1.25, 4))}
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => setZoom(z => Math.max(z / 1.25, 0.5))}
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => { setZoom(1); setPattern(externalPattern || null); }}
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </Button>

          {allowUpload && (
            <label className="ml-auto">
              <input
                type="file"
                accept=".pes"
                onChange={handleFileUpload}
                className="hidden"
              />
              <Button variant="outline" size="sm" className="h-8 cursor-pointer" asChild>
                <span>
                  <Upload className="h-3.5 w-3.5 mr-1.5" />
                  Load .pes
                </span>
              </Button>
            </label>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// Helper: Draw processed image preview with hoop
function drawProcessedPreview(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  imageUrl: string,
  hoopSize: string,
  colorMappings: { originalColor: string; threadColor: string }[]
) {
  const hoopMm = hoopSize === '100x100' ? 100 : 70;
  const padding = 20;
  const drawSize = Math.min(width, height) - padding * 2;

  // Background
  ctx.fillStyle = '#FFFFFF';
  ctx.fillRect(0, 0, width, height);

  // Hoop outline
  ctx.strokeStyle = '#d4d4d4';
  ctx.lineWidth = 2;
  ctx.setLineDash([8, 4]);
  const hoopX = (width - drawSize) / 2;
  const hoopY = (height - drawSize) / 2;
  ctx.strokeRect(hoopX, hoopY, drawSize, drawSize);
  ctx.setLineDash([]);

  // Label
  ctx.fillStyle = '#999';
  ctx.font = '11px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(`${hoopMm}×${hoopMm}mm`, width / 2, hoopY + drawSize + 14);

  // Load and draw image
  const img = new Image();
  img.crossOrigin = 'anonymous';
  img.onload = () => {
    const margin = drawSize * 0.05;
    const imgArea = drawSize - margin * 2;
    const scale = Math.min(imgArea / img.width, imgArea / img.height);
    const imgW = img.width * scale;
    const imgH = img.height * scale;
    const imgX = (width - imgW) / 2;
    const imgY = (height - imgH) / 2;
    ctx.drawImage(img, imgX, imgY, imgW, imgH);
  };
  img.src = imageUrl;
}

// Helper: Draw empty state
function drawEmptyState(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  hoopSize: string
) {
  ctx.fillStyle = '#FAFAFA';
  ctx.fillRect(0, 0, width, height);

  const drawSize = Math.min(width, height) - 40;
  const hoopX = (width - drawSize) / 2;
  const hoopY = (height - drawSize) / 2;

  // Dashed hoop
  ctx.strokeStyle = '#e0e0e0';
  ctx.lineWidth = 2;
  ctx.setLineDash([10, 6]);
  ctx.strokeRect(hoopX, hoopY, drawSize, drawSize);
  ctx.setLineDash([]);

  // Center text
  ctx.fillStyle = '#bbb';
  ctx.font = '14px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('No stitch data yet', width / 2, height / 2 - 10);
  ctx.font = '12px system-ui, sans-serif';
  ctx.fillText('Process image or drop a .pes file', width / 2, height / 2 + 10);
}

export default StitchPreview;
