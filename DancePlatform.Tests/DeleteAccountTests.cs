using DancePlatform.API.Data;
using DancePlatform.API.Models;
using DancePlatform.API.Services;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Caching.Memory;
using Xunit;

namespace DancePlatform.Tests;

/// <summary>
/// Account deletion is one <c>Users.Remove</c> leaning entirely on the cascade rules in
/// AppDbContext, so what these tests actually check is that those rules say what the privacy
/// page promises: everything personal goes, and the shared catalogue does not.
/// </summary>
public class DeleteAccountTests : IDisposable
{
    private const int TheUser = 1;
    private const int Someone = 2;

    private readonly SqliteConnection _conn;
    private readonly DbContextOptions<AppDbContext> _options;

    public DeleteAccountTests()
    {
        _conn = new SqliteConnection("DataSource=:memory:");
        _conn.Open();
        _options = new DbContextOptionsBuilder<AppDbContext>().UseSqlite(_conn).Options;

        using var ctx = new AppDbContext(_options);
        ctx.Database.EnsureCreated();
        ctx.Users.AddRange(
            new User
            {
                Id = TheUser,
                Username = "leaver",
                PasswordHash = BCrypt.Net.BCrypt.HashPassword("my-password"),
                Name = "Leaver",
                Nickname = ""
            },
            new User { Id = Someone, Username = "stays", PasswordHash = "x", Name = "S", Nickname = "" });

        // A dance they contributed to the shared catalogue, already approved and favourited by
        // somebody else — the thing that must survive.
        ctx.Dances.Add(new Dance
        {
            Id = 1,
            Name = "Contributed",
            Slug = "contributed",
            OwnerUserId = TheUser,
            ReviewState = "approved"
        });
        ctx.Videos.Add(new Video { Id = 1, Title = "V", VideoId = "v1", DanceId = 1 });
        ctx.SaveChanges();

        // And the personal trail that must not.
        ctx.UserFavoriteDances.Add(new UserFavoriteDance { UserId = TheUser, DanceId = 1 });
        ctx.UserFavoriteDances.Add(new UserFavoriteDance { UserId = Someone, DanceId = 1 });
        ctx.PracticeSessions.Add(new PracticeSession { Id = 1, UserId = TheUser, Date = new DateOnly(2026, 9, 1) });
        ctx.VideoNotes.Add(new VideoNote { Id = 1, UserId = TheUser, VideoId = 1, Text = "keep the knee soft" });
        ctx.SaveChanges();
    }

    private AppDbContext NewCtx() => new(_options);

    private UserService NewService(AppDbContext ctx) =>
        new(ctx, new MemoryCache(new MemoryCacheOptions()));

    [Fact]
    public async Task TheWrongPasswordDeletesNothing()
    {
        await using var ctx = NewCtx();
        var result = await NewService(ctx).DeleteAccountAsync(TheUser, "not-my-password");

        Assert.Equal(DeleteAccountResult.WrongPassword, result);
        Assert.NotNull(await ctx.Users.FindAsync(TheUser));
    }

    [Fact]
    public async Task DeletingTakesEverythingPersonalWithIt()
    {
        await using (var ctx = NewCtx())
            Assert.Equal(DeleteAccountResult.Ok,
                await NewService(ctx).DeleteAccountAsync(TheUser, "my-password"));

        await using var check = NewCtx();
        Assert.Null(await check.Users.FindAsync(TheUser));
        Assert.Empty(await check.PracticeSessions.Where(s => s.UserId == TheUser).ToListAsync());
        Assert.Empty(await check.VideoNotes.IgnoreQueryFilters().Where(n => n.UserId == TheUser).ToListAsync());
        Assert.Empty(await check.UserFavoriteDances.Where(f => f.UserId == TheUser).ToListAsync());
    }

    [Fact]
    public async Task TheCatalogueSurvivesWithTheNameDetached()
    {
        await using (var ctx = NewCtx())
            await NewService(ctx).DeleteAccountAsync(TheUser, "my-password");

        await using var check = NewCtx();
        var dance = await check.Dances.FindAsync(1);

        // Deleting the contributor must not delete a page other people are using — the FK clears
        // the owner instead of cascading (see the SetNull rule in AppDbContext).
        Assert.NotNull(dance);
        Assert.Null(dance!.OwnerUserId);
        Assert.Single(await check.UserFavoriteDances.Where(f => f.DanceId == 1).ToListAsync());
    }

    [Fact]
    public async Task AProviderOnlyAccountNeedsNoPassword()
    {
        await using (var ctx = NewCtx())
        {
            var user = await ctx.Users.FindAsync(Someone);
            // No password hash at all: signing in through the provider is the proof.
            user!.PasswordHash = string.Empty;
            await ctx.SaveChangesAsync();
        }

        await using var ctx2 = NewCtx();
        Assert.Equal(DeleteAccountResult.Ok, await NewService(ctx2).DeleteAccountAsync(Someone, ""));
    }

    public void Dispose()
    {
        _conn.Dispose();
        GC.SuppressFinalize(this);
    }
}
