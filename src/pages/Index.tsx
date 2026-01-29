import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Logo } from '@/components/Logo';
import { Button } from '@/components/ui/button';
import { Loader2, ArrowRight, Sparkles, Palette, Download } from 'lucide-react';

export default function Index() {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, isLoading, navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-soft">
        <div className="text-center">
          <Logo size="lg" className="justify-center mb-6" />
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-soft overflow-hidden">
      {/* Decorative stitch borders */}
      <div className="absolute top-0 left-0 right-0 h-1 stitch-border" />
      <div className="absolute bottom-0 left-0 right-0 h-1 stitch-border" />

      {/* Hero Section */}
      <div className="container px-4 py-12 min-h-screen flex flex-col">
        {/* Logo */}
        <div className="flex justify-center mb-12 animate-fade-in">
          <Logo size="lg" />
        </div>

        {/* Hero Content */}
        <div className="flex-1 flex flex-col items-center justify-center text-center max-w-lg mx-auto">
          <h1 className="text-4xl md:text-5xl font-display font-bold mb-4 animate-fade-in">
            Turn Images into
            <span className="text-gradient-warm block mt-2">Embroidery Magic</span>
          </h1>
          
          <p className="text-lg text-muted-foreground mb-8 animate-fade-in" style={{ animationDelay: '0.1s' }}>
            Convert your photos and artwork into beautiful embroidery-ready .pes files 
            for your Brother PP1 machine.
          </p>

          <Button 
            size="lg"
            className="h-14 px-8 text-lg font-semibold bg-gradient-warm hover:opacity-90 transition-opacity animate-fade-in"
            style={{ animationDelay: '0.2s' }}
            onClick={() => navigate('/auth')}
          >
            Get Started
            <ArrowRight className="ml-2 h-5 w-5" />
          </Button>
        </div>

        {/* Features */}
        <div className="grid grid-cols-3 gap-4 mt-12 pb-8">
          <div className="text-center animate-fade-in" style={{ animationDelay: '0.3s' }}>
            <div className="w-12 h-12 rounded-full bg-secondary mx-auto flex items-center justify-center mb-2">
              <Sparkles className="h-5 w-5 text-secondary-foreground" />
            </div>
            <p className="text-sm font-medium">Smart Color Detection</p>
          </div>
          <div className="text-center animate-fade-in" style={{ animationDelay: '0.4s' }}>
            <div className="w-12 h-12 rounded-full bg-secondary mx-auto flex items-center justify-center mb-2">
              <Palette className="h-5 w-5 text-secondary-foreground" />
            </div>
            <p className="text-sm font-medium">Brother Thread Match</p>
          </div>
          <div className="text-center animate-fade-in" style={{ animationDelay: '0.5s' }}>
            <div className="w-12 h-12 rounded-full bg-secondary mx-auto flex items-center justify-center mb-2">
              <Download className="h-5 w-5 text-secondary-foreground" />
            </div>
            <p className="text-sm font-medium">.PES Export</p>
          </div>
        </div>

        {/* Decorative thread spools */}
        <div className="flex justify-center gap-2 pb-4">
          {['terracotta', 'sage', 'gold', 'blush', 'navy'].map((color, i) => (
            <div
              key={color}
              className={`w-3 h-3 rounded-full bg-stitch-${color} animate-stitch-pulse`}
              style={{ animationDelay: `${i * 0.2}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
