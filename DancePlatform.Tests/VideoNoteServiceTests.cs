using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Video;
using DancePlatform.API.Models;
using DancePlatform.API.Services;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace DancePlatform.Tests;

/// <summary>
/// Exercises VideoNoteService CRUD against SQLite in-memory: ordering, ownership
/// scoping (one user can't touch another's notes), and input validation.
/// </summary>
public class VideoNoteServiceTests : IDisposable
{
    private readonly SqliteConnection _conn;
    private readonly DbContextOptions<AppDbContext> _options;

    public VideoNoteServiceTests()
    {
        _conn = new SqliteConnection("DataSource=:memory:");
        _conn.Open(); // keep open so the in-memory schema/data persists across contexts
        _options = new DbContextOptionsBuilder<AppDbContext>().UseSqlite(_conn).Options;

        using var ctx = new AppDbContext(_options);
        ctx.Database.EnsureCreated();
        ctx.Users.AddRange(
            new User { Id = 1, Username = "u1", PasswordHash = "x", Name = "U1", Nickname = "" },
            new User { Id = 2, Username = "u2", PasswordHash = "x", Name = "U2", Nickname = "" });
        ctx.Dances.Add(new Dance { Id = 1, Name = "Test", Slug = "test" });
        ctx.Videos.Add(new Video { Id = 1, Title = "V1", VideoId = "v1", DanceId = 1 });
        ctx.SaveChanges();
    }

    private AppDbContext NewCtx() => new(_options);

    private static SaveVideoNoteRequest Note(int time, string text) =>
        new() { TimeSeconds = time, Text = text };

    [Fact]
    public async Task Add_ReturnsNotesOrderedByTime_AndTrimsText()
    {
        await using var ctx = NewCtx();
        var svc = new VideoNoteService(ctx);

        await svc.AddAsync(1, 1, Note(154, "weight stays on the left foot"));
        var notes = await svc.AddAsync(1, 1, Note(30, "  count is 1-2-3, not 1-2  "));

        Assert.NotNull(notes);
        Assert.Equal(2, notes!.Count);
        Assert.Equal(30, notes[0].TimeSeconds);
        Assert.Equal("count is 1-2-3, not 1-2", notes[0].Text);
        Assert.Equal(154, notes[1].TimeSeconds);
    }

    [Fact]
    public async Task Add_RejectsBlankText_NegativeTime_AndMissingVideo()
    {
        await using var ctx = NewCtx();
        var svc = new VideoNoteService(ctx);

        Assert.Null(await svc.AddAsync(1, 1, Note(10, "   ")));
        Assert.Null(await svc.AddAsync(1, 1, Note(-1, "hi")));
        Assert.Null(await svc.AddAsync(1, videoId: 999, Note(10, "hi")));
    }

    [Fact]
    public async Task NotesArePrivatePerUser()
    {
        await using var ctx = NewCtx();
        var svc = new VideoNoteService(ctx);

        await svc.AddAsync(1, 1, Note(10, "mine"));
        var other = await svc.GetForVideoAsync(2, 1);

        Assert.Empty(other);
    }

    [Fact]
    public async Task Update_RewritesOwnNote_ButNotAnothersUsers()
    {
        await using var ctx = NewCtx();
        var svc = new VideoNoteService(ctx);

        var notes = await svc.AddAsync(1, 1, Note(10, "original"));
        var noteId = notes![0].Id;

        var updated = await svc.UpdateAsync(1, 1, noteId, Note(12, "fixed"));
        Assert.Equal(12, updated![0].TimeSeconds);
        Assert.Equal("fixed", updated[0].Text);

        Assert.Null(await svc.UpdateAsync(2, 1, noteId, Note(5, "hijack")));
        Assert.Null(await svc.UpdateAsync(1, 1, noteId, Note(5, " ")));
    }

    [Fact]
    public async Task Delete_RemovesOwnNote_ButNotAnothersUsers()
    {
        await using var ctx = NewCtx();
        var svc = new VideoNoteService(ctx);

        var notes = await svc.AddAsync(1, 1, Note(10, "bye"));
        var noteId = notes![0].Id;

        Assert.Null(await svc.DeleteAsync(2, 1, noteId));

        var remaining = await svc.DeleteAsync(1, 1, noteId);
        Assert.NotNull(remaining);
        Assert.Empty(remaining!);
    }

    public void Dispose() => _conn.Dispose();
}
