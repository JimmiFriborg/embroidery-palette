import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { useToast } from '@/hooks/use-toast';
import { 
  ArrowLeft, 
  User,
  Palette,
  Square,
  Info,
  LogOut,
  Trash2,
  Moon,
  Sun,
  HelpCircle
} from 'lucide-react';

type HoopSize = '100x100' | '70x70';

export default function Settings() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [defaultHoopSize, setDefaultHoopSize] = useState<HoopSize>('100x100');
  const [defaultThreadCount, setDefaultThreadCount] = useState(6);
  const [darkMode, setDarkMode] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);

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

  const handleDarkMode = (enabled: boolean) => {
    setDarkMode(enabled);
    document.documentElement.classList.toggle('dark', enabled);
    toast({
      title: enabled ? 'Dark mode enabled' : 'Light mode enabled',
      description: 'Theme preference saved.',
    });
  };

  const handleResetOnboarding = () => {
    localStorage.removeItem('stitchflow_onboarding_complete');
    setShowOnboarding(true);
    toast({
      title: 'Onboarding reset',
      description: 'You\'ll see the welcome guide on your next visit.',
    });
  };

  return (
    <div className="min-h-screen bg-gradient-soft pb-8">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-sm border-b border-border">
        <div className="container flex items-center h-14 px-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="ml-3 font-display font-semibold">Settings</h1>
        </div>
      </header>

      <main className="container px-4 py-6 space-y-6">
        {/* Account */}
        <Card className="border-0 shadow-soft">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-display flex items-center gap-2">
              <User className="h-5 w-5 text-primary" />
              Account
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="font-medium">{user?.name || 'User'}</p>
                <p className="text-sm text-muted-foreground">{user?.email}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Default Project Settings */}
        <Card className="border-0 shadow-soft">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-display flex items-center gap-2">
              <Palette className="h-5 w-5 text-primary" />
              Default Project Settings
            </CardTitle>
            <CardDescription>These settings apply to new projects</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Default Hoop Size */}
            <div className="space-y-3">
              <Label>Default Hoop Size</Label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  className={`relative p-3 rounded-xl border-2 transition-all ${
                    defaultHoopSize === '100x100'
                      ? 'border-primary bg-primary/5'
                      : 'border-muted hover:border-muted-foreground/50'
                  }`}
                  onClick={() => setDefaultHoopSize('100x100')}
                >
                  <div className="flex items-center gap-3">
                    <Square className="h-5 w-5" />
                    <span className="font-medium">100×100mm</span>
                  </div>
                  {defaultHoopSize === '100x100' && (
                    <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-primary" />
                  )}
                </button>
                <button
                  type="button"
                  className={`relative p-3 rounded-xl border-2 transition-all ${
                    defaultHoopSize === '70x70'
                      ? 'border-primary bg-primary/5'
                      : 'border-muted hover:border-muted-foreground/50'
                  }`}
                  onClick={() => setDefaultHoopSize('70x70')}
                >
                  <div className="flex items-center gap-3">
                    <Square className="h-4 w-4" />
                    <span className="font-medium">70×70mm</span>
                  </div>
                  {defaultHoopSize === '70x70' && (
                    <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-primary" />
                  )}
                </button>
              </div>
            </div>

            {/* Default Thread Count */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Default Thread Colors</Label>
                <span className="text-sm font-semibold text-primary">{defaultThreadCount}</span>
              </div>
              <Slider
                value={[defaultThreadCount]}
                onValueChange={(value) => setDefaultThreadCount(value[0])}
                min={2}
                max={15}
                step={1}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Simple (2)</span>
                <span>Detailed (15)</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Appearance */}
        <Card className="border-0 shadow-soft">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-display flex items-center gap-2">
              {darkMode ? <Moon className="h-5 w-5 text-primary" /> : <Sun className="h-5 w-5 text-primary" />}
              Appearance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="font-medium">Dark Mode</p>
                <p className="text-sm text-muted-foreground">Switch to dark theme</p>
              </div>
              <Switch
                checked={darkMode}
                onCheckedChange={handleDarkMode}
              />
            </div>
          </CardContent>
        </Card>

        {/* Help & Support */}
        <Card className="border-0 shadow-soft">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-display flex items-center gap-2">
              <HelpCircle className="h-5 w-5 text-primary" />
              Help & Support
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button 
              variant="ghost" 
              className="w-full justify-start"
              onClick={handleResetOnboarding}
            >
              <Info className="h-4 w-4 mr-3" />
              Show Welcome Guide Again
            </Button>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="border-0 shadow-soft border-destructive/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-display text-destructive">Danger Zone</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button 
              variant="outline" 
              className="w-full justify-start text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={handleLogout}
            >
              <LogOut className="h-4 w-4 mr-3" />
              Log Out
            </Button>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
