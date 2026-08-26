using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Video;
using DancePlatform.API.Models;
using DancePlatform.API.Services;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace DancePlatform.Tests;

/// <summary>
/// Exercises VideoService.RateVideoAsync against SQLite in-memory so the ON CONFLICT upsert,
/// the wrapping transaction, and the denormalized average/count refreshes behave as on Postgres.
/// (SQLite honours the same double-quoted identifiers and ON CONFLICT syntax the raw SQL uses.)
/// </summary>
public class VideoServiceTests : IDisposable
{
    private readonly SqliteConnection _conn;
    private readonly DbContextOptions<AppDbContext> _options;

    public VideoServiceTests()
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
        ctx.Videos.AddRange(
            new Video { Id = 1, Title = "V1", VideoId = "v1", DanceId = 1 },
            new Video { Id = 2, Title = "V2", VideoId = "v2", DanceId = 1 });
        ctx.SaveChanges();
    }

    private AppDbContext NewCtx() => new(_options);

    [Fact]
    public async Task RateVideo_UpsertsRating_AndRecomputesVideoAndDanceAggregates()
    {
        // user1 rates video1 = 4 → video1 avg 4/count 1, dance avg 4/count 1.
        await using (var ctx = NewCtx())
        {
            var dto = await new VideoService(ctx).RateVideoAsync(1, videoId: 1, rating: 4);
            Assert.Equal(4, dto?.UserRating);
        }
        await using (var ctx = NewCtx())
        {
            Assert.Equal((1, 4.0), await VideoStats(ctx, 1));
            Assert.Equal((1, 4.0), await DanceStats(ctx, 1));
        }

        // user2 rates video1 = 2 → video1 avg 3/count 2, dance avg 3/count 2.
        await using (var ctx = NewCtx())
            await new VideoService(ctx).RateVideoAsync(2, videoId: 1, rating: 2);
        await using (var ctx = NewCtx())
        {
            Assert.Equal((2, 3.0), await VideoStats(ctx, 1));
            Assert.Equal((2, 3.0), await DanceStats(ctx, 1));
        }

        // user1 RE-rates video1 = 5 → overwrites (not a second row): still 2 ratings, avg (5+2)/2 = 3.5.
        await using (var ctx = NewCtx())
            await new VideoService(ctx).RateVideoAsync(1, videoId: 1, rating: 5);
        await using (var ctx = NewCtx())
        {
            Assert.Equal(2, await ctx.VideoRatings.CountAsync(r => r.VideoId == 1)); // no duplicate row
            Assert.Equal(5, await ctx.VideoRatings.Where(r => r.UserId == 1 && r.VideoId == 1).Select(r => r.Rating).FirstAsync());
            Assert.Equal((2, 3.5), await VideoStats(ctx, 1));
        }

        // user1 rates the OTHER video on the same dance = 1 → dance aggregate spans both videos:
        // three ratings total (5, 2, 1), avg 8/3.
        await using (var ctx = NewCtx())
            await new VideoService(ctx).RateVideoAsync(1, videoId: 2, rating: 1);
        await using (var ctx = NewCtx())
        {
            Assert.Equal((1, 1.0), await VideoStats(ctx, 2));
            var (count, avg) = await DanceStats(ctx, 1);
            Assert.Equal(3, count);
            Assert.Equal(8.0 / 3.0, avg, precision: 6);
        }
    }

    [Fact]
    public async Task Create_RejectsDuplicateClip_ButAllowsOtherDanceOrOtherStartTime()
    {
        await using var ctx = NewCtx();
        ctx.Dances.Add(new Dance { Id = 2, Name = "Other", Slug = "other" });
        await ctx.SaveChangesAsync();
        var svc = new VideoService(ctx);

        CreateVideoRequest Request(int danceId, int? startTime = null) => new()
        {
            Title = "T", VideoId = "v1", Platform = "youtube", DanceId = danceId, StartTime = startTime
        };

        // Seeded video 1 is (v1, dance 1, StartTime null, global) — adding it again as admin/global is a dup.
        var (dup, video) = await svc.CreateAsync(Request(danceId: 1), userId: 1, isAdmin: true);
        Assert.Equal(CreateVideoResult.Duplicate, dup);
        Assert.Null(video);

        // A user's personal copy of an existing global clip on the same dance is also a dup for them.
        var (personalDup, _) = await svc.CreateAsync(Request(danceId: 1), userId: 1, isAdmin: false);
        Assert.Equal(CreateVideoResult.Duplicate, personalDup);

        // Same source video on a DIFFERENT dance is legitimate (multi-dance montages).
        var (otherDance, _) = await svc.CreateAsync(Request(danceId: 2), userId: 1, isAdmin: true);
        Assert.Equal(CreateVideoResult.Success, otherDance);

        // Same dance but a different StartTime is a different cut — allowed.
        var (otherCut, _) = await svc.CreateAsync(Request(danceId: 1, startTime: 90), userId: 1, isAdmin: true);
        Assert.Equal(CreateVideoResult.Success, otherCut);

        // One user's personal video doesn't block another user's personal add of the same clip.
        var (u1Personal, _) = await svc.CreateAsync(Request(danceId: 1, startTime: 30), userId: 1, isAdmin: false);
        Assert.Equal(CreateVideoResult.Success, u1Personal);
        var (u2Personal, _) = await svc.CreateAsync(Request(danceId: 1, startTime: 30), userId: 2, isAdmin: false);
        Assert.Equal(CreateVideoResult.Success, u2Personal);
    }

    [Fact]
    public async Task Create_HonoursGateOnlyForBulkImport_AndQuarantinesBelowThreshold()
    {
        await using var ctx = NewCtx();
        // The title shares no word with the dance name (title-dance-mismatch, -0.30)
        // and reads as a course advert (promo-title, -0.20), so the score lands at
        // 0.50 - under the 0.65 admit threshold. Two flags are needed because on the
        // API path DurationSeconds is always null, so too-short can never fire there.
        ctx.Dances.Add(new Dance { Id = 3, Name = "Suzie Q", Slug = "suzie-q" });
        await ctx.SaveChangesAsync();
        var svc = new VideoService(ctx);

        CreateVideoRequest Bad() => new()
        {
            Title = "Enroll in my full course - Festival Aftermovie 2019",
            VideoId = "bad1", Platform = "youtube", DanceId = 3
        };

        // The add-video form: a person looked at it, so it goes live whatever the score.
        var (formResult, formVideo) = await svc.CreateAsync(Bad(), userId: 1, isAdmin: true);
        Assert.Equal(CreateVideoResult.Success, formResult);
        var formRow = await ctx.Videos.IgnoreQueryFilters().FirstAsync(v => v.Id == formVideo!.Id);
        Assert.Equal("approved", formRow.ReviewState);
        Assert.True(formRow.QualityScore < VideoQualityGate.AdmitThreshold,
            "the fixture must actually score badly, or this test proves nothing");

        // Bulk import of the same clip onto another dance: the rubric decides, and
        // a below-threshold video is held out of every public query.
        ctx.Dances.Add(new Dance { Id = 4, Name = "Camel Walk", Slug = "camel-walk" });
        await ctx.SaveChangesAsync();
        var imported = new CreateVideoRequest
        {
            Title = "Enroll in my full course - Festival Aftermovie 2019",
            VideoId = "bad1", Platform = "youtube", DanceId = 4
        };
        var (importResult, importVideo) = await svc.CreateAsync(
            imported, userId: null, isAdmin: true, honourGate: true);
        Assert.Equal(CreateVideoResult.Success, importResult);
        var importRow = await ctx.Videos.IgnoreQueryFilters().FirstAsync(v => v.Id == importVideo!.Id);
        Assert.Equal("pending", importRow.ReviewState);
        Assert.NotNull(importRow.ReviewNote);

        // Quarantined means quarantined: the global filter hides it from a normal read.
        Assert.False(await ctx.Videos.AnyAsync(v => v.Id == importRow.Id));

        // A clean import still goes straight through - the gate holds back the bad, not the bulk.
        ctx.Dances.Add(new Dance { Id = 5, Name = "Camel Walk Two", Slug = "camel-walk-two" });
        await ctx.SaveChangesAsync();
        var (goodResult, goodVideo) = await svc.CreateAsync(new CreateVideoRequest
        {
            Title = "How To Camel Walk - Beginner Tutorial",
            VideoId = "good1", Platform = "youtube", DanceId = 5
        }, userId: null, isAdmin: true, honourGate: true);
        Assert.Equal(CreateVideoResult.Success, goodResult);
        var goodRow = await ctx.Videos.IgnoreQueryFilters().FirstAsync(v => v.Id == goodVideo!.Id);
        Assert.Equal("approved", goodRow.ReviewState);
    }

    private static async Task<(int Count, double Avg)> VideoStats(AppDbContext ctx, int videoId)
    {
        var v = await ctx.Videos.Where(x => x.Id == videoId).Select(x => new { x.RatingCount, x.AverageRating }).FirstAsync();
        return (v.RatingCount, v.AverageRating);
    }

    private static async Task<(int Count, double Avg)> DanceStats(AppDbContext ctx, int danceId)
    {
        var d = await ctx.Dances.Where(x => x.Id == danceId).Select(x => new { x.RatingCount, x.AverageRating }).FirstAsync();
        return (d.RatingCount, d.AverageRating);
    }

    public void Dispose()
    {
        _conn.Dispose();
        GC.SuppressFinalize(this);
    }
}
