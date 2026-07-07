import { Pipe, PipeTransform } from '@angular/core';
import { slugify } from '../../core/utils/slug.utils';

/**
 * Builds the routerLink for a dance: /dances/{styleSlug}/{slug}. The style segment disambiguates
 * same-named steps that live in different styles. Falls back to the legacy single-segment
 * /dances/{slug} when no style slug is known (e.g. older locally-cached "Continue learning" entries).
 *
 * The segments are normalised through the shared {@link slugify} (the same rule the server uses),
 * which is a no-op on the already-canonical slugs the app feeds in — so the produced URL is
 * unchanged — while keeping the slug format defined in exactly one place.
 *
 * Usage: [routerLink]="dance.slug | dancePath:dance.styleSlug"
 */
@Pipe({ name: 'dancePath', standalone: true })
export class DancePathPipe implements PipeTransform {
  transform(slug: string | null | undefined, styleSlug?: string | null): any[] {
    if (!slug) return ['/dances'];
    return styleSlug ? ['/dances', slugify(styleSlug), slugify(slug)] : ['/dances', slugify(slug)];
  }
}
