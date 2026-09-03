import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';

/**
 * Terms and Privacy, in one component because they are one document split in two and share a
 * layout. Which one renders comes from the route.
 *
 * The content is deliberately plain and specific to what this site actually does: it embeds other
 * people's videos, stores an account and a practice log, and sends exactly one kind of email.
 * Anything vaguer would be worse than nothing.
 */
@Component({
  selector: 'app-legal',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './legal.component.html',
  styleUrls: ['./legal.component.css']
})
export class LegalComponent implements OnInit {
  page = signal<'terms' | 'privacy'>('terms');

  /** Shown as "last updated". Bump it when the text below changes. */
  readonly updated = '3 September 2026';

  constructor(private route: ActivatedRoute) {}

  ngOnInit(): void {
    this.page.set(this.route.snapshot.url[0]?.path === 'privacy' ? 'privacy' : 'terms');
  }
}
