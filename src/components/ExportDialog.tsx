import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Download,
  Loader2,
  Clock,
  Zap,
  Scale,
  Sparkles,
  AlertTriangle,
  Info,
} from 'lucide-react';

export type QualityPreset = 'fast' | 'balanced' | 'quality';

interface StitchStats {
  stitch_count: number;
  estimated_time_minutes: number;
  color_count: number;
  region_count?: number;
  warning?: string;
}

interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onExport: (preset: QualityPreset, density?: number) => Promise<void>;
  hoopSize: '100x100' | '70x70';
  colorCount: number;
  isExporting: boolean;
  stats?: StitchStats | null;
}

const PRESET_INFO = {
  fast: {
    label: 'Fast',
    description: 'Lower density, quick test pieces',
    density: 4,
    icon: Zap,
    stitchMultiplier: 0.7,
  },
  balanced: {
    label: 'Balanced',
    description: 'Recommended for PP1',
    density: 5,
    icon: Scale,
    stitchMultiplier: 1.0,
  },
  quality: {
    label: 'Quality',
    description: 'Higher density for show pieces',
    density: 6,
    icon: Sparkles,
    stitchMultiplier: 1.3,
  },
};

export function ExportDialog({
  isOpen,
  onClose,
  onExport,
  hoopSize,
  colorCount,
  isExporting,
  stats,
}: ExportDialogProps) {
  const [selectedPreset, setSelectedPreset] = useState<QualityPreset>('balanced');
  const [customDensity, setCustomDensity] = useState<number>(5);
  const [useCustomDensity, setUseCustomDensity] = useState(false);

  const currentDensity = useCustomDensity
    ? customDensity
    : PRESET_INFO[selectedPreset].density;

  // Estimate stitch count based on hoop size and density
  const estimateStitches = () => {
    const hoopArea = hoopSize === '100x100' ? 90 * 90 : 62 * 62; // Safe area in mm²
    const baseStitches = hoopArea * currentDensity * 0.4; // Rough estimate
    return Math.round(baseStitches);
  };

  const estimatedStitches = stats?.stitch_count || estimateStitches();
  const estimatedMinutes = stats?.estimated_time_minutes || Math.round(estimatedStitches / 400);
  const isHighStitchCount = estimatedStitches > 15000;

  const formatTime = (minutes: number) => {
    if (minutes < 60) return `~${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `~${hours}h ${mins}m`;
  };

  const handleExport = async () => {
    const density = useCustomDensity ? customDensity : undefined;
    await onExport(selectedPreset, density);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            Export PES File
          </DialogTitle>
          <DialogDescription>
            Configure quality settings for your embroidery file
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Quality Preset Selector */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">Quality Preset</Label>
            <RadioGroup
              value={selectedPreset}
              onValueChange={(value) => {
                setSelectedPreset(value as QualityPreset);
                setUseCustomDensity(false);
              }}
              className="grid grid-cols-3 gap-2"
            >
              {(Object.keys(PRESET_INFO) as QualityPreset[]).map((preset) => {
                const info = PRESET_INFO[preset];
                const Icon = info.icon;
                return (
                  <label
                    key={preset}
                    className={`flex flex-col items-center gap-1.5 p-3 rounded-lg border-2 cursor-pointer transition-all ${
                      selectedPreset === preset && !useCustomDensity
                        ? 'border-primary bg-primary/5'
                        : 'border-muted hover:border-muted-foreground/50'
                    }`}
                  >
                    <RadioGroupItem value={preset} className="sr-only" />
                    <Icon className="h-5 w-5" />
                    <span className="text-sm font-medium">{info.label}</span>
                    <span className="text-xs text-muted-foreground text-center">
                      {info.density}/mm
                    </span>
                  </label>
                );
              })}
            </RadioGroup>
            <p className="text-xs text-muted-foreground">
              {PRESET_INFO[selectedPreset].description}
            </p>
          </div>

          {/* Custom Density Slider */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">Custom Density</Label>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-xs"
                onClick={() => setUseCustomDensity(!useCustomDensity)}
              >
                {useCustomDensity ? 'Use Preset' : 'Customize'}
              </Button>
            </div>
            {useCustomDensity && (
              <div className="space-y-2">
                <Slider
                  value={[customDensity]}
                  onValueChange={([value]) => setCustomDensity(value)}
                  min={3}
                  max={8}
                  step={0.5}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Sparse (3)</span>
                  <span className="font-medium">{customDensity} stitches/mm</span>
                  <span>Dense (8)</span>
                </div>
              </div>
            )}
          </div>

          <Separator />

          {/* Stitch Statistics */}
          <div className="space-y-3">
            <Label className="text-sm font-medium flex items-center gap-2">
              <Info className="h-4 w-4" />
              Estimated Output
            </Label>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-secondary/50">
                <div className="text-xs text-muted-foreground">Stitch Count</div>
                <div className="text-lg font-semibold flex items-center gap-1">
                  {estimatedStitches.toLocaleString()}
                  {isHighStitchCount && (
                    <AlertTriangle className="h-4 w-4 text-warning" />
                  )}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-secondary/50">
                <div className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Sew Time
                </div>
                <div className="text-lg font-semibold">
                  {formatTime(estimatedMinutes)}
                </div>
              </div>
            </div>

            {/* Warning for high stitch count */}
            {isHighStitchCount && (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-warning/10 border border-warning/30">
                <AlertTriangle className="h-4 w-4 text-warning shrink-0 mt-0.5" />
                <div className="text-xs text-warning-foreground">
                  <p className="font-medium">High stitch count</p>
                  <p className="text-muted-foreground mt-0.5">
                    Designs over 15,000 stitches may strain the PP1. Consider using the "Fast" preset or reducing colors.
                  </p>
                </div>
              </div>
            )}

            {/* Design Info */}
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">
                {hoopSize === '100x100' ? '100×100mm' : '70×70mm'}
              </Badge>
              <Badge variant="secondary">{colorCount} colors</Badge>
              <Badge variant="outline">{currentDensity} stitches/mm</Badge>
            </div>
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button variant="outline" onClick={onClose} disabled={isExporting}>
            Cancel
          </Button>
          <Button
            onClick={handleExport}
            disabled={isExporting}
            className="bg-gradient-warm"
          >
            {isExporting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                Export PES
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
