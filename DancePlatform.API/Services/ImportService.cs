using System.Text.RegularExpressions;
using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Dance;
using DancePlatform.API.DTOs.Import;
using DancePlatform.API.DTOs.Video;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class ImportService : IImportService
{
    private readonly AppDbContext _db;
    private readonly IVideoService _videoService;
    private readonly IOllamaService _ollama;

    // Captures the 11-char video ID from any standard YouTube URL form
    private static readonly Regex YoutubeRegex = new(
        @"(?:youtube\.com/watch\?(?:[^&]*&)*v=|youtu\.be/)([A-Za-z0-9_-]{11})",
        RegexOptions.Compiled);

    // Matches "Dance Name [MM:SS]" or "Dance Name [H:MM:SS]", with optional leading number/bullet
    private static readonly Regex EntryRegex = new(
        @"^\s*(?:\d+[\.\)]|\*|-)?\s*(.+?)\s*\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*$",
        RegexOptions.Compiled | RegexOptions.Multiline);

    public ImportService(AppDbContext db, IVideoService videoService, IOllamaService ollama)
    {
        _db = db;
        _videoService = videoService;
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

        // Load styles once for Ollama classification
        var allStyles = await _db.Styles.AsNoTracking().ToListAsync();
        var allMusicalStyles = await _db.MusicalStyles.AsNoTracking().ToListAsync();
        var stylesByName = allStyles.ToDictionary(s => s.Name.ToLower(), s => s.Id);
        var musicByName = allMusicalStyles.ToDictionary(ms => ms.Name.ToLower(), ms => ms.Id);

        for (int i = 0; i < entries.Count; i++)
        {
            var (name, startSeconds) = entries[i];
            int? endSeconds = i + 1 < entries.Count ? entries[i + 1].Start - 1 : null;

            try
            {
                var baseSlug = SlugGenerator.Slugify(name);
                var slug = baseSlug;
                for (var n = 2; await _db.Dances.AnyAsync(d => d.Slug == slug); n++)
                    slug = $"{baseSlug}-{n}";

                // Classify with Ollama (falls back to empty if unreachable)
                var classification = await _ollama.ClassifyDanceAsync(
                    name,
                    allStyles.Select(s => s.Name),
                    allMusicalStyles.Select(ms => ms.Name));

                var dance = new Dance
                {
                    Name = name,
                    Slug = slug,
                    Description = classification?.Description is { Length: > 0 } d ? d : null,
                    Difficulty = ParseDifficulty(classification?.Difficulty)
                };
                _db.Dances.Add(dance);
                await _db.SaveChangesAsync();

                // Assign dance styles
                if (classification?.DanceStyles is { Count: > 0 } danceStyles)
                {
                    foreach (var styleName in danceStyles)
                    {
                        if (stylesByName.TryGetValue(styleName.ToLower(), out var styleId))
                            _db.DanceStyles.Add(new DanceStyle { DanceId = dance.Id, StyleId = styleId });
                    }
                }

                // Assign musical styles
                if (classification?.MusicalStyles is { Count: > 0 } musicStyles)
                {
                    foreach (var musicName in musicStyles)
                    {
                        if (musicByName.TryGetValue(musicName.ToLower(), out var musicId))
                            _db.DanceMusicalStyles.Add(new DanceMusicalStyle { DanceId = dance.Id, MusicalStyleId = musicId });
                    }
                }

                await _db.SaveChangesAsync();

                if (result.VideoId is not null)
                {
                    _db.Videos.Add(new Video
                    {
                        Title = name,
                        VideoId = result.VideoId,
                        Platform = "youtube",
                        DanceId = dance.Id,
                        StartTime = startSeconds,
                        EndTime = endSeconds
                    });
                    await _db.SaveChangesAsync();
                }

                result.Created.Add(new DanceDto
                {
                    Id = dance.Id,
                    Name = dance.Name,
                    Slug = dance.Slug,
                    DateAdded = dance.DateAdded,
                    Difficulty = dance.Difficulty.ToString(),
                    VideoCount = result.VideoId is not null ? 1 : 0
                });
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
        });
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

    private static DifficultyLevel ParseDifficulty(string? value) => value switch
    {
        "Beginner" => DifficultyLevel.Beginner,
        "Intermediate" => DifficultyLevel.Intermediate,
        "Advanced" => DifficultyLevel.Advanced,
        _ => DifficultyLevel.None
    };
}
