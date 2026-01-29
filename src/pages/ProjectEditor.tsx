import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Logo } from '@/components/Logo';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { databases, storage, DATABASE_ID, COLLECTIONS, STORAGE_BUCKETS, type Project, type ColorMapping } from '@/lib/appwrite';
import { BROTHER_THREADS, findClosestThread, type BrotherThread } from '@/lib/brotherThreads';
import { ThreadPicker } from '@/components/ThreadPicker';
import { useToast } from '@/hooks/use-toast';
import { 
  ArrowLeft, 
  Image as ImageIcon,
  Palette,
  Eye,
  Download,
  Loader2,
  Settings,
  Sparkles,
  Play
} from 'lucide-react';

export default function ProjectEditor() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('original');
  const [originalImageUrl, setOriginalImageUrl] = useState<string | null>(null);
  const [processedImageUrl, setProcessedImageUrl] = useState<string | null>(null);
  const [colorMappings, setColorMappings] = useState<ColorMapping[]>([]);
  const [selectedColorIndex, setSelectedColorIndex] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    if (id) {
      fetchProject();
    }
  }, [id]);

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

      // Load color mappings
      if (projectData.colorMappings) {
        setColorMappings(projectData.colorMappings);
      } else {
        // Generate placeholder color mappings for demo
        const demoColors = generateDemoColors(projectData.threadCount);
        setColorMappings(demoColors);
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
      };
    });
  };

  const handleProcessImage = async () => {
    if (!project) return;
    
    setIsProcessing(true);
    toast({
      title: 'Processing image...',
      description: 'This may take a moment. The Appwrite function will handle color quantization.',
    });

    // TODO: Call Appwrite function for image processing
    // For now, simulate processing delay
    setTimeout(() => {
      setIsProcessing(false);
      toast({
        title: 'Processing complete!',
        description: 'Note: Full processing requires Appwrite function setup.',
      });
    }, 2000);
  };

  const handleThreadSelect = (thread: BrotherThread) => {
    if (selectedColorIndex === null) return;
    
    const updatedMappings = [...colorMappings];
    updatedMappings[selectedColorIndex] = {
      ...updatedMappings[selectedColorIndex],
      threadNumber: thread.number,
      threadName: thread.name,
      threadColor: thread.hex,
    };
    setColorMappings(updatedMappings);
    setSelectedColorIndex(null);
  };

  const handleExport = () => {
    toast({
      title: 'Export coming soon!',
      description: 'PES file generation requires the pyembroidery Appwrite function.',
    });
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
            <Button variant="ghost" size="icon">
              <Settings className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container px-4 py-4">
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
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className="w-8 h-8 rounded-lg shadow-inner flex-shrink-0"
                          style={{ backgroundColor: mapping.originalColor }}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-muted-foreground">#{mapping.threadNumber}</div>
                          <div className="text-sm font-medium truncate">{mapping.threadName}</div>
                        </div>
                        <div
                          className="w-6 h-6 rounded-full border-2 border-muted flex-shrink-0"
                          style={{ backgroundColor: mapping.threadColor }}
                        />
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
          <TabsContent value="preview" className="mt-0">
            <Card className="border-0 shadow-soft">
              <CardContent className="p-4">
                <div className="aspect-square flex flex-col items-center justify-center bg-muted rounded-lg border-2 border-dashed border-muted-foreground/25">
                  <Eye className="h-12 w-12 text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground font-medium">Stitch Preview</p>
                  <p className="text-xs text-muted-foreground mt-1 text-center px-4">
                    Preview will appear here after processing with pyembroidery
                  </p>
                </div>

                {/* Stitch Info */}
                <div className="mt-4 p-3 rounded-lg bg-secondary/50">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Estimated Stitches</span>
                      <p className="font-semibold">--</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Estimated Time</span>
                      <p className="font-semibold">--</p>
                    </div>
                  </div>
                </div>
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
            onClick={handleExport}
          >
            <Download className="h-4 w-4 mr-2" />
            Export .pes
          </Button>
        </div>
      </div>
    </div>
  );
}
