using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace DancePlatform.API.Services;

public class OllamaService : IOllamaService
{
    private readonly HttpClient _http;
    private readonly string _model;
    private readonly ILogger<OllamaService> _logger;

    public OllamaService(HttpClient http, IConfiguration config, ILogger<OllamaService> logger)
    {
        _http = http;
        _model = config["Ollama:Model"] ?? "llama3.2";
        _logger = logger;
    }

    public async Task<OllamaClassification?> ClassifyDanceAsync(
        string danceName,
        IEnumerable<string> availableStyles,
        IEnumerable<string> availableMusicalStyles)
    {
        var styles = string.Join(", ", availableStyles);
        var musicStyles = string.Join(", ", availableMusicalStyles);

        var prompt = $"""
            You are a dance classification expert. Classify this dance move for a learning platform.

            Available dance styles: {(styles.Length > 0 ? styles : "(none defined yet)")}
            Available musical styles: {(musicStyles.Length > 0 ? musicStyles : "(none defined yet)")}

            Dance name: "{danceName}"

            Return ONLY valid JSON, no explanation:
            {{
              "dance_styles": [list of matching names from Available dance styles, or []],
              "musical_styles": [list of matching names from Available musical styles, or []],
              "difficulty": "Beginner" or "Intermediate" or "Advanced" or "None",
              "description": "one sentence describing what this move is"
            }}

            Use ONLY names exactly as listed above. Use [] if nothing matches.
            """;

        var payload = JsonSerializer.Serialize(new
        {
            model = _model,
            prompt,
            stream = false,
            format = "json"
        });

        try
        {
            var response = await _http.PostAsync("/api/generate",
                new StringContent(payload, Encoding.UTF8, "application/json"));

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogWarning("Ollama returned {Status} for '{Dance}'", response.StatusCode, danceName);
                return null;
            }

            var json = await response.Content.ReadAsStringAsync();
            var envelope = JsonSerializer.Deserialize<OllamaGenerateResponse>(json);
            if (envelope?.Response is null) return null;

            var result = JsonSerializer.Deserialize<OllamaResult>(envelope.Response);
            if (result is null) return null;

            var validDifficulties = new[] { "Beginner", "Intermediate", "Advanced", "None" };
            var difficulty = validDifficulties.Contains(result.Difficulty) ? result.Difficulty : "None";

            return new OllamaClassification(
                result.DanceStyles ?? [],
                result.MusicalStyles ?? [],
                difficulty,
                result.Description ?? ""
            );
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Ollama unreachable or failed for '{Dance}' — skipping classification", danceName);
            return null;
        }
    }

    private class OllamaGenerateResponse
    {
        [JsonPropertyName("response")] public string? Response { get; set; }
    }

    private class OllamaResult
    {
        [JsonPropertyName("dance_styles")] public List<string>? DanceStyles { get; set; }
        [JsonPropertyName("musical_styles")] public List<string>? MusicalStyles { get; set; }
        [JsonPropertyName("difficulty")] public string? Difficulty { get; set; }
        [JsonPropertyName("description")] public string? Description { get; set; }
    }
}
