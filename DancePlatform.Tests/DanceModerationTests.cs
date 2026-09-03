using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Dance;
using DancePlatform.API.Models;
using DancePlatform.API.Services;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Caching.Memory;
using Xunit;

namespace DancePlatform.Tests;

/// <summary>
/// POST /dances is open to any signed-in user (the My Dances add flow), so what keeps a stranger's
/// entry out of the public catalogue is that it is created "pending" and every public read filters
/// on that. These tests pin the filter at each read that a user could reach a dance through — the
/// failure mode being guarded against is one listing quietly forgetting.
/// </summary>
public class DanceModerationTests : IDisposable
{
    private const int Contributor = 1;
    private const int Stranger = 2;

    private readonly SqliteConnection _conn;
    private readonly DbContextOptions<AppDbContext> _options;

    public DanceModerationTests()
    {
        _conn = new SqliteConnection("DataSource=:memory:");
        _conn.Open();
        _options = new DbContextOptionsBuilder<AppDbContext>().UseSqlite(_conn).Options;

        using var ctx = new AppDbContext(_options);
        ctx.Database.EnsureCreated();
        ctx.Users.AddRange(
            new User { Id = Contributor, Username = "contributor", PasswordHash = "x", Name = "C", Nickname = "" },
            new User { Id = Stranger, Username = "stranger", PasswordHash = "x", Name = "S", Nickname = "" });
        ctx.Styles.Add(new Style { Id = 1, Name = "House" });
        // The curated catalogue: approved, ownerless.
        ctx.Dances.Add(new Dance { Id = 1, Name = "Loose Legs", Slug = "loose-legs", ReviewState = "approved" });
        ctx.DanceStyles.Add(new DanceStyle { DanceId = 1, StyleId = 1 });
        ctx.SaveChanges();
    }

    private AppDbContext NewCtx() => new(_options);

    private DanceService NewService(AppDbContext ctx) =>
        new(ctx, new MemoryCache(new MemoryCacheOptions()));

    private static CreateDanceRequest Submission(string name = "Farmer") => new()
    {
        Name = name,
        StyleIds = new List<int> { 1 }
    };

    [Fact]
    public async Task AUserSubmissionIsHeldForReviewAndAttributed()
    {
        await using var ctx = NewCtx();
        var (result, dance) = await NewService(ctx).CreateAsync(Submission(), Contributor, isAdmin: false);

        Assert.Equal(CreateDanceResult.Ok, result);
        Assert.Equal("pending", dance!.ReviewState);
        // Provenance is the other half: without it a junk entry is untraceable.
        Assert.Equal(Contributor, dance.OwnerUserId);
    }

    [Fact]
    public async Task AnAdminsDanceGoesStraightIntoTheCatalogue()
    {
        await using var ctx = NewCtx();
        var (_, dance) = await NewService(ctx).CreateAsync(Submission(), Contributor, isAdmin: true);
        Assert.Equal("approved", dance!.ReviewState);
    }

    [Fact]
    public async Task APendingDanceIsInvisibleToEveryoneButItsAuthorAndAnAdmin()
    {
        int id;
        await using (var ctx = NewCtx())
            id = (await NewService(ctx).CreateAsync(Submission(), Contributor, false)).Dance!.Id;

        await using var check = NewCtx();
        var service = NewService(check);

        // Every read a visitor could arrive through.
        Assert.Null(await service.GetByIdAsync(id, null));
        Assert.Null(await service.GetByIdAsync(id, Stranger));
        Assert.Null(await service.GetBySlugAsync("farmer", Stranger));
        Assert.Null(await service.GetByStyleAndSlugAsync("house", "farmer", Stranger));
        Assert.DoesNotContain(await service.GetNamesAsync(Stranger), n => n.Id == id);

        var browse = await service.SearchAsync("", null, null, null, null, "name", Stranger);
        Assert.DoesNotContain(browse.Items, d => d.Id == id);

        // And the two ways in that must still work.
        Assert.NotNull(await service.GetByIdAsync(id, Contributor));
        Assert.NotNull(await service.GetByIdAsync(id, null, isAdmin: true));
    }

    [Fact]
    public async Task ItsAuthorStillFindsItInTheirOwnBrowseAndNameList()
    {
        int id;
        await using (var ctx = NewCtx())
            id = (await NewService(ctx).CreateAsync(Submission(), Contributor, false)).Dance!.Id;

        await using var check = NewCtx();
        var service = NewService(check);

        // The author has to keep seeing their own submission — they add a video to it next.
        var mine = await service.SearchAsync("", null, null, null, null, "name", Contributor);
        Assert.Contains(mine.Items, d => d.Id == id);
        Assert.Contains(await service.GetNamesAsync(Contributor), n => n.Id == id);
    }

    [Fact]
    public async Task ThePublicCountIgnoresWhatIsStillWaiting()
    {
        await using (var ctx = NewCtx())
            await NewService(ctx).CreateAsync(Submission(), Contributor, false);

        await using var check = NewCtx();
        var browse = await NewService(check).SearchAsync("", null, null, null, null, "name", Stranger);
        // "N of M dances" would otherwise promise a dance the visitor can never reach.
        Assert.Equal(1, browse.GrandTotal);
    }

    [Fact]
    public async Task ApprovingItPutsItInFrontOfEveryone()
    {
        int id;
        await using (var ctx = NewCtx())
            id = (await NewService(ctx).CreateAsync(Submission(), Contributor, false)).Dance!.Id;

        await using (var ctx = NewCtx())
        {
            var service = NewService(ctx);
            Assert.Contains(await service.GetPendingAsync(), d => d.Id == id);
            await service.SetReviewStateAsync(id, "approved");
        }

        await using var check = NewCtx();
        Assert.NotNull(await NewService(check).GetByIdAsync(id, Stranger));
    }

    [Fact]
    public async Task ASecondDanceOfTheSameNameInTheSameStyleIsRefused()
    {
        await using var ctx = NewCtx();
        var (result, existing) = await NewService(ctx).CreateAsync(
            Submission("loose legs"), Contributor, isAdmin: false);

        // Known-issues B: this is how prod ended up with Reebok five times. The caller is handed
        // the dance they meant, rather than a sixth one.
        Assert.Equal(CreateDanceResult.DuplicateName, result);
        Assert.Equal(1, existing!.Id);
    }

    [Fact]
    public async Task AContributorMayWithdrawTheirOwnSubmissionButNotACataloguedDance()
    {
        int id;
        await using (var ctx = NewCtx())
            id = (await NewService(ctx).CreateAsync(Submission(), Contributor, false)).Dance!.Id;

        await using (var ctx = NewCtx())
        {
            var service = NewService(ctx);
            // Not someone else's, and not a dance already in the catalogue that others may have
            // favourited — that stays an admin decision.
            Assert.False(await service.DeleteAsync(id, Stranger, isAdmin: false));
            Assert.False(await service.DeleteAsync(1, Contributor, isAdmin: false));
            Assert.True(await service.DeleteAsync(id, Contributor, isAdmin: false));
        }

        await using var check = NewCtx();
        Assert.Null(await NewService(check).GetByIdAsync(id, null, isAdmin: true));
    }

    public void Dispose()
    {
        _conn.Dispose();
        GC.SuppressFinalize(this);
    }
}
