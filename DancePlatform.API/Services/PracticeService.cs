using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Practice;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class PracticeService : IPracticeService
{
    /// <summary>A watch landing within this window of the last activity continues the same session.</summary>
    private static readonly TimeSpan ContinuationBuffer = TimeSpan.FromMinutes(10);

    private readonly AppDbContext _db;

    public PracticeService(AppDbContext db) => _db = db;

    public async Task<List<PracticeSessionDto>> GetAsync(int userId) =>
        (await SessionQuery()
            .Where(ps => ps.UserId == userId)
            .OrderByDescending(ps => ps.Date)
            .ThenByDescending(ps => ps.StartedAt)
            .ToListAsync())
            .Select(MapToDto)
            .ToList();

    public async Task<PracticeSessionDto?> CreateAsync(int userId, CreatePracticeSessionRequest request)
    {
        var danceExists = await _db.Dances.AnyAsync(d => d.Id == request.DanceId);
        if (!danceExists) return null;

        // Manual entries are explicit one-offs — they always stand alone, never merged.
        var startedAt = DateTime.UtcNow;
        var session = new PracticeSession
        {
            UserId = userId,
            Date = request.Date,
            StartedAt = startedAt,
            LastActivityAt = startedAt,
            Notes = request.Notes,
            Items =
            {
                new PracticeSessionItem
                {
                    DanceId = request.DanceId,
                    Seconds = Math.Max(0, request.DurationMinutes ?? 0) * 60
                }
            }
        };
        _db.PracticeSessions.Add(session);
        await _db.SaveChangesAsync();

        return await GetByIdAsync(session.Id);
    }

    public async Task<PracticeSessionDto?> HeartbeatAsync(int userId, PracticeHeartbeatRequest request)
    {
        var danceExists = await _db.Dances.AnyAsync(d => d.Id == request.DanceId);
        if (!danceExists) return null;

        var now = DateTime.UtcNow;
        var cutoff = now - ContinuationBuffer;

        var session = await _db.PracticeSessions
            .Include(ps => ps.Items)
            .Where(ps => ps.UserId == userId && ps.LastActivityAt >= cutoff)
            .OrderByDescending(ps => ps.LastActivityAt)
            .FirstOrDefaultAsync();

        if (session is null)
        {
            session = new PracticeSession
            {
                UserId = userId,
                Date = request.LocalDate,
                StartedAt = now,
                LastActivityAt = now
            };
            _db.PracticeSessions.Add(session);
        }

        var item = session.Items.FirstOrDefault(i => i.DanceId == request.DanceId);
        if (item is null)
        {
            item = new PracticeSessionItem { DanceId = request.DanceId };
            session.Items.Add(item);
        }
        item.Seconds += request.Seconds;
        session.LastActivityAt = now;

        await _db.SaveChangesAsync();
        return await GetByIdAsync(session.Id);
    }

    public async Task<bool> DeleteAsync(int userId, int id)
    {
        var session = await _db.PracticeSessions.FirstOrDefaultAsync(ps => ps.Id == id && ps.UserId == userId);
        if (session is null) return false;
        _db.PracticeSessions.Remove(session);
        await _db.SaveChangesAsync();
        return true;
    }

    private async Task<PracticeSessionDto?> GetByIdAsync(int id)
    {
        var session = await SessionQuery().FirstOrDefaultAsync(ps => ps.Id == id);
        return session is null ? null : MapToDto(session);
    }

    private IQueryable<PracticeSession> SessionQuery() =>
        _db.PracticeSessions
            .Include(ps => ps.Items).ThenInclude(i => i.Dance)
                .ThenInclude(d => d.DanceStyles).ThenInclude(ds => ds.Style);

    private static PracticeSessionDto MapToDto(PracticeSession ps)
    {
        var items = ps.Items
            .OrderByDescending(i => i.Seconds)
            .Select(i => new PracticeSessionItemDto
            {
                DanceId = i.DanceId,
                DanceName = i.Dance.Name,
                DanceSlug = i.Dance.Slug,
                DanceStyleSlug = SlugGenerator.StyleSlug(i.Dance),
                Seconds = i.Seconds,
                Minutes = (int)Math.Round(i.Seconds / 60.0),
                Notes = i.Notes
            })
            .ToList();

        var totalSeconds = items.Sum(i => i.Seconds);
        return new PracticeSessionDto
        {
            Id = ps.Id,
            Date = ps.Date,
            StartedAt = ps.StartedAt,
            LastActivityAt = ps.LastActivityAt,
            Notes = ps.Notes,
            TotalSeconds = totalSeconds,
            DurationMinutes = (int)Math.Round(totalSeconds / 60.0),
            Items = items
        };
    }
}
