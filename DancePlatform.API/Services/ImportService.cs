using System.Text.RegularExpressions;
using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Dance;
using DancePlatform.API.DTOs.Import;
using DancePlatform.API.Models;

namespace DancePlatform.API.Services;

public class ImportService : IImportService
{
    private readonly AppDbContext _db;

    // Captures the 11-char video ID from any standard YouTube URL form
    private static readonly Regex YoutubeRegex = new(
        @"(?:youtube\.com/watch\?(?:[^&]*&)*v=|youtu\.be/)([A-Za-z0-9_-]{11})",
        RegexOptions.Compiled);

    // Matches "Dance Name [MM:SS]" or "Dance Name [H:MM:SS]", with optional leading number/bullet
    private static readonly Regex EntryRegex = new(
        @"^\s*(?:\d+[\.\)]|\*|-)?\s*(.+?)\s*\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*$",
        RegexOptions.Compiled | RegexOptions.Multiline);

    public ImportService(AppDbContext db) => _db = db;

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

        for (int i = 0; i < entries.Count; i++)
        {
            var (name, startSeconds) = entries[i];
            int? endSeconds = i + 1 < entries.Count ? entries[i + 1].Start - 1 : null;

            try
            {
                var dance = new Dance { Name = name };
                _db.Dances.Add(dance);
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
