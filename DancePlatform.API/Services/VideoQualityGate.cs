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
                && !danceT.Overlaps(titleT) && !styleT.Overlaps(titleT))
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
