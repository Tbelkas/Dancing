using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Admin;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

/// <summary>Outcome of a tag edit. Duplicate: that name is already taken by another tag.</summary>
public enum TagEditResult { Success, NotFound, Duplicate, SameTag, InUse }

public interface ITagAdminService
{
    Task<TagAdminDto> GetAsync();
    Task<(TagEditResult Result, TagUsageDto? Tag)> RenameAsync(string kind, int id, string name);
    Task<(TagEditResult Result, MergeTagResultDto? Merge)> MergeAsync(string kind, int sourceId, int targetId);
    Task<TagEditResult> DeleteAsync(string kind, int id);
}

/// <summary>
/// Renaming and merging the two tag vocabularies.
///
/// Styles and musical styles could be created and deleted but never renamed or merged, which is
/// how the catalogue accumulated the redundant tags the 2026-06 consolidation had to clean out by
/// hand. Without a merge, the only way to fix a near-duplicate tag was SQL.
/// </summary>
public class TagAdminService : ITagAdminService
{
    private readonly AppDbContext _db;
    private readonly IDanceService _danceService;

    public TagAdminService(AppDbContext db, IDanceService danceService)
    {
        _db = db;
        _danceService = danceService;
    }

    private static bool IsStyle(string kind) => string.Equals(kind, "style", StringComparison.OrdinalIgnoreCase);

    public async Task<TagAdminDto> GetAsync()
    {
        var styles = await _db.Styles
            .Select(s => new TagUsageDto
            {
                Id = s.Id, Name = s.Name, Description = s.Description, DanceCount = s.DanceStyles.Count
            })
            .OrderByDescending(t => t.DanceCount).ThenBy(t => t.Name)
            .ToListAsync();

        var music = await _db.MusicalStyles
            .Select(s => new TagUsageDto
            {
                Id = s.Id, Name = s.Name, Description = s.Description, DanceCount = s.DanceMusicalStyles.Count
            })
            .OrderByDescending(t => t.DanceCount).ThenBy(t => t.Name)
            .ToListAsync();

        return new TagAdminDto { Styles = Slugify(styles), MusicalStyles = Slugify(music) };
    }

    // SlugGenerator can't run inside an EF query, so the slug is filled in after materializing.
    private static List<TagUsageDto> Slugify(List<TagUsageDto> tags)
    {
        foreach (var tag in tags) tag.Slug = SlugGenerator.Slugify(tag.Name);
        return tags;
    }

    public async Task<(TagEditResult, TagUsageDto?)> RenameAsync(string kind, int id, string name)
    {
        name = name.Trim();

        if (IsStyle(kind))
        {
            var style = await _db.Styles.FirstOrDefaultAsync(s => s.Id == id);
            if (style is null) return (TagEditResult.NotFound, null);
            if (await _db.Styles.AnyAsync(s => s.Id != id && s.Name.ToLower() == name.ToLower()))
                return (TagEditResult.Duplicate, null);

            style.Name = name;
            await _db.SaveChangesAsync();
            // A style's name IS the {style} segment of every dance URL under it, so a rename
            // moves those pages. Slugs of the dances themselves are unaffected; old links 404.
            var count = await _db.DanceStyles.CountAsync(ds => ds.StyleId == id);
            return (TagEditResult.Success, new TagUsageDto
            {
                Id = style.Id, Name = style.Name, Slug = SlugGenerator.Slugify(style.Name),
                Description = style.Description, DanceCount = count
            });
        }

        var music = await _db.MusicalStyles.FirstOrDefaultAsync(s => s.Id == id);
        if (music is null) return (TagEditResult.NotFound, null);
        if (await _db.MusicalStyles.AnyAsync(s => s.Id != id && s.Name.ToLower() == name.ToLower()))
            return (TagEditResult.Duplicate, null);

        music.Name = name;
        await _db.SaveChangesAsync();
        var musicCount = await _db.DanceMusicalStyles.CountAsync(dm => dm.MusicalStyleId == id);
        return (TagEditResult.Success, new TagUsageDto
        {
            Id = music.Id, Name = music.Name, Slug = SlugGenerator.Slugify(music.Name),
            Description = music.Description, DanceCount = musicCount
        });
    }

