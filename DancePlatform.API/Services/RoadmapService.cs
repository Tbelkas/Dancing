using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Roadmap;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class RoadmapService : IRoadmapService
{
    private readonly AppDbContext _db;

    public RoadmapService(AppDbContext db) => _db = db;

    public async Task<List<RoadmapSummaryDto>> GetAllAsync(int? userId)
    {
        var uid = userId ?? 0;
        var hasUser = userId.HasValue;

        // One projection, no stage/step materialisation — the index only needs counts.
        var rows = await _db.Roadmaps
            .OrderBy(r => r.SortOrder).ThenBy(r => r.Title)
            .Select(r => new
            {
                r.Id, r.Slug, r.Title, r.Subtitle, r.Description, r.StyleId,
                StyleName = r.Style.Name,
                StageCount = r.Stages.Count,
                StepCount = r.Stages.SelectMany(s => s.Steps).Count(),
                MoveCount = r.Stages.SelectMany(s => s.Steps).Count(st => st.DanceId != null),
                // Distinct: one dance can back several steps (a long tutorial sliced by segment),
                // and counting its videos once per step would inflate the headline figure.
                VideoCount = r.Stages.SelectMany(s => s.Steps)
                    .Where(st => st.Dance != null)
                    .SelectMany(st => st.Dance!.Videos)
                    .Where(v => v.OwnerUserId == null || v.OwnerUserId == uid)
                    .Select(v => v.Id)
                    .Distinct()
                    .Count(),
                LearnedCount = hasUser
                    ? r.Stages.SelectMany(s => s.Steps).Count(st => st.Dance != null && st.Dance.LearnedBy.Any(l => l.UserId == uid))
                    : 0,
                InProgressCount = hasUser
                    ? r.Stages.SelectMany(s => s.Steps).Count(st => st.Dance != null && st.Dance.InProgressBy.Any(p => p.UserId == uid))
                    : 0,
                // First video of the first linked step — the path's cover image.
                Thumbnail = r.Stages.OrderBy(s => s.SortOrder)
                    .SelectMany(s => s.Steps.OrderBy(st => st.SortOrder))
                    .Where(st => st.Dance != null)
                    .SelectMany(st => st.Dance!.Videos.Where(v => v.OwnerUserId == null || v.OwnerUserId == uid).OrderBy(v => v.DateAdded))
                    .Select(v => new { v.VideoId, v.Platform })
                    .FirstOrDefault()
            })
            .ToListAsync();

        return rows.Select(r => new RoadmapSummaryDto
        {
            Id = r.Id,
            Slug = r.Slug,
            Title = r.Title,
            Subtitle = r.Subtitle,
            Description = r.Description,
            StyleId = r.StyleId,
            StyleName = r.StyleName,
            StyleSlug = SlugGenerator.Slugify(r.StyleName),
            StageCount = r.StageCount,
            StepCount = r.StepCount,
            MoveCount = r.MoveCount,
            VideoCount = r.VideoCount,
            LearnedCount = r.LearnedCount,
            InProgressCount = r.InProgressCount,
            ThumbnailVideoId = r.Thumbnail?.VideoId,
            ThumbnailPlatform = r.Thumbnail?.Platform
        }).ToList();
    }

    public async Task<RoadmapDto?> GetByIdOrSlugAsync(string idOrSlug, int? userId)
    {
        var uid = userId ?? 0;
        var hasUser = userId.HasValue;

        var query = int.TryParse(idOrSlug, out var id)
            ? _db.Roadmaps.Where(r => r.Id == id)
            : _db.Roadmaps.Where(r => r.Slug == idOrSlug);

        var roadmap = await query
            .Select(r => new
            {
                r.Id, r.Slug, r.Title, r.Subtitle, r.Description, r.StyleId,
                StyleName = r.Style.Name,
                Stages = r.Stages.OrderBy(s => s.SortOrder).Select(s => new
                {
                    s.Id, s.Title, s.Description,
                    Steps = s.Steps.OrderBy(st => st.SortOrder).Select(st => new
                    {
                        st.Id, st.Key, st.Title, st.Description,
                        Requires = st.Prerequisites.Select(p => p.PrerequisiteStep.Key).ToList(),
                        Segment = st.VideoSegment == null ? null : new
                        {
                            st.VideoSegment.Id,
                            st.VideoSegment.Label,
                            st.VideoSegment.StartTime,
                            st.VideoSegment.EndTime,
                            st.VideoSegment.VideoId
                        },
                        Dance = st.Dance == null ? null : new
                        {
                            st.Dance.Id,
                            st.Dance.Name,
                            st.Dance.Slug,
                            // Canonical style = lowest StyleId, matching SlugGenerator.StyleSlug.
                            CanonicalStyleName = st.Dance.DanceStyles.OrderBy(ds => ds.StyleId).Select(ds => ds.Style.Name).FirstOrDefault(),
                            st.Dance.Difficulty,
                            st.Dance.AverageRating,
                            st.Dance.RatingCount,
                            IsLearned = hasUser && st.Dance.LearnedBy.Any(l => l.UserId == uid),
                            IsInProgress = hasUser && st.Dance.InProgressBy.Any(p => p.UserId == uid),
                            IsFavorite = hasUser && st.Dance.FavoritedBy.Any(f => f.UserId == uid),
                            // Global videos plus the viewer's own, same visibility rule as the dance page.
                            Videos = st.Dance.Videos
                                .Where(v => v.OwnerUserId == null || v.OwnerUserId == uid)
                                .OrderByDescending(v => v.AverageRating)
                                .ThenBy(v => v.DateAdded)
                                .Select(v => new
                                {
                                    v.Id, v.Title, v.VideoId, v.Platform, v.VideoType,
                                    v.StartTime, v.EndTime, v.DurationSeconds,
                                    v.ViewCount, v.AverageRating, v.RatingCount
                                }).ToList()
                        }
                    }).ToList()
                }).ToList()
            })
            .FirstOrDefaultAsync();

        if (roadmap is null) return null;

        var stages = roadmap.Stages.Select((s, si) => new RoadmapStageDto
        {
            Id = s.Id,
            Title = s.Title,
            Description = s.Description,
            Steps = s.Steps.Select(st => new RoadmapStepDto
            {
                Id = st.Id,
                Key = st.Key,
                Requires = st.Requires,
                StageIndex = si,
                Title = st.Title,
                Description = st.Description,
                Segment = st.Segment is null ? null : new RoadmapStepSegmentDto
                {
                    Id = st.Segment.Id,
                    Label = st.Segment.Label,
                    StartTime = st.Segment.StartTime,
                    EndTime = st.Segment.EndTime,
                    VideoId = st.Segment.VideoId
                },
                Dance = st.Dance is null ? null : new RoadmapStepDanceDto
                {
                    Id = st.Dance.Id,
                    Name = st.Dance.Name,
                    Slug = st.Dance.Slug,
                    StyleSlug = st.Dance.CanonicalStyleName is null ? string.Empty : SlugGenerator.Slugify(st.Dance.CanonicalStyleName),
                    Difficulty = st.Dance.Difficulty.ToString(),
                    AverageRating = st.Dance.AverageRating,
                    RatingCount = st.Dance.RatingCount,
                    IsLearned = st.Dance.IsLearned,
                    IsInProgress = st.Dance.IsInProgress,
                    IsFavorite = st.Dance.IsFavorite,
                    Videos = st.Dance.Videos.Select(v => new RoadmapStepVideoDto
                    {
                        Id = v.Id,
                        Title = v.Title,
                        VideoId = v.VideoId,
                        Platform = v.Platform,
                        VideoType = v.VideoType,
                        StartTime = v.StartTime,
                        EndTime = v.EndTime,
                        DurationSeconds = v.DurationSeconds,
                        ViewCount = v.ViewCount,
                        AverageRating = v.AverageRating,
                        RatingCount = v.RatingCount
                    }).ToList()
                }
            }).ToList()
        }).ToList();

        var allSteps = stages.SelectMany(s => s.Steps).ToList();
        AssignDepths(allSteps);
        AssignStates(allSteps, hasUser);
        var moves = allSteps.Where(s => s.Dance is not null).Select(s => s.Dance!).ToList();
        var cover = moves.SelectMany(m => m.Videos).FirstOrDefault();
        // Same de-duplication as the index: several steps can share one sliced-up tutorial.
        var distinctVideos = moves.SelectMany(m => m.Videos).Select(v => v.Id).Distinct().Count();

        return new RoadmapDto
        {
            Id = roadmap.Id,
            Slug = roadmap.Slug,
            Title = roadmap.Title,
            Subtitle = roadmap.Subtitle,
            Description = roadmap.Description,
            StyleId = roadmap.StyleId,
            StyleName = roadmap.StyleName,
            StyleSlug = SlugGenerator.Slugify(roadmap.StyleName),
            StageCount = stages.Count,
            StepCount = allSteps.Count,
            MoveCount = moves.Count,
            VideoCount = distinctVideos,
            LearnedCount = moves.Count(m => m.IsLearned),
            InProgressCount = moves.Count(m => m.IsInProgress),
            ThumbnailVideoId = cover?.VideoId,
            ThumbnailPlatform = cover?.Platform,
            Stages = stages,
            AvailableCount = allSteps.Count(s => s.State == "available")
        };
    }

    /// <summary>
    /// Longest distance from a root, which is what puts a node on the right ring of the tree:
    /// a step must sit outside every prerequisite, so the *max* depth is the correct one.
    ///
    /// Iterative relaxation rather than recursion — the seeder rejects cycles, but this endpoint
    /// is public and must not be one bad row away from a stack overflow. The loop is bounded by
    /// the step count, so a cycle that somehow got in yields odd depths instead of hanging.
    /// </summary>
    private static void AssignDepths(List<RoadmapStepDto> steps)
    {
        var byKey = steps.GroupBy(s => s.Key).ToDictionary(g => g.Key, g => g.First());

        for (var pass = 0; pass < steps.Count; pass++)
        {
            var changed = false;
            foreach (var step in steps)
            {
                var depth = 0;
                foreach (var key in step.Requires)
                    if (byKey.TryGetValue(key, out var parent))
                        depth = Math.Max(depth, parent.Depth + 1);

                if (depth != step.Depth) { step.Depth = depth; changed = true; }
            }
            if (!changed) break;
        }
    }

    /// <summary>
    /// Marks each step learned / available / locked. Available means every prerequisite is
    /// learned (a root always qualifies); locked means at least one isn't yet.
    /// Anonymous callers have no progress, so nothing is locked for them — a signed-out visitor
    /// should see the whole tree, not a wall of padlocks.
    /// </summary>
    private static void AssignStates(List<RoadmapStepDto> steps, bool hasUser)
    {
        var byKey = steps.GroupBy(s => s.Key).ToDictionary(g => g.Key, g => g.First());

        if (!hasUser)
        {
            // Signed out there is no progress, so nothing is locked — a visitor should see the
            // whole tree rather than a wall of padlocks.
            foreach (var step in steps) step.State = "available";
            return;
        }

        // "Satisfied" is not the same as "learned". A step with no catalog move behind it can
        // never be ticked off, so it passes through: it counts as satisfied exactly when the
        // things IT depends on are. Without the pass-through, one un-covered concept would either
        // lock its whole branch forever (if it gated) or leak the branch open early (if it
        // didn't) — Lofting would unlock before the Slide it actually follows.
        var satisfied = steps.ToDictionary(s => s.Key, s => s.Dance is not null && s.Dance.IsLearned);

        for (var pass = 0; pass < steps.Count; pass++)
        {
            var changed = false;
            foreach (var step in steps)
            {
                if (step.Dance is not null) continue; // fixed by its own learned flag
                var ok = step.Requires.All(key => !byKey.ContainsKey(key) || satisfied[key]);
                if (ok != satisfied[step.Key]) { satisfied[step.Key] = ok; changed = true; }
            }
            if (!changed) break;
        }

        foreach (var step in steps)
        {
            if (step.Dance?.IsLearned == true) { step.State = "learned"; continue; }
            var blocked = step.Requires.Any(key => byKey.ContainsKey(key) && !satisfied[key]);
            step.State = blocked ? "locked" : "available";
        }
    }
}
