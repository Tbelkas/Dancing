using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Roadmap;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class RoadmapService : IRoadmapService
{
    private readonly AppDbContext _db;

    public RoadmapService(AppDbContext db) => _db = db;

    /// <summary>
    /// Every module link the caller can see, as child roadmap id -> parent roadmap id.
    ///
    /// Small by nature (one row per module), and it answers three separate questions: which
    /// roadmaps to hide from the index, how to build a breadcrumb, and whether a proposed link
    /// would close a loop.
    /// </summary>
    private async Task<Dictionary<int, int>> ModuleLinksAsync()
    {
        var links = await _db.RoadmapSteps
            .Where(s => s.ChildRoadmapId != null)
            .Select(s => new { ChildId = s.ChildRoadmapId!.Value, ParentId = s.Stage.RoadmapId })
            .ToListAsync();

        // The unique index makes the key collision impossible in practice; the grouping is here
        // so a hand-edited database degrades to "first one wins" rather than throwing on read.
        return links.GroupBy(l => l.ChildId).ToDictionary(g => g.Key, g => g.First().ParentId);
    }

    public async Task<List<RoadmapSummaryDto>> GetAllAsync(int? userId)
    {
        var uid = userId ?? 0;
        var hasUser = userId.HasValue;
        var moduleLinks = await ModuleLinksAsync();

        // One projection, no stage/step materialisation — the index only needs counts.
        var rows = await _db.Roadmaps
            // Curated paths plus the caller's own trees — and deliberately *not* other people's
            // shared ones. The index is the curated shelf; a shared tree is reachable by link and
            // from its owner's profile. Nothing here is moderated, so it must not be pushed at
            // people who didn't go looking for it.
            .Where(r => r.OwnerUserId == null || (hasUser && r.OwnerUserId == uid))
            .OrderBy(r => r.SortOrder).ThenBy(r => r.Title)
            .Select(r => new
            {
                r.Id, r.Slug, r.Title, r.Subtitle, r.Description, r.StyleId, r.OwnerUserId, r.IsPublic,
                OwnerUsername = r.Owner == null ? null : r.Owner.Username,
                OwnerNickname = r.Owner == null ? null : (r.Owner.Nickname == "" ? r.Owner.Username : r.Owner.Nickname),
                StyleName = r.Style.Name,
                StageCount = r.Stages.Count,
                StepCount = r.Stages.SelectMany(s => s.Steps).Count(),
                // A module step counts toward the total too — it is a thing to finish, just a
                // bigger one — but its own contents are folded in separately below.
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

        var summaries = rows.Select(r => new RoadmapSummaryDto
        {
            Id = r.Id,
            Slug = r.Slug,
            Title = r.Title,
            Subtitle = r.Subtitle,
            Description = r.Description,
            StyleId = r.StyleId,
            StyleName = r.StyleName,
            StyleSlug = SlugGenerator.Slugify(r.StyleName),
            IsOwned = hasUser && r.OwnerUserId == uid,
            IsPublic = r.IsPublic,
            OwnerUsername = r.OwnerUsername,
            OwnerNickname = r.OwnerNickname,
            StageCount = r.StageCount,
            StepCount = r.StepCount,
            MoveCount = r.MoveCount,
            VideoCount = r.VideoCount,
            LearnedCount = r.LearnedCount,
            InProgressCount = r.InProgressCount,
            ThumbnailVideoId = r.Thumbnail?.VideoId,
            ThumbnailPlatform = r.Thumbnail?.Platform
        }).ToDictionary(s => s.Id);

        // Fold each module's counts into the path that owns it, so an index card reports the
        // work actually in front of you rather than "6 moves" for a path with forty behind three
        // gateways. Deepest-first, so a module's own modules are already folded into it before it
        // is folded into its parent.
        foreach (var childId in moduleLinks.Keys
                     .OrderByDescending(id => RoadmapGraph.ModuleDepth(moduleLinks, id)))
        {
            if (!summaries.TryGetValue(childId, out var child)) continue;
            if (!summaries.TryGetValue(moduleLinks[childId], out var parent)) continue;

            parent.StageCount += child.StageCount;
            parent.StepCount += child.StepCount;
            parent.MoveCount += child.MoveCount;
            parent.VideoCount += child.VideoCount;
            parent.LearnedCount += child.LearnedCount;
            parent.InProgressCount += child.InProgressCount;
            parent.ThumbnailVideoId ??= child.ThumbnailVideoId;
            parent.ThumbnailPlatform ??= child.ThumbnailPlatform;
        }

        // Modules are reachable at their own URL and through their parent, but they are not
        // shelf items: the index would otherwise list "Posing" beside "Waacking" as if they were
        // peers. Same reasoning as shared personal trees staying off the index.
        // Walking `rows` keeps the SortOrder/Title ordering the query already established.
        return rows
            .Where(r => !moduleLinks.ContainsKey(r.Id))
            .Select(r => summaries[r.Id])
            .ToList();
    }

    public async Task<RoadmapDto?> GetByIdOrSlugAsync(string idOrSlug, int? userId)
    {
        var uid = userId ?? 0;
        var hasUser = userId.HasValue;

        var query = int.TryParse(idOrSlug, out var id)
            ? _db.Roadmaps.Where(r => r.Id == id)
            : _db.Roadmaps.Where(r => r.Slug == idOrSlug);

        // Visibility is checked after loading rather than in the predicate, because a module
        // inherits it from the path above: a tree its owner shared has to open its own modules
        // for the person they shared it with, and those rows are private in their own right.
        var roadmap = await query
            .Select(r => new
            {
                r.Id, r.Slug, r.Title, r.Subtitle, r.Description, r.StyleId, r.OwnerUserId, r.IsPublic,
                OwnerUsername = r.Owner == null ? null : r.Owner.Username,
                OwnerNickname = r.Owner == null ? null : (r.Owner.Nickname == "" ? r.Owner.Username : r.Owner.Nickname),
                StyleName = r.Style.Name,
                Stages = r.Stages.OrderBy(s => s.SortOrder).Select(s => new
                {
                    s.Id, s.Title, s.Description,
                    Steps = s.Steps.OrderBy(st => st.SortOrder).Select(st => new
                    {
                        st.Id, st.Key, st.Title, st.Description, st.ChildRoadmapId,
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

        var moduleLinks = await ModuleLinksAsync();
        if (!await IsVisibleAsync(roadmap.Id, roadmap.OwnerUserId, roadmap.IsPublic, uid, hasUser, moduleLinks))
            return null;

        var moduleIds = roadmap.Stages.SelectMany(s => s.Steps)
            .Where(st => st.ChildRoadmapId != null)
            .Select(st => st.ChildRoadmapId!.Value)
            .Distinct()
            .ToList();
        var modules = await LoadModulesAsync(moduleIds, uid, hasUser);

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
                Module = st.ChildRoadmapId is int cid && modules.TryGetValue(cid, out var m) ? m : null,
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
        var stepModules = allSteps.Where(s => s.Module is not null).Select(s => s.Module!).ToList();

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
            IsOwned = hasUser && roadmap.OwnerUserId == uid,
            IsPublic = roadmap.IsPublic,
            OwnerUsername = roadmap.OwnerUsername,
            OwnerNickname = roadmap.OwnerNickname,
            StageCount = stages.Count,
            StepCount = allSteps.Count,
            // Module gateways are completable too, so they belong in the "N of M" the page shows
            // — otherwise finishing a seven-step module moves the headline not at all.
            MoveCount = moves.Count + stepModules.Count,
            VideoCount = distinctVideos,
            LearnedCount = moves.Count(m => m.IsLearned) + stepModules.Count(m => m.IsComplete),
            InProgressCount = moves.Count(m => m.IsInProgress)
                + stepModules.Count(m => !m.IsComplete && m.LearnedCount > 0),
            ThumbnailVideoId = cover?.VideoId,
            ThumbnailPlatform = cover?.Platform,
            Stages = stages,
            AvailableCount = allSteps.Count(s => s.State == "available"),
            Ancestors = await AncestorsAsync(roadmap.Id, moduleLinks)
        };
    }

    /// <summary>
    /// Curated, the caller's own, or shared — checked against this roadmap and, if it is a
    /// module, every path above it. An unshared tree belonging to someone else reads as "not
    /// found" rather than "forbidden": whether they have a path at this slug isn't the caller's
    /// business either.
    ///
    /// Inheriting downwards is the whole point: sharing a tree has to share what is inside it,
    /// or half its nodes 404 for the person it was shared with. The corollary — that a module is
    /// exposed by its parent being shared — is why a fork deep-copies rather than re-links.
    /// </summary>
    private async Task<bool> IsVisibleAsync(
        int roadmapId, int? ownerUserId, bool isPublic, int uid, bool hasUser, Dictionary<int, int> moduleLinks)
    {
        if (ownerUserId is null || (hasUser && ownerUserId == uid) || isPublic) return true;

        var seen = new HashSet<int> { roadmapId };
        var current = roadmapId;
        for (var hop = 0; hop < RoadmapGraph.MaxModuleDepth; hop++)
        {
            if (!moduleLinks.TryGetValue(current, out var parentId) || !seen.Add(parentId)) return false;

            var parent = await _db.Roadmaps
                .Where(r => r.Id == parentId)
                .Select(r => new { r.OwnerUserId, r.IsPublic })
                .FirstOrDefaultAsync();
            if (parent is null) return false;
            if (parent.OwnerUserId is null || (hasUser && parent.OwnerUserId == uid) || parent.IsPublic) return true;

            current = parentId;
        }
        return false;
    }

    /// <summary>
    /// Loads the module summaries for a set of child roadmap ids, following nesting down to
    /// <see cref="RoadmapGraph.MaxModuleDepth"/>.
    ///
    /// One query per level, not one per module: a path with eight gateways costs the same as a
    /// path with one. The depth bound is what stops a hand-edited cycle from looping forever on
    /// a public endpoint — the visited set makes it terminate, the bound makes it terminate
    /// *fast*.
    /// </summary>
    private async Task<Dictionary<int, RoadmapStepModuleDto>> LoadModulesAsync(
        List<int> rootIds, int uid, bool hasUser)
    {
        var result = new Dictionary<int, RoadmapStepModuleDto>();
        if (rootIds.Count == 0) return result;

        // roadmap id -> its steps, flattened to just what completion needs.
        var steps = new Dictionary<int, List<(int? DanceId, bool IsLearned, int? ChildId)>>();

        var frontier = rootIds.Distinct().ToList();
        for (var level = 0; level < RoadmapGraph.MaxModuleDepth && frontier.Count > 0; level++)
        {
            var loaded = await _db.Roadmaps
                .Where(r => frontier.Contains(r.Id))
                .Select(r => new
                {
                    r.Id, r.Slug, r.Title, r.Subtitle,
                    Steps = r.Stages.SelectMany(s => s.Steps).Select(st => new
                    {
                        st.DanceId,
                        st.ChildRoadmapId,
                        IsLearned = hasUser && st.Dance != null && st.Dance.LearnedBy.Any(l => l.UserId == uid)
                    }).ToList()
                })
                .ToListAsync();

            foreach (var r in loaded)
            {
                if (result.ContainsKey(r.Id)) continue;
                result[r.Id] = new RoadmapStepModuleDto
                {
                    Id = r.Id, Slug = r.Slug, Title = r.Title, Subtitle = r.Subtitle,
                    StepCount = r.Steps.Count
                };
                steps[r.Id] = r.Steps
                    .Select(s => (s.DanceId, s.IsLearned, s.ChildRoadmapId))
                    .ToList();
            }

            frontier = loaded.SelectMany(r => r.Steps)
                .Where(s => s.ChildRoadmapId != null)
                .Select(s => s.ChildRoadmapId!.Value)
                .Where(id => !result.ContainsKey(id))
                .Distinct()
                .ToList();
        }

        // Bottom-up completion. Relaxed rather than recursed, for the same reason AssignDepths
        // is: the number of passes is bounded, so bad data yields a wrong answer instead of a
        // hung request. MaxModuleDepth passes is enough for any chain we allow to exist.
        for (var pass = 0; pass < RoadmapGraph.MaxModuleDepth; pass++)
        {
            foreach (var (id, list) in steps)
            {
                var completable = 0;
                var done = 0;
                foreach (var (danceId, isLearned, childId) in list)
                {
                    if (danceId is not null)
                    {
                        completable++;
                        if (isLearned) done++;
                    }
                    else if (childId is int c && result.TryGetValue(c, out var child))
                    {
                        completable++;
                        if (child.IsComplete) done++;
                    }
                }

                var dto = result[id];
                dto.CompletableCount = completable;
                dto.LearnedCount = done;
                // A module with nothing completable in it can never be finished, so it must not
                // report itself complete — its gateway step falls back to the pass-through rule
                // that already governs steps with no move behind them.
                dto.IsComplete = completable > 0 && done == completable;
            }
        }

        return result;
    }

    /// <summary>
    /// The chain of paths above a module, outermost first, for the breadcrumb. Empty for a
    /// top-level path. Bounded by <see cref="RoadmapGraph.MaxModuleDepth"/>.
    /// </summary>
    private async Task<List<RoadmapCrumbDto>?> AncestorsAsync(int roadmapId, Dictionary<int, int> moduleLinks)
    {
        if (!moduleLinks.ContainsKey(roadmapId)) return null;

        // Walk up collecting (roadmap that owns the step, the step's title).
        var chain = new List<(int RoadmapId, int ChildId)>();
        var seen = new HashSet<int> { roadmapId };
        var current = roadmapId;
        while (chain.Count < RoadmapGraph.MaxModuleDepth && moduleLinks.TryGetValue(current, out var parent))
        {
            chain.Add((parent, current));
            if (!seen.Add(parent)) break;
            current = parent;
        }
        chain.Reverse();

        var ids = chain.Select(c => c.RoadmapId).ToList();
        var info = await _db.Roadmaps
            .Where(r => ids.Contains(r.Id))
            .Select(r => new { r.Id, r.Slug, r.Title })
            .ToDictionaryAsync(r => r.Id);
        var stepTitles = await _db.RoadmapSteps
            .Where(s => s.ChildRoadmapId != null && ids.Contains(s.Stage.RoadmapId))
            .Select(s => new { s.ChildRoadmapId, s.Title })
            .ToListAsync();
        var titleByChild = stepTitles
            .GroupBy(s => s.ChildRoadmapId!.Value)
            .ToDictionary(g => g.Key, g => g.First().Title);

        return chain
            .Where(c => info.ContainsKey(c.RoadmapId))
            .Select(c => new RoadmapCrumbDto
            {
                Slug = info[c.RoadmapId].Slug,
                Title = info[c.RoadmapId].Title,
                StepTitle = titleByChild.GetValueOrDefault(c.ChildId, string.Empty)
            })
            .ToList();
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

        // Modules go with the tree that contains them. Leaving them behind would strand subtrees
        // on the user's index with no way to tell what they belonged to — deleting "my Waacking
        // tree" plainly means the Posing module inside it too. Innermost first, so no step is
        // still pointing at a roadmap being removed.
        var links = await ModuleLinksAsync();
        var doomed = new List<int>();
        var frontier = new List<int> { roadmap.Id };
        for (var level = 0; level < RoadmapGraph.MaxModuleDepth && frontier.Count > 0; level++)
        {
            frontier = links.Where(l => frontier.Contains(l.Value) && !doomed.Contains(l.Key))
                .Select(l => l.Key).ToList();
            doomed.AddRange(frontier);
        }

        foreach (var childId in Enumerable.Reverse(doomed))
        {
            var child = await _db.Roadmaps
                .Include(r => r.Stages).ThenInclude(s => s.Steps)
                .FirstOrDefaultAsync(r => r.Id == childId && r.OwnerUserId == userId);
            if (child is null) continue; // a curated module, or someone else's — leave it alone
            await RemoveTreeAsync(child);
            _db.Roadmaps.Remove(child);
        }

        // Edges first, for the same reason ApplyAsync does it — see RemoveTreeAsync.
        await RemoveTreeAsync(roadmap);
        _db.Roadmaps.Remove(roadmap);
        await _db.SaveChangesAsync();
        return true;
    }

    public async Task<RoadmapDto?> SetSharedAsync(int userId, int id, bool shared)
    {
        var roadmap = await _db.Roadmaps.FirstOrDefaultAsync(r => r.Id == id && r.OwnerUserId == userId);
        if (roadmap is null) return null;

        roadmap.IsPublic = shared;
        await _db.SaveChangesAsync();
        return await GetByIdOrSlugAsync(id.ToString(), userId);
    }

    public Task<RoadmapSaveResult> CopyAsync(int userId, string idOrSlug) =>
        CopyInternalAsync(userId, idOrSlug, depth: 0);

    /// <summary>
    /// Forks a path, <b>deep-copying its modules</b>.
    ///
    /// The deep copy is a correctness requirement, not a nicety: pointing the fork's gateway at
    /// the original's module would leave one user's tree containing a roadmap another user owns
    /// and can edit or delete underneath them — and, since a module inherits its parent's
    /// visibility, would expose it to everyone the fork is later shared with. Modules are copied
    /// first, depth-first, so their new ids exist before the parent's steps are written.
    /// </summary>
    private async Task<RoadmapSaveResult> CopyInternalAsync(int userId, string idOrSlug, int depth)
    {
        // Read through the normal reader, so the visibility rule is the one already tested: a
        // curated path, one of your own, or one someone shared — never an unshared private tree.
        var source = await GetByIdOrSlugAsync(idOrSlug, userId);
        if (source is null) return RoadmapSaveResult.NotFound;

        var copiedModules = new Dictionary<int, int>();
        if (depth + 1 < RoadmapGraph.MaxModuleDepth)
        {
            foreach (var module in source.Stages.SelectMany(s => s.Steps)
                         .Select(s => s.Module).OfType<RoadmapStepModuleDto>())
            {
                if (copiedModules.ContainsKey(module.Id)) continue;
                var copied = await CopyInternalAsync(userId, module.Id.ToString(), depth + 1);
                // A module that fails to copy costs its gateway, not the whole fork — the step
                // survives as a plain unlinked node.
                if (copied.Roadmap is not null) copiedModules[module.Id] = copied.Roadmap.Id;
            }
        }

        // The copy is private whatever the original was: CreateAsync leaves IsPublic false, and
        // inheriting it would republish someone else's tree under a new owner by accident.
        // Only the outermost copy is renamed; a module keeps its name, since "(my copy)" on every
        // rung would read as noise inside a tree that is already yours.
        return await CreateAsync(userId, new SaveRoadmapRequest
        {
            Title = Clip(depth == 0 ? $"{source.Title} (my copy)" : source.Title, MaxTitleLength)!,
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
                    ChildRoadmapId = step.Module is not null && copiedModules.TryGetValue(step.Module.Id, out var newId)
                        ? newId
                        : null,
                    Requires = step.Requires.ToList()
                }).ToList()
            }).ToList()
        });
    }

    /// <summary>
    /// Which of the requested module links are allowed to stand. Dropped rather than rejected,
    /// because none of these are things the user can see and fix in the builder — the same split
    /// the save path already applies to a deleted dance or a stale prerequisite. A cycle the user
    /// *did* just draw is still a 400, via <see cref="FindCycle"/>.
    ///
    /// A module must be the caller's own tree, must not already be some other step's module, and
    /// must not close a loop or nest too deep.
    /// </summary>
    private async Task<HashSet<int>> ResolveModulesAsync(
        List<SaveRoadmapStepRequest> steps, Roadmap roadmap, int userId)
    {
        var wanted = steps
            .Where(s => s.DanceId is null && s.ChildRoadmapId is not null)
            .Select(s => s.ChildRoadmapId!.Value)
            .Distinct()
            .ToList();
        var ok = new HashSet<int>();
        if (wanted.Count == 0) return ok;

        // Ownership is the authorisation check: someone else's tree, a curated path, and a
        // deleted row all simply fail to appear here.
        var mine = await _db.Roadmaps
            .Where(r => r.OwnerUserId == userId && wanted.Contains(r.Id))
            .Select(r => r.Id)
            .ToListAsync();

        var links = await ModuleLinksAsync();
        // This tree's own current links are about to be rewritten, so they must not count as
        // "already claimed" — otherwise re-saving an unchanged tree would drop every module.
        foreach (var (childId, parentId) in links.ToList())
            if (parentId == roadmap.Id) links.Remove(childId);

        foreach (var id in wanted)
        {
            if (!mine.Contains(id)) continue;
            if (links.ContainsKey(id)) continue;
            if (RoadmapGraph.CreatesModuleCycle(links, roadmap.Id, id)) continue;

            links[id] = roadmap.Id;
            if (RoadmapGraph.ModuleDepth(links, id) >= RoadmapGraph.MaxModuleDepth)
            {
                links.Remove(id);
                continue;
            }
            ok.Add(id);
        }

        return ok;
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
        var modules = await ResolveModulesAsync(flat, roadmap, userId);

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
                    // A step is a move or a gateway, never both — the move wins, since it is the
                    // thing the user picked most recently in the builder's own ordering.
                    ChildRoadmapId = danceId is null && step.ChildRoadmapId is int cid && modules.Contains(cid)
                        ? cid
                        : null,
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
        //
        // A module gateway is the third kind of step and behaves like a move, not like a bare
        // concept: it *can* be finished, by finishing the module, so it gates its branch on that
        // rather than passing through.
        var satisfied = steps.ToDictionary(s => s.Key, IsDone);

        for (var pass = 0; pass < steps.Count; pass++)
        {
            var changed = false;
            foreach (var step in steps)
            {
                if (IsSelfDetermined(step)) continue; // fixed by its own learned/complete flag
                var ok = step.Requires.All(key => !byKey.ContainsKey(key) || satisfied[key]);
                if (ok != satisfied[step.Key]) { satisfied[step.Key] = ok; changed = true; }
            }
            if (!changed) break;
        }

        foreach (var step in steps)
        {
            if (IsDone(step)) { step.State = "learned"; continue; }
            var blocked = step.Requires.Any(key => byKey.ContainsKey(key) && !satisfied[key]);
            step.State = blocked ? "locked" : "available";
        }
    }

    /// <summary>
    /// A step whose completion is its own business rather than inherited from its prerequisites:
    /// it has a move to tick off, or a module to finish. Everything else passes through.
    /// </summary>
    private static bool IsSelfDetermined(RoadmapStepDto step) => step.Dance is not null || step.Module is not null;

    /// <summary>Finished, by either definition — the move is learned, or the module is complete.</summary>
    private static bool IsDone(RoadmapStepDto step) => step.Dance?.IsLearned == true || step.Module?.IsComplete == true;
}
