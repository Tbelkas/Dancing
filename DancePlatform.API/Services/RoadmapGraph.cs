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
}
