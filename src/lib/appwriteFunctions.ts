import { ID, Functions } from 'appwrite';
import client from './appwrite';

// Appwrite function endpoints (fallback for direct calls)
const APPWRITE_ENDPOINT = import.meta.env.VITE_APPWRITE_ENDPOINT || 'https://cloud.appwrite.io/v1';
const APPWRITE_PROJECT_ID = import.meta.env.VITE_APPWRITE_PROJECT_ID || '';

// Appwrite SDK Functions client
const functions = new Functions(client);

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
 * Execute an Appwrite function using the SDK
 */
async function executeFunction<T>(functionId: string, data: object): Promise<T> {
  const execution = await functions.createExecution(
    functionId,
    JSON.stringify(data),  // body
    false,                 // async
    '/',                   // path
    'POST',               // method
    { 'Content-Type': 'application/json' }  // headers
  );

  if (execution.responseStatusCode >= 400) {
    throw new Error(execution.responseBody || `Function returned status ${execution.responseStatusCode}`);
  }

  // Parse the function response
  if (execution.responseBody) {
    return JSON.parse(execution.responseBody);
  }

  return execution as unknown as T;
}

// Async execution with polling (for long-running functions like PES export)
async function executeFunctionAndWait<T>(
  functionId: string,
  data: object,
  timeoutMs = 120000,
  pollMs = 1500
): Promise<T> {
  const execution = await functions.createExecution(
    functionId,
    JSON.stringify(data),
    true,   // async
    '/',
    'POST',
    { 'Content-Type': 'application/json' }
  );

  const start = Date.now();
  let status = execution.status;
  let exec = execution;

  while (status !== 'completed') {
    if (Date.now() - start > timeoutMs) {
      throw new Error('Function execution timed out. Please try again.');
    }
    await new Promise(r => setTimeout(r, pollMs));
    exec = await functions.getExecution(functionId, exec.$id);
    status = exec.status;
    if (status === 'failed') {
      throw new Error(exec.responseBody || 'Function execution failed');
    }
  }

  if (exec.responseStatusCode >= 400) {
    throw new Error(exec.responseBody || `Function returned status ${exec.responseStatusCode}`);
  }

  if (exec.responseBody) {
    return JSON.parse(exec.responseBody);
  }

  return exec as unknown as T;
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
    // PES generation can be slow → use async + polling to avoid 30s timeout
    const response = await executeFunctionAndWait<GeneratePesResponse>('generate-pes', payload, 180000, 2000);
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
