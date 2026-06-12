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
        await _db.PracticeSessions
            .Where(ps => ps.UserId == userId)
            .Include(ps => ps.Dance)
            .OrderByDescending(ps => ps.Date)
            .ThenByDescending(ps => ps.DateAdded)
            .Select(ps => new PracticeSessionDto
            {
                Id = ps.Id,
                DanceId = ps.DanceId,
                DanceName = ps.Dance.Name,
                DanceSlug = ps.Dance.Slug,
                Date = ps.Date,
                DurationMinutes = ps.DurationMinutes,
                Notes = ps.Notes
            })
            .ToListAsync();

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

        return await _db.PracticeSessions
            .Where(ps => ps.Id == session.Id)
            .Include(ps => ps.Dance)
            .Select(ps => new PracticeSessionDto
            {
                Id = ps.Id,
                DanceId = ps.DanceId,
                DanceName = ps.Dance.Name,
                DanceSlug = ps.Dance.Slug,
                Date = ps.Date,
                DurationMinutes = ps.DurationMinutes,
                Notes = ps.Notes
            })
            .FirstOrDefaultAsync();
    }

    public async Task<bool> DeleteAsync(int userId, int id)
    {
        var session = await _db.PracticeSessions.FirstOrDefaultAsync(ps => ps.Id == id && ps.UserId == userId);
        if (session is null) return false;
        _db.PracticeSessions.Remove(session);
        await _db.SaveChangesAsync();
        return true;
    }
}
