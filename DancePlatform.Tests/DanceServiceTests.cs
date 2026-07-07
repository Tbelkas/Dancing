using DancePlatform.API.Data;
using DancePlatform.API.Models;
using DancePlatform.API.Services;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Caching.Memory;
using Xunit;

namespace DancePlatform.Tests;

/// <summary>
/// Exercises DanceService against a real (SQLite in-memory) relational store so transactions,
/// EXISTS projections, and the denormalized counters behave as they do on Postgres.
/// </summary>
public class DanceServiceTests : IDisposable
{
    private readonly SqliteConnection _conn;
    private readonly DbContextOptions<AppDbContext> _options;

    public DanceServiceTests()
    {
        _conn = new SqliteConnection("DataSource=:memory:");
        _conn.Open(); // keep the connection open so the in-memory schema/data persists across contexts
        _options = new DbContextOptionsBuilder<AppDbContext>().UseSqlite(_conn).Options;

        using var ctx = new AppDbContext(_options);
        ctx.Database.EnsureCreated();
        ctx.Users.Add(new User { Id = 1, Username = "u", PasswordHash = "x", Name = "U", Nickname = "" });
        ctx.Dances.Add(new Dance { Id = 1, Name = "Test", Slug = "test" });
        ctx.SaveChanges();
    }

    private AppDbContext NewCtx() => new(_options);

    // DanceService now takes an IMemoryCache (backs the grandTotal cache); a throwaway real one
    // keeps each test's construction identical to production wiring without mocking.
    private static DanceService Svc(AppDbContext ctx) => new(ctx, new MemoryCache(new MemoryCacheOptions()));

    [Fact]
    public async Task SetStatus_IsMutuallyExclusive_AndTracksLearnedCount()
    {
        await using (var ctx = NewCtx())
        {
            var r = await Svc(ctx).SetStatusAsync(1, 1, "learned");
            Assert.True(r.IsLearned);
            Assert.False(r.IsInProgress);
        }
        await using (var ctx = NewCtx())
        {
            Assert.Equal(1, await ctx.Dances.Where(d => d.Id == 1).Select(d => d.LearnedCount).FirstAsync());
            Assert.True(await ctx.UserLearnedDances.AnyAsync(x => x.UserId == 1 && x.DanceId == 1));
        }

        // Switching to in-progress must clear "learned" (and its count) — the two can't coexist.
        await using (var ctx = NewCtx())
        {
            var r = await Svc(ctx).SetStatusAsync(1, 1, "inprogress");
            Assert.False(r.IsLearned);
            Assert.True(r.IsInProgress);
        }
        await using (var ctx = NewCtx())
        {
            Assert.Equal(0, await ctx.Dances.Where(d => d.Id == 1).Select(d => d.LearnedCount).FirstAsync());
            Assert.False(await ctx.UserLearnedDances.AnyAsync(x => x.UserId == 1 && x.DanceId == 1));
            Assert.True(await ctx.UserInProgressDances.AnyAsync(x => x.UserId == 1 && x.DanceId == 1));
        }
    }

    [Fact]
    public async Task ToggleFavorite_FlipsJoinRowAndCounterAtomically()
    {
        await using (var ctx = NewCtx())
            Assert.True(await Svc(ctx).ToggleFavoriteAsync(1, 1)); // on

        await using (var ctx = NewCtx())
        {
            Assert.Equal(1, await ctx.Dances.Where(d => d.Id == 1).Select(d => d.FavoriteCount).FirstAsync());
            Assert.True(await ctx.UserFavoriteDances.AnyAsync(x => x.UserId == 1 && x.DanceId == 1));
        }

        await using (var ctx = NewCtx())
            Assert.False(await Svc(ctx).ToggleFavoriteAsync(1, 1)); // off

        await using (var ctx = NewCtx())
        {
            Assert.Equal(0, await ctx.Dances.Where(d => d.Id == 1).Select(d => d.FavoriteCount).FirstAsync());
            Assert.False(await ctx.UserFavoriteDances.AnyAsync(x => x.UserId == 1 && x.DanceId == 1));
        }
    }

