// Brother Embroidery Thread Database
// Official Brother thread colors for the PP1 embroidery machine

export interface BrotherThread {
  number: string;
  name: string;
  hex: string;
  category: string;
}

// Brother Embroidery Thread palette (common colors for PP1)
export const BROTHER_THREADS: BrotherThread[] = [
  // Whites & Creams
  { number: '001', name: 'White', hex: '#FFFFFF', category: 'Whites' },
  { number: '002', name: 'Linen White', hex: '#FAF0E6', category: 'Whites' },
  { number: '010', name: 'Cream', hex: '#FFFDD0', category: 'Whites' },
  { number: '027', name: 'Ivory', hex: '#FFFFF0', category: 'Whites' },
  
  // Reds
  { number: '030', name: 'Salmon Pink', hex: '#FA8072', category: 'Reds' },
  { number: '032', name: 'Flesh Pink', hex: '#FFCBA4', category: 'Reds' },
  { number: '058', name: 'Red Wine', hex: '#722F37', category: 'Reds' },
  { number: '070', name: 'Deep Rose', hex: '#C76574', category: 'Reds' },
  { number: '086', name: 'Light Rose', hex: '#FFB6C1', category: 'Reds' },
  { number: '202', name: 'Red', hex: '#FF0000', category: 'Reds' },
  { number: '206', name: 'Dark Red', hex: '#8B0000', category: 'Reds' },
  { number: '207', name: 'Cherry Red', hex: '#DE3163', category: 'Reds' },
  { number: '209', name: 'Crimson', hex: '#DC143C', category: 'Reds' },
  { number: '800', name: 'Vermilion', hex: '#E34234', category: 'Reds' },
  
  // Oranges
  { number: '126', name: 'Pumpkin', hex: '#FF7518', category: 'Oranges' },
  { number: '205', name: 'Tangerine', hex: '#FF9966', category: 'Oranges' },
  { number: '208', name: 'Orange', hex: '#FFA500', category: 'Oranges' },
  { number: '214', name: 'Deep Orange', hex: '#FF4500', category: 'Oranges' },
  { number: '308', name: 'Rust', hex: '#B7410E', category: 'Oranges' },
  
  // Yellows
  { number: '205', name: 'Pale Yellow', hex: '#FFFFE0', category: 'Yellows' },
  { number: '208', name: 'Lemon Yellow', hex: '#FFFACD', category: 'Yellows' },
  { number: '209', name: 'Canary Yellow', hex: '#FFEF00', category: 'Yellows' },
  { number: '214', name: 'Gold', hex: '#FFD700', category: 'Yellows' },
  { number: '348', name: 'Amber', hex: '#FFBF00', category: 'Yellows' },
  { number: '512', name: 'Bright Yellow', hex: '#FFFF00', category: 'Yellows' },
  { number: '513', name: 'Sunflower', hex: '#FFDA03', category: 'Yellows' },
  
  // Greens
  { number: '027', name: 'Mint Green', hex: '#98FF98', category: 'Greens' },
  { number: '206', name: 'Lime Green', hex: '#32CD32', category: 'Greens' },
  { number: '208', name: 'Kelly Green', hex: '#4CBB17', category: 'Greens' },
  { number: '232', name: 'Forest Green', hex: '#228B22', category: 'Greens' },
  { number: '328', name: 'Sage', hex: '#9DC183', category: 'Greens' },
  { number: '415', name: 'Olive', hex: '#808000', category: 'Greens' },
  { number: '507', name: 'Moss Green', hex: '#8A9A5B', category: 'Greens' },
  { number: '515', name: 'Emerald', hex: '#50C878', category: 'Greens' },
  { number: '534', name: 'Teal', hex: '#008080', category: 'Greens' },
  { number: '808', name: 'Dark Green', hex: '#006400', category: 'Greens' },
  
  // Blues
  { number: '017', name: 'Light Blue', hex: '#ADD8E6', category: 'Blues' },
  { number: '019', name: 'Sky Blue', hex: '#87CEEB', category: 'Blues' },
  { number: '070', name: 'Baby Blue', hex: '#89CFF0', category: 'Blues' },
  { number: '405', name: 'Powder Blue', hex: '#B0E0E6', category: 'Blues' },
  { number: '406', name: 'Royal Blue', hex: '#4169E1', category: 'Blues' },
  { number: '415', name: 'Navy', hex: '#000080', category: 'Blues' },
  { number: '420', name: 'Deep Blue', hex: '#00008B', category: 'Blues' },
  { number: '502', name: 'Cornflower', hex: '#6495ED', category: 'Blues' },
  { number: '534', name: 'Electric Blue', hex: '#7DF9FF', category: 'Blues' },
  { number: '612', name: 'Turquoise', hex: '#40E0D0', category: 'Blues' },
  { number: '613', name: 'Aqua', hex: '#00FFFF', category: 'Blues' },
  
  // Purples
  { number: '030', name: 'Lavender', hex: '#E6E6FA', category: 'Purples' },
  { number: '607', name: 'Light Purple', hex: '#DDA0DD', category: 'Purples' },
  { number: '612', name: 'Violet', hex: '#8F00FF', category: 'Purples' },
  { number: '614', name: 'Purple', hex: '#800080', category: 'Purples' },
  { number: '620', name: 'Deep Purple', hex: '#301934', category: 'Purples' },
  { number: '810', name: 'Magenta', hex: '#FF00FF', category: 'Purples' },
  { number: '614', name: 'Plum', hex: '#DDA0DD', category: 'Purples' },
  
  // Pinks
  { number: '085', name: 'Light Pink', hex: '#FFB6C1', category: 'Pinks' },
  { number: '086', name: 'Pink', hex: '#FFC0CB', category: 'Pinks' },
  { number: '124', name: 'Hot Pink', hex: '#FF69B4', category: 'Pinks' },
  { number: '125', name: 'Fuchsia', hex: '#FF00FF', category: 'Pinks' },
  { number: '131', name: 'Dusty Rose', hex: '#C4A4A4', category: 'Pinks' },
  { number: '807', name: 'Coral', hex: '#FF7F50', category: 'Pinks' },
  
  // Browns
  { number: '328', name: 'Beige', hex: '#F5F5DC', category: 'Browns' },
  { number: '348', name: 'Tan', hex: '#D2B48C', category: 'Browns' },
  { number: '457', name: 'Light Brown', hex: '#C4A484', category: 'Browns' },
  { number: '459', name: 'Medium Brown', hex: '#8B4513', category: 'Browns' },
  { number: '461', name: 'Dark Brown', hex: '#654321', category: 'Browns' },
  { number: '476', name: 'Chocolate', hex: '#7B3F00', category: 'Browns' },
  { number: '514', name: 'Espresso', hex: '#3C1414', category: 'Browns' },
  
  // Grays & Black
  { number: '399', name: 'Light Gray', hex: '#D3D3D3', category: 'Grays' },
  { number: '415', name: 'Medium Gray', hex: '#808080', category: 'Grays' },
  { number: '418', name: 'Dark Gray', hex: '#A9A9A9', category: 'Grays' },
  { number: '420', name: 'Charcoal', hex: '#36454F', category: 'Grays' },
  { number: '900', name: 'Black', hex: '#000000', category: 'Grays' },
  
  // Metallics (if available on PP1)
  { number: '990', name: 'Metallic Gold', hex: '#D4AF37', category: 'Metallics' },
  { number: '991', name: 'Metallic Silver', hex: '#C0C0C0', category: 'Metallics' },
];

