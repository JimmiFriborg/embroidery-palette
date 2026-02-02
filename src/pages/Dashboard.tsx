import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Logo } from '@/components/Logo';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { databases, storage, DATABASE_ID, COLLECTIONS, STORAGE_BUCKETS, Query, type Project } from '@/lib/appwrite';
import { 
  Plus, 
  FolderOpen, 
  Clock, 
  Settings, 
  LogOut, 
  Image as ImageIcon,
  Sparkles,
  ChevronRight,
  Loader2
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchProjects();
  }, [user]);

  const fetchProjects = async () => {
    if (!user) return;
    
    setIsLoading(true);
    try {
      const response = await databases.listDocuments(
        DATABASE_ID,
        COLLECTIONS.PROJECTS,
        [
          Query.equal('userId', user.$id),
          Query.orderDesc('$updatedAt'),
          Query.limit(10)
        ]
      );
      setProjects(response.documents as unknown as Project[]);
    } catch (error) {
      // Database might not be set up yet - that's okay
      console.log('Projects collection may not exist yet');
      setProjects([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/');
      toast({
        title: 'Logged out',
        description: 'See you next time!',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to log out. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const getStatusColor = (status: Project['status']) => {
    switch (status) {
      case 'draft': return 'bg-muted text-muted-foreground';
      case 'processing': return 'bg-accent text-accent-foreground';
      case 'ready': return 'bg-secondary text-secondary-foreground';
      case 'exported': return 'bg-primary text-primary-foreground';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-soft pb-24">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-sm border-b border-border">
        <div className="container flex items-center justify-between h-16 px-4">
          <Logo size="sm" />
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={() => navigate('/settings')}>
              <Settings className="h-5 w-5" />
            </Button>
            <Button variant="ghost" size="icon" onClick={handleLogout}>
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container px-4 py-6">
        {/* Greeting */}
        <div className="mb-8">
          <h1 className="text-2xl font-display font-bold text-foreground">
            {getGreeting()}, {user?.name?.split(' ')[0] || 'Creator'}!
          </h1>
          <p className="text-muted-foreground mt-1">
            Ready to create something beautiful?
          </p>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <Card 
            className="cursor-pointer hover:shadow-craft transition-shadow border-0 shadow-soft bg-gradient-warm text-primary-foreground"
            onClick={() => navigate('/new-project')}
          >
            <CardContent className="p-4 flex flex-col items-center justify-center text-center min-h-[120px]">
              <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center mb-3">
                <Plus className="h-6 w-6" />
              </div>
              <span className="font-semibold">New Project</span>
            </CardContent>
          </Card>

          <Card 
            className="cursor-pointer hover:shadow-craft transition-shadow border-0 shadow-soft"
            onClick={() => navigate('/projects')}
          >
            <CardContent className="p-4 flex flex-col items-center justify-center text-center min-h-[120px]">
              <div className="w-12 h-12 rounded-full bg-secondary flex items-center justify-center mb-3">
                <FolderOpen className="h-6 w-6 text-secondary-foreground" />
              </div>
              <span className="font-semibold text-foreground">All Projects</span>
            </CardContent>
          </Card>
        </div>

        {/* Recent Projects */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-display font-semibold flex items-center gap-2">
              <Clock className="h-5 w-5 text-muted-foreground" />
              Recent Projects
            </h2>
            {projects.length > 0 && (
              <Button variant="ghost" size="sm" onClick={() => navigate('/projects')}>
                View all
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            )}
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : projects.length > 0 ? (
            <div className="space-y-3">
              {projects.slice(0, 5).map((project) => (
                <Card 
                  key={project.$id}
                  className="cursor-pointer hover:shadow-soft transition-shadow border-0"
                  onClick={() => navigate(`/project/${project.$id}`)}
                >
                  <CardContent className="p-4 flex items-center gap-4">
                    <div className="w-14 h-14 rounded-lg bg-muted flex items-center justify-center flex-shrink-0 overflow-hidden">
                      {(project.processedImageId || project.originalImageId) ? (
                        <img 
                          src={storage.getFilePreview(
                            STORAGE_BUCKETS.IMAGES,
                            project.processedImageId || project.originalImageId!,
                            56, 56
                          ).toString()}
                          alt={project.name}
                          className="w-full h-full object-cover"
                          crossOrigin="anonymous"
                        />
                      ) : (
                        <ImageIcon className="h-6 w-6 text-muted-foreground" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold truncate">{project.name}</h3>
                      <p className="text-sm text-muted-foreground">
                        {project.hoopSize === '100x100' ? '100×100mm' : '70×70mm'} • {project.threadCount} colors
                      </p>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full ${getStatusColor(project.status)}`}>
                      {project.status}
                    </span>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="border-dashed border-2 border-muted">
              <CardContent className="p-8 text-center">
                <div className="w-16 h-16 rounded-full bg-muted mx-auto flex items-center justify-center mb-4">
                  <Sparkles className="h-8 w-8 text-muted-foreground" />
                </div>
                <CardTitle className="text-lg mb-2">No projects yet</CardTitle>
                <CardDescription className="mb-4">
                  Create your first embroidery project to get started
                </CardDescription>
                <Button onClick={() => navigate('/new-project')} className="bg-gradient-warm">
                  <Plus className="h-4 w-4 mr-2" />
                  New Project
                </Button>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Tips Section */}
        <Card className="bg-secondary/30 border-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-display flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-accent" />
              Pro Tip
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <p className="text-sm text-muted-foreground">
              For best results, use images with clear outlines and distinct colors. 
              The Brother PP1 works great with 4-8 thread colors for detailed designs.
            </p>
          </CardContent>
        </Card>
      </main>

      {/* Bottom Navigation (Mobile) */}
      <nav className="fixed bottom-0 left-0 right-0 bg-background border-t border-border md:hidden">
        <div className="grid grid-cols-3 h-16">
          <button 
            className="flex flex-col items-center justify-center text-primary"
            onClick={() => navigate('/dashboard')}
          >
            <FolderOpen className="h-5 w-5" />
            <span className="text-xs mt-1">Projects</span>
          </button>
          <button 
            className="flex flex-col items-center justify-center"
            onClick={() => navigate('/new-project')}
          >
            <div className="w-12 h-12 -mt-6 rounded-full bg-gradient-warm flex items-center justify-center shadow-craft">
              <Plus className="h-6 w-6 text-primary-foreground" />
            </div>
          </button>
          <button 
            className="flex flex-col items-center justify-center text-muted-foreground"
            onClick={() => navigate('/settings')}
          >
            <Settings className="h-5 w-5" />
            <span className="text-xs mt-1">Settings</span>
          </button>
        </div>
      </nav>
    </div>
  );
}
