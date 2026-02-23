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
            YouTubeId = request.YouTubeId,
            Description = request.Description,
            DanceId = request.DanceId
        };

        _db.Videos.Add(video);
        await _db.SaveChangesAsync();
        return await GetByIdAsync(video.Id);
    }

    public async Task<VideoDto?> UpdateAsync(int id, UpdateVideoRequest request)
    {
        var video = await _db.Videos.FindAsync(id);
        if (video is null) return null;

        if (request.Title is not null) video.Title = request.Title;
        if (request.YouTubeId is not null) video.YouTubeId = request.YouTubeId;
        if (request.Description is not null) video.Description = request.Description;

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

    private IQueryable<VideoDto> BuildQuery() =>
        _db.Videos.Include(v => v.Dance).Select(v => new VideoDto
        {
            Id = v.Id,
            Title = v.Title,
            YouTubeId = v.YouTubeId,
            Description = v.Description,
            DateAdded = v.DateAdded,
            DanceId = v.DanceId,
            DanceName = v.Dance.Name
        });
}
