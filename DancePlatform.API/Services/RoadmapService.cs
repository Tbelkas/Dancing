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
                VideoCount = r.Stages.SelectMany(s => s.Steps)
                    .Where(st => st.Dance != null)
                    .SelectMany(st => st.Dance!.Videos)
                    .Count(v => v.OwnerUserId == null || v.OwnerUserId == uid),
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
                        st.Id, st.Title, st.Description,
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

        var stages = roadmap.Stages.Select(s => new RoadmapStageDto
        {
            Id = s.Id,
            Title = s.Title,
            Description = s.Description,
            Steps = s.Steps.Select(st => new RoadmapStepDto
            {
                Id = st.Id,
                Title = st.Title,
                Description = st.Description,
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
        var moves = allSteps.Where(s => s.Dance is not null).Select(s => s.Dance!).ToList();
        var cover = moves.SelectMany(m => m.Videos).FirstOrDefault();

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
            VideoCount = moves.Sum(m => m.Videos.Count),
            LearnedCount = moves.Count(m => m.IsLearned),
            InProgressCount = moves.Count(m => m.IsInProgress),
            ThumbnailVideoId = cover?.VideoId,
            ThumbnailPlatform = cover?.Platform,
            Stages = stages
        };
    }
}
