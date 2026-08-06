using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Roadmap;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class RoadmapService : IRoadmapService
{
    private readonly AppDbContext _db;

    public RoadmapService(AppDbContext db) => _db = db;

    public async Task<List<RoadmapSummaryDto>> GetAllAsync(int? userId)
    {
        var uid = userId ?? 0;
        var hasUser = userId.HasValue;

        // One projection, no stage/step materialisation — the index only needs counts.
        var rows = await _db.Roadmaps
            // Curated paths plus the caller's own trees. Someone else's personal tree is private,
            // and filtering here rather than in the caller means no endpoint can forget to.
            .Where(r => r.OwnerUserId == null || (hasUser && r.OwnerUserId == uid))
            .OrderBy(r => r.SortOrder).ThenBy(r => r.Title)
            .Select(r => new
            {
                r.Id, r.Slug, r.Title, r.Subtitle, r.Description, r.StyleId, r.OwnerUserId,
                StyleName = r.Style.Name,
                StageCount = r.Stages.Count,
                StepCount = r.Stages.SelectMany(s => s.Steps).Count(),
                MoveCount = r.Stages.SelectMany(s => s.Steps).Count(st => st.DanceId != null),
                // Distinct: one dance can back several steps (a long tutorial sliced by segment),
                // and counting its videos once per step would inflate the headline figure.
                VideoCount = r.Stages.SelectMany(s => s.Steps)
                    .Where(st => st.Dance != null)
                    .SelectMany(st => st.Dance!.Videos)
                    .Where(v => v.OwnerUserId == null || v.OwnerUserId == uid)
                    .Select(v => v.Id)
                    .Distinct()
                    .Count(),
                LearnedCount = hasUser
                    ? r.Stages.SelectMany(s => s.Steps).Count(st => st.Dance != null && st.Dance.LearnedBy.Any(l => l.UserId == uid))
                    : 0,
                InProgressCount = hasUser
                    ? r.Stages.SelectMany(s => s.Steps).Count(st => st.Dance != null && st.Dance.InProgressBy.Any(p => p.UserId == uid))
                    : 0,
                // First video of the first linked step — the path's cover image.
                Thumbnail = r.Stages.OrderBy(s => s.SortOrder)
                    .SelectMany(s => s.Steps.OrderBy(st => st.SortOrder))
                    .Where(st => st.Dance != null)
                    .SelectMany(st => st.Dance!.Videos.Where(v => v.OwnerUserId == null || v.OwnerUserId == uid).OrderBy(v => v.DateAdded))
                    .Select(v => new { v.VideoId, v.Platform })
                    .FirstOrDefault()
            })
            .ToListAsync();

        return rows.Select(r => new RoadmapSummaryDto
        {
            Id = r.Id,
            Slug = r.Slug,
            Title = r.Title,
            Subtitle = r.Subtitle,
            Description = r.Description,
            StyleId = r.StyleId,
            StyleName = r.StyleName,
            StyleSlug = SlugGenerator.Slugify(r.StyleName),
            IsOwned = r.OwnerUserId != null,
            StageCount = r.StageCount,
            StepCount = r.StepCount,
            MoveCount = r.MoveCount,
            VideoCount = r.VideoCount,
            LearnedCount = r.LearnedCount,
            InProgressCount = r.InProgressCount,
            ThumbnailVideoId = r.Thumbnail?.VideoId,
            ThumbnailPlatform = r.Thumbnail?.Platform
        }).ToList();
    }

    public async Task<RoadmapDto?> GetByIdOrSlugAsync(string idOrSlug, int? userId)
    {
        var uid = userId ?? 0;
        var hasUser = userId.HasValue;

        var query = int.TryParse(idOrSlug, out var id)
            ? _db.Roadmaps.Where(r => r.Id == id)
            : _db.Roadmaps.Where(r => r.Slug == idOrSlug);

        // Another user's tree reads as "not found" rather than "forbidden": whether someone else
        // has a path at this slug isn't the caller's business either.
        query = query.Where(r => r.OwnerUserId == null || (hasUser && r.OwnerUserId == uid));

        var roadmap = await query
            .Select(r => new
            {
                r.Id, r.Slug, r.Title, r.Subtitle, r.Description, r.StyleId, r.OwnerUserId,
                StyleName = r.Style.Name,
                Stages = r.Stages.OrderBy(s => s.SortOrder).Select(s => new
                {
                    s.Id, s.Title, s.Description,
                    Steps = s.Steps.OrderBy(st => st.SortOrder).Select(st => new
                    {
                        st.Id, st.Key, st.Title, st.Description,
                        Requires = st.Prerequisites.Select(p => p.PrerequisiteStep.Key).ToList(),
                        Segment = st.VideoSegment == null ? null : new
                        {
                            st.VideoSegment.Id,
                            st.VideoSegment.Label,
                            st.VideoSegment.StartTime,
                            st.VideoSegment.EndTime,
                            st.VideoSegment.VideoId
                        },
                        Dance = st.Dance == null ? null : new
                        {
                            st.Dance.Id,
                            st.Dance.Name,
                            st.Dance.Slug,
                            // Canonical style = lowest StyleId, matching SlugGenerator.StyleSlug.
                            CanonicalStyleName = st.Dance.DanceStyles.OrderBy(ds => ds.StyleId).Select(ds => ds.Style.Name).FirstOrDefault(),
                            st.Dance.Difficulty,
                            st.Dance.AverageRating,
                            st.Dance.RatingCount,
                            IsLearned = hasUser && st.Dance.LearnedBy.Any(l => l.UserId == uid),
                            IsInProgress = hasUser && st.Dance.InProgressBy.Any(p => p.UserId == uid),
                            IsFavorite = hasUser && st.Dance.FavoritedBy.Any(f => f.UserId == uid),
                            // Global videos plus the viewer's own, same visibility rule as the dance page.
                            Videos = st.Dance.Videos
                                .Where(v => v.OwnerUserId == null || v.OwnerUserId == uid)
                                .OrderByDescending(v => v.AverageRating)
                                .ThenBy(v => v.DateAdded)
                                .Select(v => new
                                {
                                    v.Id, v.Title, v.VideoId, v.Platform, v.VideoType,
                                    v.StartTime, v.EndTime, v.DurationSeconds,
                                    v.ViewCount, v.AverageRating, v.RatingCount
                                }).ToList()
                        }
                    }).ToList()
                }).ToList()
            })
            .FirstOrDefaultAsync();

        if (roadmap is null) return null;

        var stages = roadmap.Stages.Select((s, si) => new RoadmapStageDto
        {
            Id = s.Id,
            Title = s.Title,
            Description = s.Description,
            Steps = s.Steps.Select(st => new RoadmapStepDto
            {
                Id = st.Id,
                Key = st.Key,
                Requires = st.Requires,
                StageIndex = si,
                Title = st.Title,
                Description = st.Description,
                Segment = st.Segment is null ? null : new RoadmapStepSegmentDto
                {
                    Id = st.Segment.Id,
                    Label = st.Segment.Label,
                    StartTime = st.Segment.StartTime,
                    EndTime = st.Segment.EndTime,
                    VideoId = st.Segment.VideoId
                },
                Dance = st.Dance is null ? null : new RoadmapStepDanceDto
                {
                    Id = st.Dance.Id,
                    Name = st.Dance.Name,
                    Slug = st.Dance.Slug,
                    StyleSlug = st.Dance.CanonicalStyleName is null ? string.Empty : SlugGenerator.Slugify(st.Dance.CanonicalStyleName),
                    Difficulty = st.Dance.Difficulty.ToString(),
                    AverageRating = st.Dance.AverageRating,
                    RatingCount = st.Dance.RatingCount,
                    IsLearned = st.Dance.IsLearned,
                    IsInProgress = st.Dance.IsInProgress,
                    IsFavorite = st.Dance.IsFavorite,
                    Videos = st.Dance.Videos.Select(v => new RoadmapStepVideoDto
                    {
                        Id = v.Id,
                        Title = v.Title,
                        VideoId = v.VideoId,
                        Platform = v.Platform,
                        VideoType = v.VideoType,
                        StartTime = v.StartTime,
                        EndTime = v.EndTime,
                        DurationSeconds = v.DurationSeconds,
                        ViewCount = v.ViewCount,
                        AverageRating = v.AverageRating,
                        RatingCount = v.RatingCount
                    }).ToList()
                }
            }).ToList()
        }).ToList();

        var allSteps = stages.SelectMany(s => s.Steps).ToList();
        AssignDepths(allSteps);
        AssignStates(allSteps, hasUser);
        var moves = allSteps.Where(s => s.Dance is not null).Select(s => s.Dance!).ToList();
        var cover = moves.SelectMany(m => m.Videos).FirstOrDefault();
        // Same de-duplication as the index: several steps can share one sliced-up tutorial.
        var distinctVideos = moves.SelectMany(m => m.Videos).Select(v => v.Id).Distinct().Count();

        return new RoadmapDto
        {
            Id = roadmap.Id,
            Slug = roadmap.Slug,
            Title = roadmap.Title,
            Subtitle = roadmap.Subtitle,
            Description = roadmap.Description,
            StyleId = roadmap.StyleId,
            StyleName = roadmap.StyleName,
            StyleSlug = SlugGenerator.Slugify(roadmap.StyleName),
            IsOwned = roadmap.OwnerUserId != null,
            StageCount = stages.Count,
            StepCount = allSteps.Count,
            MoveCount = moves.Count,
            VideoCount = distinctVideos,
            LearnedCount = moves.Count(m => m.IsLearned),
            InProgressCount = moves.Count(m => m.IsInProgress),
            ThumbnailVideoId = cover?.VideoId,
            ThumbnailPlatform = cover?.Platform,
            Stages = stages,
            AvailableCount = allSteps.Count(s => s.State == "available")
        };
    }

    // ---------------------------------------------------------------------------------------
    // Personal skill trees
    //
    // A user's own roadmap is written through here rather than through a JSON file. Every save
    // is a full replace of the tree — see SaveRoadmapRequest for why — so create and update run
    // the same code and differ only in whether the row already exists.
    // ---------------------------------------------------------------------------------------

    /// <summary>
    /// Caps, so one account can't turn the shared Roadmaps table into its own storage. They are
    /// well above any real path — the largest authored one is 6 stages and 31 steps.
    /// </summary>
    private const int MaxTreesPerUser = 50;
    private const int MaxStages = 30;
    private const int MaxSteps = 250;
    private const int MaxTitleLength = 120;
    private const int MaxSubtitleLength = 200;
    private const int MaxDescriptionLength = 2000;

    public async Task<RoadmapSaveResult> CreateAsync(int userId, SaveRoadmapRequest request)
    {
        if (Validate(request) is string invalid) return RoadmapSaveResult.Fail(invalid);

        if (!await _db.Styles.AnyAsync(s => s.Id == request.StyleId))
            return RoadmapSaveResult.Fail("Pick a style for this tree.");

        if (await _db.Roadmaps.CountAsync(r => r.OwnerUserId == userId) >= MaxTreesPerUser)
            return RoadmapSaveResult.Fail($"You can keep {MaxTreesPerUser} skill trees. Delete one to make room for another.");

        var roadmap = new Roadmap
        {
            OwnerUserId = userId,
            Slug = await UniqueSlugAsync(request.Title),
            DateAdded = DateTime.UtcNow
        };
        _db.Roadmaps.Add(roadmap);

        return await ApplyAsync(roadmap, request, userId);
    }

    public async Task<RoadmapSaveResult> UpdateAsync(int userId, int id, SaveRoadmapRequest request)
    {
        if (Validate(request) is string invalid) return RoadmapSaveResult.Fail(invalid);

        if (!await _db.Styles.AnyAsync(s => s.Id == request.StyleId))
            return RoadmapSaveResult.Fail("Pick a style for this tree.");

        // OwnerUserId in the predicate is the authorisation check: a curated path (null owner) and
        // someone else's tree both simply fail to match.
        var roadmap = await _db.Roadmaps
            .Include(r => r.Stages).ThenInclude(s => s.Steps)
            .FirstOrDefaultAsync(r => r.Id == id && r.OwnerUserId == userId);
        if (roadmap is null) return RoadmapSaveResult.NotFound;

        // The slug is deliberately left alone on rename. It is the tree's URL, and someone who
        // has bookmarked it or linked it from a practice note shouldn't lose it over a typo fix.
        return await ApplyAsync(roadmap, request, userId);
    }

    public async Task<bool> DeleteAsync(int userId, int id)
    {
        // The stages and steps have to be loaded, or RemoveTreeAsync sees no steps, clears no
        // edges, and the delete cascades into the NoAction side of RoadmapStepPrerequisites.
        var roadmap = await _db.Roadmaps
            .Include(r => r.Stages).ThenInclude(s => s.Steps)
            .FirstOrDefaultAsync(r => r.Id == id && r.OwnerUserId == userId);
        if (roadmap is null) return false;

        // Edges first, for the same reason ApplyAsync does it — see RemoveTreeAsync.
        await RemoveTreeAsync(roadmap);
        _db.Roadmaps.Remove(roadmap);
        await _db.SaveChangesAsync();
        return true;
    }

    public async Task<RoadmapSaveResult> CopyAsync(int userId, string idOrSlug)
    {
        // Read through the normal reader, so the visibility rule is the one already tested: you
        // can fork a curated path or one of your own, never someone else's.
        var source = await GetByIdOrSlugAsync(idOrSlug, userId);
        if (source is null) return RoadmapSaveResult.NotFound;

        return await CreateAsync(userId, new SaveRoadmapRequest
        {
            Title = Clip($"{source.Title} (my copy)", MaxTitleLength)!,
            Subtitle = source.Subtitle,
            Description = source.Description,
            StyleId = source.StyleId,
            Stages = source.Stages.Select(stage => new SaveRoadmapStageRequest
            {
                Title = stage.Title,
                Description = stage.Description,
                Steps = stage.Steps.Select(step => new SaveRoadmapStepRequest
                {
                    Key = step.Key,
                    Title = step.Title,
                    Description = step.Description,
                    DanceId = step.Dance?.Id,
                    VideoSegmentId = step.Segment?.Id,
                    Requires = step.Requires.ToList()
                }).ToList()
            }).ToList()
        });
    }

    /// <summary>Everything a save checks before it touches a row. Null = the request is fine.</summary>
    private static string? Validate(SaveRoadmapRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Title)) return "Give the tree a name.";
        if (request.Title.Trim().Length > MaxTitleLength) return $"Keep the name under {MaxTitleLength} characters.";
        if (request.Stages.Count > MaxStages) return $"A tree can have up to {MaxStages} branches.";
        if (request.Stages.Sum(s => s.Steps.Count) > MaxSteps) return $"A tree can have up to {MaxSteps} moves.";
        return null;
    }

    /// <summary>
    /// Writes a request onto a roadmap row: metadata, then a wholesale rebuild of its stages,
    /// steps and edges. Shared by create and update.
    /// </summary>
    private async Task<RoadmapSaveResult> ApplyAsync(Roadmap roadmap, SaveRoadmapRequest request, int userId)
    {
        roadmap.Title = request.Title.Trim();
        roadmap.Subtitle = Clip(request.Subtitle, MaxSubtitleLength) ?? string.Empty;
        roadmap.Description = Clip(request.Description, MaxDescriptionLength);
        roadmap.StyleId = request.StyleId;
        roadmap.DateModified = DateTime.UtcNow;

        // A step with no title is a row the user opened and never filled in. Dropping it beats
        // saving a nameless node onto the tree — but it happens before keys are assigned, so a
        // `requires` pointing at one is pruned by the same pass that prunes deleted steps.
        var plan = request.Stages
            .Select((stage, si) => new
            {
                Title = Clip(stage.Title, MaxTitleLength) is { Length: > 0 } t ? t : $"Branch {si + 1}",
                Description = Clip(stage.Description, MaxDescriptionLength),
                Steps = stage.Steps.Where(p => !string.IsNullOrWhiteSpace(p.Title)).ToList()
            })
            .ToList();

        var flat = plan.SelectMany(s => s.Steps).ToList();
        var keys = AssignKeys(flat, out var keyMap);
        var requires = BuildRequires(flat, keys, keyMap);

        if (FindCycle(flat, keys, requires) is string cycle) return RoadmapSaveResult.Fail(cycle);

        var (dances, segments) = await ResolveLinksAsync(flat, userId);

        await RemoveTreeAsync(roadmap);

        var cursor = 0;
        foreach (var (stage, si) in plan.Select((s, i) => (s, i)))
        {
            var steps = new List<RoadmapStep>();
            foreach (var step in stage.Steps)
            {
                var danceId = step.DanceId is int d && dances.Contains(d) ? d : (int?)null;
                steps.Add(new RoadmapStep
                {
                    Key = keys[cursor++],
                    Title = Clip(step.Title, MaxTitleLength)!,
                    Description = Clip(step.Description, MaxDescriptionLength),
                    SortOrder = steps.Count,
                    DanceId = danceId,
                    // A segment only means anything inside its own dance's video, so a link to
                    // one that lives elsewhere widens the step back to the whole move.
                    VideoSegmentId = step.VideoSegmentId is int seg && danceId is not null
                        && segments.TryGetValue(seg, out var owner) && owner == danceId
                            ? seg
                            : null
                });
            }

            roadmap.Stages.Add(new RoadmapStage
            {
                Title = stage.Title,
                Description = stage.Description,
                SortOrder = si,
                Steps = steps
            });
        }

        await _db.SaveChangesAsync();

        // Edges last: the step rows have to exist before keys can be turned into ids.
        var idsByKey = roadmap.Stages.SelectMany(s => s.Steps)
            .ToDictionary(s => s.Key, s => s.Id, StringComparer.OrdinalIgnoreCase);
        foreach (var (key, deps) in requires)
            foreach (var dep in deps)
                _db.RoadmapStepPrerequisites.Add(new RoadmapStepPrerequisite
                {
                    StepId = idsByKey[key],
                    PrerequisiteStepId = idsByKey[dep]
                });

        await _db.SaveChangesAsync();

        var saved = await GetByIdOrSlugAsync(roadmap.Id.ToString(), userId);
        return saved is null ? RoadmapSaveResult.NotFound : RoadmapSaveResult.Ok(saved);
    }

    /// <summary>
    /// Clears a roadmap's stages, steps and edges.
    ///
    /// The edges go first and explicitly. Deleting a step cascades away the edges that *start* at
    /// it, but the other side of the join is NoAction (see AppDbContext — Postgres won't take two
    /// cascade paths into one table), so an edge still pointing at a step deleted earlier in the
    /// same rebuild would fail its foreign key. Removing them up front makes the order irrelevant.
    /// </summary>
    private async Task RemoveTreeAsync(Roadmap roadmap)
    {
        var stepIds = roadmap.Stages.SelectMany(s => s.Steps).Select(s => s.Id).ToList();
        if (stepIds.Count > 0)
        {
            var edges = await _db.RoadmapStepPrerequisites
                .Where(p => stepIds.Contains(p.StepId) || stepIds.Contains(p.PrerequisiteStepId))
                .ToListAsync();
            _db.RoadmapStepPrerequisites.RemoveRange(edges);
            await _db.SaveChangesAsync();
        }

        _db.RoadmapStages.RemoveRange(roadmap.Stages);
        roadmap.Stages.Clear();
    }

    /// <summary>
    /// Gives every step its stored key, and maps the keys the client sent onto them.
    ///
    /// The client owns its keys but doesn't have to keep them tidy: they are slugified and made
    /// unique here, and <paramref name="keyMap"/> carries the rewrite so `requires` still lands on
    /// the right step. A blank key never enters the map — nothing can name it, so a second blank
    /// can't shadow the first.
    /// </summary>
    private static List<string> AssignKeys(List<SaveRoadmapStepRequest> steps, out Dictionary<string, string> keyMap)
    {
        keyMap = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var used = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var keys = new List<string>(steps.Count);

        foreach (var step in steps)
        {
            var authored = step.Key?.Trim() ?? string.Empty;
            var basis = SlugGenerator.Slugify(authored.Length > 0 ? authored : step.Title);

            var key = basis;
            for (var n = 2; !used.Add(key); n++) key = $"{basis}-{n}";

            keys.Add(key);
            if (authored.Length > 0) keyMap.TryAdd(authored, key);
        }

        return keys;
    }

    /// <summary>
    /// The adjacency the tree will be stored with, keyed by stored key. Edges naming a step that
    /// no longer exists are dropped rather than rejected — that is a stale tab, not a mistake the
    /// user can see or fix — as are self-edges and repeats.
    /// </summary>
    private static Dictionary<string, List<string>> BuildRequires(
        List<SaveRoadmapStepRequest> steps, List<string> keys, Dictionary<string, string> keyMap)
    {
        var requires = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);

        for (var i = 0; i < steps.Count; i++)
        {
            var key = keys[i];
            var deps = new List<string>();
            foreach (var raw in steps[i].Requires)
            {
                if (string.IsNullOrWhiteSpace(raw)) continue;
                if (!keyMap.TryGetValue(raw.Trim(), out var target)) continue;
                if (string.Equals(target, key, StringComparison.OrdinalIgnoreCase)) continue;
                if (deps.Contains(target, StringComparer.OrdinalIgnoreCase)) continue;
                deps.Add(target);
            }
            requires[key] = deps;
        }

        return requires;
    }

    /// <summary>
    /// The message for the first cycle in the graph, or null when there isn't one.
    ///
    /// Unlike the seeder, which drops a cycling edge and logs, a save is refused: the user drew
    /// that link seconds ago and a save that silently threw it away would read as the save not
    /// having worked. The message names both moves so the builder can point at them.
    /// </summary>
    private static string? FindCycle(
        List<SaveRoadmapStepRequest> steps, List<string> keys, Dictionary<string, List<string>> requires)
    {
        var titles = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        for (var i = 0; i < steps.Count; i++) titles[keys[i]] = steps[i].Title.Trim();

        foreach (var (key, deps) in requires)
            foreach (var dep in deps)
                if (RoadmapGraph.CreatesCycle(requires, from: dep, to: key))
                    return $"“{titles.GetValueOrDefault(key, key)}” and “{titles.GetValueOrDefault(dep, dep)}” "
                         + "each end up coming after the other. Remove one of those links.";

        return null;
    }

    /// <summary>
    /// Which of the requested dance and segment ids actually exist, so a stale one nulls the link
    /// instead of failing the save — exactly what the seeder does with a slug that resolves to
    /// nothing. Segments are restricted to videos the owner can see; unlike the curated paths,
    /// a personal tree may legitimately pin a clip of the user's own video.
    /// </summary>
    private async Task<(HashSet<int> Dances, Dictionary<int, int> Segments)> ResolveLinksAsync(
        List<SaveRoadmapStepRequest> steps, int userId)
    {
        var danceIds = steps.Select(s => s.DanceId).OfType<int>().Distinct().ToList();
        var segmentIds = steps.Select(s => s.VideoSegmentId).OfType<int>().Distinct().ToList();

        var dances = danceIds.Count == 0
            ? new HashSet<int>()
            : (await _db.Dances.Where(d => danceIds.Contains(d.Id)).Select(d => d.Id).ToListAsync()).ToHashSet();

        var segments = segmentIds.Count == 0
            ? new Dictionary<int, int>()
            : await _db.VideoSegments
                .Where(seg => segmentIds.Contains(seg.Id)
                    && (seg.Video.OwnerUserId == null || seg.Video.OwnerUserId == userId))
                .Select(seg => new { seg.Id, seg.Video.DanceId })
                .ToDictionaryAsync(x => x.Id, x => x.DanceId);

        return (dances, segments);
    }

    /// <summary>
    /// A URL key for a new tree. Slugs are unique across curated and personal roadmaps alike, so
    /// this steps around both — and around the style slugs, which are the names the authored files
    /// use ("house", "waacking"). Without that reservation a user calling their tree "Hip Hop"
    /// today would sit on the slug tomorrow's authored hip-hop path wants.
    /// </summary>
    private async Task<string> UniqueSlugAsync(string title)
    {
        var basis = SlugGenerator.Slugify(title.Trim());
        if (basis.Length > 60) basis = basis[..60].TrimEnd('-');

        var taken = (await _db.Roadmaps.Select(r => r.Slug).ToListAsync()).ToHashSet(StringComparer.OrdinalIgnoreCase);
        foreach (var name in await _db.Styles.Select(s => s.Name).ToListAsync())
            taken.Add(SlugGenerator.Slugify(name));

        var slug = basis;
        for (var n = 2; taken.Contains(slug); n++) slug = $"{basis}-{n}";
        return slug;
    }

    /// <summary>Trims, and caps length so a pasted essay can't become the page title.</summary>
    private static string? Clip(string? value, int max)
    {
        var trimmed = value?.Trim();
        if (string.IsNullOrEmpty(trimmed)) return trimmed is null ? null : string.Empty;
        return trimmed.Length <= max ? trimmed : trimmed[..max].TrimEnd();
    }

    /// <summary>
    /// Longest distance from a root, which is what puts a node on the right ring of the tree:
    /// a step must sit outside every prerequisite, so the *max* depth is the correct one.
    ///
    /// Iterative relaxation rather than recursion — the seeder rejects cycles, but this endpoint
    /// is public and must not be one bad row away from a stack overflow. The loop is bounded by
    /// the step count, so a cycle that somehow got in yields odd depths instead of hanging.
    /// </summary>
    private static void AssignDepths(List<RoadmapStepDto> steps)
    {
        var byKey = steps.GroupBy(s => s.Key).ToDictionary(g => g.Key, g => g.First());

        for (var pass = 0; pass < steps.Count; pass++)
        {
            var changed = false;
            foreach (var step in steps)
            {
                var depth = 0;
                foreach (var key in step.Requires)
                    if (byKey.TryGetValue(key, out var parent))
                        depth = Math.Max(depth, parent.Depth + 1);

                if (depth != step.Depth) { step.Depth = depth; changed = true; }
            }
            if (!changed) break;
        }
    }

    /// <summary>
    /// Marks each step learned / available / locked. Available means every prerequisite is
    /// learned (a root always qualifies); locked means at least one isn't yet.
    /// Anonymous callers have no progress, so nothing is locked for them — a signed-out visitor
    /// should see the whole tree, not a wall of padlocks.
    /// </summary>
    private static void AssignStates(List<RoadmapStepDto> steps, bool hasUser)
    {
        var byKey = steps.GroupBy(s => s.Key).ToDictionary(g => g.Key, g => g.First());

        if (!hasUser)
        {
            // Signed out there is no progress, so nothing is locked — a visitor should see the
            // whole tree rather than a wall of padlocks.
            foreach (var step in steps) step.State = "available";
            return;
        }

        // "Satisfied" is not the same as "learned". A step with no catalog move behind it can
        // never be ticked off, so it passes through: it counts as satisfied exactly when the
        // things IT depends on are. Without the pass-through, one un-covered concept would either
        // lock its whole branch forever (if it gated) or leak the branch open early (if it
        // didn't) — Lofting would unlock before the Slide it actually follows.
        var satisfied = steps.ToDictionary(s => s.Key, s => s.Dance is not null && s.Dance.IsLearned);

        for (var pass = 0; pass < steps.Count; pass++)
        {
            var changed = false;
            foreach (var step in steps)
            {
                if (step.Dance is not null) continue; // fixed by its own learned flag
                var ok = step.Requires.All(key => !byKey.ContainsKey(key) || satisfied[key]);
                if (ok != satisfied[step.Key]) { satisfied[step.Key] = ok; changed = true; }
            }
            if (!changed) break;
        }

        foreach (var step in steps)
        {
            if (step.Dance?.IsLearned == true) { step.State = "learned"; continue; }
            var blocked = step.Requires.Any(key => byKey.ContainsKey(key) && !satisfied[key]);
            step.State = blocked ? "locked" : "available";
        }
    }
}