    [Fact]
    public async Task GenerateUniqueSlug_IsScopedPerStyle()
    {
        await using (var ctx = NewCtx())
        {
            ctx.Styles.AddRange(new Style { Id = 1, Name = "House" }, new Style { Id = 2, Name = "Hiphop" });
            ctx.Dances.Add(new Dance
            {
                Id = 2,
                Name = "Reebok",
                Slug = "reebok",
                DanceStyles = new List<DanceStyle> { new() { StyleId = 1 } }
            });
            await ctx.SaveChangesAsync();
        }

        await using (var ctx = NewCtx())
        {
            var svc = Svc(ctx);
            // Same style as the existing "reebok" → must suffix.
            Assert.Equal("reebok-2", await svc.GenerateUniqueSlugAsync("Reebok", new[] { 1 }));
            // Different style → the clean slug is free to reuse (slugs are unique per style).
            Assert.Equal("reebok", await svc.GenerateUniqueSlugAsync("Reebok", new[] { 2 }));
        }
    }

    [Fact]
    public async Task GetByIdAsync_ProjectsPerUserFlags()
    {
        await using (var ctx = NewCtx())
            await Svc(ctx).ToggleFavoriteAsync(1, 1);

        await using (var ctx = NewCtx())
        {
            var withUser = await Svc(ctx).GetByIdAsync(1, userId: 1);
            var anon = await Svc(ctx).GetByIdAsync(1, userId: null);
            Assert.NotNull(withUser);
            Assert.True(withUser!.IsFavorite);   // EXISTS subquery sees the row
            Assert.False(anon!.IsFavorite);      // no user → always false, no subquery
        }
    }

    [Fact]
    public async Task SetStatus_LearnedToNotStarted_DecrementsCountAndRemovesJoinRows()
    {
        await using (var ctx = NewCtx())
            await Svc(ctx).SetStatusAsync(1, 1, "learned");
        await using (var ctx = NewCtx())
            Assert.Equal(1, await ctx.Dances.Where(d => d.Id == 1).Select(d => d.LearnedCount).FirstAsync());

        // learned → notstarted must roll the counter back to 0 and drop BOTH join rows.
        await using (var ctx = NewCtx())
        {
            var r = await Svc(ctx).SetStatusAsync(1, 1, "notstarted");
            Assert.False(r.IsLearned);
            Assert.False(r.IsInProgress);
        }
        await using (var ctx = NewCtx())
        {
            Assert.Equal(0, await ctx.Dances.Where(d => d.Id == 1).Select(d => d.LearnedCount).FirstAsync());
            Assert.False(await ctx.UserLearnedDances.AnyAsync(x => x.UserId == 1 && x.DanceId == 1));
            Assert.False(await ctx.UserInProgressDances.AnyAsync(x => x.UserId == 1 && x.DanceId == 1));
        }
    }

    [Fact]
    public async Task GetNeighbors_ReturnsAlphabeticalPrevNextWithinStyle()
    {
        // Three dances in one style; by Name the order is A, B, C regardless of insertion/id order.
        await using (var ctx = NewCtx())
        {
            ctx.Styles.Add(new Style { Id = 1, Name = "House" });
            ctx.Dances.AddRange(
                new Dance { Id = 10, Name = "C", Slug = "c", DanceStyles = new List<DanceStyle> { new() { StyleId = 1 } } },
                new Dance { Id = 11, Name = "A", Slug = "a", DanceStyles = new List<DanceStyle> { new() { StyleId = 1 } } },
                new Dance { Id = 12, Name = "B", Slug = "b", DanceStyles = new List<DanceStyle> { new() { StyleId = 1 } } });
            await ctx.SaveChangesAsync();
        }

        await using (var ctx = NewCtx())
        {
            var svc = Svc(ctx);

            var bn = await svc.GetNeighborsAsync(12, null); // B → prev A, next C
            Assert.Equal("A", bn.Prev?.Name);
            Assert.Equal("C", bn.Next?.Name);

            var an = await svc.GetNeighborsAsync(11, null); // A is first → no prev
            Assert.Null(an.Prev);
            Assert.Equal("B", an.Next?.Name);

            var cn = await svc.GetNeighborsAsync(10, null); // C is last → no next
            Assert.Equal("B", cn.Prev?.Name);
            Assert.Null(cn.Next);
        }
    }

    public void Dispose()
    {
        _conn.Dispose();
        GC.SuppressFinalize(this);
    }
}
