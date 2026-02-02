// Brother Embroidery Thread Database
// Official Brother 61-color embroidery thread palette
// Source: EduTech Wiki Brother Thread Chart

export interface BrotherThread {
  number: string;
  name: string;
  hex: string;
  category: string;
}

export const BROTHER_THREADS: BrotherThread[] = [
  // Reds & Pinks
  { number: '800', name: 'Red', hex: '#ED171F', category: 'Reds & Pinks' },
  { number: '085', name: 'Pink', hex: '#F993BC', category: 'Reds & Pinks' },
  { number: '086', name: 'Deep Rose', hex: '#F64A8A', category: 'Reds & Pinks' },
  { number: '124', name: 'Flesh Pink', hex: '#FDD9DE', category: 'Reds & Pinks' },
  { number: '107', name: 'Dark Fuchsia', hex: '#C70156', category: 'Reds & Pinks' },
  { number: '030', name: 'Vermillion', hex: '#FE370F', category: 'Reds & Pinks' },
  { number: '807', name: 'Carmine', hex: '#F73866', category: 'Reds & Pinks' },
  { number: '079', name: 'Salmon Pink', hex: '#FCBBC4', category: 'Reds & Pinks' },
  { number: '333', name: 'Amber Red', hex: '#B54C64', category: 'Reds & Pinks' },

  // Oranges & Yellows
  { number: '202', name: 'Lemon Yellow', hex: '#F0F970', category: 'Oranges & Yellows' },
  { number: '205', name: 'Yellow', hex: '#FFFF00', category: 'Oranges & Yellows' },
  { number: '206', name: 'Harvest Gold', hex: '#FFD911', category: 'Oranges & Yellows' },
  { number: '208', name: 'Orange', hex: '#FEBA35', category: 'Oranges & Yellows' },
  { number: '126', name: 'Pumpkin', hex: '#FEB343', category: 'Oranges & Yellows' },
  { number: '209', name: 'Tangerine', hex: '#FE9E32', category: 'Oranges & Yellows' },
  { number: '010', name: 'Cream Brown', hex: '#FFFFB3', category: 'Oranges & Yellows' },
  { number: '812', name: 'Cream Yellow', hex: '#FFF08D', category: 'Oranges & Yellows' },
  { number: '214', name: 'Deep Gold', hex: '#E8A900', category: 'Oranges & Yellows' },

  // Browns & Neutrals
  { number: '348', name: 'Khaki', hex: '#D0A660', category: 'Browns & Neutrals' },
  { number: '328', name: 'Brass', hex: '#BA9800', category: 'Browns & Neutrals' },
  { number: '307', name: 'Linen', hex: '#FEE3C5', category: 'Browns & Neutrals' },
  { number: '058', name: 'Dark Brown', hex: '#2A1301', category: 'Browns & Neutrals' },
  { number: '337', name: 'Reddish Brown', hex: '#D15C00', category: 'Browns & Neutrals' },
  { number: '339', name: 'Clay Brown', hex: '#D15400', category: 'Browns & Neutrals' },
  { number: '843', name: 'Beige', hex: '#EFE3B9', category: 'Browns & Neutrals' },
  { number: '399', name: 'Warm Gray', hex: '#D8CCC6', category: 'Browns & Neutrals' },
  { number: '330', name: 'Russet Brown', hex: '#7D6F00', category: 'Browns & Neutrals' },
  { number: '323', name: 'Light Brown', hex: '#B27624', category: 'Browns & Neutrals' },

  // Greens
  { number: '542', name: 'Seacrest', hex: '#A8DDC4', category: 'Greens' },
  { number: '502', name: 'Mint Green', hex: '#9ED67D', category: 'Greens' },
  { number: '509', name: 'Leaf Green', hex: '#66BA49', category: 'Greens' },
  { number: '519', name: 'Olive Green', hex: '#132B1A', category: 'Greens' },
  { number: '517', name: 'Dark Olive', hex: '#435607', category: 'Greens' },
  { number: '534', name: 'Teal Green', hex: '#008777', category: 'Greens' },
  { number: '507', name: 'Emerald Green', hex: '#00673E', category: 'Greens' },
  { number: '808', name: 'Deep Green', hex: '#003822', category: 'Greens' },
  { number: '027', name: 'Fresh Green', hex: '#E3F35B', category: 'Greens' },
  { number: '513', name: 'Lime Green', hex: '#70BC1F', category: 'Greens' },
  { number: '515', name: 'Moss Green', hex: '#2F7E20', category: 'Greens' },

  // Blues
  { number: '405', name: 'Blue', hex: '#0A55A3', category: 'Blues' },
  { number: '406', name: 'Ultra Marine', hex: '#0B3D91', category: 'Blues' },
  { number: '017', name: 'Light Blue', hex: '#A8DEEB', category: 'Blues' },
  { number: '019', name: 'Sky Blue', hex: '#2584BB', category: 'Blues' },
  { number: '420', name: 'Electric Blue', hex: '#095BA6', category: 'Blues' },
  { number: '415', name: 'Peacock Blue', hex: '#134A76', category: 'Blues' },
  { number: '007', name: 'Prussian Blue', hex: '#0E1F7C', category: 'Blues' },
  { number: '070', name: 'Cornflower Blue', hex: '#4B6BAF', category: 'Blues' },

  // Purples
  { number: '869', name: 'Royal Purple', hex: '#770176', category: 'Purples' },
  { number: '620', name: 'Magenta', hex: '#913697', category: 'Purples' },
  { number: '810', name: 'Light Lilac', hex: '#E49ACB', category: 'Purples' },
  { number: '612', name: 'Lilac', hex: '#915FAC', category: 'Purples' },
  { number: '613', name: 'Violet', hex: '#6A1C8A', category: 'Purples' },
  { number: '614', name: 'Purple', hex: '#4E2990', category: 'Purples' },
  { number: '804', name: 'Lavender', hex: '#B2AFD4', category: 'Purples' },
  { number: '607', name: 'Wisteria Violet', hex: '#686AB0', category: 'Purples' },

  // Grays & Black
  { number: '900', name: 'Black', hex: '#000000', category: 'Grays & Black' },
  { number: '001', name: 'White', hex: '#F0F0F0', category: 'Grays & Black' },
  { number: '704', name: 'Pewter', hex: '#4F5556', category: 'Grays & Black' },
  { number: '707', name: 'Dark Gray', hex: '#293133', category: 'Grays & Black' },
  { number: '005', name: 'Silver', hex: '#A8A8A8', category: 'Grays & Black' },
  { number: '817', name: 'Gray', hex: '#878787', category: 'Grays & Black' },
];

