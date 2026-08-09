using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Roadmap;
using DancePlatform.API.Models;
using DancePlatform.API.Services;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace DancePlatform.Tests;

/// <summary>
/// The personal skill tree write path, against a real (SQLite in-memory) relational store rather
/// than the in-memory provider, so the projections and foreign keys behave as they do on Postgres.
///
/// One known fidelity gap, measured rather than assumed: SQLite enforces the foreign keys here
/// (the fixture turns the pragma on), but it still **tolerates the cascade ordering Postgres
/// rejects** — deleting a step while another step's prerequisite row still points at it through
/// the NoAction side. So the delete/rebuild tests below verify the *outcome* (the right rows are
/// gone, the wrong caller is refused); they do not guard the ordering. The e2e suite, which runs
/// against real Postgres, is what catches that — and did.
/// </summary>
public class RoadmapServiceTests : IDisposable
{
    private const int Owner = 1;
    private const int Stranger = 2;
    private const int HouseStyle = 10;

    private readonly SqliteConnection _conn;
    private readonly DbContextOptions<AppDbContext> _options;

    public RoadmapServiceTests()
    {
        _conn = new SqliteConnection("DataSource=:memory:");
        _conn.Open(); // keep it open so the schema/data survive across contexts

        // SQLite enforces foreign keys only when asked, and EF's provider asks on the
        // connections *it* opens — not one handed to it already open, as here. Without this the
        // whole point of using a relational store for these tests is lost: the rebuild and
        // delete paths both step around a NoAction constraint on RoadmapStepPrerequisites, and
        // an unenforced FK lets a broken ordering pass.
        using (var pragma = _conn.CreateCommand())
        {
            pragma.CommandText = "PRAGMA foreign_keys = ON;";
            pragma.ExecuteNonQuery();
        }

        _options = new DbContextOptionsBuilder<AppDbContext>().UseSqlite(_conn).Options;

        using var ctx = new AppDbContext(_options);
        ctx.Database.EnsureCreated();
        ctx.Users.AddRange(
            new User { Id = Owner, Username = "owner", PasswordHash = "x", Name = "Owner", Nickname = "" },
            new User { Id = Stranger, Username = "stranger", PasswordHash = "x", Name = "Stranger", Nickname = "" });
        ctx.Styles.Add(new Style { Id = HouseStyle, Name = "House" });
        ctx.Dances.Add(new Dance { Id = 100, Name = "The jack", Slug = "house-jack" });
        ctx.SaveChanges();
    }

    private AppDbContext NewCtx() => new(_options);
    private static RoadmapService Svc(AppDbContext ctx) => new(ctx);

    private static SaveRoadmapRequest Request(string title, params SaveRoadmapStepRequest[] steps) => new()
    {
        Title = title,
        StyleId = HouseStyle,
        Stages = [new SaveRoadmapStageRequest { Title = "Branch one", Steps = [.. steps] }]
    };

    private static SaveRoadmapStepRequest Step(string key, string title, params string[] requires) =>
        new() { Key = key, Title = title, Requires = [.. requires] };

    // ---- Creating ---------------------------------------------------------------------------

    [Fact]
    public async Task Create_StoresTheTreeAndComputesRings()
    {
        await using var ctx = NewCtx();
        var result = await Svc(ctx).CreateAsync(Owner, Request("My House path",
            Step("a", "The jack"),
            Step("b", "The heel toe", "a"),
            Step("c", "The farmer", "b")));

        Assert.Null(result.Error);
        var tree = result.Roadmap!;
        Assert.True(tree.IsOwned);
        Assert.Equal(3, tree.StepCount);

        // Depth is the longest distance from a root — the ring the node lands on.
        var steps = tree.Stages.SelectMany(s => s.Steps).ToDictionary(s => s.Key);
        Assert.Equal(0, steps["a"].Depth);
        Assert.Equal(1, steps["b"].Depth);
        Assert.Equal(2, steps["c"].Depth);
        Assert.Equal(["b"], steps["c"].Requires);
    }

