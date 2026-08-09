namespace DancePlatform.API.Services;

/// <summary>
/// Graph rules shared by the two things that build a roadmap's prerequisite edges: the seeder
/// (from an authored JSON file) and <see cref="RoadmapService"/> (from a builder save). They
/// disagree about what to do with a bad edge — the seeder drops it and logs, the builder refuses
/// the save so the user can fix what they just drew — but they must agree about what *is* bad,
/// or a tree that renders would stop rendering the moment it was seeded from a file.
/// </summary>
public static class RoadmapGraph
{
    /// <summary>
    /// True when <paramref name="to"/> is already reachable from <paramref name="from"/>, i.e.
    /// adding "<paramref name="to"/> requires <paramref name="from"/>" would close a cycle.
    /// A cycle makes every node in it unreachable and has no depth, so it must never be stored.
    /// </summary>
    public static bool CreatesCycle(IReadOnlyDictionary<string, List<string>> requires, string from, string to)
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var stack = new Stack<string>([from]);
        while (stack.Count > 0)
        {
            var current = stack.Pop();
            if (string.Equals(current, to, StringComparison.OrdinalIgnoreCase)) return true;
            if (!seen.Add(current)) continue;
            if (requires.TryGetValue(current, out var deps))
                foreach (var d in deps) stack.Push(d);
        }
        return false;
    }

    /// <summary>
    /// How many roadmaps a module chain may span, counting the top-level path as 1. Three means
    /// "Waacking › Posing › Screen icons" and no further.
    ///
    /// A cap and not just cycle detection, because the two failures are different: a cycle is a
    /// bug, but a legitimately 40-deep chain would still be a public endpoint doing 40 rounds of
    /// queries per request. Depth is checked where modules are linked, and again where they are
    /// read, since a chain can also get too deep from the *other* end — attaching a module to a
    /// path that is already itself a module three levels down.
    /// </summary>
    public const int MaxModuleDepth = 3;

    /// <summary>
    /// True when making <paramref name="childId"/> a module of a step inside
    /// <paramref name="parentId"/> would close a loop — either directly (a path claiming itself)
    /// or through an existing chain.
    ///
    /// <paramref name="childToParent"/> maps a module roadmap id to the id of the roadmap whose
    /// step claims it, i.e. it walks *upwards*. Walking up from the proposed parent must never
    /// reach the proposed child.
    /// </summary>
    public static bool CreatesModuleCycle(IReadOnlyDictionary<int, int> childToParent, int parentId, int childId)
    {
        if (parentId == childId) return true;

        var seen = new HashSet<int>();
        var current = parentId;
        while (seen.Add(current) && childToParent.TryGetValue(current, out var up))
        {
            if (up == childId) return true;
            current = up;
        }
        return false;
    }

    /// <summary>
    /// How many roadmaps sit above <paramref name="roadmapId"/> in the module chain, so 0 for a
    /// top-level path. Bounded by <see cref="MaxModuleDepth"/> rather than trusting the data:
    /// this runs on the read path, where a bad row must degrade rather than hang.
    /// </summary>
    public static int ModuleDepth(IReadOnlyDictionary<int, int> childToParent, int roadmapId)
    {
        var depth = 0;
        var seen = new HashSet<int>();
        var current = roadmapId;
        while (depth <= MaxModuleDepth && seen.Add(current) && childToParent.TryGetValue(current, out var up))
        {
            depth++;
            current = up;
        }
        return depth;
    }
}
