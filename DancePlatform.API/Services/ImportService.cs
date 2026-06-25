using System.Text.RegularExpressions;
using DancePlatform.API.DTOs.Dance;
using DancePlatform.API.DTOs.Import;
using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.Services;

public class ImportService : IImportService
{
    private readonly IDanceService _danceService;
    private readonly IVideoService _videoService;
    private readonly IStyleService _styleService;
    private readonly IMusicalStyleService _musicalStyleService;
    private readonly IOllamaService _ollama;

    // Captures the 11-char video ID from any standard YouTube URL form
    private static readonly Regex YoutubeRegex = new(
        @"(?:youtube\.com/watch\?(?:[^&]*&)*v=|youtu\.be/)([A-Za-z0-9_-]{11})",
        RegexOptions.Compiled);

    // Matches "Dance Name [MM:SS]" or "Dance Name [H:MM:SS]", with optional leading number/bullet
    private static readonly Regex EntryRegex = new(
        @"^\s*(?:\d+[\.\)]|\*|-)?\s*(.+?)\s*\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*$",
        RegexOptions.Compiled | RegexOptions.Multiline);

    public ImportService(
        IDanceService danceService,
        IVideoService videoService,
        IStyleService styleService,
        IMusicalStyleService musicalStyleService,
        IOllamaService ollama)
    {
        _danceService = danceService;
        _videoService = videoService;
        _styleService = styleService;
        _musicalStyleService = musicalStyleService;
        _ollama = ollama;
    }

    public async Task<BulkImportResult> ImportDancesAsync(BulkImportRequest request)
    {
        var result = new BulkImportResult();

        var youtubeMatch = YoutubeRegex.Match(request.Text);
        result.VideoId = youtubeMatch.Success ? youtubeMatch.Groups[1].Value : null;

        var entries = EntryRegex.Matches(request.Text)
            .Select(m => (Name: m.Groups[1].Value.Trim(), Start: ParseTimestamp(m.Groups[2].Value)))
            .ToList();

        if (entries.Count == 0)
        {
            result.Errors.Add("No dance entries found. Expected format: 'Dance Name [MM:SS]'");
            return result;
        }

        var allStyles = await _styleService.GetAllAsync();
        var allMusicalStyles = await _musicalStyleService.GetAllAsync();
        var stylesByName = allStyles.ToDictionary(s => s.Name.ToLower(), s => s.Id);
        var musicByName = allMusicalStyles.ToDictionary(ms => ms.Name.ToLower(), ms => ms.Id);

        var classifications = await Task.WhenAll(entries.Select(e =>
            _ollama.ClassifyDanceAsync(e.Name, allStyles.Select(s => s.Name), allMusicalStyles.Select(ms => ms.Name))));

        for (int i = 0; i < entries.Count; i++)
        {
            var (name, startSeconds) = entries[i];
            int? endSeconds = i + 1 < entries.Count ? entries[i + 1].Start - 1 : null;
            var classification = classifications[i];

            try
            {
                var styleIds = classification?.DanceStyles?
                    .Where(s => stylesByName.ContainsKey(s.ToLower()))
                    .Select(s => stylesByName[s.ToLower()])
                    .ToList() ?? [];

                var musicalStyleIds = classification?.MusicalStyles?
                    .Where(ms => musicByName.ContainsKey(ms.ToLower()))
                    .Select(ms => musicByName[ms.ToLower()])
                    .ToList() ?? [];

                var dance = await _danceService.CreateAsync(new CreateDanceRequest
                {
                    Name = name,
                    Description = classification?.Description is { Length: > 0 } d ? d : null,
                    Difficulty = classification?.Difficulty ?? "None",
                    StyleIds = styleIds,
                    MusicalStyleIds = musicalStyleIds
                });

                if (result.VideoId is not null)
                {
                    await _videoService.CreateAsync(new CreateVideoRequest
                    {
                        Title = name,
                        VideoId = result.VideoId,
                        Platform = "youtube",
                        DanceId = dance.Id,
                        StartTime = startSeconds,
                        EndTime = endSeconds,
                        Segments = []
                    }, null);
                }

                result.Created.Add(dance);
            }
            catch (Exception ex)
            {
                result.Errors.Add($"Failed to create '{name}': {ex.Message}");
            }
        }

        return result;
    }

    public async Task<VideoDto?> ImportYoutubeVideoAsync(YoutubeVideoImportRequest request)
    {
        var match = YoutubeRegex.Match(request.YoutubeUrl);
        if (!match.Success) return null;

        return await _videoService.CreateAsync(new CreateVideoRequest
        {
            Title = request.Title,
            VideoId = match.Groups[1].Value,
            Platform = "youtube",
            VideoType = request.VideoType,
            DanceId = request.DanceId,
            StartTime = request.StartTime,
            EndTime = request.EndTime,
            Segments = request.Segments
        }, null);
    }

    private static int ParseTimestamp(string ts)
    {
        var parts = ts.Split(':');
        return parts.Length switch
        {
            2 => int.Parse(parts[0]) * 60 + int.Parse(parts[1]),
            3 => int.Parse(parts[0]) * 3600 + int.Parse(parts[1]) * 60 + int.Parse(parts[2]),
            _ => 0
        };
    }
}
