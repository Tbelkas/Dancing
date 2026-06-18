/** Full set of difficulty levels — used in edit/create forms where 'None' is a valid selection. */
export const DIFFICULTY_LEVELS = ['None', 'Beginner', 'Intermediate', 'Advanced'] as const;

/** Difficulty options for filter UI — excludes 'None' since it isn't a meaningful filter target. */
export const DIFFICULTY_FILTER_OPTIONS = ['Beginner', 'Intermediate', 'Advanced'] as const;
