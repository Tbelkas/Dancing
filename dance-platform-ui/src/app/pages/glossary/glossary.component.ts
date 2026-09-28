import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { GlossaryService } from '../../core/services/glossary.service';
import { AuthService } from '../../core/services/auth.service';
import { GlossarySummary } from '../../models/glossary.model';
import { delayedLoading } from '../../core/utils/delayed-loading';

@Component({
  selector: 'app-glossary',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './glossary.component.html',
  styleUrls: ['./glossary.component.css']
})
export class GlossaryComponent implements OnInit {
  glossaries = signal<GlossarySummary[]>([]);
  loading = signal(true);
  showSkeleton = delayedLoading(this.loading);
  failed = signal(false);

  constructor(private glossaryService: GlossaryService, public auth: AuthService) {}

  ngOnInit(): void {
    this.glossaryService.getAll().subscribe({
      next: list => { this.glossaries.set(list); this.loading.set(false); },
      error: () => { this.failed.set(true); this.loading.set(false); }
    });
  }

  progressPercent(g: GlossarySummary): number {
    return g.moveCount === 0 ? 0 : Math.round((g.learnedCount / g.moveCount) * 100);
  }
}
