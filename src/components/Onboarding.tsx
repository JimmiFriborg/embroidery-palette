import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { 
  Camera, 
  Palette, 
  Download, 
  Sparkles,
  ChevronRight,
  ChevronLeft,
  X
} from 'lucide-react';

interface OnboardingProps {
  onComplete: () => void;
}

const STEPS = [
  {
    icon: Camera,
    title: 'Upload Your Image',
    description: 'Take a photo or upload an image you want to turn into embroidery. Works best with clear outlines and distinct colors.',
    color: 'from-primary to-accent',
  },
  {
    icon: Sparkles,
    title: 'Smart Processing',
    description: 'Our AI automatically removes backgrounds and reduces colors to match your thread count. No manual editing needed!',
    color: 'from-accent to-secondary',
  },
  {
    icon: Palette,
    title: 'Map Brother Threads',
    description: 'Match each detected color to official Brother thread numbers. We suggest the closest matches automatically.',
    color: 'from-secondary to-primary',
  },
  {
    icon: Download,
    title: 'Export to PES',
    description: 'Download your embroidery-ready .pes file and load it directly onto your Brother PP1 machine.',
    color: 'from-primary to-accent',
  },
];

export function Onboarding({ onComplete }: OnboardingProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [isVisible, setIsVisible] = useState(true);

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleComplete();
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = () => {
    localStorage.setItem('stitchflow_onboarding_complete', 'true');
    setIsVisible(false);
    setTimeout(onComplete, 300);
  };

  const handleSkip = () => {
    handleComplete();
  };

  const step = STEPS[currentStep];
  const Icon = step.icon;

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/95 backdrop-blur-sm animate-fade-in">
      <div className="absolute inset-0 bg-gradient-soft" />
      
      <div className="relative w-full max-w-md mx-4">
        {/* Skip Button */}
        <button
          onClick={handleSkip}
          className="absolute -top-12 right-0 text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1 text-sm"
        >
          Skip
          <X className="h-4 w-4" />
        </button>

        {/* Card */}
        <div className="bg-card rounded-2xl shadow-craft overflow-hidden">
          {/* Icon Area */}
          <div className={`h-48 flex items-center justify-center bg-gradient-to-br ${step.color}`}>
            <div className="w-24 h-24 rounded-full bg-white/20 flex items-center justify-center backdrop-blur-sm animate-scale-in">
              <Icon className="h-12 w-12 text-white" />
            </div>
          </div>

          {/* Content */}
          <div className="p-6 text-center">
            <h2 className="text-2xl font-display font-bold mb-3">{step.title}</h2>
            <p className="text-muted-foreground leading-relaxed">{step.description}</p>
          </div>

          {/* Progress Dots */}
          <div className="flex justify-center gap-2 pb-4">
            {STEPS.map((_, index) => (
              <button
                key={index}
                onClick={() => setCurrentStep(index)}
                className={`w-2 h-2 rounded-full transition-all ${
                  index === currentStep
                    ? 'bg-primary w-6'
                    : 'bg-muted-foreground/30 hover:bg-muted-foreground/50'
                }`}
              />
            ))}
          </div>

          {/* Navigation */}
          <div className="flex gap-3 p-4 border-t border-border">
            <Button
              variant="outline"
              onClick={handlePrev}
              disabled={currentStep === 0}
              className="flex-1"
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Back
            </Button>
            <Button
              onClick={handleNext}
              className="flex-1 bg-gradient-warm"
            >
              {currentStep === STEPS.length - 1 ? 'Get Started' : 'Next'}
              {currentStep < STEPS.length - 1 && <ChevronRight className="h-4 w-4 ml-1" />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
