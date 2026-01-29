import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Logo } from '@/components/Logo';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { databases, DATABASE_ID, COLLECTIONS, Query, type Project } from '@/lib/appwrite';
import { 
  ArrowLeft,
  Plus, 
  Search,
  Image as ImageIcon,
  Loader2,
  FolderOpen
} from 'lucide-react';

export default function Projects() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

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
          Query.limit(100)
        ]
      );
      setProjects(response.documents as unknown as Project[]);
    } catch (error) {
      console.log('Projects collection may not exist yet');
      setProjects([]);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredProjects = projects.filter(p => 
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
    <div className="min-h-screen bg-gradient-soft pb-20">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-sm border-b border-border">
        <div className="container flex items-center h-14 px-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/dashboard')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="ml-3 font-display font-semibold">All Projects</h1>
          <Button 
            variant="ghost" 
            size="icon" 
            className="ml-auto"
            onClick={() => navigate('/new-project')}
          >
            <Plus className="h-5 w-5" />
          </Button>
        </div>
      </header>

      <main className="container px-4 py-4">
        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Projects List */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : filteredProjects.length > 0 ? (
          <div className="space-y-3">
            {filteredProjects.map((project) => (
              <Card 
                key={project.$id}
                className="cursor-pointer hover:shadow-soft transition-shadow border-0"
                onClick={() => navigate(`/project/${project.$id}`)}
              >
                <CardContent className="p-4 flex items-center gap-4">
                  <div className="w-14 h-14 rounded-lg bg-muted flex items-center justify-center flex-shrink-0 overflow-hidden">
                    {project.previewImageId ? (
                      <img 
                        src={`/preview/${project.previewImageId}`} 
                        alt={project.name}
                        className="w-full h-full object-cover"
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
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Updated {new Date(project.$updatedAt).toLocaleDateString()}
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
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
              <FolderOpen className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="font-semibold mb-1">
              {searchQuery ? 'No matching projects' : 'No projects yet'}
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              {searchQuery 
                ? 'Try a different search term' 
                : 'Create your first embroidery project'}
            </p>
            {!searchQuery && (
              <Button onClick={() => navigate('/new-project')} className="bg-gradient-warm">
                <Plus className="h-4 w-4 mr-2" />
                New Project
              </Button>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