// Get thread categories
export const getThreadCategories = (): string[] => {
  return [...new Set(BROTHER_THREADS.map(t => t.category))];
};

// Search threads by name or number
export const searchThreads = (query: string): BrotherThread[] => {
  const lowerQuery = query.toLowerCase();
  return BROTHER_THREADS.filter(
    t => t.name.toLowerCase().includes(lowerQuery) || t.number.includes(query)
  );
};

// Find closest thread to a given hex color
export const findClosestThread = (hex: string): BrotherThread => {
  const targetRgb = hexToRgb(hex);
  
  let closestThread = BROTHER_THREADS[0];
  let minDistance = Infinity;
  
  for (const thread of BROTHER_THREADS) {
    const threadRgb = hexToRgb(thread.hex);
    const distance = colorDistance(targetRgb, threadRgb);
    
    if (distance < minDistance) {
      minDistance = distance;
      closestThread = thread;
    }
  }
  
  return closestThread;
};

// Convert hex to RGB
function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : { r: 0, g: 0, b: 0 };
}

// Calculate color distance (simple Euclidean in RGB space)
function colorDistance(
  c1: { r: number; g: number; b: number },
  c2: { r: number; g: number; b: number }
): number {
  return Math.sqrt(
    Math.pow(c1.r - c2.r, 2) +
    Math.pow(c1.g - c2.g, 2) +
    Math.pow(c1.b - c2.b, 2)
  );
}

export default BROTHER_THREADS;
