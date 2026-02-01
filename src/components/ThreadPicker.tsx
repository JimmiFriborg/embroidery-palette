import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { BROTHER_THREADS, getThreadCategories, searchThreads, findClosestThread, type BrotherThread } from '@/lib/brotherThreads';
import { Search, Sparkles, X } from 'lucide-react';

interface ThreadPickerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (thread: BrotherThread) => void;
  currentColor?: string;
  allowSkip?: boolean;
}

export function ThreadPicker({ isOpen, onClose, onSelect, currentColor, allowSkip = true }: ThreadPickerProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  
  const categories = useMemo(() => getThreadCategories(), []);
  
  const suggestedThread = useMemo(() => {
    if (currentColor) {
      return findClosestThread(currentColor);
    }
    return null;
  }, [currentColor]);

  const filteredThreads = useMemo(() => {
    let threads = BROTHER_THREADS;
    
    if (searchQuery) {
      threads = searchThreads(searchQuery);
    } else if (selectedCategory) {
      threads = threads.filter(t => t.category === selectedCategory);
    }
    
    return threads;
  }, [searchQuery, selectedCategory]);

  const handleSelect = (thread: BrotherThread) => {
    onSelect(thread);
    onClose();
    setSearchQuery('');
    setSelectedCategory(null);
  };

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="bottom" className="h-[85vh] rounded-t-2xl">
        <SheetHeader className="pb-4">
          <SheetTitle className="flex items-center gap-2 font-display">
            Brother Thread Picker
          </SheetTitle>
        </SheetHeader>

        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by name or number..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setSelectedCategory(null);
            }}
            className="pl-9"
          />
          {searchQuery && (
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
              onClick={() => setSearchQuery('')}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Skip Option */}
        {allowSkip && !searchQuery && !selectedCategory && (
          <div className="mb-4 p-3 rounded-xl bg-destructive/5 border-2 border-destructive/20">
            <button
              onClick={() => handleSelect({ number: 'SKIP', name: 'Skip color', hex: '#FFFFFF', category: 'Skip' })}
              className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-destructive/10 transition-colors"
            >
              <div className="w-10 h-10 rounded-lg border-2 border-dashed border-destructive/40 flex items-center justify-center text-destructive font-bold">
                —
              </div>
              <div className="text-left">
                <div className="font-semibold text-destructive">Skip this color</div>
                <div className="text-xs text-muted-foreground">Do not stitch this color</div>
              </div>
            </button>
          </div>
        )}

        {/* Suggested Thread */}
        {suggestedThread && !searchQuery && !selectedCategory && (
          <div className="mb-4 p-3 rounded-xl bg-primary/5 border-2 border-primary/20">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium text-primary">Best Match</span>
            </div>
            <button
              onClick={() => handleSelect(suggestedThread)}
              className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-primary/10 transition-colors"
            >
              <div
                className="w-10 h-10 rounded-lg shadow-inner flex-shrink-0"
                style={{ backgroundColor: suggestedThread.hex }}
              />
              <div className="text-left">
                <div className="font-semibold">#{suggestedThread.number} {suggestedThread.name}</div>
                <div className="text-xs text-muted-foreground">{suggestedThread.category}</div>
              </div>
              {currentColor && (
                <div className="ml-auto flex items-center gap-1">
                  <div
                    className="w-5 h-5 rounded border"
                    style={{ backgroundColor: currentColor }}
                  />
                  <span className="text-xs text-muted-foreground">→</span>
                  <div
                    className="w-5 h-5 rounded border"
                    style={{ backgroundColor: suggestedThread.hex }}
                  />
                </div>
              )}
            </button>
          </div>
        )}

        {/* Category Chips */}
        {!searchQuery && (
          <div className="flex gap-2 overflow-x-auto pb-3 mb-3 -mx-4 px-4 scrollbar-hide">
            <Button
              variant={selectedCategory === null ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(null)}
              className="flex-shrink-0"
            >
              All
            </Button>
            {categories.map((category) => (
              <Button
                key={category}
                variant={selectedCategory === category ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedCategory(category)}
                className="flex-shrink-0"
              >
                {category}
              </Button>
            ))}
          </div>
        )}

        {/* Thread List */}
        <ScrollArea className="h-[calc(85vh-280px)]">
          <div className="grid grid-cols-2 gap-2 pb-4">
            {filteredThreads.map((thread) => (
              <button
                key={`${thread.number}-${thread.name}`}
                onClick={() => handleSelect(thread)}
                className="flex items-center gap-2 p-2.5 rounded-lg border border-muted hover:border-primary hover:bg-primary/5 transition-all text-left"
              >
                <div
                  className="w-8 h-8 rounded-lg shadow-inner flex-shrink-0"
                  style={{ backgroundColor: thread.hex }}
                />
                <div className="min-w-0">
                  <div className="text-xs text-muted-foreground">#{thread.number}</div>
                  <div className="text-sm font-medium truncate">{thread.name}</div>
                </div>
              </button>
            ))}
          </div>
          
          {filteredThreads.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <p>No threads found</p>
              <p className="text-sm">Try a different search term</p>
            </div>
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
