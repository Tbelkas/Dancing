using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Video;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class VideoService : IVideoService
{
    private readonly AppDbContext _db;

    public VideoService(AppDbContext db) => _db = db;

    public async Task<List<VideoDto>> GetByDanceAsync(int danceId) =>
        await BuildQuery().Where(v => v.DanceId == danceId).ToListAsync();

    public async Task<VideoDto?> GetByIdAsync(int id) =>
        await BuildQuery().FirstOrDefaultAsync(v => v.Id == id);

    public async Task<VideoDto?> CreateAsync(CreateVideoRequest request)
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
        return await GetByIdAsync(video.Id);
    }

    public async Task<VideoDto?> UpdateAsync(int id, UpdateVideoRequest request)
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
        return await GetByIdAsync(id);
    }

    public async Task<bool> DeleteAsync(int id)
    {
        var video = await _db.Videos.FindAsync(id);
        if (video is null) return false;
        _db.Videos.Remove(video);
        await _db.SaveChangesAsync();
        return true;
    }

    public async Task<bool> IncrementViewCountAsync(int id)
    {
        var video = await _db.Videos.FindAsync(id);
        if (video is null) return false;
        video.ViewCount++;
        await _db.SaveChangesAsync();
        return true;
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

    private IQueryable<VideoDto> BuildQuery() =>
        _db.Videos.Include(v => v.Dance).Select(v => new VideoDto
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
