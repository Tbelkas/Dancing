using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Video;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class VideoService : IVideoService
{
    private readonly AppDbContext _db;

    public VideoService(AppDbContext db) => _db = db;

    // Within a dance, surface the videos the current user rated 4–5 stars first
    // (their personal favourites for this dance), then everything else by add order.
    public async Task<List<VideoDto>> GetByDanceAsync(int danceId, int? userId)
    {
        var ordered = _db.Videos
            .Where(v => v.DanceId == danceId)
            .OrderByDescending(v => userId != null && v.Ratings.Any(r => r.UserId == userId && r.Rating >= 4))
            .ThenByDescending(v => userId == null
                ? 0
                : v.Ratings.Where(r => r.UserId == userId).Select(r => r.Rating).FirstOrDefault())
            .ThenBy(v => v.Id);
        return await Project(ordered, userId).ToListAsync();
    }

    public async Task<VideoDto?> GetByIdAsync(int id, int? userId) =>
        await Project(_db.Videos.Where(v => v.Id == id), userId).FirstOrDefaultAsync();

    // All dances whose segments live in the same source video (same platform + id),
    // ordered by where they start so the player can offer in-place jump chips.
    public async Task<List<VideoChapterDto>> GetRelatedAsync(int id)
    {
        var current = await _db.Videos.AsNoTracking()
            .Where(v => v.Id == id)
            .Select(v => new { v.VideoId, v.Platform })
            .FirstOrDefaultAsync();
        if (current is null) return new List<VideoChapterDto>();

        return await _db.Videos
            .Where(v => v.VideoId == current.VideoId && v.Platform == current.Platform)
            .OrderBy(v => v.StartTime ?? 0)
            .Select(v => new VideoChapterDto
            {
                Id = v.Id,
                DanceId = v.DanceId,
                DanceName = v.Dance.Name,
                DanceSlug = v.Dance.Slug,
                StartTime = v.StartTime,
                EndTime = v.EndTime
            })
            .ToListAsync();
    }

    public async Task<VideoDto?> CreateAsync(CreateVideoRequest request, int? userId)
    {
        var danceExists = await _db.Dances.AnyAsync(d => d.Id == request.DanceId);
        if (!danceExists) return null;

        var video = new Video
        {
            Title = request.Title,
            VideoId = request.VideoId,
            Platform = request.Platform,
            VideoType = NormalizeVideoType(request.VideoType),
            Description = request.Description,
            DanceId = request.DanceId,
            StartTime = request.StartTime,
            EndTime = request.EndTime,
            Segments = MapSegments(request.VideoType, request.Segments)
        };

        _db.Videos.Add(video);
        await _db.SaveChangesAsync();
        return await GetByIdAsync(video.Id, userId);
    }

    public async Task<VideoDto?> UpdateAsync(int id, UpdateVideoRequest request, int? userId)
    {
        var video = await _db.Videos.Include(v => v.Segments).FirstOrDefaultAsync(v => v.Id == id);
        if (video is null) return null;

        if (request.Title is not null) video.Title = request.Title;
        if (request.VideoId is not null) video.VideoId = request.VideoId;
        if (request.Description is not null) video.Description = request.Description;
        if (request.VideoType is not null) video.VideoType = NormalizeVideoType(request.VideoType);
        if (request.UpdateTimes)
        {
            video.StartTime = request.StartTime;
            video.EndTime = request.EndTime;
        }
        if (request.UpdateSegments)
        {
            video.Segments.Clear();
            video.Segments.AddRange(MapSegments(video.VideoType, request.Segments));
        }

        await _db.SaveChangesAsync();
        return await GetByIdAsync(id, userId);
    }

    // Reassigns a video to another dance. Only DanceId changes — the source clip
    // (VideoId/Platform), times, and segments are untouched, so any "related" chapter
    // grouping (which keys off VideoId+Platform) still holds; the video simply now
    // lists under the target dance and inherits its style. Both dances' rating
    // aggregates are recomputed since the video's ratings move with it.
    public async Task<(MoveVideoResult Result, VideoDto? Video)> MoveToDanceAsync(int id, int danceId, int? userId)
    {
        var video = await _db.Videos.FirstOrDefaultAsync(v => v.Id == id);
        if (video is null) return (MoveVideoResult.VideoNotFound, null);

        if (!await _db.Dances.AnyAsync(d => d.Id == danceId))
            return (MoveVideoResult.DanceNotFound, null);

        if (video.DanceId != danceId)
        {
            var previousDanceId = video.DanceId;
            video.DanceId = danceId;
            await _db.SaveChangesAsync();
            await RecomputeDanceRatingAsync(previousDanceId);
            await RecomputeDanceRatingAsync(danceId);
        }
        return (MoveVideoResult.Success, await GetByIdAsync(id, userId));
    }

    // Appends a single named loop region without disturbing existing segments, and
    // independent of VideoType — admins mark practice loops on any video, not just tutorials.
    public async Task<VideoDto?> AddSegmentAsync(int id, VideoSegmentDto segment, int? userId)
    {
        if (string.IsNullOrWhiteSpace(segment.Label)) return null;
        var video = await _db.Videos.Include(v => v.Segments).FirstOrDefaultAsync(v => v.Id == id);
        if (video is null) return null;

        video.Segments.Add(new VideoSegment
        {
            Label = segment.Label.Trim(),
            StartTime = segment.StartTime,
            EndTime = segment.EndTime
        });
        await _db.SaveChangesAsync();
        return await GetByIdAsync(id, userId);
    }

    public async Task<VideoDto?> DeleteSegmentAsync(int videoId, int segmentId, int? userId)
    {
        var segment = await _db.VideoSegments
            .FirstOrDefaultAsync(s => s.Id == segmentId && s.VideoId == videoId);
        if (segment is null) return null;
        _db.VideoSegments.Remove(segment);
        await _db.SaveChangesAsync();
        return await GetByIdAsync(videoId, userId);
    }

    public async Task<bool> DeleteAsync(int id)
    {
        var video = await _db.Videos.FindAsync(id);
        if (video is null) return false;
        var danceId = video.DanceId;
        _db.Videos.Remove(video);
        await _db.SaveChangesAsync();
        // The deleted video's ratings (cascade-removed) no longer count toward its dance.
        await RecomputeDanceRatingAsync(danceId);
        return true;
    }

    public async Task<bool> IncrementViewCountAsync(int id)
    {
        var affected = await _db.Videos
            .Where(v => v.Id == id)
            .ExecuteUpdateAsync(s => s.SetProperty(v => v.ViewCount, v => v.ViewCount + 1));
        return affected > 0;
    }

    // Upserts a user's 1–5 rating for a single video, then refreshes the video's own
    // average plus its dance's aggregate (the mean of all ratings across the dance's videos).
    public async Task<VideoDto?> RateVideoAsync(int userId, int videoId, int rating)
    {
        var video = await _db.Videos.FirstOrDefaultAsync(v => v.Id == videoId);
        if (video is null) return null;

        var existing = await _db.VideoRatings.FindAsync(userId, videoId);
        if (existing is not null)
            existing.Rating = rating;
        else
            _db.VideoRatings.Add(new VideoRating { UserId = userId, VideoId = videoId, Rating = rating });
        await _db.SaveChangesAsync();

        await RecomputeVideoRatingAsync(videoId);
        await RecomputeDanceRatingAsync(video.DanceId);

        return await GetByIdAsync(videoId, userId);
    }

    private async Task RecomputeVideoRatingAsync(int videoId)
    {
        var stats = await _db.VideoRatings
            .Where(r => r.VideoId == videoId)
            .GroupBy(r => r.VideoId)
            .Select(g => new { Count = g.Count(), Avg = g.Average(r => (double)r.Rating) })
            .FirstOrDefaultAsync();
        await _db.Videos.Where(v => v.Id == videoId).ExecuteUpdateAsync(s => s
            .SetProperty(v => v.RatingCount, stats != null ? stats.Count : 0)
            .SetProperty(v => v.AverageRating, stats != null ? stats.Avg : 0.0));
    }

    private async Task RecomputeDanceRatingAsync(int danceId)
    {
        var stats = await _db.VideoRatings
            .Where(r => r.Video.DanceId == danceId)
            .GroupBy(r => r.Video.DanceId)
            .Select(g => new { Count = g.Count(), Avg = g.Average(r => (double)r.Rating) })
            .FirstOrDefaultAsync();
        await _db.Dances.Where(d => d.Id == danceId).ExecuteUpdateAsync(s => s
            .SetProperty(d => d.RatingCount, stats != null ? stats.Count : 0)
            .SetProperty(d => d.AverageRating, stats != null ? stats.Avg : 0.0));
    }

    private static string NormalizeVideoType(string? type) =>
        type == "tutorial" ? "tutorial" : "steps";

    // Segments only apply to tutorials; entries without a label are dropped
    private static List<VideoSegment> MapSegments(string? videoType, List<VideoSegmentDto> segments) =>
        NormalizeVideoType(videoType) != "tutorial"
            ? new List<VideoSegment>()
            : segments
                .Where(s => !string.IsNullOrWhiteSpace(s.Label))
                .OrderBy(s => s.StartTime)
                .Select(s => new VideoSegment
                {
                    Label = s.Label.Trim(),
                    StartTime = s.StartTime,
                    EndTime = s.EndTime
                })
                .ToList();

    private static IQueryable<VideoDto> Project(IQueryable<Video> source, int? userId) =>
        source.Select(v => new VideoDto
        {
            Id = v.Id,
            Title = v.Title,
            VideoId = v.VideoId,
            Platform = v.Platform,
            VideoType = v.VideoType,
            Description = v.Description,
            DateAdded = v.DateAdded,
            ViewCount = v.ViewCount,
            StartTime = v.StartTime,
            EndTime = v.EndTime,
            AverageRating = v.AverageRating,
            RatingCount = v.RatingCount,
            UserRating = userId == null
                ? null
                : v.Ratings.Where(r => r.UserId == userId).Select(r => (int?)r.Rating).FirstOrDefault(),
            DanceId = v.DanceId,
            DanceName = v.Dance.Name,
            Segments = v.Segments
                .OrderBy(s => s.StartTime)
                .Select(s => new VideoSegmentDto
                {
                    Id = s.Id,
                    Label = s.Label,
                    StartTime = s.StartTime,
                    EndTime = s.EndTime
                })
                .ToList()
        });
}
