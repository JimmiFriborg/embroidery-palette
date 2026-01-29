import { cn } from '@/lib/utils';

interface LogoProps {
  className?: string;
  showText?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function Logo({ className, showText = true, size = 'md' }: LogoProps) {
  const sizes = {
    sm: { icon: 'w-8 h-8', text: 'text-lg' },
    md: { icon: 'w-10 h-10', text: 'text-xl' },
    lg: { icon: 'w-14 h-14', text: 'text-3xl' },
  };

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {/* Needle & Thread Icon */}
      <div className={cn('relative', sizes[size].icon)}>
        <svg
          viewBox="0 0 48 48"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full"
        >
          {/* Thread spool body */}
          <ellipse
            cx="24"
            cy="32"
            rx="12"
            ry="8"
            className="fill-primary/20 stroke-primary"
            strokeWidth="2"
          />
          <rect
            x="12"
            y="16"
            width="24"
            height="16"
            rx="2"
            className="fill-secondary stroke-primary"
            strokeWidth="2"
          />
          <ellipse
            cx="24"
            cy="16"
            rx="12"
            ry="8"
            className="fill-stitch-cream stroke-primary"
            strokeWidth="2"
          />
          
          {/* Thread wrapping */}
          <path
            d="M14 20 Q24 18 34 20"
            className="stroke-primary"
            strokeWidth="1.5"
            fill="none"
          />
          <path
            d="M14 24 Q24 22 34 24"
            className="stroke-primary"
            strokeWidth="1.5"
            fill="none"
          />
          <path
            d="M14 28 Q24 26 34 28"
            className="stroke-primary"
            strokeWidth="1.5"
            fill="none"
          />
          
          {/* Needle */}
          <path
            d="M36 8 L42 2"
            className="stroke-stitch-navy"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <ellipse
            cx="43"
            cy="1"
            rx="1.5"
            ry="1"
            className="fill-stitch-navy"
            transform="rotate(-45 43 1)"
          />
          
          {/* Thread from needle */}
          <path
            d="M36 8 Q32 12 28 14"
            className="stroke-primary"
            strokeWidth="1.5"
            fill="none"
            strokeDasharray="3 2"
          />
        </svg>
      </div>
      
      {showText && (
        <span className={cn('font-display font-bold text-gradient-warm', sizes[size].text)}>
          StitchFlow
        </span>
      )}
    </div>
  );
}
