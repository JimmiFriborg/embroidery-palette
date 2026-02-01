import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Logo } from '@/components/Logo';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { useToast } from '@/hooks/use-toast';
import { databases, storage, DATABASE_ID, COLLECTIONS, STORAGE_BUCKETS, ID, type Project } from '@/lib/appwrite';
import { 
  ArrowLeft, 
  Camera, 
  Upload, 
  Image as ImageIcon,
  X,
  Loader2,
  Square,
  Info
} from 'lucide-react';

type HoopSize = '100x100' | '70x70';

export default function NewProject() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  
  const [projectName, setProjectName] = useState('');
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [hoopSize, setHoopSize] = useState<HoopSize>('100x100');
  const [threadCount, setThreadCount] = useState(6);
  const [isCreating, setIsCreating] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const handleImageSelect = useCallback((file: File) => {
    if (!file.type.startsWith('image/')) {
      toast({
        title: 'Invalid file type',
        description: 'Please select an image file',
        variant: 'destructive',
      });
      return;
    }

    setSelectedImage(file);
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result as string);
    };
    reader.readAsDataURL(file);

    // Auto-generate project name if empty
    if (!projectName) {
      const baseName = file.name.replace(/\.[^/.]+$/, '');
      setProjectName(baseName);
    }
  }, [projectName, toast]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleImageSelect(file);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleImageSelect(file);
  }, [handleImageSelect]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const clearImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (cameraInputRef.current) cameraInputRef.current.value = '';
  };

  const handleCreateProject = async () => {
    if (!user || !selectedImage) return;

    if (!projectName.trim()) {
      toast({
        title: 'Name required',
        description: 'Please enter a project name',
        variant: 'destructive',
      });
      return;
    }

    setIsCreating(true);
    
    try {
      // Upload original image to storage
      let originalImageId: string | undefined;
      try {
        const uploadedFile = await storage.createFile(
          STORAGE_BUCKETS.IMAGES,
          ID.unique(),
          selectedImage
        );
        originalImageId = uploadedFile.$id;
      } catch (storageError) {
        console.log('Storage bucket may not exist yet:', storageError);
        // Continue without image storage for now
      }

      // Create project document
      const projectData: Omit<Project, '$id' | '$createdAt' | '$updatedAt'> = {
        userId: user.$id,
        name: projectName.trim(),
        hoopSize,
        threadCount,
        status: 'draft',
        originalImageId,
      };

      const newProject = await databases.createDocument(
        DATABASE_ID,
        COLLECTIONS.PROJECTS,
        ID.unique(),
        projectData
      );

      toast({
        title: 'Project created!',
        description: 'Your project is ready for editing',
      });

      // Navigate to editor
      navigate(`/project/${newProject.$id}`);
    } catch (error) {
      console.error('Failed to create project:', error);
      const message = error instanceof Error ? error.message : 'Unknown error';
      toast({
        title: 'Error creating project',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-soft">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-sm border-b border-border">
        <div className="container flex items-center h-14 px-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="ml-3 font-display font-semibold">New Project</h1>
        </div>
      </header>

      <main className="container px-4 py-6 pb-24">
        {/* Image Upload Section */}
        <Card className="mb-6 border-0 shadow-soft overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-display">Upload Image</CardTitle>
            <CardDescription>Select or capture an image to embroider</CardDescription>
          </CardHeader>
          <CardContent>
            {!imagePreview ? (
              <div
                className={`relative border-2 border-dashed rounded-xl p-8 transition-colors ${
                  isDragging 
                    ? 'border-primary bg-primary/5' 
                    : 'border-muted-foreground/25 hover:border-primary/50'
                }`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
              >
                <div className="flex flex-col items-center justify-center text-center">
                  <div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center mb-4">
                    <ImageIcon className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <p className="text-muted-foreground mb-4">
                    Drag & drop an image here, or
                  </p>
                  <div className="flex gap-3">
                    <Button
                      variant="outline"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Upload className="h-4 w-4 mr-2" />
                      Browse
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => cameraInputRef.current?.click()}
                      className="md:hidden"
                    >
                      <Camera className="h-4 w-4 mr-2" />
                      Camera
                    </Button>
                  </div>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileInput}
                  className="hidden"
                />
                <input
                  ref={cameraInputRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={handleFileInput}
                  className="hidden"
                />
              </div>
            ) : (
              <div className="relative">
                <img
                  src={imagePreview}
                  alt="Preview"
                  className="w-full max-h-64 object-contain rounded-lg bg-muted"
                />
                <Button
                  variant="destructive"
                  size="icon"
                  className="absolute top-2 right-2"
                  onClick={clearImage}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Project Settings */}
        <Card className="mb-6 border-0 shadow-soft">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-display">Project Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Project Name */}
            <div className="space-y-2">
              <Label htmlFor="name">Project Name</Label>
              <Input
                id="name"
                placeholder="My Embroidery Project"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
              />
            </div>

            {/* Hoop Size */}
            <div className="space-y-3">
              <Label className="flex items-center gap-2">
                Hoop Size
                <span className="text-xs text-muted-foreground">(PP1 compatible)</span>
              </Label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  className={`relative p-4 rounded-xl border-2 transition-all ${
                    hoopSize === '100x100'
                      ? 'border-primary bg-primary/5'
                      : 'border-muted hover:border-muted-foreground/50'
                  }`}
                  onClick={() => setHoopSize('100x100')}
                >
                  <div className="flex flex-col items-center">
                    <div className="w-12 h-12 border-2 border-current rounded mb-2 flex items-center justify-center">
                      <Square className="h-8 w-8" />
                    </div>
                    <span className="font-semibold">100×100mm</span>
                    <span className="text-xs text-muted-foreground">4" × 4"</span>
                  </div>
                  {hoopSize === '100x100' && (
                    <div className="absolute top-2 right-2 w-3 h-3 rounded-full bg-primary" />
                  )}
                </button>
                <button
                  type="button"
                  className={`relative p-4 rounded-xl border-2 transition-all ${
                    hoopSize === '70x70'
                      ? 'border-primary bg-primary/5'
                      : 'border-muted hover:border-muted-foreground/50'
                  }`}
                  onClick={() => setHoopSize('70x70')}
                >
                  <div className="flex flex-col items-center">
                    <div className="w-10 h-10 border-2 border-current rounded mb-2 flex items-center justify-center">
                      <Square className="h-6 w-6" />
                    </div>
                    <span className="font-semibold">70×70mm</span>
                    <span className="text-xs text-muted-foreground">2.75" × 2.75"</span>
                  </div>
                  {hoopSize === '70x70' && (
                    <div className="absolute top-2 right-2 w-3 h-3 rounded-full bg-primary" />
                  )}
                </button>
              </div>
            </div>

            {/* Thread Count */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Thread Colors</Label>
                <span className="text-sm font-semibold text-primary">{threadCount}</span>
              </div>
              <Slider
                value={[threadCount]}
                onValueChange={(value) => setThreadCount(value[0])}
                min={2}
                max={15}
                step={1}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Simple (2)</span>
                <span>Detailed (15)</span>
              </div>
              <div className="flex items-start gap-2 p-3 rounded-lg bg-secondary/50">
                <Info className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                <p className="text-xs text-muted-foreground">
                  Fewer colors = simpler design, faster stitching. 
                  Recommended: 4-8 colors for best PP1 results.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Create Button */}
        <Button
          className="w-full h-14 text-lg bg-gradient-warm shadow-craft"
          disabled={!selectedImage || !projectName.trim() || isCreating}
          onClick={handleCreateProject}
        >
          {isCreating ? (
            <>
              <Loader2 className="h-5 w-5 mr-2 animate-spin" />
              Creating Project...
            </>
          ) : (
            'Create Project'
          )}
        </Button>
      </main>
    </div>
  );
}
