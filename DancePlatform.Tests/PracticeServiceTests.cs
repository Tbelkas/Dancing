using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Practice;
using DancePlatform.API.Models;
using DancePlatform.API.Services;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace DancePlatform.Tests;

/// <summary>
/// Exercises PracticeService.HeartbeatAsync against SQLite in-memory, covering the 10-minute
/// continuation window that decides whether a beat extends the live session or starts a new one.
/// </summary>
public class PracticeServiceTests : IDisposable
{
    private readonly SqliteConnection _conn;
    private readonly DbContextOptions<AppDbContext> _options;

    public PracticeServiceTests()
    {
        _conn = new SqliteConnection("DataSource=:memory:");
        _conn.Open(); // keep open so the in-memory schema/data persists across contexts
        _options = new DbContextOptionsBuilder<AppDbContext>().UseSqlite(_conn).Options;

        using var ctx = new AppDbContext(_options);
        ctx.Database.EnsureCreated();
        ctx.Users.Add(new User { Id = 1, Username = "u", PasswordHash = "x", Name = "U", Nickname = "" });
        ctx.Dances.AddRange(
            new Dance { Id = 1, Name = "A", Slug = "a" },
            new Dance { Id = 2, Name = "B", Slug = "b" });
        ctx.SaveChanges();
    }

    private AppDbContext NewCtx() => new(_options);

    private static PracticeHeartbeatRequest Beat(int danceId, int seconds) =>
        new() { DanceId = danceId, Seconds = seconds, LocalDate = DateOnly.FromDateTime(DateTime.UtcNow) };

    [Fact]
    public async Task Heartbeat_WithinWindow_MergesIntoOneSession_ThenNewSessionAfterWindow()
    {
        // First beat: dance 1, 60s → creates a session with one item.
        await using (var ctx = NewCtx())
            await new PracticeService(ctx).HeartbeatAsync(1, Beat(1, 60));

        // Second beat within the window: same dance → accumulates onto the same item (90s total),
        // still exactly one session.
        await using (var ctx = NewCtx())
            await new PracticeService(ctx).HeartbeatAsync(1, Beat(1, 30));

        // Third beat within the window: a different dance → a SECOND item on the same session.
        await using (var ctx = NewCtx())
            await new PracticeService(ctx).HeartbeatAsync(1, Beat(2, 45));

        await using (var ctx = NewCtx())
        {
            Assert.Equal(1, await ctx.PracticeSessions.CountAsync());
            var session = await ctx.PracticeSessions.Include(s => s.Items).SingleAsync();
            Assert.Equal(2, session.Items.Count);
            Assert.Equal(90, session.Items.Single(i => i.DanceId == 1).Seconds);
            Assert.Equal(45, session.Items.Single(i => i.DanceId == 2).Seconds);
        }

        // Can't fake the clock, so simulate "the window lapsed" by back-dating the live session's
        // LastActivityAt beyond the 10-minute continuation buffer.
        await using (var ctx = NewCtx())
        {
            // Precompute the timestamp (a literal parameter EF can translate) rather than an
            // in-query DateTime arithmetic expression, which the SQLite provider can't render.
            var staleTime = DateTime.UtcNow - TimeSpan.FromMinutes(20);
            await ctx.PracticeSessions.ExecuteUpdateAsync(s =>
                s.SetProperty(x => x.LastActivityAt, staleTime));
        }

        // Next beat now falls outside the window → a brand-new session (two sessions total).
        await using (var ctx = NewCtx())
            await new PracticeService(ctx).HeartbeatAsync(1, Beat(1, 15));

        await using (var ctx = NewCtx())
            Assert.Equal(2, await ctx.PracticeSessions.CountAsync());
    }

    public void Dispose()
    {
        _conn.Dispose();
        GC.SuppressFinalize(this);
    }
}
