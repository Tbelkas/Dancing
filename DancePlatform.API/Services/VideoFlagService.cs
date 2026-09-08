using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Video;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class VideoFlagService : IVideoFlagService
{
    private readonly AppDbContext _db;

    public VideoFlagService(AppDbContext db) => _db = db;

    private static readonly Dictionary<string, string> ReasonLabels = new()
    {
        ["dead-video"] = "The video won't play",
        ["wrong-dance"] = "It isn't this dance",
        ["bad-sections"] = "The sections are wrong",
        ["wrong-timing"] = "It starts or ends in the wrong place",
        ["other"] = "Something else"
    };

    public async Task<ReportVideoResult> ReportAsync(int videoId, ReportVideoRequest request, int? userId, string source = "viewer")
    {
        // IgnoreQueryFilters: the checker reports on videos regardless of state, and a viewer can
        // only reach an approved one anyway, so filtering here would only break the checker.
        if (!await _db.Videos.IgnoreQueryFilters().AnyAsync(v => v.Id == videoId))
            return ReportVideoResult.VideoNotFound;

        // One open flag per video per reason. Ten people reporting the same dead embed is ten
        // rows saying one thing, and the queue is worked by a person -- OpenFlagsOnVideo carries
        // the "several people said so" signal without the duplication.
        var duplicate = await _db.VideoFlags.AnyAsync(f =>
            f.VideoId == videoId && f.Reason == request.Reason && f.ResolvedAt == null);
        if (duplicate) return ReportVideoResult.Duplicate;

        _db.VideoFlags.Add(new VideoFlag
        {
            VideoId = videoId,
            Reason = request.Reason,
            Detail = string.IsNullOrWhiteSpace(request.Detail) ? null : request.Detail.Trim(),
            Source = source,
            ReportedByUserId = userId,
            CreatedAt = DateTime.UtcNow
        });
        await _db.SaveChangesAsync();
        return ReportVideoResult.Success;
    }

    public async Task<List<VideoFlagDto>> GetAsync(string state)
    {
        var open = !string.Equals(state, "resolved", StringComparison.OrdinalIgnoreCase);

        // IgnoreQueryFilters is load-bearing, not defensive: the projection reads through
        // f.Video, and the intake filter on Video would silently drop every flag whose video has
        // since been quarantined -- which is exactly the flag most worth reading.
        var source = _db.VideoFlags.IgnoreQueryFilters()
            .Where(f => open ? f.ResolvedAt == null : f.ResolvedAt != null);

        // Oldest first while open: a report that has sat for a week is the one going stale.
        // Newest first once closed, because that list is read as history.
        var ordered = open ? source.OrderBy(f => f.CreatedAt) : source.OrderByDescending(f => f.ResolvedAt);

        return Finish(await Project(ordered).ToListAsync());
    }

    public async Task<VideoFlagDto?> ResolveAsync(int flagId, string? resolution, int? adminUserId)
    {
        var flag = await _db.VideoFlags.FirstOrDefaultAsync(f => f.Id == flagId);
        if (flag is null) return null;

        flag.ResolvedAt = DateTime.UtcNow;
        flag.ResolvedByUserId = adminUserId;
        flag.Resolution = string.IsNullOrWhiteSpace(resolution) ? "dismissed" : resolution.Trim();
        await _db.SaveChangesAsync();

        var rows = await Project(_db.VideoFlags.IgnoreQueryFilters().Where(f => f.Id == flagId)).ToListAsync();
        return Finish(rows).FirstOrDefault();
    }

    public Task<int> CountOpenAsync() => _db.VideoFlags.CountAsync(f => f.ResolvedAt == null);

    // StyleSlug and ReasonLabel are both post-processing: SlugGenerator can't run inside an EF
    // query, and the label table lives here rather than in the database.
    private static List<VideoFlagDto> Finish(List<VideoFlagDto> rows)
    {
        foreach (var r in rows)
        {
            r.StyleSlug = string.IsNullOrEmpty(r.StyleSlug) ? string.Empty : SlugGenerator.Slugify(r.StyleSlug);
            r.ReasonLabel = ReasonLabels.TryGetValue(r.Reason, out var label) ? label : r.Reason;
        }
        return rows;
    }

    private IQueryable<VideoFlagDto> Project(IQueryable<VideoFlag> source) =>
        source.Select(f => new VideoFlagDto
        {
            Id = f.Id,
            Reason = f.Reason,
            Detail = f.Detail,
            Source = f.Source,
            ReportedByUserId = f.ReportedByUserId,
            ReportedByUsername = f.ReportedBy == null ? null : f.ReportedBy.Username,
            CreatedAt = f.CreatedAt,
            ResolvedAt = f.ResolvedAt,
            Resolution = f.Resolution,
            VideoId = f.VideoId,
            VideoTitle = f.Video.Title,
            SourceVideoId = f.Video.VideoId,
            Platform = f.Video.Platform,
            VideoReviewState = f.Video.ReviewState,
            DanceId = f.Video.DanceId,
            DanceName = f.Video.Dance.Name,
            DanceSlug = f.Video.Dance.Slug,
            // The style NAME here; Finish() slugifies it in memory.
            StyleSlug = f.Video.Dance.DanceStyles.OrderBy(ds => ds.StyleId).Select(ds => ds.Style.Name).FirstOrDefault() ?? string.Empty,
            OpenFlagsOnVideo = _db.VideoFlags.Count(o => o.VideoId == f.VideoId && o.ResolvedAt == null)
        });
}
