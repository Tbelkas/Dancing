using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Video;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class UserVideoLoopService : IUserVideoLoopService
{
    private readonly AppDbContext _db;

    public UserVideoLoopService(AppDbContext db) => _db = db;

    public Task<List<UserVideoLoopDto>> GetForVideoAsync(int userId, int videoId) =>
        QueryFor(userId, videoId).ToListAsync();

    public async Task<List<UserVideoLoopDto>?> AddAsync(int userId, int videoId, VideoSegmentDto loop)
    {
        if (string.IsNullOrWhiteSpace(loop.Label) || loop.EndTime is null || loop.EndTime <= loop.StartTime)
            return null;
        if (!await _db.Videos.AnyAsync(v => v.Id == videoId)) return null;

        _db.UserVideoLoops.Add(new UserVideoLoop
        {
            UserId = userId,
            VideoId = videoId,
            Label = loop.Label.Trim(),
            StartTime = loop.StartTime,
            EndTime = loop.EndTime
        });
        await _db.SaveChangesAsync();
        return await GetForVideoAsync(userId, videoId);
    }

    public async Task<List<UserVideoLoopDto>?> DeleteAsync(int userId, int videoId, int loopId)
    {
        var loop = await _db.UserVideoLoops
            .FirstOrDefaultAsync(l => l.Id == loopId && l.UserId == userId && l.VideoId == videoId);
        if (loop is null) return null;

        _db.UserVideoLoops.Remove(loop);
        await _db.SaveChangesAsync();
        return await GetForVideoAsync(userId, videoId);
    }

    private IQueryable<UserVideoLoopDto> QueryFor(int userId, int videoId) =>
        _db.UserVideoLoops
            .Where(l => l.UserId == userId && l.VideoId == videoId)
            .OrderBy(l => l.StartTime)
            .Select(l => new UserVideoLoopDto
            {
                Id = l.Id,
                VideoId = l.VideoId,
                Label = l.Label,
                StartTime = l.StartTime,
                EndTime = l.EndTime
            });
}
