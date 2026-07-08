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
        // A beat practices exactly one thing: a catalog dance or one of the user's local choreos.
        if (request.DanceId.HasValue == request.ChoreoId.HasValue) return null;

        if (request.DanceId.HasValue && !await _db.Dances.AnyAsync(d => d.Id == request.DanceId.Value))
            return null;
        // Choreos are personal — a beat for someone else's choreo id is rejected, not recorded.
        if (request.ChoreoId.HasValue && !await _db.UserChoreos.AnyAsync(c => c.Id == request.ChoreoId.Value && c.UserId == userId))
            return null;

        // A stale/unknown video id shouldn't reject the beat — record the time unattributed.
        var videoId = request.VideoId;
        if (videoId.HasValue && !await _db.Videos.AnyAsync(v => v.Id == videoId.Value))
            videoId = null;

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

        // Items are keyed per (dance, video) so history can follow a video that later moves to
        // another dance; choreo items are keyed per choreo. The DTO regroups per dance for display.
        var item = session.Items.FirstOrDefault(i =>
            i.DanceId == request.DanceId && i.VideoId == videoId && i.UserChoreoId == request.ChoreoId);
        if (item is null)
        {
            item = new PracticeSessionItem { DanceId = request.DanceId, VideoId = videoId, UserChoreoId = request.ChoreoId };
            session.Items.Add(item);
        }
        item.Seconds += request.Seconds;
        session.LastActivityAt = now;

        await _db.SaveChangesAsync();
        return await GetByIdAsync(session.Id);
    }

    public async Task<PracticeSessionDto?> UpdateAsync(int userId, int id, UpdatePracticeSessionRequest request)
    {
        var session = await _db.PracticeSessions
            .Include(ps => ps.Items)
            .FirstOrDefaultAsync(ps => ps.Id == id && ps.UserId == userId);
        if (session is null) return null;

        session.Date = request.Date;
        session.Notes = string.IsNullOrWhiteSpace(request.Notes) ? null : request.Notes.Trim();

        // Duration edits only make sense when there's one dance/choreo to attribute the time to;
        // multi-dance (tracked) sessions keep their per-dance split untouched. A single dance may
        // span several per-video items — the override collapses them onto one (attribution is
        // meaningless for a hand-edited total anyway).
        if (request.DurationMinutes.HasValue && session.Items.Select(i => (i.DanceId, i.UserChoreoId)).Distinct().Count() == 1)
        {
            var keeper = session.Items.First();
            keeper.Seconds = Math.Max(0, request.DurationMinutes.Value) * 60;
            keeper.VideoId = null;
            foreach (var extra in session.Items.Skip(1).ToList())
            {
                session.Items.Remove(extra);
                _db.PracticeSessionItems.Remove(extra);
            }
        }

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
                .ThenInclude(d => d!.DanceStyles).ThenInclude(ds => ds.Style)
            .Include(ps => ps.Items).ThenInclude(i => i.Choreo);

    private static PracticeSessionDto MapToDto(PracticeSession ps)
    {
        // Items are stored per (dance, video); the UI thinks in dances, so fold the videos back
        // together. Choreo items group per choreo and surface the choreo's name instead.
        var items = ps.Items
            .GroupBy(i => (i.DanceId, i.UserChoreoId))
            .Select(g =>
            {
                var first = g.First();
                var dance = first.Dance;
                var seconds = g.Sum(i => i.Seconds);
                return new PracticeSessionItemDto
                {
                    DanceId = g.Key.DanceId ?? 0,
                    ChoreoId = g.Key.UserChoreoId,
                    // A choreo item whose choreo was since removed keeps its time under a tombstone name.
                    DanceName = dance?.Name ?? first.Choreo?.Name ?? "Removed choreo",
                    DanceSlug = dance?.Slug ?? string.Empty,
                    DanceStyleSlug = dance is null ? string.Empty : SlugGenerator.StyleSlug(dance),
                    DanceStyleName = dance is null
                        ? "My choreos"
                        : dance.DanceStyles.OrderBy(ds => ds.StyleId).Select(ds => ds.Style.Name).FirstOrDefault() ?? string.Empty,
                    Seconds = seconds,
                    Minutes = (int)Math.Round(seconds / 60.0),
                    Notes = g.Select(i => i.Notes).FirstOrDefault(n => n is not null)
                };
            })
            .OrderByDescending(i => i.Seconds)
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
