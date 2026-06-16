namespace DancePlatform.API.Services;

public record OllamaClassification(
    List<string> DanceStyles,
    List<string> MusicalStyles,
    string Difficulty,
    string Description
);

public interface IOllamaService
{
    Task<OllamaClassification?> ClassifyDanceAsync(
        string danceName,
        IEnumerable<string> availableStyles,
        IEnumerable<string> availableMusicalStyles);
}
