import { Client, Account, Databases, Storage, ID, Query } from 'appwrite';

// Appwrite client configuration
const client = new Client();

const endpoint = import.meta.env.VITE_APPWRITE_ENDPOINT;
const projectId = import.meta.env.VITE_APPWRITE_PROJECT_ID;

if (!endpoint || !projectId) {
  console.warn('Appwrite configuration missing. Please set VITE_APPWRITE_ENDPOINT and VITE_APPWRITE_PROJECT_ID');
}

export const APPWRITE_CONFIG = {
  endpoint: endpoint || 'https://cloud.appwrite.io/v1',
  projectId: projectId || '',
};

client
  .setEndpoint(APPWRITE_CONFIG.endpoint)
  .setProject(APPWRITE_CONFIG.projectId);

// Export Appwrite services
export const account = new Account(client);
export const databases = new Databases(client);
export const storage = new Storage(client);

// Export utilities
export { ID, Query };

// Database and collection IDs - configured in Appwrite console
export const DATABASE_ID = 'newstitchdb';
export const COLLECTIONS = {
  PROJECTS: 'projects',
  USER_PREFERENCES: 'user_preferences',
} as const;

export const STORAGE_BUCKETS = {
  IMAGES: 'project_images',
  PES_FILES: 'pes_files',
  PREVIEWS: 'stitch_previews',
} as const;

// Types for StitchFlow
export interface Project {
  $id: string;
  $createdAt: string;
  $updatedAt: string;
  userId: string;
  name: string;
  description?: string;
  originalImageId?: string;
  processedImageId?: string;
  outlineImageId?: string;
  pesFileId?: string;
  previewImageId?: string;
  hoopSize: '100x100' | '70x70';
  threadCount: number;
  colorMappings?: ColorMapping[];
  extractedColors?: string[];
  contourCount?: number;
  status: 'draft' | 'processing' | 'ready' | 'exported';
}

export interface ColorMapping {
  originalColor: string; // hex
  threadNumber: string;
  threadName: string;
  threadColor: string; // hex
}

export interface UserPreferences {
  $id: string;
  userId: string;
  defaultHoopSize: '100x100' | '70x70';
  defaultThreadCount: number;
  savedColorPresets: ColorMapping[][];
}

export default client;