    public async Task<(TagEditResult, MergeTagResultDto?)> MergeAsync(string kind, int sourceId, int targetId)
    {
        if (sourceId == targetId) return (TagEditResult.SameTag, null);

        // One transaction: a merge that moved half the dances and then failed would leave the
        // catalogue split across two tags with no record of which half went where.
        await using var tx = await _db.Database.BeginTransactionAsync();

        MergeTagResultDto result;

        if (IsStyle(kind))
        {
            var source = await _db.Styles.FirstOrDefaultAsync(s => s.Id == sourceId);
            var target = await _db.Styles.FirstOrDefaultAsync(s => s.Id == targetId);
            if (source is null || target is null) return (TagEditResult.NotFound, null);

            var links = await _db.DanceStyles.Where(ds => ds.StyleId == sourceId).ToListAsync();
            var alreadyOnTarget = await _db.DanceStyles
                .Where(ds => ds.StyleId == targetId)
                .Select(ds => ds.DanceId)
                .ToListAsync();

            // (DanceId, StyleId) is the composite key, so a link can't be repointed in place --
            // EF refuses to update a key property. Every link is removed; the ones whose dance
            // isn't already on the target come back as a new row pointing at it.
            var moved = 0;
            var duplicates = 0;
            _db.DanceStyles.RemoveRange(links);
            await _db.SaveChangesAsync();

            foreach (var link in links)
            {
                if (alreadyOnTarget.Contains(link.DanceId)) { duplicates++; continue; }
                _db.DanceStyles.Add(new DanceStyle { DanceId = link.DanceId, StyleId = targetId });
                moved++;
            }

            await _db.SaveChangesAsync();
            _db.Styles.Remove(source);
            await _db.SaveChangesAsync();

            result = new MergeTagResultDto
            {
                SourceName = source.Name, TargetName = target.Name,
                Moved = moved, AlreadyTagged = duplicates
            };
        }
        else
        {
            var source = await _db.MusicalStyles.FirstOrDefaultAsync(s => s.Id == sourceId);
            var target = await _db.MusicalStyles.FirstOrDefaultAsync(s => s.Id == targetId);
            if (source is null || target is null) return (TagEditResult.NotFound, null);

            var links = await _db.DanceMusicalStyles.Where(dm => dm.MusicalStyleId == sourceId).ToListAsync();
            var alreadyOnTarget = await _db.DanceMusicalStyles
                .Where(dm => dm.MusicalStyleId == targetId)
                .Select(dm => dm.DanceId)
                .ToListAsync();

            // Same composite-key dance as styles above: remove every link, re-add the ones that
            // aren't already on the target.
            var moved = 0;
            var duplicates = 0;
            _db.DanceMusicalStyles.RemoveRange(links);
            await _db.SaveChangesAsync();

            foreach (var link in links)
            {
                if (alreadyOnTarget.Contains(link.DanceId)) { duplicates++; continue; }
                _db.DanceMusicalStyles.Add(new DanceMusicalStyle { DanceId = link.DanceId, MusicalStyleId = targetId });
                moved++;
            }

            await _db.SaveChangesAsync();
            _db.MusicalStyles.Remove(source);
            await _db.SaveChangesAsync();

            result = new MergeTagResultDto
            {
                SourceName = source.Name, TargetName = target.Name,
                Moved = moved, AlreadyTagged = duplicates
            };
        }

        // Slugs are unique per STYLE, so folding two styles together can put two dances with the
        // same slug under one style — and /dances/{style}/{slug} would then resolve to whichever
        // came first. Re-slugging is only meaningful for a style merge; for music it's a no-op
        // that costs one pass over the catalogue, which is cheap enough not to special-case.
        result.Reslugged = await _danceService.ReslugAllAsync();

        await tx.CommitAsync();
        return (TagEditResult.Success, result);
    }

    public async Task<TagEditResult> DeleteAsync(string kind, int id)
    {
        if (IsStyle(kind))
        {
            var style = await _db.Styles.FirstOrDefaultAsync(s => s.Id == id);
            if (style is null) return TagEditResult.NotFound;
            // Refused rather than cascaded. The FK would happily take the DanceStyles rows with
            // it, silently untagging every dance under the style -- and an untagged dance has no
            // URL and falls out of browse. Merge it into another tag instead; that is what the
            // merge is for.
            if (await _db.DanceStyles.AnyAsync(ds => ds.StyleId == id)) return TagEditResult.InUse;
            _db.Styles.Remove(style);
        }
        else
        {
            var music = await _db.MusicalStyles.FirstOrDefaultAsync(s => s.Id == id);
            if (music is null) return TagEditResult.NotFound;
            if (await _db.DanceMusicalStyles.AnyAsync(dm => dm.MusicalStyleId == id)) return TagEditResult.InUse;
            _db.MusicalStyles.Remove(music);
        }
        await _db.SaveChangesAsync();
        return TagEditResult.Success;
    }
}
