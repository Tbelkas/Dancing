import { Pipe, PipeTransform } from '@angular/core';

/**
 * Builds the routerLink for a dance: /dances/{styleSlug}/{slug}. The style segment disambiguates
 * same-named steps that live in different styles. Falls back to the legacy single-segment
 * /dances/{slug} when no style slug is known (e.g. older locally-cached "Continue learning" entries).
 *
 * Usage: [routerLink]="dance.slug | dancePath:dance.styleSlug"
 */
@Pipe({ name: 'dancePath', standalone: true })
export class DancePathPipe implements PipeTransform {
  transform(slug: string | null | undefined, styleSlug?: string | null): any[] {
    if (!slug) return ['/dances'];
    return styleSlug ? ['/dances', styleSlug, slug] : ['/dances', slug];
  }
}
