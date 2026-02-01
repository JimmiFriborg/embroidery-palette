import { ID } from 'appwrite';

// Appwrite function endpoints
const APPWRITE_ENDPOINT = import.meta.env.VITE_APPWRITE_ENDPOINT || 'https://cloud.appwrite.io/v1';
const APPWRITE_PROJECT_ID = import.meta.env.VITE_APPWRITE_PROJECT_ID || '';

interface ProcessImagePayload {
  projectId: string;
  imageId: string;
  threadCount: number;
  hoopSize: '100x100' | '70x70';
}

interface ProcessImageResponse {
  success: boolean;
  processedImageId?: string;
  outlineImageId?: string;
  extractedColors?: string[];
  colorCount?: number;
  contourCount?: number;
  regionData?: {
    regions: Array<{
      color: string;
      type: 'fill' | 'outline' | 'detail';
      area_mm2: number;
      contour_count: number;
    }>;
    summary: {
      total_regions: number;
      fill_count: number;
      outline_count: number;
      detail_count: number;
    };
  };
  pipeline?: string;
  error?: string;
}

interface GeneratePesPayload {
  projectId: string;
  colorMappings: Array<{
    originalColor: string;
    threadNumber: string;
    threadName: string;
    threadColor: string;
    skip?: boolean;
  }>;
  hoopSize: '100x100' | '70x70';
  qualityPreset?: 'fast' | 'balanced' | 'quality';
  density?: number;
}

export interface StitchStats {
  stitch_count: number;
  estimated_time_minutes: number;
  color_count: number;
  region_count?: number;
  quality_preset?: string;
  warning?: string | null;
}

interface GeneratePesResponse {
  success: boolean;
  pesFileId?: string;
  previewImageId?: string;
  downloadUrl?: string;
  stats?: StitchStats;
  pipeline?: string;
  error?: string;
}

/**
 * Execute an Appwrite function
 */
async function executeFunction<T>(functionId: string, data: object): Promise<T> {
  const response = await fetch(`${APPWRITE_ENDPOINT}/functions/${functionId}/executions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Appwrite-Project': APPWRITE_PROJECT_ID,
    },
    body: JSON.stringify({
      data: JSON.stringify(data),
      async: false,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Function execution failed: ${errorText}`);
  }

  const result = await response.json();
  
  // Parse the function response
  if (result.responseBody) {
    return JSON.parse(result.responseBody);
  }
  
  return result;
}

/**
 * Process an image for embroidery
 * - Removes background
 * - Quantizes colors
 * - Resizes for hoop
 */
export async function processImage(payload: ProcessImagePayload): Promise<ProcessImageResponse> {
  try {
    const response = await executeFunction<ProcessImageResponse>('process-image', payload);
    return response;
  } catch (error) {
    console.error('Process image error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Generate PES embroidery file
 * - Converts processed image to stitches
 * - Applies thread color mappings
 * - Creates downloadable .pes file
 */
export async function generatePes(payload: GeneratePesPayload): Promise<GeneratePesResponse> {
  try {
    const response = await executeFunction<GeneratePesResponse>('generate-pes', payload);
    return response;
  } catch (error) {
    console.error('Generate PES error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Get the download URL for a PES file
 */
export function getPesDownloadUrl(pesFileId: string): string {
  return `${APPWRITE_ENDPOINT}/storage/buckets/pes_files/files/${pesFileId}/download?project=${APPWRITE_PROJECT_ID}`;
}

/**
 * Get preview URL for stitch simulation
 */
export function getPreviewUrl(previewImageId: string): string {
  return `${APPWRITE_ENDPOINT}/storage/buckets/stitch_previews/files/${previewImageId}/preview?project=${APPWRITE_PROJECT_ID}`;
}
