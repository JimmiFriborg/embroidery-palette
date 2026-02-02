import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Logo } from '@/components/Logo';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { databases, storage, DATABASE_ID, COLLECTIONS, STORAGE_BUCKETS, type Project, type ColorMapping } from '@/lib/appwrite';
import { processImage, generatePes, getPesDownloadUrl, getPreviewUrl, type StitchStats } from '@/lib/appwriteFunctions';
import { BROTHER_THREADS, findClosestThread, type BrotherThread } from '@/lib/brotherThreads';
import { ThreadPicker } from '@/components/ThreadPicker';
import { ExportDialog, type QualityPreset } from '@/components/ExportDialog';
import { useToast } from '@/hooks/use-toast';
import { useSwipeGesture } from '@/hooks/useSwipeGesture';
import { StitchPreview } from '@/components/StitchPreview';
import { parsePes, type PesPattern } from '@/lib/pesParser';
import { 
  ArrowLeft, 
  Image as ImageIcon,
  Palette,
  Eye,
  Download,
  Loader2,
  Settings,
  Sparkles,
  Play,
  ExternalLink,
  Layers,
  PenTool,
  Trash2,
  MoreVertical,
  RefreshCw
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export default function ProjectEditor() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { toast } = useToast();
  
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('original');
  const [originalImageUrl, setOriginalImageUrl] = useState<string | null>(null);
  const [processedImageUrl, setProcessedImageUrl] = useState<string | null>(null);
  const [outlineImageUrl, setOutlineImageUrl] = useState<string | null>(null);
  const [previewMode, setPreviewMode] = useState<'processed' | 'outline' | 'original'>('processed');
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);
  const [pesDownloadUrl, setPesDownloadUrl] = useState<string | null>(null);
  const [colorMappings, setColorMappings] = useState<ColorMapping[]>([]);
  const [selectedColorIndex, setSelectedColorIndex] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [regionSummary, setRegionSummary] = useState<{ total_area_mm2?: number; total_regions?: number } | null>(null);
  const [processingStep, setProcessingStep] = useState(0);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [lastStitchStats, setLastStitchStats] = useState<StitchStats | null>(null);
  const [showOutlineView, setShowOutlineView] = useState(false);
  const [pesPattern, setPesPattern] = useState<PesPattern | null>(null);

  // Swipe gesture for tab navigation
  const TABS = ['original', 'colors', 'preview'] as const;
  
  const handleSwipeLeft = useCallback(() => {
    const currentIndex = TABS.indexOf(activeTab as typeof TABS[number]);
    if (currentIndex < TABS.length - 1) {
      setActiveTab(TABS[currentIndex + 1]);
    }
  }, [activeTab]);

  const handleSwipeRight = useCallback(() => {
    const currentIndex = TABS.indexOf(activeTab as typeof TABS[number]);
    if (currentIndex > 0) {
      setActiveTab(TABS[currentIndex - 1]);
    }
  }, [activeTab]);

  const [swipeState, swipeHandlers] = useSwipeGesture({
    threshold: 50,
    onSwipeLeft: handleSwipeLeft,
    onSwipeRight: handleSwipeRight,
  });

  useEffect(() => {
    if (id) {
      fetchProject();
    }
  }, [id]);

  // Auto-process when coming from project creation
  const [autoProcessTriggered, setAutoProcessTriggered] = useState(false);
  useEffect(() => {
    if (
      searchParams.get('autoProcess') === 'true' &&
      project?.originalImageId &&
      !project?.processedImageId &&
      !isProcessing &&
      !autoProcessTriggered
    ) {
      setAutoProcessTriggered(true);
      // Clear the URL param
      searchParams.delete('autoProcess');
      setSearchParams(searchParams, { replace: true });
      // Trigger processing
      handleProcessImage();
    }
  }, [project, searchParams, isProcessing, autoProcessTriggered]);

  // Fun processing messages
  const PROCESS_STEPS = [
    'Waking the thread elves…',
    'Removing background fluff…',
    'Quantizing colors…',
    'Finding shapes…',
    'Planning stitches…',
    'Polishing preview…'
  ];

  useEffect(() => {
    if (!isProcessing) return;
    setProcessingStep(0);
    const interval = setInterval(() => {
      setProcessingStep((prev) => (prev + 1) % PROCESS_STEPS.length);
    }, 1800);
    return () => clearInterval(interval);
  }, [isProcessing]);

  const fetchProject = async () => {
    if (!id) return;
    
    setIsLoading(true);
    try {
      const doc = await databases.getDocument(DATABASE_ID, COLLECTIONS.PROJECTS, id);
      const projectData = doc as unknown as Project;
      setProject(projectData);
      
      // Load original image if available
      if (projectData.originalImageId) {
        try {
          const fileUrl = storage.getFilePreview(STORAGE_BUCKETS.IMAGES, projectData.originalImageId);
          setOriginalImageUrl(fileUrl.toString());
        } catch (e) {
          console.log('Could not load original image');
        }
      }

      // Load processed image if available
      if (projectData.processedImageId) {
        try {
          const fileUrl = storage.getFilePreview(STORAGE_BUCKETS.IMAGES, projectData.processedImageId);
          setProcessedImageUrl(fileUrl.toString());
        } catch (e) {
          console.log('Could not load processed image');
        }
      }

      // Load outline image if available
      if (projectData.outlineImageId) {
        try {
          const fileUrl = storage.getFilePreview(STORAGE_BUCKETS.IMAGES, projectData.outlineImageId);
          setOutlineImageUrl(fileUrl.toString());
        } catch (e) {
          console.log('Could not load outline image');
        }
      }

      // Load color mappings (stored as JSON string in Appwrite)
      if (projectData.colorMappings) {
        try {
          const parsed = typeof projectData.colorMappings === 'string'
            ? JSON.parse(projectData.colorMappings)
            : projectData.colorMappings;
          setColorMappings(parsed);
        } catch (e) {
          console.warn('Failed to parse colorMappings', e);
          setColorMappings([]);
        }
      } else {
        // Generate placeholder color mappings for demo
        const demoColors = generateDemoColors(projectData.threadCount);
        setColorMappings(demoColors);
      }

      // Load region summary from stored metadata if available
      if (projectData.regionMetadata) {
        try {
          const meta = JSON.parse(projectData.regionMetadata);
          if (meta?.summary) {
            setRegionSummary({
              total_area_mm2: meta.summary.total_area_mm2,
              total_regions: meta.summary.total_regions,
            });
          }
        } catch (e) {
          console.warn('Failed to parse regionMetadata', e);
        }
      }
    } catch (error) {
      console.error('Failed to fetch project:', error);
      toast({
        title: 'Error',
        description: 'Failed to load project',
        variant: 'destructive',
      });
      navigate('/dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  // Generate demo color mappings for development
  const generateDemoColors = (count: number): ColorMapping[] => {
    const sampleColors = [
      '#FF5733', '#33FF57', '#3357FF', '#FF33F5', '#F5FF33',
      '#33FFF5', '#FF3333', '#33FF33', '#3333FF', '#FFFF33',
      '#FF33FF', '#33FFFF', '#FF6600', '#6600FF', '#00FF66'
    ];
    
    return sampleColors.slice(0, count).map((color, index) => {
      const closestThread = findClosestThread(color);
      return {
        originalColor: color,
        threadNumber: closestThread.number,
        threadName: closestThread.name,
        threadColor: closestThread.hex,
        skip: false,
      };
    });
  };

  const handleProcessImage = async () => {
    if (!project || !project.originalImageId) {
      toast({
        title: 'No image',
        description: 'Please upload an image first.',
        variant: 'destructive',
      });
      return;
    }
    
    setIsProcessing(true);
    toast({
      title: 'Processing image...',
      description: 'Removing background and quantizing colors...',
    });

    try {
      const result = await processImage({
        projectId: project.$id,
        imageId: project.originalImageId,
        threadCount: project.threadCount,
        hoopSize: project.hoopSize,
      });

      if (result.success && result.processedImageId) {
        // Update local state - processed image
        const fileUrl = storage.getFilePreview(STORAGE_BUCKETS.IMAGES, result.processedImageId);
        setProcessedImageUrl(fileUrl.toString());

        // Auto-switch to Preview tab after processing
        setActiveTab('preview');
        setPreviewMode('processed');
        
        // Load outline image if available
        if (result.outlineImageId) {
          const outlineUrl = storage.getFilePreview(STORAGE_BUCKETS.IMAGES, result.outlineImageId);
          setOutlineImageUrl(outlineUrl.toString());
        }
        
        // Generate color mappings from extracted colors
        if (result.extractedColors) {
          const mappings = result.extractedColors.map(color => {
            const closestThread = findClosestThread(color);
            return {
              originalColor: color,
              threadNumber: closestThread.number,
              threadName: closestThread.name,
              threadColor: closestThread.hex,
              skip: false,
            };
          });
          setColorMappings(mappings);
          saveColorMappings(mappings);
        }

        // Store region summary for better stitch estimates
        if (result.regionData?.summary) {
          setRegionSummary({
            total_area_mm2: result.regionData.summary.total_area_mm2,
            total_regions: result.regionData.summary.total_regions,
          });
        }

        const contourInfo = result.contourCount ? ` • ${result.contourCount} contours` : '';
        toast({
          title: 'Processing complete!',
          description: `Extracted ${result.colorCount} colors${contourInfo}.`,
        });
        
        setActiveTab('colors');
      } else {
        throw new Error(result.error || 'Processing failed');
      }
    } catch (error) {
      console.error('Processing error:', error);
      toast({
        title: 'Processing failed',
        description: error instanceof Error ? error.message : 'Check Appwrite function setup.',
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Delete project and all associated files
  const handleDeleteProject = async () => {
    if (!project) return;
    
    const confirmed = window.confirm(`Delete "${project.name}"? This cannot be undone.`);
    if (!confirmed) return;

    try {
      // Delete associated files (best effort)
      const fileIds = [
        project.originalImageId,
        project.processedImageId,
        project.outlineImageId,
        project.pesFileId,
        project.previewImageId,
      ].filter(Boolean) as string[];

      for (const fileId of fileIds) {
        try {
          // Try each bucket
          for (const bucket of [STORAGE_BUCKETS.IMAGES, STORAGE_BUCKETS.PES_FILES, STORAGE_BUCKETS.PREVIEWS]) {
            try {
              await storage.deleteFile(bucket, fileId);
              break;
            } catch { /* wrong bucket, try next */ }
          }
        } catch { /* file already gone */ }
      }

      // Delete the project document
      await databases.deleteDocument(DATABASE_ID, COLLECTIONS.PROJECTS, project.$id);

      toast({ title: 'Project deleted' });
      navigate('/dashboard');
    } catch (error) {
      console.error('Delete failed:', error);
      toast({
        title: 'Delete failed',
        description: error instanceof Error ? error.message : 'Please try again.',
        variant: 'destructive',
      });
    }
  };

  // Persist color mappings to Appwrite
  const saveColorMappings = async (mappings: ColorMapping[]) => {
    if (!project) return;
    try {
      await databases.updateDocument(
        DATABASE_ID,
        COLLECTIONS.PROJECTS,
        project.$id,
        { colorMappings: JSON.stringify(mappings) }
      );
    } catch (e) {
      console.error('Failed to save color mappings:', e);
    }
  };

  const handleThreadSelect = (thread: BrotherThread) => {
    if (selectedColorIndex === null) return;
    
    const updatedMappings = [...colorMappings];
    if (thread.number === 'SKIP') {
      updatedMappings[selectedColorIndex] = {
        ...updatedMappings[selectedColorIndex],
        skip: true,
      };
    } else {
      updatedMappings[selectedColorIndex] = {
        ...updatedMappings[selectedColorIndex],
        threadNumber: thread.number,
        threadName: thread.name,
        threadColor: thread.hex,
        skip: false,
      };
    }
    setColorMappings(updatedMappings);
    saveColorMappings(updatedMappings);
    setSelectedColorIndex(null);
  };

  const handleExportClick = () => {
    if (colorMappings.length === 0) {
      toast({
        title: 'No colors mapped',
        description: 'Please process the image and map thread colors first.',
        variant: 'destructive',
      });
      return;
    }
    setShowExportDialog(true);
  };

  const handleExport = async (qualityPreset: QualityPreset, density?: number) => {
    if (!project) return;

    setIsExporting(true);
    toast({
      title: 'Generating PES file...',
      description: `Using ${qualityPreset} quality preset...`,
    });

    try {
      const result = await generatePes({
        projectId: project.$id,
        colorMappings,
        hoopSize: project.hoopSize,
        qualityPreset,
        density,
      });

      if (result.success && result.pesFileId) {
        // Store stats for display
        if (result.stats) {
          setLastStitchStats(result.stats);
        }

        // Set download URL
        const downloadUrl = getPesDownloadUrl(result.pesFileId);
        setPesDownloadUrl(downloadUrl);

        // Set preview if available
        if (result.previewImageId) {
          setPreviewImageUrl(getPreviewUrl(result.previewImageId));
        }

        const stitchCount = result.stats?.stitch_count?.toLocaleString() || '';
        const timeMinutes = result.stats?.estimated_time_minutes 
          ? `~${Math.round(result.stats.estimated_time_minutes)} min`
          : '';

        toast({
          title: 'PES file ready!',
          description: `${stitchCount} stitches${timeMinutes ? `, ${timeMinutes} sew time` : ''}`,
        });

        // Close dialog and open download
        setShowExportDialog(false);
        window.open(downloadUrl, '_blank');
      } else {
        throw new Error(result.error || 'PES generation failed');
      }
    } catch (error) {
      console.error('Export error:', error);
      toast({
        title: 'Export failed',
        description: error instanceof Error ? error.message : 'Check Appwrite function setup.',
        variant: 'destructive',
      });
    } finally {
      setIsExporting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-soft">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!project) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-soft pb-20">
      {/* Processing Overlay */}
      {isProcessing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-background rounded-2xl shadow-soft p-6 w-[85%] max-w-sm text-center">
            <div className="text-lg font-semibold mb-2">Processing your design</div>
            <div className="text-sm text-muted-foreground mb-4">{PROCESS_STEPS[processingStep]}</div>
            <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
              <div className="h-2 bg-primary animate-pulse" style={{ width: `${((processingStep + 1) / PROCESS_STEPS.length) * 100}%` }} />
            </div>
            <div className="text-xs text-muted-foreground mt-3">Please wait… this can take a bit ⏳</div>
          </div>
        </div>
      )}
      {/* Header */}
      <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-sm border-b border-border">
        <div className="container flex items-center justify-between h-14 px-4">
          <div className="flex items-center">
            <Button variant="ghost" size="icon" onClick={() => navigate('/dashboard')}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div className="ml-3">
              <h1 className="font-display font-semibold truncate max-w-[180px]">{project.name}</h1>
              <p className="text-xs text-muted-foreground">
                {project.hoopSize === '100x100' ? '100×100mm' : '70×70mm'} • {project.threadCount} colors
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MoreVertical className="h-5 w-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleProcessImage} disabled={isProcessing || !project?.originalImageId}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Re-process Image
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={handleDeleteProject}
                  className="text-destructive focus:text-destructive"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete Project
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      {/* Main Content - Swipeable */}
      <main 
        className="container px-4 py-4"
        {...swipeHandlers}
      >
        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-4">
            <TabsTrigger value="original" className="text-sm">
              <ImageIcon className="h-4 w-4 mr-1.5" />
              Original
            </TabsTrigger>
            <TabsTrigger value="colors" className="text-sm">
              <Palette className="h-4 w-4 mr-1.5" />
              Colors
            </TabsTrigger>
            <TabsTrigger value="preview" className="text-sm">
              <Eye className="h-4 w-4 mr-1.5" />
              Preview
            </TabsTrigger>
          </TabsList>

          {/* Original Image Tab */}
          <TabsContent value="original" className="mt-0">
            <Card className="border-0 shadow-soft">
              <CardContent className="p-4">
                {originalImageUrl ? (
                  <div className="relative">
                    <img
                      src={originalImageUrl}
                      alt="Original"
                      className="w-full max-h-[50vh] object-contain rounded-lg bg-muted"
                    />
                    {processedImageUrl ? (
                      <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
                        <Sparkles className="h-4 w-4 text-primary" />
                        <span>Processed • {colorMappings.length} colors extracted</span>
                      </div>
                    ) : (
                      <Button
                        className="mt-4 w-full bg-gradient-warm"
                        onClick={handleProcessImage}
                        disabled={isProcessing}
                      >
                        {isProcessing ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Processing...
                          </>
                        ) : (
                          <>
                            <Sparkles className="h-4 w-4 mr-2" />
                            Process Image
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                ) : (
                  <div className="aspect-square flex flex-col items-center justify-center bg-muted rounded-lg">
                    <ImageIcon className="h-12 w-12 text-muted-foreground mb-2" />
                    <p className="text-sm text-muted-foreground">No image uploaded</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Storage bucket may need to be created in Appwrite
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Color Mapping Tab */}
          <TabsContent value="colors" className="mt-0">
            <Card className="border-0 shadow-soft mb-4">
              <CardContent className="p-4">
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <Palette className="h-4 w-4" />
                  Thread Color Mapping
                </h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Tap a color to assign a Brother thread
                </p>
                
                <div className="grid grid-cols-2 gap-3">
                  {colorMappings.map((mapping, index) => (
                    <button
                      key={index}
                      onClick={() => setSelectedColorIndex(index)}
                      className={`p-3 rounded-xl border-2 transition-all text-left ${
                        selectedColorIndex === index
                          ? 'border-primary ring-2 ring-primary/20'
                          : 'border-muted hover:border-muted-foreground/50'
                      } ${mapping.skip ? 'opacity-60' : ''}`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className="w-8 h-8 rounded-lg shadow-inner flex-shrink-0"
                          style={{ backgroundColor: mapping.originalColor }}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-muted-foreground">
                            {mapping.skip ? 'SKIPPED' : `#${mapping.threadNumber}`}
                          </div>
                          <div className="text-sm font-medium truncate">
                            {mapping.skip ? 'Not stitched' : mapping.threadName}
                          </div>
                        </div>
                        <div
                          className="w-6 h-6 rounded-full border-2 border-muted flex-shrink-0"
                          style={{ backgroundColor: mapping.skip ? '#FFFFFF' : mapping.threadColor }}
                        />
                      </div>
                      <div className="mt-2 flex justify-end">
                        <button
                          type="button"
                          className={`text-xs px-2 py-1 rounded-full border ${mapping.skip ? 'border-primary text-primary' : 'border-muted text-muted-foreground'}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            const updated = [...colorMappings];
                            const wasSkipped = !!updated[index].skip;
                            updated[index] = {
                              ...updated[index],
                              skip: !wasSkipped,
                            };
                            setColorMappings(updated);
                          }}
                        >
                          {mapping.skip ? 'Unskip' : 'Skip'}
                        </button>
                      </div>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Thread Picker Modal */}
            {selectedColorIndex !== null && (
              <ThreadPicker
                isOpen={selectedColorIndex !== null}
                onClose={() => setSelectedColorIndex(null)}
                onSelect={handleThreadSelect}
                currentColor={colorMappings[selectedColorIndex]?.originalColor}
              />
            )}
          </TabsContent>

          {/* Preview Tab */}
          <TabsContent value="preview" className="mt-0 space-y-4">
            {/* Image Toggle Buttons */}
            {(processedImageUrl || outlineImageUrl || pesPattern) && (
              <div className="flex gap-2 flex-wrap">
                <Button
                  variant={previewMode === 'processed' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => { setPreviewMode('processed'); }}
                  className={previewMode === 'processed' ? 'bg-gradient-warm' : ''}
                  disabled={!processedImageUrl}
                >
                  <Layers className="h-4 w-4 mr-1.5" />
                  Colors
                </Button>
                <Button
                  variant={previewMode === 'outline' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setPreviewMode('outline')}
                  disabled={!outlineImageUrl}
                  className={previewMode === 'outline' ? 'bg-gradient-warm' : ''}
                >
                  <PenTool className="h-4 w-4 mr-1.5" />
                  Outlines
                </Button>
                <Button
                  variant={previewMode === 'original' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setPreviewMode('original')}
                  disabled={!originalImageUrl}
                  className={previewMode === 'original' ? 'bg-gradient-warm' : ''}
                >
                  <ImageIcon className="h-4 w-4 mr-1.5" />
                  Original
                </Button>
              </div>
            )}

            {/* Image Preview (direct img tag for reliability) */}
            {!pesPattern && (previewMode === 'processed' ? processedImageUrl : previewMode === 'outline' ? outlineImageUrl : originalImageUrl) && (
              <div className="relative rounded-xl overflow-hidden border border-border bg-white">
                <img
                  src={previewMode === 'outline' ? outlineImageUrl! : previewMode === 'original' ? originalImageUrl! : processedImageUrl!}
                  alt={`${previewMode} preview`}
                  className="w-full h-auto max-h-[400px] object-contain"
                  crossOrigin="anonymous"
                />
                <div className="absolute bottom-2 right-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
                  {project?.hoopSize === '100x100' ? '100×100mm' : '70×70mm'}
                </div>
              </div>
            )}

            {/* Stitch Preview Component (for PES pattern rendering + file upload) */}
            <StitchPreview
              pattern={pesPattern}
              processedImageUrl={pesPattern ? undefined : undefined}
              hoopSize={project?.hoopSize || '100x100'}
              colorMappings={colorMappings.map(m => ({
                originalColor: m.originalColor,
                threadColor: m.threadColor,
                threadName: m.threadName,
              }))}
              allowUpload={true}
              width={380}
              height={380}
              onPatternLoaded={(p) => setPesPattern(p)}
              compact={!pesPattern}
            />

            {/* Color Mapping Summary */}
            {colorMappings.length > 0 && (
              <Card className="border-0 shadow-soft">
                <CardContent className="p-4">
                  <h3 className="text-sm font-semibold mb-3">Thread Colors</h3>
                  <div className="flex flex-wrap gap-2">
                    {colorMappings.filter(m => !m.skip).map((m, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-xs">
                        <div
                          className="w-4 h-4 rounded-sm border border-border"
                          style={{ backgroundColor: m.originalColor }}
                          title={`Original: ${m.originalColor}`}
                        />
                        <span className="text-muted-foreground">→</span>
                        <div
                          className="w-4 h-4 rounded-sm border border-border"
                          style={{ backgroundColor: m.threadColor }}
                          title={`${m.threadName} (${m.threadNumber})`}
                        />
                        <span className="text-muted-foreground">{m.threadName}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Stitch Info */}
            <Card className="border-0 shadow-soft">
              <CardContent className="p-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Hoop Size</span>
                    <p className="font-semibold">{project?.hoopSize === '100x100' ? '100×100mm' : '70×70mm'}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Thread Colors</span>
                    <p className="font-semibold">{colorMappings.length || project?.threadCount || '--'}</p>
                  </div>
                  {(lastStitchStats || pesPattern) && (
                    <>
                      <div>
                        <span className="text-muted-foreground">Stitch Count</span>
                        <p className="font-semibold">
                          {pesPattern
                            ? pesPattern.totalStitches.toLocaleString()
                            : lastStitchStats?.stitch_count?.toLocaleString() || '--'}
                        </p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Sew Time</span>
                        <p className="font-semibold">
                          {pesPattern
                            ? `~${Math.round(pesPattern.totalStitches / 400)} min`
                            : lastStitchStats?.estimated_time_minutes
                              ? `~${Math.round(lastStitchStats.estimated_time_minutes)} min`
                              : '--'}
                        </p>
                      </div>
                    </>
                  )}
                </div>

                {/* Download button if PES is ready */}
                {pesDownloadUrl && (
                  <Button
                    className="mt-4 w-full bg-gradient-warm"
                    onClick={() => window.open(pesDownloadUrl, '_blank')}
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Download PES File
                  </Button>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Bottom Action Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-background border-t border-border p-4">
        <div className="container flex gap-3">
          <Button 
            variant="outline" 
            className="flex-1"
            onClick={() => setActiveTab('preview')}
          >
            <Play className="h-4 w-4 mr-2" />
            Preview
          </Button>
          <Button 
            className="flex-1 bg-gradient-warm"
            onClick={handleExportClick}
            disabled={isExporting || colorMappings.length === 0}
          >
            <Download className="h-4 w-4 mr-2" />
            Export .pes
          </Button>
        </div>
      </div>

      {/* Export Dialog */}
      <ExportDialog
        isOpen={showExportDialog}
        onClose={() => setShowExportDialog(false)}
        onExport={handleExport}
        hoopSize={project?.hoopSize || '100x100'}
        colorCount={colorMappings.length}
        isExporting={isExporting}
        stats={lastStitchStats}
        regionAreaMm2={regionSummary?.total_area_mm2}
        regionCount={regionSummary?.total_regions}
      />
    </div>
  );
}