    /// <summary>
    /// Slugs are unique across curated and personal paths alike, and the style names are what the
    /// authored files use — a user's "House" tree must not sit on the slug the House file wants.
    /// </summary>
    [Fact]
    public async Task Create_StepsAroundStyleSlugsAndExistingRoadmaps()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);

        var first = await svc.CreateAsync(Owner, Request("House", Step("a", "The jack")));
        var second = await svc.CreateAsync(Owner, Request("House", Step("a", "The jack")));

        Assert.Equal("house-2", first.Roadmap!.Slug);   // "house" is reserved by the style
        Assert.Equal("house-3", second.Roadmap!.Slug);
    }

    [Fact]
    public async Task Create_RejectsATreeWithNoName()
    {
        await using var ctx = NewCtx();
        var result = await Svc(ctx).CreateAsync(Owner, Request("   ", Step("a", "The jack")));

        Assert.Null(result.Roadmap);
        Assert.Contains("name", result.Error, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task Create_RejectsAnUnknownStyle()
    {
        await using var ctx = NewCtx();
        var request = Request("My path", Step("a", "The jack"));
        request.StyleId = 999;

        var result = await Svc(ctx).CreateAsync(Owner, request);

        Assert.Null(result.Roadmap);
        Assert.Contains("style", result.Error, StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>
    /// A cycle has no depth and makes every node in it unreachable. The seeder drops the edge and
    /// logs; a save refuses, because the user drew that link seconds ago and dropping it silently
    /// would read as the save not working.
    /// </summary>
    [Fact]
    public async Task Create_RefusesACycle()
    {
        await using var ctx = NewCtx();
        var result = await Svc(ctx).CreateAsync(Owner, Request("Looping path",
            Step("a", "First", "c"),
            Step("b", "Second", "a"),
            Step("c", "Third", "b")));

        Assert.Null(result.Roadmap);
        Assert.Contains("each end up coming after the other", result.Error);
        Assert.Empty(await ctx.Roadmaps.ToListAsync());
    }

    [Fact]
    public async Task Create_DropsBlankStepsAndEdgesThatNameNothing()
    {
        await using var ctx = NewCtx();
        var result = await Svc(ctx).CreateAsync(Owner, Request("My path",
            Step("a", "The jack"),
            Step("blank", "   "),                    // a row the user opened and never filled in
            Step("b", "The heel toe", "a", "gone"))); // "gone" was deleted in another tab

        var steps = result.Roadmap!.Stages.SelectMany(s => s.Steps).ToList();
        Assert.Equal(2, steps.Count);
        Assert.Equal(["a"], steps.Single(s => s.Key == "b").Requires);
    }

    /// <summary>
    /// The client owns its keys but doesn't have to keep them tidy. A repeat is uniquified rather
    /// than rejected, and `requires` still lands on the first step of that name.
    /// </summary>
    [Fact]
    public async Task Create_UniquifiesRepeatedKeys()
    {
        await using var ctx = NewCtx();
        var result = await Svc(ctx).CreateAsync(Owner, Request("My path",
            Step("dup", "First"),
            Step("dup", "Second"),
            Step("c", "Third", "dup")));

        var steps = result.Roadmap!.Stages.SelectMany(s => s.Steps).ToList();
        Assert.Equal(["dup", "dup-2", "c"], steps.Select(s => s.Key));
        Assert.Equal(["dup"], steps.Single(s => s.Key == "c").Requires);
    }

    [Fact]
    public async Task Create_NullsALinkToADanceThatDoesNotExist()
    {
        await using var ctx = NewCtx();
        var request = Request("My path", Step("a", "The jack"), Step("b", "Ghost"));
        request.Stages[0].Steps[0].DanceId = 100;
        request.Stages[0].Steps[1].DanceId = 999;

        var steps = (await Svc(ctx).CreateAsync(Owner, request)).Roadmap!.Stages.SelectMany(s => s.Steps).ToList();

        Assert.Equal(100, steps[0].Dance!.Id);
        Assert.Null(steps[1].Dance);
    }

    // ---- Updating ---------------------------------------------------------------------------

    /// <summary>
    /// A save replaces the tree wholesale: every step goes and is recreated, and the stored edges
    /// must end up matching the request rather than accumulating.
    ///
    /// (The *ordering* this depends on — edges cleared before the steps they point at — is not
    /// what this asserts; see the class summary. This asserts the result.)
    /// </summary>
    [Fact]
    public async Task Update_ReplacesTheWholeTreeIncludingItsEdges()
    {
        int id;
        await using (var ctx = NewCtx())
        {
            var created = await Svc(ctx).CreateAsync(Owner, Request("My path",
                Step("a", "The jack"),
                Step("b", "The heel toe", "a"),
                Step("c", "The farmer", "b")));
            id = created.Roadmap!.Id;
        }

        await using (var ctx = NewCtx())
        {
            // Every original step goes; the replacement shares one key but nothing else.
            var result = await Svc(ctx).UpdateAsync(Owner, id, Request("My path, re-cut",
                Step("a", "The jack"),
                Step("z", "The skate", "a")));

            Assert.Null(result.Error);
            Assert.Equal("My path, re-cut", result.Roadmap!.Title);
            Assert.Equal(["a", "z"], result.Roadmap.Stages.SelectMany(s => s.Steps).Select(s => s.Key));
        }

        await using (var ctx = NewCtx())
        {
            Assert.Equal(2, await ctx.RoadmapSteps.CountAsync());
            Assert.Equal(1, await ctx.RoadmapStepPrerequisites.CountAsync());
        }
    }

    /// <summary>The slug is the tree's URL, so renaming must not move it.</summary>
    [Fact]
    public async Task Update_KeepsTheSlugWhenTheTitleChanges()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var created = (await svc.CreateAsync(Owner, Request("My path", Step("a", "The jack")))).Roadmap!;

        var updated = await svc.UpdateAsync(Owner, created.Id, Request("Something else", Step("a", "The jack")));

        Assert.Equal(created.Slug, updated.Roadmap!.Slug);
    }

    [Fact]
    public async Task Update_RefusesATreeThatIsNotTheCallersOwn()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var mine = (await svc.CreateAsync(Owner, Request("My path", Step("a", "The jack")))).Roadmap!;

        var result = await svc.UpdateAsync(Stranger, mine.Id, Request("Hijacked", Step("a", "Mine now")));

        // Not-found rather than forbidden: whether someone else has a tree here isn't their business.
        Assert.Null(result.Roadmap);
        Assert.Null(result.Error);
        Assert.Equal("My path", (await svc.GetByIdOrSlugAsync(mine.Id.ToString(), Owner))!.Title);
    }

    /// <summary>Curated paths are content, edited by editing their JSON file — never through here.</summary>
    [Fact]
    public async Task Update_RefusesACuratedPath()
    {
        int curatedId;
        await using (var ctx = NewCtx())
        {
            var curated = new Roadmap { Slug = "house", Title = "House", StyleId = HouseStyle };
            ctx.Roadmaps.Add(curated);
            await ctx.SaveChangesAsync();
            curatedId = curated.Id;
        }

        await using (var ctx = NewCtx())
        {
            var result = await Svc(ctx).UpdateAsync(Owner, curatedId, Request("Mine now", Step("a", "The jack")));
            Assert.Null(result.Roadmap);
            Assert.Null(result.Error);
        }
    }

    // ---- Visibility -------------------------------------------------------------------------

    [Fact]
    public async Task GetAll_ShowsCuratedPathsAndOnlyTheCallersOwnTrees()
    {
        await using var ctx = NewCtx();
        ctx.Roadmaps.Add(new Roadmap { Slug = "house", Title = "House", StyleId = HouseStyle });
        await ctx.SaveChangesAsync();

        var svc = Svc(ctx);
        await svc.CreateAsync(Owner, Request("Mine", Step("a", "The jack")));
        await svc.CreateAsync(Stranger, Request("Theirs", Step("a", "The jack")));

        Assert.Equal(["House", "Mine"], (await svc.GetAllAsync(Owner)).Select(r => r.Title).Order());
        Assert.Equal(["House", "Theirs"], (await svc.GetAllAsync(Stranger)).Select(r => r.Title).Order());
        // Signed out: the curated paths and nothing else.
        Assert.Equal(["House"], (await svc.GetAllAsync(null)).Select(r => r.Title));
    }

    [Fact]
    public async Task GetByIdOrSlug_HidesAnotherUsersTree()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var mine = (await svc.CreateAsync(Owner, Request("Mine", Step("a", "The jack")))).Roadmap!;

        Assert.NotNull(await svc.GetByIdOrSlugAsync(mine.Slug, Owner));
        Assert.Null(await svc.GetByIdOrSlugAsync(mine.Slug, Stranger));
        Assert.Null(await svc.GetByIdOrSlugAsync(mine.Slug, null));
    }

    // ---- Deleting and copying ---------------------------------------------------------------

    [Fact]
    public async Task Delete_TakesTheTreeAndItsEdgesButOnlyForItsOwner()
    {
        int id;
        await using (var ctx = NewCtx())
        {
            id = (await Svc(ctx).CreateAsync(Owner, Request("My path",
                Step("a", "The jack"),
                Step("b", "The heel toe", "a")))).Roadmap!.Id;
        }

        await using (var ctx = NewCtx()) Assert.False(await Svc(ctx).DeleteAsync(Stranger, id));
        await using (var ctx = NewCtx()) Assert.True(await Svc(ctx).DeleteAsync(Owner, id));

        await using (var ctx = NewCtx())
        {
            Assert.Empty(await ctx.Roadmaps.ToListAsync());
            Assert.Empty(await ctx.RoadmapSteps.ToListAsync());
            Assert.Empty(await ctx.RoadmapStepPrerequisites.ToListAsync());
        }
    }

    /// <summary>
    /// Forking a curated path is how it gets personalised: the curated one is untouched, and the
    /// copy carries the structure over so it isn't a blank page with extra steps.
    /// </summary>
    [Fact]
    public async Task Copy_ForksAPathIntoOneOfTheCallersOwn()
    {
        await using var ctx = NewCtx();
        var curated = new Roadmap
        {
            Slug = "house", Title = "House", StyleId = HouseStyle,
            Stages = [new RoadmapStage { Title = "Find the pulse", SortOrder = 0, Steps = [
                new RoadmapStep { Key = "jack", Title = "The jack", SortOrder = 0, DanceId = 100 },
                new RoadmapStep { Key = "heel-toe", Title = "The heel toe", SortOrder = 1 }
            ] }]
        };
        ctx.Roadmaps.Add(curated);
        await ctx.SaveChangesAsync();
        ctx.RoadmapStepPrerequisites.Add(new RoadmapStepPrerequisite
        {
            StepId = curated.Stages[0].Steps[1].Id,
            PrerequisiteStepId = curated.Stages[0].Steps[0].Id
        });
        await ctx.SaveChangesAsync();

        var svc = Svc(ctx);
        var copy = (await svc.CopyAsync(Owner, "house")).Roadmap!;

        Assert.True(copy.IsOwned);
        Assert.Equal("House (my copy)", copy.Title);
        Assert.NotEqual("house", copy.Slug);
        var steps = copy.Stages.SelectMany(s => s.Steps).ToList();
        Assert.Equal(["The jack", "The heel toe"], steps.Select(s => s.Title));
        Assert.Equal(["jack"], steps[1].Requires);   // the edge came with it
        Assert.Equal(100, steps[0].Dance!.Id);       // and so did the catalog link

        // The original is untouched, and still everyone's.
        var original = (await svc.GetByIdOrSlugAsync("house", Owner))!;
        Assert.False(original.IsOwned);
        Assert.Equal("House", original.Title);
    }

    [Fact]
    public async Task Copy_RefusesAnotherUsersTree()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var theirs = (await svc.CreateAsync(Stranger, Request("Theirs", Step("a", "The jack")))).Roadmap!;

        var result = await svc.CopyAsync(Owner, theirs.Slug);

        Assert.Null(result.Roadmap);
        Assert.Null(result.Error);
    }

    // ---- Sharing ----------------------------------------------------------------------------

    [Fact]
    public async Task Create_MakesAPrivateTree()
    {
        await using var ctx = NewCtx();
        var tree = (await Svc(ctx).CreateAsync(Owner, Request("Mine", Step("a", "The jack")))).Roadmap!;

        Assert.False(tree.IsPublic);
        Assert.Equal("owner", tree.OwnerUsername);
    }

    /// <summary>
    /// Sharing widens the read to everyone with the link — signed out included, who get the same
    /// teaser the curated paths give. It stays off the roadmap index either way; that is the
    /// curated shelf, and nothing here is moderated.
    /// </summary>
    [Fact]
    public async Task SetShared_OpensTheTreeToEveryoneWithTheLinkButNotTheIndex()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var tree = (await svc.CreateAsync(Owner, Request("Mine", Step("a", "The jack")))).Roadmap!;

        Assert.Null(await svc.GetByIdOrSlugAsync(tree.Slug, Stranger));

        var shared = await svc.SetSharedAsync(Owner, tree.Id, true);
        Assert.True(shared!.IsPublic);

        var asStranger = await svc.GetByIdOrSlugAsync(tree.Slug, Stranger);
        Assert.NotNull(asStranger);
        Assert.False(asStranger!.IsOwned);            // readable, not editable
        Assert.Equal("owner", asStranger.OwnerUsername);
        Assert.NotNull(await svc.GetByIdOrSlugAsync(tree.Slug, null));

        Assert.DoesNotContain(await svc.GetAllAsync(Stranger), r => r.Slug == tree.Slug);
        Assert.DoesNotContain(await svc.GetAllAsync(null), r => r.Slug == tree.Slug);
        // The owner still sees their own, shared or not.
        Assert.Contains(await svc.GetAllAsync(Owner), r => r.Slug == tree.Slug);
    }

    [Fact]
    public async Task SetShared_ClosesTheTreeAgain()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var tree = (await svc.CreateAsync(Owner, Request("Mine", Step("a", "The jack")))).Roadmap!;

        await svc.SetSharedAsync(Owner, tree.Id, true);
        var closed = await svc.SetSharedAsync(Owner, tree.Id, false);

        Assert.False(closed!.IsPublic);
        Assert.Null(await svc.GetByIdOrSlugAsync(tree.Slug, Stranger));
    }

    [Fact]
    public async Task SetShared_RefusesATreeThatIsNotTheCallersOwn()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var tree = (await svc.CreateAsync(Owner, Request("Mine", Step("a", "The jack")))).Roadmap!;

        Assert.Null(await svc.SetSharedAsync(Stranger, tree.Id, true));
        Assert.Null(await svc.GetByIdOrSlugAsync(tree.Slug, Stranger));
    }

    /// <summary>A save must not be able to unshare a tree — sharing is its own endpoint.</summary>
    [Fact]
    public async Task Update_LeavesSharingAlone()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var tree = (await svc.CreateAsync(Owner, Request("Mine", Step("a", "The jack")))).Roadmap!;
        await svc.SetSharedAsync(Owner, tree.Id, true);

        var updated = await svc.UpdateAsync(Owner, tree.Id, Request("Mine, re-cut", Step("a", "The jack")));

        Assert.True(updated.Roadmap!.IsPublic);
    }

    /// <summary>
    /// A fork of a shared tree is private. Inheriting the flag would republish someone else's
    /// work under a new owner without them ever choosing to.
    /// </summary>
    [Fact]
    public async Task Copy_OfASharedTreeIsPrivateAndOwnedByTheForker()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var theirs = (await svc.CreateAsync(Stranger, Request("Theirs", Step("a", "The jack")))).Roadmap!;
        await svc.SetSharedAsync(Stranger, theirs.Id, true);

        var fork = (await svc.CopyAsync(Owner, theirs.Slug)).Roadmap!;

        Assert.False(fork.IsPublic);
        Assert.True(fork.IsOwned);
        Assert.Equal("owner", fork.OwnerUsername);
        // And the original is untouched.
        Assert.True((await svc.GetByIdOrSlugAsync(theirs.Slug, Stranger))!.IsPublic);
    }

    // ---- Modules ----------------------------------------------------------------------------

    /// <summary>Links `child` as the module of the first step of `parent`.</summary>
    private static SaveRoadmapRequest WithModule(string title, int childId, params SaveRoadmapStepRequest[] steps)
    {
        var request = Request(title, steps);
        request.Stages[0].Steps[0].ChildRoadmapId = childId;
        return request;
    }

    [Fact]
    public async Task Module_GatewayIsLearnedOnlyWhenEveryCompletableStepInItIs()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);

        // The module has one completable step (a linked move) and one that can never be ticked.
        var module = (await svc.CreateAsync(Owner, Request("Posing",
            Step("pose", "Basic pose"), Step("drill", "A drill with no video")))).Roadmap!;
        await svc.UpdateAsync(Owner, module.Id, Request("Posing",
            new SaveRoadmapStepRequest { Key = "pose", Title = "Basic pose", DanceId = 100 },
            Step("drill", "A drill with no video")));

        var parent = (await svc.CreateAsync(Owner, WithModule("Waacking", module.Id,
            Step("gateway", "Posing")))).Roadmap!;

        var gateway = parent.Stages[0].Steps[0];
        Assert.NotNull(gateway.Module);
        Assert.Equal(module.Id, gateway.Module!.Id);
        Assert.Equal(1, gateway.Module.CompletableCount);   // the unlinked step doesn't count
        Assert.Equal(0, gateway.Module.LearnedCount);
        Assert.False(gateway.Module.IsComplete);
        Assert.Equal("available", gateway.State);

        // Learn the move the module hangs on, and the gateway marks itself.
        ctx.UserLearnedDances.Add(new UserLearnedDance { UserId = Owner, DanceId = 100 });
        await ctx.SaveChangesAsync();

        var after = (await Svc(NewCtx()).GetByIdOrSlugAsync(parent.Slug, Owner))!;
        var done = after.Stages[0].Steps[0];
        Assert.True(done.Module!.IsComplete);
        Assert.Equal("learned", done.State);
        Assert.Equal(1, after.LearnedCount);
    }

    [Fact]
    public async Task Module_WithNothingCompletableNeverReportsItselfComplete()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var module = (await svc.CreateAsync(Owner, Request("Empty", Step("a", "No video")))).Roadmap!;
        var parent = (await svc.CreateAsync(Owner, WithModule("Parent", module.Id, Step("g", "Gateway")))).Roadmap!;

        var gateway = parent.Stages[0].Steps[0];
        Assert.Equal(0, gateway.Module!.CompletableCount);
        Assert.False(gateway.Module.IsComplete);
    }

    [Fact]
    public async Task Module_IsKeptOffTheIndexButItsCountsRollUpIntoItsParent()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var module = (await svc.CreateAsync(Owner, Request("Posing",
            new SaveRoadmapStepRequest { Key = "p", Title = "Basic pose", DanceId = 100 }))).Roadmap!;
        var parent = (await svc.CreateAsync(Owner, WithModule("Waacking", module.Id, Step("g", "Posing")))).Roadmap!;

        var index = await svc.GetAllAsync(Owner);

        Assert.DoesNotContain(index, r => r.Id == module.Id);
        var row = Assert.Single(index, r => r.Id == parent.Id);
        // 1 gateway + 1 step inside it.
        Assert.Equal(2, row.StepCount);
    }

    /// <summary>
    /// The one that actually matters for privacy. A fork that re-linked the original's module
    /// would leave one user's tree containing a roadmap another user owns, can edit, and can
    /// delete underneath them — and would expose it to anyone the fork is later shared with.
    /// </summary>
    [Fact]
    public async Task Copy_DeepCopiesModulesRatherThanPointingAtTheOriginals()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var theirModule = (await svc.CreateAsync(Stranger, Request("Their posing",
            new SaveRoadmapStepRequest { Key = "p", Title = "Basic pose", DanceId = 100 }))).Roadmap!;
        var theirs = (await svc.CreateAsync(Stranger, WithModule("Theirs", theirModule.Id,
            Step("g", "Posing")))).Roadmap!;
        await svc.SetSharedAsync(Stranger, theirs.Id, true);

        var fork = (await svc.CopyAsync(Owner, theirs.Slug)).Roadmap!;

        var gateway = fork.Stages[0].Steps[0];
        Assert.NotNull(gateway.Module);
        Assert.NotEqual(theirModule.Id, gateway.Module!.Id);

        // The copy is the forker's, and private.
        var copied = (await svc.GetByIdOrSlugAsync(gateway.Module.Id.ToString(), Owner))!;
        Assert.True(copied.IsOwned);
        Assert.False(copied.IsPublic);
        Assert.Equal("Their posing", copied.Title);   // modules keep their name; only the root is renamed
        Assert.Equal(100, copied.Stages[0].Steps[0].Dance!.Id);
    }

    /// <summary>A module inherits its parent's visibility, or half a shared tree 404s.</summary>
    [Fact]
    public async Task Module_OfASharedTreeIsReadableByAStranger()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var module = (await svc.CreateAsync(Owner, Request("Posing", Step("p", "Basic pose")))).Roadmap!;
        var parent = (await svc.CreateAsync(Owner, WithModule("Mine", module.Id, Step("g", "Posing")))).Roadmap!;

        // Private to start with: the module is as invisible as its parent.
        Assert.Null(await svc.GetByIdOrSlugAsync(module.Slug, Stranger));

        await svc.SetSharedAsync(Owner, parent.Id, true);

        var seen = await svc.GetByIdOrSlugAsync(module.Slug, Stranger);
        Assert.NotNull(seen);
        // …and it knows where it came from, so the reader gets a breadcrumb rather than a
        // context-free tree.
        Assert.Equal(["Mine"], seen!.Ancestors!.Select(a => a.Title));
    }

    [Fact]
    public async Task Delete_TakesTheTreesModulesWithIt()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var module = (await svc.CreateAsync(Owner, Request("Posing", Step("p", "Basic pose")))).Roadmap!;
        var parent = (await svc.CreateAsync(Owner, WithModule("Mine", module.Id, Step("g", "Posing")))).Roadmap!;

        Assert.True(await svc.DeleteAsync(Owner, parent.Id));

        await using var check = NewCtx();
        Assert.Null(await check.Roadmaps.FindAsync(parent.Id));
        Assert.Null(await check.Roadmaps.FindAsync(module.Id));
    }

    [Fact]
    public async Task Module_CannotBeAnotherUsersTreeAndCannotLoop()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var theirs = (await svc.CreateAsync(Stranger, Request("Theirs", Step("a", "The jack")))).Roadmap!;
        var mine = (await svc.CreateAsync(Owner, Request("Mine", Step("g", "Gateway")))).Roadmap!;

        // Someone else's tree is dropped, not linked.
        var grabbed = (await svc.UpdateAsync(Owner, mine.Id,
            WithModule("Mine", theirs.Id, Step("g", "Gateway")))).Roadmap!;
        Assert.Null(grabbed.Stages[0].Steps[0].Module);

        // And a tree cannot be its own module.
        var selfish = (await svc.UpdateAsync(Owner, mine.Id,
            WithModule("Mine", mine.Id, Step("g", "Gateway")))).Roadmap!;
        Assert.Null(selfish.Stages[0].Steps[0].Module);
    }

    [Fact]
    public async Task Module_IsDroppedWhenAnotherStepAlreadyClaimsIt()
    {
        await using var ctx = NewCtx();
        var svc = Svc(ctx);
        var module = (await svc.CreateAsync(Owner, Request("Posing", Step("p", "Basic pose")))).Roadmap!;
        await svc.CreateAsync(Owner, WithModule("First", module.Id, Step("g", "Gateway")));

        var second = (await svc.CreateAsync(Owner, WithModule("Second", module.Id, Step("g", "Gateway")))).Roadmap!;

        Assert.Null(second.Stages[0].Steps[0].Module);
    }

    public void Dispose() => _conn.Dispose();
}
