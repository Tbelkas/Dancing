import { VideoSegment } from './video.model';

/** A choreography video that lives on the user's own computer. The server knows only
 *  the file's name and the loop time slots — the video itself never leaves the device. */
export interface Choreo {
  id: number;
  name: string;
  fileName: string;
  durationSeconds?: number;
  dateAdded: string;
  loops: VideoSegment[];
}
