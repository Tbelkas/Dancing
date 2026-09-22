using System.Text.Json;

namespace DancePlatform.API.Services;

/// <summary>
/// Reads a video's author off the platform's public oEmbed endpoint — keyless, no quota, and
/// it answers in one small JSON document. YouTube and TikTok have one; Instagram's needs an app
/// token, so an Instagram video stays uncredited. Every failure path returns null: a missing
/// credit must never stop a video being added.
/// </summary>
public class VideoChannelService : IVideoChannelService
{
    private readonly HttpClient _http;
    private readonly ILogger<VideoChannelService> _logger;

    public VideoChannelService(HttpClient http, ILogger<VideoChannelService> logger)
    {
        _http = http;
        _logger = logger;
    }

    public async Task<(string Name, string Url)?> LookupAsync(string platform, string videoId, CancellationToken ct = default)
    {
        var endpoint = platform switch
        {
            "youtube" => "https://www.youtube.com/oembed?format=json&url=" +
                         Uri.EscapeDataString($"https://www.youtube.com/watch?v={videoId}"),
            "tiktok" => "https://www.tiktok.com/oembed?url=" +
                        Uri.EscapeDataString($"https://www.tiktok.com/video/{videoId}"),
            _ => null
        };
        if (endpoint is null) return null;

        try
        {
            using var res = await _http.GetAsync(endpoint, ct);
            if (!res.IsSuccessStatusCode) return null;
            using var doc = JsonDocument.Parse(await res.Content.ReadAsStringAsync(ct));
            var name = doc.RootElement.TryGetProperty("author_name", out var n) ? n.GetString()?.Trim() : null;
            var url = doc.RootElement.TryGetProperty("author_url", out var u) ? u.GetString()?.Trim() : null;
            if (string.IsNullOrEmpty(name) || string.IsNullOrEmpty(url)) return null;
            return (name, url);
        }
        catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException or JsonException)
        {
            _logger.LogInformation("Channel lookup failed for {Platform}/{VideoId}: {Message}", platform, videoId, ex.Message);
            return null;
        }
    }
}
