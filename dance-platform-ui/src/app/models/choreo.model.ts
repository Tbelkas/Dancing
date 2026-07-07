import { VideoSegment } from './video.model';

/** A choreography video that lives on the user's own computer. The server knows only
 *  the file's name and the loop time slots — the video itself never leaves the device. */
export interface Choreo {
  id: number;
  name: string;
  fileName: string;
  durationSeconds?: number;
  /** Clockwise playback rotation (0 | 90 | 180 | 270) for sideways phone recordings. */
  rotationDegrees: number;
  dateAdded: string;
  loops: VideoSegment[];
}
