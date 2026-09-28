using DancePlatform.API.Data;
using DancePlatform.API.Models;
using DancePlatform.API.Services;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace DancePlatform.Tests;

/// <summary>
/// The glossary seeder and service against SQLite in-memory. The seeder's contract that matters
/// most is that a re-seed never costs a user their learned marks, so that is tested explicitly.
/// </summary>
public class GlossaryTests : IDisposable
{
    private const int User = 1;
    private const int HouseStyle = 10;

    private readonly SqliteConnection _conn;
    private readonly DbContextOptions<AppDbContext> _options;
    private readonly string _root;

    public GlossaryTests()
    {
        _conn = new SqliteConnection("DataSource=:memory:");
        _conn.Open();
        using (var pragma = _conn.CreateCommand())
        {
            pragma.CommandText = "PRAGMA foreign_keys = ON;";
            pragma.ExecuteNonQuery();
        }
        _options = new DbContextOptionsBuilder<AppDbContext>().UseSqlite(_conn).Options;

        using var ctx = new AppDbContext(_options);
        ctx.Database.EnsureCreated();
        ctx.Users.Add(new User { Id = User, Username = "u", PasswordHash = "x", Name = "U", Nickname = "" });
        ctx.Styles.Add(new Style { Id = HouseStyle, Name = "House" });
        ctx.Styles.Add(new Style { Id = 11, Name = "Hip-hop" });
        ctx.Dances.Add(new Dance { Id = 100, Name = "House Jack", Slug = "house-jack" });
        // Same slug in another style, with a lower id: slugs are unique per style only, and a
        // global lookup keyed on slug crashed the boot in production.
        ctx.Dances.Add(new Dance { Id = 50, Name = "Other Jack", Slug = "house-jack" });
        ctx.DanceStyles.Add(new DanceStyle { DanceId = 100, StyleId = HouseStyle });
        ctx.DanceStyles.Add(new DanceStyle { DanceId = 50, StyleId = 11 });
        ctx.Videos.Add(new Video { Id = 1, DanceId = 100, Title = "Jack", VideoId = "abc", Platform = "youtube" });
        ctx.SaveChanges();

        _root = Path.Combine(Path.GetTempPath(), "glossary-tests-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(Path.Combine(_root, "Data", "Glossary"));
    }

    public void Dispose()
    {
        _conn.Dispose();
        Directory.Delete(_root, recursive: true);
    }

    private AppDbContext NewCtx() => new(_options);

    private void WriteHouse(string terms) => File.WriteAllText(
        Path.Combine(_root, "Data", "Glossary", "house.json"),
        $$"""
        // comment lines are allowed
        { "styleName": "House", "categories": [ { "name": "Grooves", "terms": [ {{terms}} ] } ] }
        """);

    private const string Jack = """
        { "slug": "jack", "name": "The jack", "summary": "s", "description": "d",
          "steps": ["one", "two"], "related": ["bounce", "nope"], "difficulty": "Beginner", "danceSlug": "house-jack" }
        """;
    private const string Bounce = """{ "slug": "bounce", "name": "Bounce", "summary": "s", "description": "d" }""";
    private const string Concept = """{ "slug": "on-the-one", "name": "On the one", "learnable": false, "summary": "s", "description": "d" }""";

    private async Task Seed()
    {
        using var ctx = NewCtx();
        await GlossarySeeder.SeedAsync(ctx, _root, NullLogger.Instance);
    }

    private async Task<int> TermId(string slug)
    {
        using var ctx = NewCtx();
        return await ctx.GlossaryTerms.Where(t => t.Slug == slug).Select(t => t.Id).SingleAsync();
    }

    [Fact]
    public async Task Seeds_terms_links_the_dance_and_drops_unknown_related_slugs()
    {
        WriteHouse($"{Jack}, {Bounce}, {Concept}");
        await Seed();

        using var ctx = NewCtx();
        var g = await new GlossaryService(ctx).GetByStyleAsync("house", null);

        Assert.NotNull(g);
        Assert.Equal(3, g!.TermCount);
        Assert.Equal(2, g.MoveCount);
        var jack = g.Categories.Single().Terms.First();
        Assert.Equal("jack", jack.Slug);
        Assert.Equal(new[] { "one", "two" }, jack.Steps);
        Assert.Equal("Beginner", jack.Difficulty);
        Assert.Equal(100, jack.Dance?.Id);
        Assert.Equal(new[] { "bounce" }, jack.Related.Select(r => r.Slug));
    }

    [Fact]
    public async Task Reseeding_keeps_learned_marks_and_removes_dropped_terms()
    {
        WriteHouse($"{Jack}, {Bounce}");
        await Seed();
        var jackId = await TermId("jack");
        using (var ctx = NewCtx())
            Assert.True(await new GlossaryService(ctx).SetLearnedAsync(User, jackId, true));

        // Reworded jack, bounce removed.
        WriteHouse(Jack.Replace("\"description\": \"d\"", "\"description\": \"reworded\""));
        await Seed();

        using var check = NewCtx();
        Assert.Equal(jackId, await TermId("jack"));
        Assert.Equal("reworded", (await check.GlossaryTerms.SingleAsync(t => t.Id == jackId)).Description);
        Assert.False(await check.GlossaryTerms.AnyAsync(t => t.Slug == "bounce"));
        Assert.True(await check.UserLearnedGlossaryTerms.AnyAsync(l => l.UserId == User && l.GlossaryTermId == jackId));
    }

    [Fact]
    public async Task Learned_marks_are_idempotent_and_concepts_refuse_them()
    {
        WriteHouse($"{Jack}, {Concept}");
        await Seed();
        var jackId = await TermId("jack");
        var conceptId = await TermId("on-the-one");

        using (var ctx = NewCtx())
        {
            var svc = new GlossaryService(ctx);
            Assert.True(await svc.SetLearnedAsync(User, jackId, true));
            Assert.True(await svc.SetLearnedAsync(User, jackId, true));
            Assert.False(await svc.SetLearnedAsync(User, conceptId, true));
            Assert.False(await svc.SetLearnedAsync(User, 9999, true));
        }

        using (var ctx = NewCtx())
        {
            var g = await new GlossaryService(ctx).GetByStyleAsync("house", User);
            Assert.Equal(1, g!.LearnedCount);
            var summary = Assert.Single(await new GlossaryService(ctx).GetAllAsync(User));
            Assert.Equal(1, summary.LearnedCount);
            Assert.Equal(0, (await new GlossaryService(ctx).GetAllAsync(null)).Single().LearnedCount);
        }

        using (var ctx = NewCtx())
        {
            Assert.True(await new GlossaryService(ctx).SetLearnedAsync(User, jackId, false));
            Assert.False(await ctx.UserLearnedGlossaryTerms.AnyAsync());
        }
    }

    [Fact]
    public async Task Duplicate_slugs_refuse_the_whole_file()
    {
        WriteHouse($"{Jack}, {Jack}");
        await Seed();
        using var ctx = NewCtx();
        Assert.False(await ctx.GlossaryTerms.AnyAsync());
    }

    /// <summary>
    /// The shipped content itself: parses, seeds in full, and every related slug resolves — a typo
    /// there would otherwise only show up as a silently missing chip in production.
    /// </summary>
    [Fact]
    public async Task Authored_house_glossary_seeds_cleanly()
    {
        var dir = AppContext.BaseDirectory;
        while (dir is not null && !Directory.Exists(Path.Combine(dir, "DancePlatform.API", "Data", "Glossary")))
            dir = Path.GetDirectoryName(dir);
        Assert.NotNull(dir);
        var apiRoot = Path.Combine(dir!, "DancePlatform.API");

        using (var ctx = NewCtx())
            await GlossarySeeder.SeedAsync(ctx, apiRoot, NullLogger.Instance);

        using var check = NewCtx();
        var terms = await check.GlossaryTerms.Where(t => t.StyleId == HouseStyle).ToListAsync();
        Assert.True(terms.Count > 30, $"expected a full glossary, got {terms.Count}");
        Assert.Contains(terms, t => t.Slug == "jack" && t.IsLearnable);
        var slugs = terms.Select(t => t.Slug).ToHashSet();
        Assert.All(terms, t => Assert.All(t.Related, r => Assert.Contains(r, slugs)));
        Assert.All(terms.Where(t => t.IsLearnable), t => Assert.NotEmpty(t.Steps));
    }
}
