/** Which vocabulary a tag belongs to. Matches the {kind} segment of the admin tag routes. */
export type TagKind = 'style' | 'music';

export interface TagUsage {
  id: number;
  name: string;
  /** What the name slugifies to. For a style that's the {style} segment of every dance URL under it. */
  slug: string;
  description?: string;
  /** Dances carrying this tag. Zero means nothing links to it. */
  danceCount: number;
}

export interface TagAdmin {
  styles: TagUsage[];
  musicalStyles: TagUsage[];
}

/** What a merge did. The numbers are the only way to check it did what you meant. */
export interface MergeTagResult {
  sourceName: string;
  targetName: string;
  moved: number;
  /** Dances that already carried both tags, so the source link was just dropped. */
  alreadyTagged: number;
  /** Slugs rewritten afterwards — folding two styles can collide slugs inside the survivor. */
  reslugged: number;
}
