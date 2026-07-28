using System.Text.Json;
using System.Text.RegularExpressions;
using DancePlatform.API.DTOs.Video;
using Microsoft.Extensions.Caching.Memory;

namespace DancePlatform.API.Services;

/// <summary>
/// Pulls a YouTube video's own chapters off its watch page. Two sources, in order of trust:
/// the chapter bar YouTube renders (creator-set or auto-generated), then the timestamp list
/// in the description. Both live in the page's embedded JSON, so this is scraping — it is
/// deliberately best-effort and every failure path yields "no chapters" rather than an error.
/// </summary>
public class YoutubeChapterService : IYoutubeChapterService
{
    private readonly HttpClient _http;
    private readonly IMemoryCache _cache;
    private readonly ILogger<YoutubeChapterService> _logger;

    private static readonly Regex VideoIdRegex = new(@"^[A-Za-z0-9_-]{11}$", RegexOptions.Compiled);

    // The chapter bar's entries, as embedded in ytInitialData.
    private static readonly Regex ChapterRendererRegex = new(
        @"""chapterRenderer"":\{""title"":\{""simpleText"":""((?:[^""\\]|\\.)*)""\},""timeRangeStartMillis"":(\d+)",
        RegexOptions.Compiled);

    // m:ss, mm:ss or h:mm:ss, not glued to further digits (so "1234:56" or a bitrate isn't a time).
    private static readonly Regex TimestampRegex = new(
        @"(?<!\d)(?:(\d{1,3}):)?(\d{1,2}):(\d{2})(?!\d)", RegexOptions.Compiled);

    // Bullets, dashes and list numbering that wrap a chapter label in a description line.
    private static readonly Regex LabelEdgeRegex = new(
        @"^[\s\-–—•*·:|>#\[\]\(\)]+|[\s\-–—•*·:|<#\[\]\(\)]+$", RegexOptions.Compiled);
    private static readonly Regex LeadingNumberRegex = new(@"^\d{1,2}[\.\)]\s*", RegexOptions.Compiled);

    private const int MaxChapters = 60;
    private static readonly TimeSpan HitTtl = TimeSpan.FromHours(6);
    private static readonly TimeSpan MissTtl = TimeSpan.FromMinutes(30);

    public YoutubeChapterService(HttpClient http, IMemoryCache cache, ILogger<YoutubeChapterService> logger)
    {
        _http = http;
        _cache = cache;
        _logger = logger;
    }

    public async Task<YoutubeChaptersDto> GetChaptersAsync(string videoId, CancellationToken ct = default)
    {
        if (!VideoIdRegex.IsMatch(videoId))
            return new YoutubeChaptersDto { VideoId = videoId };

        if (_cache.TryGetValue($"yt:chapters:{videoId}", out YoutubeChaptersDto? cached) && cached is not null)
            return cached;

        var result = await FetchAsync(videoId, ct);
        _cache.Set($"yt:chapters:{videoId}", result, result.Chapters.Count > 0 ? HitTtl : MissTtl);
        return result;
    }

    private async Task<YoutubeChaptersDto> FetchAsync(string videoId, CancellationToken ct)
    {
        var result = new YoutubeChaptersDto { VideoId = videoId };

        string html;
        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, $"https://www.youtube.com/watch?v={videoId}&hl=en");
            using var response = await _http.SendAsync(request, ct);
            if (!response.IsSuccessStatusCode)
            {
                if (_logger.IsEnabled(LogLevel.Information))
                    _logger.LogInformation("YouTube chapter lookup for {VideoId} returned {Status}", videoId, response.StatusCode);
                return result;
            }
            html = await response.Content.ReadAsStringAsync(ct);
        }
        catch (Exception ex)
        {
            if (_logger.IsEnabled(LogLevel.Information))
                _logger.LogInformation(ex, "YouTube chapter lookup for {VideoId} failed", videoId);
            return result;
        }

        result.Duration = ReadDuration(html);

        var chapters = ReadChapterBar(html);
        var source = "chapters";
        if (chapters.Count < 2)
        {
            chapters = ReadDescriptionTimestamps(html);
            source = "description";
        }

        chapters = Normalize(chapters, result.Duration);
        if (chapters.Count < 2) return result;

        result.Chapters = chapters;
        result.Source = source;
        return result;
    }

    /// <summary>Video length, from the player response embedded in the watch page.</summary>
    private static int? ReadDuration(string html)
    {
        var json = ExtractEmbeddedObject(html, "ytInitialPlayerResponse");
        if (json is null) return null;
        try
        {
            using var doc = JsonDocument.Parse(json);
            if (doc.RootElement.TryGetProperty("videoDetails", out var details) &&
                details.TryGetProperty("lengthSeconds", out var length) &&
                int.TryParse(length.GetString(), out var seconds) && seconds > 0)
                return seconds;
        }
        catch (JsonException) { /* page shape changed — duration is optional */ }
        return null;
    }

    private static List<VideoSegmentDto> ReadChapterBar(string html) =>
        ChapterRendererRegex.Matches(html)
            .Select(m => new VideoSegmentDto
            {
                Label = UnescapeJsonString(m.Groups[1].Value),
                StartTime = (int)(long.Parse(m.Groups[2].Value) / 1000)
            })
            .ToList();

    /// <summary>Chapters as most creators actually write them: one "0:00 Intro" line per section.</summary>
    private static List<VideoSegmentDto> ReadDescriptionTimestamps(string html)
    {
        var description = ReadDescription(html);
        if (string.IsNullOrWhiteSpace(description)) return new List<VideoSegmentDto>();

        var found = new List<VideoSegmentDto>();
        foreach (var line in description.Split('\n'))
        {
            var match = TimestampRegex.Match(line);
            if (!match.Success) continue;

            // The label sits on one side of the timestamp — "0:00 Intro" or "Intro - 0:00".
            var after = CleanLabel(line[(match.Index + match.Length)..]);
            var before = CleanLabel(line[..match.Index]);
            var label = after.Length > 0 ? after : before;
            if (label.Length == 0 || label.Length > 80) continue;

            var hours = match.Groups[1].Success ? int.Parse(match.Groups[1].Value) : 0;
            found.Add(new VideoSegmentDto
            {
                Label = label,
                StartTime = hours * 3600 + int.Parse(match.Groups[2].Value) * 60 + int.Parse(match.Groups[3].Value)
            });
        }
        return found;
    }

    private static string? ReadDescription(string html)
    {
        var json = ExtractEmbeddedObject(html, "ytInitialPlayerResponse");
        if (json is null) return null;
        try
        {
            using var doc = JsonDocument.Parse(json);
            return doc.RootElement.TryGetProperty("videoDetails", out var details) &&
                   details.TryGetProperty("shortDescription", out var text)
                ? text.GetString()
                : null;
        }
        catch (JsonException) { return null; }
    }

    /// <summary>
    /// Drops anything out of order (descriptions often carry a second, unrelated timestamp list)
    /// and gives each chapter the next one's start as its end, the last one the video duration.
    /// </summary>
    private static List<VideoSegmentDto> Normalize(List<VideoSegmentDto> chapters, int? duration)
    {
        var ordered = new List<VideoSegmentDto>();
        foreach (var chapter in chapters)
        {
            if (ordered.Count > 0 && chapter.StartTime <= ordered[^1].StartTime) continue;
            if (duration is int d && chapter.StartTime >= d) continue;
            ordered.Add(chapter);
            if (ordered.Count == MaxChapters) break;
        }

        for (var i = 0; i < ordered.Count; i++)
            ordered[i].EndTime = i + 1 < ordered.Count ? ordered[i + 1].StartTime : duration;

        return ordered;
    }

    /// <summary>
    /// Lifts one embedded JSON object out of the watch page HTML by matching braces from the
    /// first one after <paramref name="marker"/>, skipping braces inside string literals.
    /// </summary>
    private static string? ExtractEmbeddedObject(string html, string marker)
    {
        var markerIndex = html.IndexOf(marker, StringComparison.Ordinal);
        if (markerIndex < 0) return null;
        var start = html.IndexOf('{', markerIndex + marker.Length);
        if (start < 0) return null;

        var depth = 0;
        var inString = false;
        var escaped = false;
        for (var i = start; i < html.Length; i++)
        {
            var c = html[i];
            if (escaped) { escaped = false; continue; }
            if (inString)
            {
                if (c == '\\') escaped = true;
                else if (c == '"') inString = false;
                continue;
            }
            if (c == '"') inString = true;
            else if (c == '{') depth++;
            else if (c == '}' && --depth == 0) return html[start..(i + 1)];
        }
        return null;
    }

    /// <summary>Strips the punctuation, bullets and "1)" numbering a description line wraps its label in.</summary>
    private static string CleanLabel(string raw)
    {
        var label = LabelEdgeRegex.Replace(raw, string.Empty);
        label = LeadingNumberRegex.Replace(label, string.Empty);
        return LabelEdgeRegex.Replace(label, string.Empty);
    }

    private static string UnescapeJsonString(string raw)
    {
        try { return JsonSerializer.Deserialize<string>($"\"{raw}\"") ?? raw; }
        catch (JsonException) { return raw; }
    }
}
