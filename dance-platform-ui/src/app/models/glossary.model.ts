export interface GlossarySummary {
  styleId: number;
  styleName: string;
  styleSlug: string;
  termCount: number;
  /** Terms that can be marked learned — concepts are excluded. */
  moveCount: number;
  learnedCount: number;
}

export interface Glossary extends GlossarySummary {
  categories: GlossaryCategory[];
}

export interface GlossaryCategory {
  name: string;
  terms: GlossaryTerm[];
}

export interface GlossaryTerm {
  id: number;
  slug: string;
  name: string;
  aliases: string[];
  summary: string;
  description: string;
  steps: string[];
  tips: string[];
  related: { slug: string; name: string }[];
  difficulty: 'None' | 'Beginner' | 'Intermediate' | 'Advanced';
  isLearnable: boolean;
  isLearned: boolean;
  /** The catalog move whose videos demonstrate it; null when there's none yet. */
  dance: {
    id: number;
    slug: string;
    styleSlug: string;
    videoCount: number;
    thumbnailVideoId: string | null;
    thumbnailPlatform: string | null;
  } | null;
}
