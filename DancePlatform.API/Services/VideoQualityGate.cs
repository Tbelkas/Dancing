using System.Text.RegularExpressions;
using DancePlatform.API.Models;

namespace DancePlatform.API.Services;

/// <summary>
/// The cheap half of the intake rubric, for the API path.
///
/// scripts/video_gate.py is the full three-tier version and owns the thresholds;
/// this is deliberately only its tier 0 - the checks that need nothing but the row
/// being inserted and a couple of counts. The expensive tiers (yt-dlp metadata, a
/// Whisper transcript) take seconds to tens of seconds and would stall the admin
/// add-video form, so they run out of band and stamp the row afterwards.
///
/// Videos added through the API are admitted regardless of score: someone has
/// already looked at them. The score and flags are recorded so a bad one can be
/// found later, in the dashboard's Intake tab.
/// </summary>
public static class VideoQualityGate
{
    public const float AdmitThreshold = 0.65f;

    private static readonly Regex Promo = new(
        @"(enroll|sign\s?up|link in bio|full course|masterclass|discount|promo code|patreon|subscribe now|join my|book now)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    // Words too generic to prove a title matches a dance. Mirrors STOP in video_gate.py.
    private static readonly HashSet<string> Stop = new(StringComparer.OrdinalIgnoreCase)
    {
        "the", "a", "an", "and", "of", "to", "in", "on", "with", "for", "dance",
        "dancing", "tutorial", "how", "step", "steps", "move", "moves", "basic",
        "beginner", "easy", "learn", "lesson"
    };

    /// <param name="sameClipOtherDances">
    /// How many OTHER dances already carry this exact clip. A montage legitimately
    /// spans several; the same clip on many dances with no start time is the
    /// mis-sourcing signature instead.
    /// </param>
    public static (float Score, string? Flags) Grade(
        Video video, string? danceName, string? styleNames, int sameClipOtherDances)
    {
        var flags = new List<string>();
        var score = 1.0f;
        var isSlice = video.StartTime is not null;

        if (!isSlice && video.DurationSeconds is > 0 and < 30)
        {
            score -= 0.25f;
            flags.Add("too-short");
        }

        if (sameClipOtherDances >= 3 && !isSlice)
        {
            score -= 0.25f;
            flags.Add($"same-clip-on-{sameClipOtherDances}-dances");
        }

        // A montage window is titled for the whole video, not for the one move this
        // slice teaches, so comparing the two there yields nothing but noise.
        var montage = isSlice || sameClipOtherDances >= 3;
        if (!montage)
        {
            var danceT = Tokens(danceName);
            var titleT = Tokens(video.Title);
            var styleT = Tokens(styleNames);
            if (danceT.Count > 0 && titleT.Count > 0
                && !NameMatches(danceName, video.Title) && !styleT.Overlaps(titleT))
            {
                score -= 0.30f;
                flags.Add("title-dance-mismatch");
            }
        }

        if (!string.IsNullOrEmpty(video.Title) && Promo.IsMatch(video.Title))
        {
            score -= 0.20f;
            flags.Add("promo-title");
        }

        score = Math.Clamp(score, 0f, 1f);
        return (score, flags.Count == 0 ? null : string.Join(",", flags));
    }

    /// <summary>
    /// Does <paramref name="text"/> name this dance? Tolerant of how the same move gets
    /// written. Mirrors name_matches() in scripts/video_gate.py — keep the two in step.
    ///
    /// A bare token intersection accuses correct videos, because move names are not
    /// written consistently: "Waacking" against "Beginner Whacking Tutorial" is one
    /// substitution, and "Breakdance" against "10 Easy Break Dance TOPROCKS" differs by
    /// a space that Tokens() cannot see, because "dance" is a stop word. On the import
    /// path that mismatch is not cosmetic — it costs 0.30 and quarantines a good video.
    ///
    /// Still strict about genuinely different moves: Tendu does not match a plié
    /// combination, and Blade does not match a backspin.
    /// </summary>
    private static bool NameMatches(string? danceName, string? text)
    {
        var danceT = Tokens(danceName);
        var textT = Tokens(text);
        if (danceT.Overlaps(textT)) return true;

        var flatText = Flatten(text);
        foreach (var w in danceT)
            if (w.Length >= 5 && flatText.Contains(w, StringComparison.Ordinal)) return true;

        var flatDance = Flatten(danceName);
        if (flatDance.Length >= 5 && flatText.Contains(flatDance, StringComparison.Ordinal))
            return true;

        foreach (var w in danceT)
        {
            if (w.Length < 6) continue;
            foreach (var t in textT)
                if (Math.Abs(w.Length - t.Length) <= 2 && Similarity(w, t) >= 0.85)
                    return true;
        }
        return false;
    }

    private static string Flatten(string? s) =>
        s is null ? "" : Regex.Replace(s.ToLowerInvariant(), "[^a-z0-9]+", "");

    /// <summary>Normalised Levenshtein similarity, matching difflib's ratio closely
    /// enough for the one-substitution cases this guards against.</summary>
    private static double Similarity(string a, string b)
    {
        if (a.Length == 0 || b.Length == 0) return 0;
        var prev = new int[b.Length + 1];
        var cur = new int[b.Length + 1];
        for (var j = 0; j <= b.Length; j++) prev[j] = j;
        for (var i = 1; i <= a.Length; i++)
        {
            cur[0] = i;
            for (var j = 1; j <= b.Length; j++)
                cur[j] = Math.Min(Math.Min(cur[j - 1] + 1, prev[j] + 1),
                                  prev[j - 1] + (a[i - 1] == b[j - 1] ? 0 : 1));
            (prev, cur) = (cur, prev);
        }
        return 1.0 - (double)prev[b.Length] / Math.Max(a.Length, b.Length);
    }

    private static HashSet<string> Tokens(string? s)
    {
        var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (string.IsNullOrWhiteSpace(s)) return set;
        foreach (Match m in Regex.Matches(s.ToLowerInvariant(), "[a-z0-9]+"))
        {
            var w = m.Value;
            if (w.Length > 2 && !Stop.Contains(w)) set.Add(Stem(w));
        }
        return set;
    }

    // "Old Way Switches" and "Front Switch and Side Switch" are the same move; a bare
    // set intersection calls that a mismatch. Mirrors _stem() in video_gate.py.
    private static string Stem(string w)
    {
        if (w.EndsWith("ies") && w.Length >= 6) return w[..^3] + "y";
        if (w.EndsWith("es") && w.Length >= 5) return w[..^2];
        if (w.EndsWith("s") && w.Length >= 4) return w[..^1];
        return w;
    }
}
