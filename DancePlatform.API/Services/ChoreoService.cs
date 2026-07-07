using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Choreo;
using DancePlatform.API.DTOs.Video;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class ChoreoService : IChoreoService
{
    private readonly AppDbContext _db;

    public ChoreoService(AppDbContext db) => _db = db;

    public Task<List<ChoreoDto>> GetMineAsync(int userId) =>
        Query(c => c.UserId == userId)
            .OrderByDescending(c => c.DateAdded)
            .ToListAsync();

    public Task<ChoreoDto?> GetByIdAsync(int userId, int choreoId) =>
        Query(c => c.UserId == userId && c.Id == choreoId).FirstOrDefaultAsync();

    public async Task<ChoreoDto?> CreateAsync(int userId, CreateChoreoRequest request)
    {
        var name = request.Name.Trim();
        var fileName = request.FileName.Trim();
        if (name.Length == 0 || fileName.Length == 0) return null;

        var choreo = new UserChoreo
        {
            UserId = userId,
            Name = name,
            FileName = fileName,
            DurationSeconds = Sanitize(request.DurationSeconds)
        };
        _db.UserChoreos.Add(choreo);
        await _db.SaveChangesAsync();
        return await GetByIdAsync(userId, choreo.Id);
    }

    public async Task<ChoreoDto?> UpdateAsync(int userId, int choreoId, UpdateChoreoRequest request)
    {
        var choreo = await _db.UserChoreos
            .FirstOrDefaultAsync(c => c.Id == choreoId && c.UserId == userId);
        if (choreo is null) return null;

        if (!string.IsNullOrWhiteSpace(request.Name)) choreo.Name = request.Name.Trim();
        if (!string.IsNullOrWhiteSpace(request.FileName)) choreo.FileName = request.FileName.Trim();
        if (request.DurationSeconds is not null) choreo.DurationSeconds = Sanitize(request.DurationSeconds);

        await _db.SaveChangesAsync();
        return await GetByIdAsync(userId, choreoId);
    }

    public async Task<bool> DeleteAsync(int userId, int choreoId)
    {
        var choreo = await _db.UserChoreos
            .FirstOrDefaultAsync(c => c.Id == choreoId && c.UserId == userId);
        if (choreo is null) return false;

        _db.UserChoreos.Remove(choreo);
        await _db.SaveChangesAsync();
        return true;
    }

    public async Task<ChoreoDto?> AddLoopAsync(int userId, int choreoId, VideoSegmentDto loop)
    {
        if (string.IsNullOrWhiteSpace(loop.Label) || loop.EndTime is null || loop.EndTime <= loop.StartTime || loop.StartTime < 0)
            return null;
        var choreo = await _db.UserChoreos
            .FirstOrDefaultAsync(c => c.Id == choreoId && c.UserId == userId);
        if (choreo is null) return null;

        _db.UserChoreoLoops.Add(new UserChoreoLoop
        {
            UserChoreoId = choreoId,
            Label = loop.Label.Trim(),
            StartTime = loop.StartTime,
            EndTime = loop.EndTime.Value
        });
        await _db.SaveChangesAsync();
        return await GetByIdAsync(userId, choreoId);
    }

    public async Task<ChoreoDto?> DeleteLoopAsync(int userId, int choreoId, int loopId)
    {
        var loop = await _db.UserChoreoLoops
            .FirstOrDefaultAsync(l => l.Id == loopId && l.UserChoreoId == choreoId && l.Choreo.UserId == userId);
        if (loop is null) return null;

        _db.UserChoreoLoops.Remove(loop);
        await _db.SaveChangesAsync();
        return await GetByIdAsync(userId, choreoId);
    }

    private static int? Sanitize(int? durationSeconds) =>
        durationSeconds is > 0 and < 60 * 60 * 24 ? durationSeconds : null;

    private IQueryable<ChoreoDto> Query(System.Linq.Expressions.Expression<Func<UserChoreo, bool>> where) =>
        _db.UserChoreos
            .Where(where)
            .Select(c => new ChoreoDto
            {
                Id = c.Id,
                Name = c.Name,
                FileName = c.FileName,
                DurationSeconds = c.DurationSeconds,
                DateAdded = c.DateAdded,
                Loops = c.Loops
                    .OrderBy(l => l.StartTime)
                    .Select(l => new VideoSegmentDto
                    {
                        Id = l.Id,
                        Label = l.Label,
                        StartTime = l.StartTime,
                        EndTime = l.EndTime
                    })
                    .ToList()
            });
}
