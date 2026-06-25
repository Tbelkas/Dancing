using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Practice;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class PracticeService : IPracticeService
{
    private readonly AppDbContext _db;

    public PracticeService(AppDbContext db) => _db = db;

    public async Task<List<PracticeSessionDto>> GetAsync(int userId) =>
        (await SessionQuery()
            .Where(ps => ps.UserId == userId)
            .OrderByDescending(ps => ps.Date)
            .ThenByDescending(ps => ps.DateAdded)
            .ToListAsync())
            .Select(MapToDto)
            .ToList();

    public async Task<PracticeSessionDto?> CreateAsync(int userId, CreatePracticeSessionRequest request)
    {
        var danceExists = await _db.Dances.AnyAsync(d => d.Id == request.DanceId);
        if (!danceExists) return null;

        var session = new PracticeSession
        {
            UserId = userId,
            DanceId = request.DanceId,
            Date = request.Date,
            DurationMinutes = request.DurationMinutes,
            Notes = request.Notes
        };
        _db.PracticeSessions.Add(session);
        await _db.SaveChangesAsync();

        var created = await SessionQuery()
            .Where(ps => ps.Id == session.Id)
            .FirstOrDefaultAsync();
        return created is null ? null : MapToDto(created);
    }

    public async Task<bool> DeleteAsync(int userId, int id)
    {
        var session = await _db.PracticeSessions.FirstOrDefaultAsync(ps => ps.Id == id && ps.UserId == userId);
        if (session is null) return false;
        _db.PracticeSessions.Remove(session);
        await _db.SaveChangesAsync();
        return true;
    }

    private IQueryable<PracticeSession> SessionQuery() =>
        _db.PracticeSessions
            .Include(ps => ps.Dance).ThenInclude(d => d.DanceStyles).ThenInclude(ds => ds.Style);

    private static PracticeSessionDto MapToDto(PracticeSession ps) =>
        new PracticeSessionDto
        {
            Id = ps.Id,
            DanceId = ps.DanceId,
            DanceName = ps.Dance.Name,
            DanceSlug = ps.Dance.Slug,
            DanceStyleSlug = SlugGenerator.StyleSlug(ps.Dance),
            Date = ps.Date,
            DurationMinutes = ps.DurationMinutes,
            Notes = ps.Notes
        };
}