// ---------------------------------------------------------------------------
// sRGB → CIELAB conversion (inline, no dependencies)
// ---------------------------------------------------------------------------

function hexToRgb(hex: string): [number, number, number] {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return [0, 0, 0];
  return [
    parseInt(result[1], 16),
    parseInt(result[2], 16),
    parseInt(result[3], 16),
  ];
}

/** Linearize an sRGB channel (0-255 → linear 0-1). */
function srgbToLinear(c: number): number {
  const s = c / 255;
  return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}

/** Convert sRGB (0-255 each) to CIELAB [L, a, b]. */
function rgbToLab(r: number, g: number, b: number): [number, number, number] {
  // sRGB → linear RGB
  const rl = srgbToLinear(r);
  const gl = srgbToLinear(g);
  const bl = srgbToLinear(b);

  // Linear RGB → XYZ (D65 illuminant)
  let x = 0.4124564 * rl + 0.3575761 * gl + 0.1804375 * bl;
  let y = 0.2126729 * rl + 0.7151522 * gl + 0.0721750 * bl;
  let z = 0.0193339 * rl + 0.1191920 * gl + 0.9503041 * bl;

  // Normalize to D65 white point
  x /= 0.95047;
  y /= 1.0;
  z /= 1.08883;

  // XYZ → Lab
  const epsilon = 0.008856;
  const kappa = 903.3;

  const fx = x > epsilon ? Math.cbrt(x) : (kappa * x + 16) / 116;
  const fy = y > epsilon ? Math.cbrt(y) : (kappa * y + 16) / 116;
  const fz = z > epsilon ? Math.cbrt(z) : (kappa * z + 16) / 116;

  const L = 116 * fy - 16;
  const a = 500 * (fx - fy);
  const bVal = 200 * (fy - fz);

  return [L, a, bVal];
}

/** CIE76 Delta-E distance between two Lab colors. */
function deltaE(lab1: [number, number, number], lab2: [number, number, number]): number {
  return Math.sqrt(
    (lab1[0] - lab2[0]) ** 2 +
    (lab1[1] - lab2[1]) ** 2 +
    (lab1[2] - lab2[2]) ** 2
  );
}

function hexToLab(hex: string): [number, number, number] {
  const [r, g, b] = hexToRgb(hex);
  return rgbToLab(r, g, b);
}

// Pre-compute Lab values for all threads for fast lookup
const threadLabCache = new Map<string, [number, number, number]>();
for (const thread of BROTHER_THREADS) {
  threadLabCache.set(thread.number, hexToLab(thread.hex));
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** Get all unique thread categories. */
export const getThreadCategories = (): string[] => {
  return [...new Set(BROTHER_THREADS.map(t => t.category))];
};

/** Search threads by name or number (case-insensitive). */
export const searchThreads = (query: string): BrotherThread[] => {
  const lowerQuery = query.toLowerCase();
  return BROTHER_THREADS.filter(
    t => t.name.toLowerCase().includes(lowerQuery) || t.number.includes(query)
  );
};

/**
 * Find the closest Brother thread to a given hex color using
 * CIELAB Delta-E (CIE76) perceptual color distance.
 */
export const findClosestThread = (hex: string): BrotherThread => {
  const targetLab = hexToLab(hex);

  let closestThread = BROTHER_THREADS[0];
  let minDistance = Infinity;

  for (const thread of BROTHER_THREADS) {
    const threadLab = threadLabCache.get(thread.number)!;
    const dist = deltaE(targetLab, threadLab);

    if (dist < minDistance) {
      minDistance = dist;
      closestThread = thread;
    }
  }

  return closestThread;
};

export default BROTHER_THREADS;
