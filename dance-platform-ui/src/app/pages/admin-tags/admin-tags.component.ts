import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../../core/services/admin.service';
import { ConfirmService } from '../../core/services/confirm.service';
import { ToastService } from '../../core/services/toast.service';
import { TagAdmin, TagKind, TagUsage } from '../../models/tag-admin.model';

/**
 * The tag manager: rename, merge, and delete the style and musical-style vocabularies.
 *
 * Both could be created and deleted but never renamed or merged, which is how the catalogue
 * accumulated the near-duplicate tags the 2026-06 consolidation had to clear out by hand. Without
 * a merge the only fix was SQL, and a fix that needs SQL doesn't happen until it's a problem.
 */
@Component({
  selector: 'app-admin-tags',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin-tags.component.html',
  styleUrls: ['./admin-tags.component.css']
})
export class AdminTagsComponent implements OnInit {
  tags = signal<TagAdmin | null>(null);
  loading = signal(true);
  loadError = signal(false);
  busy = signal(false);

  /** The tag being renamed, as "{kind}:{id}" — only one row is ever in edit. */
  editing = signal<string | null>(null);
  editName = '';

  /** The tag being merged away, as "{kind}:{id}". */
  merging = signal<string | null>(null);
  mergeTargetId: number | null = null;

  constructor(
    private admin: AdminService,
    private confirm: ConfirmService,
    private toast: ToastService
  ) {}

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.admin.getTags().subscribe({
      next: tags => { this.tags.set(tags); this.loading.set(false); this.loadError.set(false); },
      error: () => { this.loading.set(false); this.loadError.set(true); }
    });
  }

  /** The two vocabularies as one list, so the template renders them with one block instead of two. */
  groups = computed<{ kind: TagKind; title: string; list: TagUsage[] }[]>(() => {
    const tags = this.tags();
    if (!tags) return [];
    return [
      { kind: 'style', title: 'Styles', list: tags.styles },
      { kind: 'music', title: 'Music', list: tags.musicalStyles }
    ];
  });

  key(kind: TagKind, tag: TagUsage): string {
    return `${kind}:${tag.id}`;
  }

  /** Every other tag in the same vocabulary — the candidates a merge can land on. */
  others(kind: TagKind, tag: TagUsage): TagUsage[] {
    const all = kind === 'style' ? this.tags()?.styles : this.tags()?.musicalStyles;
    return (all ?? []).filter(t => t.id !== tag.id);
  }

  startRename(kind: TagKind, tag: TagUsage): void {
    this.merging.set(null);
    this.editing.set(this.key(kind, tag));
    this.editName = tag.name;
  }

  startMerge(kind: TagKind, tag: TagUsage): void {
    this.editing.set(null);
    this.merging.set(this.key(kind, tag));
    this.mergeTargetId = null;
  }

  cancel(): void {
    this.editing.set(null);
    this.merging.set(null);
  }

  rename(kind: TagKind, tag: TagUsage): void {
    const name = this.editName.trim();
    if (!name || name === tag.name) { this.cancel(); return; }

    this.busy.set(true);
    this.admin.renameTag(kind, tag.id, name).subscribe({
      next: () => {
        this.busy.set(false);
        this.cancel();
        this.load();
        this.toast.success(kind === 'style'
          // Worth saying every time: the style name is the {style} segment of the URL, so this
          // moved every dance page under it and old links now 404.
          ? `Renamed to "${name}". Every dance URL under it changed.`
          : `Renamed to "${name}".`);
      },
      error: err => {
        this.busy.set(false);
        this.toast.error(err?.error?.message ?? "That rename didn't save.");
      }
    });
  }

  async merge(kind: TagKind, tag: TagUsage): Promise<void> {
    if (!this.mergeTargetId) return;
    const target = this.others(kind, tag).find(t => t.id === this.mergeTargetId);
    if (!target) return;

    const ok = await this.confirm.ask(
      `Move all ${tag.danceCount} dance${tag.danceCount === 1 ? '' : 's'} from "${tag.name}" onto ` +
      `"${target.name}", then delete "${tag.name}"? This can't be undone from here.`,
      { title: 'Merge tags', confirmLabel: 'Merge', danger: true });
    if (!ok) return;

    this.busy.set(true);
    this.admin.mergeTag(kind, tag.id, target.id).subscribe({
      next: result => {
        this.busy.set(false);
        this.cancel();
        this.load();
        const extras = [
          result.alreadyTagged ? `${result.alreadyTagged} already had both` : '',
          result.reslugged ? `${result.reslugged} slug${result.reslugged === 1 ? '' : 's'} rewritten` : ''
        ].filter(Boolean).join(', ');
        this.toast.success(
          `Moved ${result.moved} onto "${result.targetName}"${extras ? ` (${extras})` : ''}.`);
      },
      error: err => {
        this.busy.set(false);
        this.toast.error(err?.error?.message ?? "That merge didn't go through.");
      }
    });
  }

  async remove(kind: TagKind, tag: TagUsage): Promise<void> {
    const ok = await this.confirm.ask(`Delete the unused tag "${tag.name}"?`,
      { title: 'Delete tag', confirmLabel: 'Delete', danger: true });
    if (!ok) return;

    this.busy.set(true);
    this.admin.deleteTag(kind, tag.id).subscribe({
      next: () => { this.busy.set(false); this.load(); this.toast.success(`Deleted "${tag.name}".`); },
      error: err => {
        this.busy.set(false);
        this.toast.error(err?.error?.message ?? "That tag couldn't be deleted.");
      }
    });
  }
}
